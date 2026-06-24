"""Fonte RAIS 2023: vínculos formais no setor de resíduos por município.

Offline (padrão): lê todos os CSVs em data/raw/rais/.
Refresh: consulta BigQuery (basedosdados.br_me_rais.microdados_estabelecimentos)
com ADC (application-default credentials). Ver scripts/fetch_rais.py (Fase 4).

Esquema esperado (colunas):
  municipio, uf, codigo_ibge, formais_residuos, ano, fonte
formais_residuos=0 significa ausência de estabelecimentos formais no setor — não null.
RAIS tem cobertura completa do setor formal; ausência de linha = 0 vínculo (não missing).

Chave de junção: key = slug(municipio) — NÃO usar codigo_ibge para join.
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug

RAW = Path("data/raw/rais")

SCHEMA: dict[str, type] = {
    "municipio": pl.String,
    "uf": pl.String,
    "codigo_ibge": pl.String,       # 7 dígitos
    "formais_residuos": pl.Int64,   # vínculos formais ativos em 31/12
    "ano": pl.Int64,
    "fonte": pl.String,
}

# CNAEs do setor de resíduos (Classificação Nacional de Atividades Econômicas 2.0)
# Verificados via servicodados.ibge.gov.br/api/v2/cnae/subclasses — 2026-06-23
# Excluídos: 4687701/4687702/4687703 (comércio atacadista de sucatas — atravessadores)
WASTE_CNAES: list[str] = [
    "3811400",  # Coleta de resíduos não perigosos
    "3812200",  # Coleta de resíduos perigosos
    "3821100",  # Tratamento e disposição de resíduos não perigosos
    "3822000",  # Tratamento e disposição de resíduos perigosos
    "3831901",  # Recuperação de sucatas de alumínio
    "3832700",  # Recuperação de materiais plásticos
    "3839401",  # Usinas de compostagem
    "3839499",  # Recuperação de materiais não especificados
    "3900500",  # Descontaminação e outros serviços de gestão de resíduos
]


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega snapshot offline da RAIS 2023 — vínculos formais por município.

    Retorna DataFrame com 27 linhas quando o CSV de snapshot existe.
    formais_residuos=0 (Int64) para municípios sem estabelecimento no setor —
    este é um dado real (RAIS tem cobertura completa), não dado faltante.

    Chave de junção: coluna 'key' = slug(municipio).
    """
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        # Inclui coluna 'key' para que os joins em transform.build_region() não falhem
        # quando nenhum CSV existe (ex.: cold-start antes do primeiro refresh)
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    frames = [
        pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0)
        for f in files
    ]
    df = pl.concat(frames, how="vertical_relaxed")
    # dedup: mantém ano mais recente por município
    df = (
        df.with_columns(
            pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")
        )
        .sort("ano", descending=True)
        .unique(subset=["key"], keep="first")
    )
    return df


def refresh(root: Path = Path(".")) -> None:  # noqa: ARG001
    """Baixa dados via BigQuery e regrava data/raw/rais/.

    Requer ADC (application-default credentials) em ~/.config/gcloud.
    NÃO commitado no git. Billing project: residuos-github.

    SQL canônico:
      SELECT
        id_municipio,
        SUM(quantidade_vinculos_ativos) AS formais_residuos
      FROM `basedosdados.br_me_rais.microdados_estabelecimentos`
      WHERE sigla_uf = 'SP'
        AND ano = 2023
        AND id_municipio IN (<RMS_IBGE_CODES>)
        AND cnae_2_subclasse IN (<WASTE_CNAES>)
      GROUP BY id_municipio
      ORDER BY id_municipio

    Nota: municípios sem resultado no GROUP BY têm formais=0 (não NULL).
    A pipeline RAIS preenche formais_residuos=0 para esses casos após o join.

    Converter para Polars sem pandas:
      result = client.query(sql).result()
      df = pl.from_arrow(result.to_arrow())

    Implementação completa: ver scripts/fetch_rais.py (Fase 4, GEN-02).
    """
    raise NotImplementedError(
        "Refresh RAIS 2023 não implementado nesta fase. "
        "Ver scripts/fetch_rais.py (planejado para Fase 4, GEN-02). "
        "Requer: google.cloud.bigquery.Client(project='residuos-github'). "
        f"CNAEs: {', '.join(WASTE_CNAES)}. "
        "Tabela: basedosdados.br_me_rais.microdados_estabelecimentos."
    )
