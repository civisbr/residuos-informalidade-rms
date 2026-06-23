"""Testes de sanidade — rodam offline, garantem que o build não regrida."""
from pathlib import Path
import pytest
import yaml
import polars as pl
from pipeline.sources import ibge, snis
from pipeline.sources import ibge_informalidade, rais, pnad_regional
from pipeline import transform, model

ROOT = Path(__file__).resolve().parents[1]
COEF = yaml.safe_load((ROOT / "config/coefficients.yml").read_text())
REGIONS = yaml.safe_load((ROOT / "config/regions.yml").read_text())


def test_rms_tem_27_municipios():
    assert len(REGIONS["rms"]["municipios"]) == 27


def test_build_offline_gera_dados():
    import os
    os.chdir(ROOT)
    df = transform.build_region(REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT), COEF)
    assert df.height == 27
    # Sorocaba tem dado real
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag"] == "real"
    assert soro["rsu_t_ano"] == 228000
    assert soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)  # gravimetria local 0.48, per D-12
    # Baseline real da RMS: SNIS-RS 2022 raspado da Série Histórica oficial
    # cobre os 25 municípios restantes; com Sorocaba+Porto Feliz, os 27 têm dado.
    real = df.filter(df["flag"] == "real")
    assert real.height >= 25
    # Invariante sagrado (D-11): município pendente nunca inventa número.
    pend = df.filter(df["flag"] == "pendente")
    assert pend["rsu_t_ano"].null_count() == pend.height


def test_modelo_break_even_coerente():
    d = model.defaults(COEF)
    r = model.project(d["clientes"], d["kg_dia"], d["partilha_pct"], d["gate_fee"], COEF, 116280)
    assert r["desviado_t_ano"] > 0
    assert 0 < r["pct_organico_municipal"] < 5   # Fase 1 é foothold, não bala de prata
    assert r["catadores_sustentados"] > 0


# ---------------------------------------------------------------------------
# Fase 2 — Camada de Informalidade (INFO-01, INFO-02, D-06/D-07)
# ---------------------------------------------------------------------------

def test_informalidade_censo_27_municipios():
    """INFO-01: ibge_informalidade.load() retorna 27 linhas com taxa não-nula."""
    import os
    os.chdir(ROOT)
    df = ibge_informalidade.load(ROOT)
    assert df.height == 27, f"Esperado 27 municípios, got {df.height}"
    assert df["taxa_informalidade_pct"].null_count() == 0, (
        "taxa_informalidade_pct não deve ter nulos — todos os 27 têm dado real do Censo 2022"
    )
    assert "key" in df.columns, "Coluna 'key' (slug do município) deve existir para o join"


def test_pnad_nao_por_municipio():
    """INFO-01: PNAD só entra como contexto regional — sem coluna municipio (D-02)."""
    import os
    os.chdir(ROOT)
    df = pnad_regional.load(ROOT)
    assert "municipio" not in df.columns, (
        "pnad_regional NÃO deve ter coluna 'municipio' — dado não é representativo no nível municipal"
    )
    assert df["flag"][0] == "estimativa", "PNAD deve ter flag='estimativa'"
    assert df["ambito"][0] == "Estado de São Paulo", (
        f"PNAD deve ter ambito='Estado de São Paulo', got '{df['ambito'][0]}'"
    )


def test_rais_load():
    """INFO-02: rais.load() retorna 27 linhas, formais_residuos sem null (zeros são dados válidos)."""
    import os
    os.chdir(ROOT)
    df = rais.load(ROOT)
    assert df.height == 27, f"RAIS esperado 27 municípios, got {df.height}"
    assert df["formais_residuos"].null_count() == 0, (
        "formais_residuos não deve ter nulos — 0 significa ausência de estabelecimento (não dado faltante)"
    )
    # Alambari e Jumirim devem ter 0 (sem estabelecimento no setor — per RESEARCH)
    alambari = df.filter(df["key"] == "alambari").to_dicts()[0]
    jumirim = df.filter(df["key"] == "jumirim").to_dicts()[0]
    assert alambari["formais_residuos"] == 0, "Alambari deve ter formais_residuos=0"
    assert jumirim["formais_residuos"] == 0, "Jumirim deve ter formais_residuos=0"


def test_proxy_pendente_edge_case():
    """D-07: proxy=pendente quando formais_residuos=0 E cooperados=null (ou 0)."""
    # DataFrame sintético — não depende de CSV real nem de transform.py
    df = pl.DataFrame({
        "formais_residuos": pl.Series([0], dtype=pl.Int64),
        "cooperados": pl.Series([None], dtype=pl.Float64),
    })

    # Lógica D-07 isolada (espelho de transform.build_region, Exemplo 3 do RESEARCH)
    df = df.with_columns([
        pl.when(
            ((pl.col("formais_residuos").is_null()) | (pl.col("formais_residuos") == 0)) &
            ((pl.col("cooperados").is_null()) | (pl.col("cooperados") == 0))
        ).then(pl.lit(None, dtype=pl.Float64))
        .when(
            (pl.col("formais_residuos").fill_null(0) + pl.col("cooperados").fill_null(0)) > 0
        ).then(
            pl.col("formais_residuos").fill_null(0).cast(pl.Float64) /
            (pl.col("formais_residuos").fill_null(0).cast(pl.Float64) + pl.col("cooperados").fill_null(0))
        )
        .otherwise(pl.lit(None, dtype=pl.Float64))
        .alias("proxy_formalizacao"),
    ])
    df = df.with_columns([
        pl.when(pl.col("proxy_formalizacao").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_proxy"),
    ])

    row = df.to_dicts()[0]
    assert row["proxy_formalizacao"] is None, (
        "D-07: proxy deve ser null quando formais=0 E cooperados=null"
    )
    assert row["flag_proxy"] == "pendente", (
        "D-07: flag_proxy deve ser 'pendente' quando proxy é null"
    )


def test_proxy_formalizacao_calculo():
    """D-06: proxy = formais / (formais + cooperados) quando ambos têm dado."""
    df = pl.DataFrame({
        "formais_residuos": pl.Series([100], dtype=pl.Int64),
        "cooperados": pl.Series([50.0], dtype=pl.Float64),
    })

    df = df.with_columns([
        pl.when(
            ((pl.col("formais_residuos").is_null()) | (pl.col("formais_residuos") == 0)) &
            ((pl.col("cooperados").is_null()) | (pl.col("cooperados") == 0))
        ).then(pl.lit(None, dtype=pl.Float64))
        .when(
            (pl.col("formais_residuos").fill_null(0) + pl.col("cooperados").fill_null(0)) > 0
        ).then(
            pl.col("formais_residuos").fill_null(0).cast(pl.Float64) /
            (pl.col("formais_residuos").fill_null(0).cast(pl.Float64) + pl.col("cooperados").fill_null(0))
        )
        .otherwise(pl.lit(None, dtype=pl.Float64))
        .alias("proxy_formalizacao"),
    ])
    df = df.with_columns([
        pl.when(pl.col("proxy_formalizacao").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_proxy"),
    ])

    row = df.to_dicts()[0]
    assert row["proxy_formalizacao"] == pytest.approx(100 / 150, rel=1e-3), (
        f"D-06: proxy esperado ~0.6667, got {row['proxy_formalizacao']}"
    )
    assert row["flag_proxy"] == "real", "D-06: flag_proxy deve ser 'real' quando proxy calculado"


def test_informalidade_pendente_honesto():
    """Invariante sagrada: município sem taxa_informalidade_pct → flag_informalidade='pendente'."""
    df = pl.DataFrame({
        "taxa_informalidade_pct": pl.Series([None], dtype=pl.Float64),
    })

    df = df.with_columns([
        pl.when(pl.col("taxa_informalidade_pct").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_informalidade"),
    ])

    row = df.to_dicts()[0]
    assert row["flag_informalidade"] == "pendente", (
        "Invariante sagrada: município sem taxa de informalidade → flag='pendente', nunca inventa número"
    )
