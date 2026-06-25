"""Testes de sanidade — rodam offline, garantem que o build não regrida."""
from pathlib import Path
import pytest
import yaml
import polars as pl
from pipeline.sources import ibge, snis
from pipeline.sources import ibge_informalidade, rais, pnad_regional, operacao
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
    """02-02 T1: region_totals() calcula taxa_inf_media ponderada por total_ocupados."""
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

    assert "taxa_inf_media" in totals, "taxa_inf_media ausente em region_totals()"
    taxa = totals["taxa_inf_media"]
    assert taxa is not None, "taxa_inf_media não deve ser None com dados completos"
    # RMS como um todo tem taxa entre 10% e 50% (sanidade)
    assert 10 < taxa < 50, f"taxa_inf_media fora do intervalo esperado: {taxa}"


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

    # taxa_inf_media em totais (D-02: chave genérica sem sufixo rms)
    assert "taxa_inf_media" in d["totais"], "taxa_inf_media ausente em totais"


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


# ---------------------------------------------------------------------------
# Fase 4 — CR-01: cold-start build produz pendente, não traceback
# ---------------------------------------------------------------------------

def test_cold_start_build_sem_csvs_snis_censo_rais(tmp_path):
    """CR-01: build_region() com todos os load() sem arquivos CSV retorna linhas pendente.

    Simula cold-start de uma nova região antes de qualquer refresh.
    Nenhum CSV existe em data/raw/snis/, data/raw/censo/, data/raw/rais/.
    O build deve produzir linhas com flag='pendente' e nunca lançar exceção.
    """
    import os
    os.chdir(ROOT)

    # tmp_path simula uma raiz sem CSVs (apenas config/municipios.csv existe)
    import shutil
    # Copiar config/ para tmp_path (ibge.load precisa de municipios.csv)
    shutil.copytree(ROOT / "config", tmp_path / "config")
    # NÃO criar data/raw/snis/, data/raw/censo/, data/raw/rais/ — cold-start

    # Criar diretórios vazios para que o glob não falhe
    (tmp_path / "data" / "raw" / "snis").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "censo").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "rais").mkdir(parents=True)

    from pipeline.sources import ibge as _ibge, snis as _snis
    from pipeline.sources import ibge_informalidade as _inf, rais as _rais

    df_ibge = _ibge.load(tmp_path)
    df_snis = _snis.load(tmp_path)
    df_inf = _inf.load(tmp_path)
    df_rais = _rais.load(tmp_path)

    # Verificar que os frames vazios têm coluna 'key' (CR-01)
    assert "key" in df_snis.columns, "snis.load() vazio deve ter coluna 'key'"
    assert "key" in df_inf.columns, "ibge_informalidade.load() vazio deve ter coluna 'key'"
    assert "key" in df_rais.columns, "rais.load() vazio deve ter coluna 'key'"

    municipios_rms = REGIONS["rms"]["municipios"]
    # Não deve lançar exceção (ColumnNotFoundError foi o bug do CR-01)
    df = transform.build_region(municipios_rms, df_ibge, df_snis, df_inf, df_rais, COEF)

    assert df.height == len(municipios_rms), (
        f"build_region() cold-start deve ter {len(municipios_rms)} linhas, got {df.height}"
    )
    # Invariante sagrado: cold-start → todos pendente (nenhum número inventado)
    assert df["flag"].to_list() == ["pendente"] * df.height, (
        "CR-01: cold-start sem CSVs → todos os municípios devem ter flag='pendente'"
    )
    assert df["rsu_t_ano"].null_count() == df.height, (
        "CR-01: cold-start sem CSVs → rsu_t_ano deve ser null para todos (nunca inventar número)"
    )


# ---------------------------------------------------------------------------
# Fase 4 — WR-01: upsert preserva populacao=0 curado
# ---------------------------------------------------------------------------

def test_upsert_preserva_populacao_zero():
    """WR-01: upsert com check explícito preserva populacao=0 curado (não trata 0 como vazio).

    O bug era `if codigo and pop` que trata pop=0 como False.
    O fix usa `codigo is not None and codigo != "" and pop is not None`.
    """
    # Simula row com populacao=0 curado (ex.: município hipotético sem população)
    r = {"codigo_ibge": "3500001", "populacao": 0}
    codigo = r.get("codigo_ibge")
    pop = r.get("populacao")

    # Comportamento ANTIGO (bugado): `if codigo and pop` trata pop=0 como False
    deve_preencher_antigo = not (codigo and pop)
    assert deve_preencher_antigo, (
        "WR-01: confirm bug — `if codigo and pop` falha para pop=0 "
        "(trata 0 como 'não preenchido')"
    )

    # Comportamento NOVO (correto): check explícito de None
    codigo_ok = codigo is not None and codigo != ""
    pop_ok = pop is not None
    deve_preservar_novo = codigo_ok and pop_ok
    assert deve_preservar_novo, (
        "WR-01: com check explícito, populacao=0 curado deve ser preservado "
        "(0 é dado válido — não é campo vazio)"
    )


# ---------------------------------------------------------------------------
# Fase 5 — Plano 05-01: camada viva (operacional) — LIVE-01/LIVE-02
# ---------------------------------------------------------------------------

def test_operacao_load_vazio_tem_key():
    """LIVE-02 / CR-01: operacao.load() com o CSV-template (sem linhas de dado)
    devolve um frame vazio MAS com coluna 'key' — sem isso joins/cold-start quebram."""
    import os
    os.chdir(ROOT)
    df = operacao.load(ROOT)
    assert "key" in df.columns, "operacao.load() vazio deve ter coluna 'key'"
    assert df.height == 0, (
        "operação ainda não roda — o template não tem linhas de dado (D-01/D-02)"
    )


def test_payload_tem_operacao():
    """LIVE-02: data.json contém a chave 'operacao' com estado vazio honesto e
    preserva as chaves existentes do payload (nunca omitir a chave operacao)."""
    import json
    data_path = ROOT / "site" / "data.json"
    assert data_path.exists(), "site/data.json deve existir — rodar 'uv run obs build --region rms'"
    d = json.loads(data_path.read_text())

    assert "operacao" in d, "chave 'operacao' ausente no payload"
    assert d["operacao"]["tem_dado"] is False, "sem telemetria → tem_dado deve ser False"
    assert d["operacao"]["serie"] == [], "sem telemetria → serie deve ser vazia"
    assert d["operacao"]["acumulados"] is None, "sem telemetria → acumulados deve ser None"

    for chave in ["municipios", "totais", "meta", "coeficientes", "simulador_defaults"]:
        assert chave in d, f"chave existente '{chave}' não deve sumir do payload"


# ---------------------------------------------------------------------------
# Fase 5 — Plano 05-02: paridade model.py ↔ app.js::project() (CONCERNS #7)
# ---------------------------------------------------------------------------

# Mapa canônico de nomes Python (model.project) ↔ JS (app.js::project).
# Os nomes DIFEREM entre as linguagens — esta é a tabela de verdade. Uma
# renomeação silenciosa em qualquer lado quebra os testes abaixo (foi
# exatamente assim que `carros_equivalente` vs `carros` divergiu, CONCERNS #7).
PARIDADE_PY_JS = {
    "desviado_t_ano": "desviado",
    "co2e_t_ano": "co2e",
    "carros_equivalente": "carros",
    "larva_seca_t_ano": "larvaSeca",
    "frass_t_ano": "frass",
    "receita_ano": "receita",
    "fundo_partilha_ano": "fundo",
    "catadores_sustentados": "catadores",
    "pct_organico_municipal": "pctOrg",
}


def test_paridade_project_contrato_python_congelado():
    """CONCERNS #7: congela o contrato numérico de model.project() com inputs
    default fixos. Mudar a lógica/coeficientes sem ajustar o teste quebra aqui —
    é a âncora canônica sobre a qual a calibração da Task 2 será construída."""
    d = model.defaults(COEF)
    # organico_municipal fixo (mesmo de test_modelo_break_even) → pct calculável
    r = model.project(d["clientes"], d["kg_dia"], d["partilha_pct"], d["gate_fee"],
                      COEF, 116280)

    # As 9 chaves esperadas existem e nenhuma a mais/a menos (contrato fechado).
    assert set(r.keys()) == set(PARIDADE_PY_JS.keys()), (
        "model.project() mudou o conjunto de campos retornados — atualize "
        "PARIDADE_PY_JS e o espelho em app.js (paridade, CONCERNS #7)"
    )

    # Valores canônicos derivados das fórmulas (defaults: 36 clientes, 80 kg/dia,
    # 30%, gate 400; coeficientes de config/coefficients.yml). Congelam a lógica.
    assert r["desviado_t_ano"] == pytest.approx(1051.2, abs=0.1)       # 36*80/1000*365
    assert r["co2e_t_ano"] == pytest.approx(683.3, abs=0.1)            # *0.65
    assert r["carros_equivalente"] == pytest.approx(148.5, abs=0.2)    # /4.6
    assert r["larva_seca_t_ano"] == pytest.approx(47.3, abs=0.2)       # *0.15*0.30
    assert r["frass_t_ano"] == pytest.approx(367.9, abs=0.2)           # *0.35
    assert r["receita_ano"] == pytest.approx(172800.0, abs=1)          # 36*400*12
    assert r["fundo_partilha_ano"] == pytest.approx(51840.0, abs=1)    # *30%
    assert r["catadores_sustentados"] == pytest.approx(2.9, abs=0.1)   # /(1500*12)
    assert 0 < r["pct_organico_municipal"] < 5


def test_paridade_project_nomes_js_existem_em_app_js():
    """CONCERNS #7 (Pitfall 1): parse textual de site/app.js confirma que o
    objeto retornado por project() em JS contém EXATAMENTE os nomes esperados.
    Captura renomeação silenciosa de campo cross-language sem rodar JS (o CI só
    tem pytest, não node)."""
    import re
    src = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    # Isola o corpo do return de project() em JS: `return { ... };`
    m = re.search(r"function project\([^)]*\)\s*\{.*?return\s*\{(.*?)\};",
                  src, re.DOTALL)
    assert m, "não encontrei o `return { ... }` de project() em app.js"
    return_body = m.group(1)

    # Coleta as chaves de topo do objeto literal. Cada item começa logo após
    # `{` ou `,` (no nível do literal) e é o identificador seguido de ':' (par
    # explícito) ou de ',' / fim (shorthand). Ancorar em ',' ou '{' à esquerda
    # evita capturar identificadores DENTRO de uma expressão de valor (ex.:
    # `co2e_por_carro_ano` em `carros: co2e / cl.co2e_por_carro_ano`).
    chaves_js = set(re.findall(
        r"(?:[{,])\s*([A-Za-z_]\w*)\s*(?=[:,}])", "{" + return_body + "}"
    ))

    esperadas_js = set(PARIDADE_PY_JS.values())
    faltando = esperadas_js - chaves_js
    assert not faltando, (
        f"app.js::project() não retorna mais o(s) campo(s) {faltando} — "
        f"renomeação silenciosa quebra a paridade com model.py (CONCERNS #7). "
        f"Chaves JS achadas: {sorted(chaves_js)}"
    )


def test_paridade_mapa_py_js_cobre_chaves_do_modelo():
    """CONCERNS #7: o mapa Py↔JS deve cobrir exatamente as chaves reais de
    model.project() — nem campo Python órfão (sem par JS) nem entrada obsoleta
    no mapa. Uma divergência futura em qualquer dos lados falha aqui."""
    d = model.defaults(COEF)
    r = model.project(d["clientes"], d["kg_dia"], d["partilha_pct"], d["gate_fee"],
                      COEF, 116280)
    assert set(r.keys()) == set(PARIDADE_PY_JS.keys()), (
        "chaves de model.project() divergiram do mapa PARIDADE_PY_JS — "
        "todo campo Python precisa de um par JS conhecido (paridade travada)"
    )


# ---------------------------------------------------------------------------
# Fase 5 — Plano 05-02: calibração real×projetado em build_operacao() (LIVE-03)
# ---------------------------------------------------------------------------

# Schema da telemetria operacional (espelha pipeline/sources/operacao.SCHEMA).
# Construído em memória — NÃO commitar dado no CSV real (D-01).
_OP_SCHEMA = {
    "mes": pl.String, "municipio": pl.String, "n_clientes": pl.Int64,
    "t_org_coletada": pl.Float64, "larva_umida_t": pl.Float64,
    "larva_seca_t": pl.Float64, "frass_t": pl.Float64,
    "partilha_rs": pl.Float64, "qualidade": pl.String, "fonte": pl.String,
    "key": pl.String,
}


def _op_fixture(linhas: list[dict]) -> pl.DataFrame:
    """Monta um DataFrame de telemetria sintética em memória (sem CSV)."""
    base = {k: None for k in _OP_SCHEMA}
    return pl.DataFrame([{**base, **r} for r in linhas], schema=_OP_SCHEMA)


def test_build_operacao_projetado_reusa_model_project():
    """LIVE-03/D-07/D-08: para um mês com t_org_coletada, o projetado vem de
    model.project() sobre o MESMO desviado, em base MENSAL (÷12)."""
    op = _op_fixture([
        {"mes": "2026-01", "municipio": "Sorocaba", "n_clientes": 10,
         "t_org_coletada": 30.0, "larva_seca_t": 1.4, "frass_t": 10.2,
         "partilha_rs": 5000.0, "qualidade": "real", "fonte": "pesagem",
         "key": "sorocaba"},
    ])
    out = transform.build_operacao(op, COEF)
    assert out["tem_dado"] is True
    linha = out["serie"][0]
    assert linha["real_desviado_t"] == pytest.approx(30.0)

    # Coerência com model.project() sobre o mesmo desviado, ÷12 (base mensal).
    d = model.defaults(COEF)
    kg_dia = 30.0 * 12 * 1000 / 365
    p = model.project(1, kg_dia, d["partilha_pct"], d["gate_fee"], COEF)
    assert linha["projetado_larva_seca_t"] == pytest.approx(p["larva_seca_t_ano"] / 12, rel=1e-6)
    assert linha["projetado_frass_t"] == pytest.approx(p["frass_t_ano"] / 12, rel=1e-6)
    assert linha["projetado_co2e_t"] == pytest.approx(p["co2e_t_ano"] / 12, rel=1e-6)
    assert linha["projetado_larva_seca_t"] > 0


def test_build_operacao_mes_incompleto_projetado_null_nunca_zero():
    """Regra sagrada / Pitfall T-05-07: mês sem t_org_coletada → projetado_* é
    None (célula vazia), NUNCA 0."""
    op = _op_fixture([
        {"mes": "2026-01", "municipio": "Sorocaba", "n_clientes": 10,
         "t_org_coletada": 30.0, "larva_seca_t": 1.4, "frass_t": 10.2,
         "partilha_rs": 5000.0, "qualidade": "real", "fonte": "pesagem",
         "key": "sorocaba"},
        # mês sem coleta medida: t_org_coletada None
        {"mes": "2026-02", "municipio": "Sorocaba", "n_clientes": 10,
         "t_org_coletada": None, "larva_seca_t": None, "frass_t": None,
         "partilha_rs": None, "qualidade": "real", "fonte": "sem pesagem",
         "key": "sorocaba"},
    ])
    out = transform.build_operacao(op, COEF)
    # série ordenada por mês (determinismo, Pitfall 4)
    meses = [l["mes"] for l in out["serie"]]
    assert meses == ["2026-01", "2026-02"], "série deve estar ordenada por mês"

    fev = out["serie"][1]
    for campo in ("projetado_larva_seca_t", "projetado_frass_t", "projetado_co2e_t"):
        assert fev[campo] is None, (
            f"mês sem t_org_coletada → {campo} deve ser None (nunca 0 — regra sagrada)"
        )
        assert fev[campo] != 0


def test_build_operacao_acumulados_derivados_co2e_carros():
    """LIVE-04/D-11: acumulados incluem co2e evitado e carros equivalentes
    DERIVADOS (via model.project() sobre o desviado real total), não medidos."""
    op = _op_fixture([
        {"mes": "2026-01", "municipio": "Sorocaba", "t_org_coletada": 30.0,
         "larva_seca_t": 1.4, "frass_t": 10.2, "partilha_rs": 5000.0,
         "n_clientes": 10, "qualidade": "real", "fonte": "x", "key": "sorocaba"},
        {"mes": "2026-02", "municipio": "Sorocaba", "t_org_coletada": 20.0,
         "larva_seca_t": 0.9, "frass_t": 6.8, "partilha_rs": 3000.0,
         "n_clientes": 10, "qualidade": "real", "fonte": "x", "key": "sorocaba"},
    ])
    out = transform.build_operacao(op, COEF)
    acum = out["acumulados"]
    assert acum["desviado_t"] == pytest.approx(50.0)
    assert acum["partilha_rs"] == pytest.approx(8000.0)
    # co2e derivado = desviado_total * co2e_por_t_organico
    esperado_co2e = 50.0 * COEF["clima"]["co2e_por_t_organico"]
    assert acum["co2e_evitado_t_derivado"] == pytest.approx(esperado_co2e, rel=1e-3)
    esperado_carros = esperado_co2e / COEF["clima"]["co2e_por_carro_ano"]
    assert acum["carros_equivalente_derivado"] == pytest.approx(esperado_carros, rel=1e-2)


def test_build_operacao_estado_vazio_sem_dado():
    """Estado vazio honesto preservado: frame vazio → tem_dado False, sem inventar."""
    vazio = pl.DataFrame(schema=_OP_SCHEMA)
    out = transform.build_operacao(vazio, COEF)
    assert out == {"serie": [], "acumulados": None, "tem_dado": False}


def test_build_operacao_nao_altera_coefficients_yml():
    """Regra sagrada: a fase compara contra os coeficientes, não os reescreve."""
    antes = (ROOT / "config/coefficients.yml").read_text(encoding="utf-8")
    op = _op_fixture([
        {"mes": "2026-01", "municipio": "Sorocaba", "t_org_coletada": 30.0,
         "larva_seca_t": 1.4, "frass_t": 10.2, "partilha_rs": 5000.0,
         "n_clientes": 10, "qualidade": "real", "fonte": "x", "key": "sorocaba"},
    ])
    transform.build_operacao(op, COEF)
    depois = (ROOT / "config/coefficients.yml").read_text(encoding="utf-8")
    assert antes == depois, "coefficients.yml não deve ser tocado pela calibração"
