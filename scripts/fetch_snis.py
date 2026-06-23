"""[BECO SEM SAÍDA p/ RESÍDUOS] Extrai SNIS da Base dos Dados (BigQuery).

ATENÇÃO: a Base dos Dados só espelha o SNIS de ÁGUA/ESGOTO (dataset
`br_mdr_snis`: tabelas prestador_agua_esgoto, municipio_agua_esgoto). NÃO há
tabela de resíduos sólidos (manejo de RSU). Para o baseline de resíduos, use
`scripts/scrape_snis.py` (Série Histórica oficial). Este script é mantido apenas
como referência do caminho BigQuery.

Por que este script existe: a Base dos Dados espelha o SNIS em BigQuery — fonte
citável, consultável por SQL. Semente do `pipeline/sources/snis.py::refresh()`
(ver GSD.md, M4 / GEN-02) caso a BD publique resíduos sólidos no futuro.

REGRA SAGRADA (CLAUDE.md): nunca inventar número. Município sem linha no SNIS
sai como `pendente` (rsu_t_ano vazio). Todo dado real cita sua `fonte`.

Pré-requisitos:
    pip install basedosdados            # (ou: uv add --group dev basedosdados)
    gcloud auth application-default login
    # e um projeto GCP com BigQuery habilitado (1 TB/mês grátis; esta query usa pouco)

Uso:
    # 1) DESCOBRIR a tabela e as colunas reais (não chutamos schema):
    python scripts/fetch_snis.py --inspect --billing-project SEU_PROJETO_GCP

    # 2) MONTAR o CSV no schema do projeto:
    python scripts/fetch_snis.py --build --region rms --billing-project SEU_PROJETO_GCP \
        --exclude sorocaba "porto feliz"      # já têm dado citável no sample
    # -> escreve data/raw/snis/snis_rms_sp.csv

Depois: `uv run obs build --region rms && uv run pytest -q`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Reusa a normalização de nome do projeto (NFKD, sem acento, lower) — chave de junção.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.sources.base import slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ROOT / "config" / "regions.yml"
OUT_DEFAULT = ROOT / "data" / "raw" / "snis" / "snis_rms_sp.csv"

# Datasets candidatos da Base dos Dados (o MDR virou Ministério das Cidades;
# o nome do dataset pode ter migrado). O script tenta nesta ordem.
DATASET_CANDIDATES = ["br_mcid_snis", "br_mdr_snis", "br_ms_snis"]

# Colunas do schema do projeto (pipeline/sources/snis.py::SCHEMA) e os SUBSTRINGS
# candidatos de nome na Base dos Dados. A resolução é feita contra o schema REAL
# da tabela (INFORMATION_SCHEMA) — substrings não-resolvidos ficam null (pendente),
# nunca inventados. Ajuste após rodar --inspect e ver os nomes reais.
FIELD_CANDIDATES: dict[str, list[str]] = {
    # rsu total coletado (t/ano). No SNIS bruto: CO116+CO117+CO142+CS048.
    "rsu_t_ano": [
        "quantidade_total_residuo", "quantidade_rdo_rpu", "co116",
        "massa_coletada", "quantidade_coletada_total",
    ],
    "reciclado_t_ano": ["quantidade_recuperada_material", "cs026", "massa_recuperada_reciclaveis"],
    "reciclado_pct": ["taxa_recuperacao_reciclaveis", "in031"],
    "coleta_seletiva_pop_pct": ["taxa_cobertura_coleta_seletiva", "in030", "cobertura_coleta_seletiva"],
    "cooperados": ["quantidade_trabalhador", "catador", "cooperad"],
    "custo_mensal_rs": ["despesa_total_servico", "fn220", "despesa_total_manejo"],
}

# A coluna de despesa do SNIS é ANUAL — dividir por 12 para custo_mensal_rs (D-10).
ANNUAL_TO_MONTHLY = {"custo_mensal_rs"}


def _load_region(region_key: str) -> tuple[dict, list[dict]]:
    regions = yaml.safe_load(REGIONS.read_text(encoding="utf-8"))
    if region_key not in regions:
        sys.exit(f"Região '{region_key}' não existe em {REGIONS}. Veja: uv run obs regions")
    meta = regions[region_key]
    return meta, meta["municipios"]


def _import_bd():
    try:
        import basedosdados as bd  # noqa
        return bd
    except ImportError:
        sys.exit(
            "Pacote 'basedosdados' não instalado.\n"
            "  uv add --group dev basedosdados   (ou: pip install basedosdados)\n"
            "E autentique: gcloud auth application-default login"
        )


def _resolve_dataset(bd, billing_project: str) -> str:
    """Encontra qual dataset SNIS existe na Base dos Dados (sem chutar)."""
    for ds in DATASET_CANDIDATES:
        q = (
            f"SELECT table_name FROM `basedosdados.{ds}.INFORMATION_SCHEMA.TABLES` LIMIT 50"
        )
        try:
            tables = bd.read_sql(q, billing_project_id=billing_project)
            print(f"\n✓ Dataset encontrado: basedosdados.{ds}")
            print("  Tabelas:")
            for t in tables["table_name"].tolist():
                print(f"    - {t}")
            return ds
        except Exception:
            continue
    sys.exit(
        "Nenhum dataset SNIS encontrado na Base dos Dados sob os nomes "
        f"{DATASET_CANDIDATES}. Confira em https://basedosdados.org e ajuste "
        "DATASET_CANDIDATES no topo do script."
    )


def _resolve_rs_table(bd, dataset: str, billing_project: str) -> str:
    """Acha a tabela de resíduos sólidos por município (keyword 'residuo')."""
    q = (
        f"SELECT table_name FROM `basedosdados.{dataset}.INFORMATION_SCHEMA.TABLES` "
        "WHERE LOWER(table_name) LIKE '%residuo%'"
    )
    tables = bd.read_sql(q, billing_project_id=billing_project)["table_name"].tolist()
    # preferir granularidade por município
    municipal = [t for t in tables if "municipio" in t.lower()]
    chosen = (municipal or tables or [None])[0]
    if not chosen:
        sys.exit(
            f"Nenhuma tabela com 'residuo' em basedosdados.{dataset}. "
            "Rode --inspect e ajuste manualmente."
        )
    return chosen


def _columns(bd, dataset: str, table: str, billing_project: str) -> list[str]:
    q = (
        f"SELECT column_name FROM `basedosdados.{dataset}.INFORMATION_SCHEMA.COLUMNS` "
        f"WHERE table_name = '{table}' ORDER BY ordinal_position"
    )
    return bd.read_sql(q, billing_project_id=billing_project)["column_name"].tolist()


def _resolve_mapping(columns: list[str]) -> dict[str, str | None]:
    """Mapeia campo do projeto -> coluna real da BD (ou None se não achar)."""
    lower = {c.lower(): c for c in columns}
    mapping: dict[str, str | None] = {}
    for field, candidates in FIELD_CANDIDATES.items():
        hit = None
        for cand in candidates:
            for lc, original in lower.items():
                if cand in lc:
                    hit = original
                    break
            if hit:
                break
        mapping[field] = hit
    return mapping


def cmd_inspect(args) -> int:
    bd = _import_bd()
    dataset = _resolve_dataset(bd, args.billing_project)
    table = _resolve_rs_table(bd, dataset, args.billing_project)
    cols = _columns(bd, dataset, table, args.billing_project)
    print(f"\n✓ Tabela de resíduos sólidos: basedosdados.{dataset}.{table}")
    print(f"  ({len(cols)} colunas)")
    for c in cols:
        print(f"    - {c}")
    print("\n=== Mapeamento proposto (campo do projeto -> coluna BD) ===")
    mapping = _resolve_mapping(cols)
    for field, col in mapping.items():
        mark = "✓" if col else "✗ NÃO RESOLVIDO (ficará null/pendente)"
        print(f"  {field:24} -> {col or '—'}   {mark}")
    print(
        "\nSe algum campo ficou NÃO RESOLVIDO, ajuste FIELD_CANDIDATES no topo do "
        "script com o nome real visto acima e rode --inspect de novo. Depois --build."
    )
    return 0


def cmd_build(args) -> int:
    import polars as pl

    bd = _import_bd()
    meta, municipios = _load_region(args.region)
    exclude = {slug(x) for x in (args.exclude or [])}
    wanted = {slug(m["nome"]): m for m in municipios if slug(m["nome"]) not in exclude}

    dataset = _resolve_dataset(bd, args.billing_project)
    table = _resolve_rs_table(bd, dataset, args.billing_project)
    cols = _columns(bd, dataset, table, args.billing_project)
    mapping = _resolve_mapping(cols)

    has_uf = any(c.lower() == "sigla_uf" for c in cols)
    has_id = any(c.lower() == "id_municipio" for c in cols)
    has_ano = any(c.lower() == "ano" for c in cols)
    if not (has_id and has_ano):
        sys.exit(
            f"Tabela basedosdados.{dataset}.{table} não tem id_municipio/ano esperados. "
            "Rode --inspect e ajuste o script."
        )

    select_cols = ["id_municipio", "ano"] + ([f"sigla_uf"] if has_uf else [])
    select_cols += [c for c in mapping.values() if c]
    uf_filter = f"WHERE sigla_uf = '{meta['uf']}'" if has_uf else ""
    q = (
        f"SELECT {', '.join(dict.fromkeys(select_cols))} "
        f"FROM `basedosdados.{dataset}.{table}` {uf_filter}"
    )
    print(f"\nConsultando basedosdados.{dataset}.{table} (UF={meta.get('uf')})...")
    raw = pl.from_pandas(bd.read_sql(q, billing_project_id=args.billing_project))

    # Resolve nomes dos municípios via diretório da BD (id_municipio -> nome).
    dir_q = (
        "SELECT id_municipio, nome FROM `basedosdados.br_bd_diretorios_brasil.municipio`"
    )
    diretorio = pl.from_pandas(bd.read_sql(dir_q, billing_project_id=args.billing_project))
    raw = raw.join(diretorio, on="id_municipio", how="left")

    # Ano mais recente por município (D-04: comportamento equivalente ao snis.load()).
    raw = raw.with_columns(
        pl.col("nome").map_elements(slug, return_dtype=pl.String).alias("key")
    )
    raw = raw.filter(pl.col("key").is_in(list(wanted.keys())))
    raw = raw.sort("ano", descending=True).unique(subset=["key"], keep="first")

    fonte_base = f"SNIS-RS via Base dos Dados (basedosdados.{dataset}.{table})"
    rows: list[dict] = []
    found = set()
    for r in raw.iter_rows(named=True):
        key = r["key"]
        m = wanted[key]
        found.add(key)
        rec: dict = {
            "municipio": m["nome"], "uf": m["uf"], "ano": r.get("ano"),
            "qualidade": "real",
            "fonte": f"{fonte_base}, ano {r.get('ano')}",
            "composicao_organico": "",  # só Sorocaba tem gravimetria local (no sample)
            "composicao_fonte": "média Brasil (estimativa)",
        }
        for field, col in mapping.items():
            val = r.get(col) if col else None
            if val is not None and field in ANNUAL_TO_MONTHLY:
                val = round(float(val) / 12, 2)
            rec[field] = "" if val is None else val
        if rec.get("cooperados") not in ("", None):
            rec["fonte"] += " | cooperados: SNIS autodeclarado — tratar como piso"
        rows.append(rec)

    # Municípios da RMS SEM linha no SNIS -> pendente honesto (regra sagrada).
    for key, m in wanted.items():
        if key in found:
            continue
        rows.append({
            "municipio": m["nome"], "uf": m["uf"], "ano": "",
            "rsu_t_ano": "", "reciclado_t_ano": "", "reciclado_pct": "",
            "coleta_seletiva_pop_pct": "", "cooperados": "", "custo_mensal_rs": "",
            "qualidade": "pendente",
            "fonte": f"{fonte_base} — município sem linha no SNIS-RS",
            "composicao_organico": "", "composicao_fonte": "",
        })

    schema_cols = [
        "municipio", "uf", "ano", "rsu_t_ano", "reciclado_t_ano", "reciclado_pct",
        "coleta_seletiva_pop_pct", "cooperados", "custo_mensal_rs", "qualidade",
        "fonte", "composicao_organico", "composicao_fonte",
    ]
    out = pl.DataFrame([{c: r.get(c, "") for c in schema_cols} for r in rows])
    out = out.sort("municipio")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.write_csv(args.out)

    n_real = sum(1 for r in rows if r["qualidade"] == "real")
    n_pend = sum(1 for r in rows if r["qualidade"] == "pendente")
    print(f"\n✓ {args.out}")
    print(f"  {len(rows)} municípios: {n_real} com dado real, {n_pend} pendentes")
    print("  Confira a fonte por linha e rode: uv run obs build --region rms && uv run pytest -q")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extrai SNIS-RS da Base dos Dados (BigQuery)")
    p.add_argument("--inspect", action="store_true", help="lista tabela/colunas reais e o mapeamento")
    p.add_argument("--build", action="store_true", help="monta o CSV no schema do projeto")
    p.add_argument("--region", default="rms", help="chave da região em config/regions.yml")
    p.add_argument("--billing-project", required=True, help="ID do projeto GCP para faturar a query BigQuery")
    p.add_argument("--exclude", nargs="*", default=[], help="municípios a pular (já têm dado citável)")
    p.add_argument("--out", type=Path, default=OUT_DEFAULT, help="caminho do CSV de saída")
    args = p.parse_args(argv)

    if args.inspect:
        return cmd_inspect(args)
    if args.build:
        return cmd_build(args)
    p.error("informe --inspect ou --build")


if __name__ == "__main__":
    raise SystemExit(main())
