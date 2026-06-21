"""Fonte SNIS-RS: indicadores de resíduos sólidos por município.

Offline (padrão): lê todos os CSVs em data/raw/snis/.
Refresh: baixe o export anual do SNIS e solte em data/raw/snis/ (ver
scripts/refresh_snis.md). A pipeline reprocessa tudo de forma determinística.

Esquema esperado (colunas):
  municipio, uf, ano, rsu_t_ano, reciclado_t_ano, reciclado_pct,
  coleta_seletiva_pop_pct, cooperados, custo_mensal_rs, qualidade, fonte
Campos vazios viram null -> o município aparece como 'pendente' no painel.
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug

RAW = Path("data/raw/snis")

SCHEMA = {
    "municipio": pl.String, "uf": pl.String, "ano": pl.Int64,
    "rsu_t_ano": pl.Float64, "reciclado_t_ano": pl.Float64,
    "reciclado_pct": pl.Float64, "coleta_seletiva_pop_pct": pl.Float64,
    "cooperados": pl.Float64, "custo_mensal_rs": pl.Float64,
    "qualidade": pl.String, "fonte": pl.String,
    # por-município: composição orgânica local (null = usa fallback global em transform.py)
    "composicao_organico": pl.Float64,
    "composicao_fonte": pl.String,
}


def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    # mantém o ano mais recente por município
    df = (
        df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
          .sort("ano", descending=True)
          .unique(subset=["key"], keep="first")
    )
    return df
