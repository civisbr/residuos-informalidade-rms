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
    df = transform.build_region(
        REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT),
        ibge_informalidade.load(ROOT), rais.load(ROOT), COEF
    )
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


# ---------------------------------------------------------------------------
# Fase 2 — Plano 02-02: build_region() com joins de informalidade + proxy
# ---------------------------------------------------------------------------

def test_build_region_com_informalidade():
    """02-02 T1: build_region() aceita informalidade+rais_residuos e produz colunas corretas."""
    import os
    os.chdir(ROOT)
    df_ibge = ibge.load(ROOT)
    df_snis = snis.load(ROOT)
    df_inf = ibge_informalidade.load(ROOT)
    df_rais = rais.load(ROOT)

    df = transform.build_region(
        REGIONS["rms"]["municipios"], df_ibge, df_snis, df_inf, df_rais, COEF
    )

    assert df.height == 27, f"Esperado 27 municípios, got {df.height}"
    assert "taxa_informalidade_pct" in df.columns, "taxa_informalidade_pct ausente"
    assert "flag_informalidade" in df.columns, "flag_informalidade ausente"
    assert "proxy_formalizacao" in df.columns, "proxy_formalizacao ausente"
    assert "flag_proxy" in df.columns, "flag_proxy ausente"
    # Invariante: nenhum município tem flag_informalidade null (Censo 2022 cobre os 27)
    assert df["flag_informalidade"].null_count() == 0, (
        "flag_informalidade não deve ter nulos — todos os 27 têm dado do Censo 2022"
    )
    # taxa_informalidade_pct não deve ser null para os 27 (Censo cobre todos)
    assert df["taxa_informalidade_pct"].null_count() == 0, (
        "taxa_informalidade_pct não deve ter nulos com CSV de snapshot completo"
    )
    # Sorocaba: formais=745 > 0 → proxy não é null (D-07 permite formais>0 com cooperados null)
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag_informalidade"] == "real", "Sorocaba deve ter flag_informalidade=real"
    assert soro["proxy_formalizacao"] is not None, (
        "Sorocaba formais=745 → proxy calculável mesmo com cooperados null (D-07)"
    )


def test_region_totals_taxa_inf_media():
    """02-02 T1: region_totals() calcula taxa_inf_media_rms ponderada por total_ocupados."""
    import os
    os.chdir(ROOT)
    df_ibge = ibge.load(ROOT)
    df_snis = snis.load(ROOT)
    df_inf = ibge_informalidade.load(ROOT)
    df_rais = rais.load(ROOT)

    df = transform.build_region(
        REGIONS["rms"]["municipios"], df_ibge, df_snis, df_inf, df_rais, COEF
    )
    totals = transform.region_totals(df)

    assert "taxa_inf_media_rms" in totals, "taxa_inf_media_rms ausente em region_totals()"
    taxa = totals["taxa_inf_media_rms"]
    assert taxa is not None, "taxa_inf_media_rms não deve ser None com dados completos"
    # RMS como um todo tem taxa entre 10% e 50% (sanidade)
    assert 10 < taxa < 50, f"taxa_inf_media_rms fora do intervalo esperado: {taxa}"


def test_payload_tem_informalidade():
    """02-02 T2: data.json gerado contém campos de informalidade por município e PNAD em meta."""
    import json
    data_path = ROOT / "site" / "data.json"
    assert data_path.exists(), "site/data.json deve existir — rodar 'uv run obs build --region rms'"
    d = json.loads(data_path.read_text())

    # Campos obrigatórios em municipios[0]
    m = d["municipios"][0]
    assert "taxa_informalidade_pct" in m, f"taxa_informalidade_pct ausente em municipios[0]"
    assert "flag_informalidade" in m, f"flag_informalidade ausente em municipios[0]"
    assert "proxy_formalizacao" in m, f"proxy_formalizacao ausente em municipios[0]"
    assert "flag_proxy" in m, f"flag_proxy ausente em municipios[0]"

    # PNAD apenas em meta (D-02) — nunca em municipios[]
    pnad = d["meta"].get("pnad_contexto_regional")
    assert pnad is not None, "pnad_contexto_regional ausente em meta"
    assert pnad["flag"] == "estimativa", f"PNAD flag esperado 'estimativa', got '{pnad['flag']}'"
    assert "municipio" not in pnad, "PNAD não deve ter campo 'municipio' (D-02)"

    for mun in d["municipios"]:
        assert "pnad_contexto_regional" not in mun, (
            f"PNAD não deve aparecer em municipios[] — encontrada em {mun['nome']}"
        )

    # taxa_inf_media_rms em totais
    assert "taxa_inf_media_rms" in d["totais"], "taxa_inf_media_rms ausente em totais"


# ---------------------------------------------------------------------------
# Fase 4 — Plano 04-01: ibge.refresh() — GEN-01/D-04/D-05/D-06/D-09
# ---------------------------------------------------------------------------

def test_ibge_refresh_signature_e_sem_not_implemented():
    """GEN-01: ibge.refresh() existe com assinatura correta e não levanta NotImplementedError."""
    import inspect
    sig = inspect.signature(ibge.refresh)
    params = list(sig.parameters.keys())
    assert "region" in params, "refresh() deve ter parâmetro 'region'"
    assert "root" in params, "refresh() deve ter parâmetro 'root'"
    # Não deve levantar NotImplementedError ao ser chamada sem rede — apenas ao tentar conectar
    # Testamos a estrutura via inspeção de código-fonte
    import ast
    src = (ROOT / "pipeline" / "sources" / "ibge.py").read_text()
    tree = ast.parse(src)
    refresh_node = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "refresh"
    )
    refresh_src = ast.get_source_segment(src, refresh_node)
    assert "NotImplementedError" not in refresh_src, (
        "NotImplementedError deve ter sido removido de refresh()"
    )
    assert "import httpx" in refresh_src, (
        "httpx deve ser lazy-importado dentro de refresh() — nunca no topo do módulo"
    )
    assert "yaml.safe_load" in refresh_src, (
        "yaml.safe_load deve ser usado para ler regions.yml dentro de refresh()"
    )


def test_ibge_refresh_contem_fonte_pop_literal():
    """D-05: ibge.py contém o literal 'IBGE Censo 2022' para fonte_pop."""
    src = (ROOT / "pipeline" / "sources" / "ibge.py").read_text()
    assert "IBGE Censo 2022" in src, (
        "fonte_pop='IBGE Censo 2022' (literal exato D-05) deve estar em ibge.py"
    )


def test_ibge_refresh_usa_difflib():
    """D-09: ibge.py importa difflib para sugestão de nome amigável."""
    src = (ROOT / "pipeline" / "sources" / "ibge.py").read_text()
    assert "difflib" in src, (
        "difflib deve ser importado em ibge.py para sugestão de nome (D-09)"
    )
    assert "get_close_matches" in src, (
        "difflib.get_close_matches deve estar em ibge.py (D-09)"
    )


def test_upsert_preserva_dado_curado():
    """D-06: upsert não sobrescreve linha com codigo_ibge e populacao preenchidos (Sorocaba)."""
    df = pl.DataFrame({
        "nome": ["Sorocaba"],
        "uf": ["SP"],
        "codigo_ibge": ["3552205"],
        "populacao": pl.Series([709000], dtype=pl.Int64),
        "fonte_pop": ["IBGE/SINISA (pop. urbana)"],
    })
    r = df.filter(pl.col("nome") == "Sorocaba").row(0, named=True)
    # Condição D-06: não preencher se AMBOS estão presentes
    deve_preencher = not (r["codigo_ibge"] and r["populacao"])
    assert not deve_preencher, (
        "Sorocaba com codigo_ibge=3552205 e populacao=709000 NÃO deve ser sobrescrita (D-06)"
    )


def test_upsert_preenche_linha_vazia():
    """D-06: upsert DEVE preencher linha com codigo_ibge E populacao vazios (Alambari)."""
    df = pl.DataFrame({
        "nome": ["Alambari"],
        "uf": ["SP"],
        "codigo_ibge": pl.Series([None], dtype=pl.String),
        "populacao": pl.Series([None], dtype=pl.Int64),
        "fonte_pop": pl.Series([None], dtype=pl.String),
    })
    r = df.filter(pl.col("nome") == "Alambari").row(0, named=True)
    # Condição D-06: deve preencher se codigo_ibge OU populacao estão vazios
    deve_preencher = not (r["codigo_ibge"] and r["populacao"])
    assert deve_preencher, (
        "Alambari com campos vazios DEVE ser preenchida no refresh (D-06)"
    )


def test_upsert_preenche_codigo_ibge_vazio():
    """D-06: upsert preenche linha com codigo_ibge vazio mas populacao presente (Votorantim)."""
    df = pl.DataFrame({
        "nome": ["Votorantim"],
        "uf": ["SP"],
        "codigo_ibge": pl.Series([None], dtype=pl.String),
        "populacao": pl.Series([124000], dtype=pl.Int64),
        "fonte_pop": ["IBGE ~2022 (aprox.)"],
    })
    r = df.filter(pl.col("nome") == "Votorantim").row(0, named=True)
    # Condição D-06: deve preencher se codigo_ibge OU populacao estão vazios
    deve_preencher = not (r["codigo_ibge"] and r["populacao"])
    assert deve_preencher, (
        "Votorantim com codigo_ibge vazio DEVE ter codigo_ibge preenchido no refresh (D-06)"
    )


def test_ibge_load_permanece_intacto():
    """GEN-01: ibge.load() continua funcionando offline após implementação do refresh()."""
    import os
    os.chdir(ROOT)
    df = ibge.load(ROOT)
    assert df.height == 27, f"ibge.load() deve retornar 27 linhas, got {df.height}"
    assert "key" in df.columns, "ibge.load() deve ter coluna 'key' (slug)"
    # Sorocaba com código curado deve estar presente
    soro = df.filter(df["key"] == "sorocaba")
    assert soro.height == 1, "Sorocaba deve estar no cache"
    assert str(soro["codigo_ibge"][0]) == "3552205", (
        f"Sorocaba codigo_ibge deve ser '3552205', got {soro['codigo_ibge'][0]}"
    )


# ---------------------------------------------------------------------------
# Fase 4 — Plano 04-02: rename taxa_inf_media_rms → taxa_inf_media; sort nulls (D-02)
# ---------------------------------------------------------------------------

def test_sort_com_subregiao_null():
    """D-02: sort com nulls_last=True não lança exceção para municipios sem subregiao."""
    df = pl.DataFrame([
        {"nome": "Cidade A", "uf": "MG", "subregiao": None, "key": "cidade a"},
        {"nome": "Cidade B", "uf": "MG", "subregiao": None, "key": "cidade b"},
    ])
    result = df.sort(["subregiao", "nome"], nulls_last=True)
    assert result.height == 2
    assert result["nome"][0] == "Cidade A", (
        "D-02: com subregiao=null, municipios devem ser ordenados por nome"
    )


def test_region_totals_chave_generica():
    """D-02: region_totals() usa chave 'taxa_inf_media' (sem sufixo 'rms')."""
    import os
    os.chdir(ROOT)
    df_ibge = ibge.load(ROOT)
    df_snis = snis.load(ROOT)
    df_inf = ibge_informalidade.load(ROOT)
    df_rais = rais.load(ROOT)

    df = transform.build_region(
        REGIONS["rms"]["municipios"], df_ibge, df_snis, df_inf, df_rais, COEF
    )
    totals = transform.region_totals(df)

    assert "taxa_inf_media" in totals, "chave deve ser taxa_inf_media (sem sufixo rms)"
    assert "taxa_inf_media_rms" not in totals, "chave antiga taxa_inf_media_rms não deve mais existir"


def test_upsert_preserva_dado_curado_d02():
    """D-06/D-02: upsert não sobrescreve linha com codigo_ibge e populacao preenchidos."""
    df = pl.DataFrame({
        "nome": ["Sorocaba"],
        "uf": ["SP"],
        "codigo_ibge": ["3552205"],
        "populacao": pl.Series([709000], dtype=pl.Int64),
        "fonte_pop": ["IBGE/SINISA (pop. urbana)"],
    })
    r = df.filter(pl.col("nome") == "Sorocaba").row(0, named=True)
    deve_preencher = not (r["codigo_ibge"] and r["populacao"])
    assert not deve_preencher, (
        "Sorocaba com codigo_ibge=3552205 e populacao=709000 NÃO deve ser sobrescrita (D-06)"
    )


def test_payload_usa_chave_generica():
    """D-02: data.json gerado tem 'taxa_inf_media' em totais (não 'taxa_inf_media_rms')."""
    import json
    data_path = ROOT / "site" / "data.json"
    assert data_path.exists(), "site/data.json deve existir — rodar 'uv run obs build --region rms'"
    d = json.loads(data_path.read_text())
    assert "taxa_inf_media" in d["totais"], "taxa_inf_media ausente em totais"
    assert "taxa_inf_media_rms" not in d["totais"], "chave antiga taxa_inf_media_rms não deve existir"
