"""Fonte IBGE: código do município e população.

Offline (padrão): lê config/municipios.csv — build determinístico, sem rede.
Refresh (--refresh-ibge): consulta a API pública do IBGE e regrava o cache.

A API do IBGE é gratuita e sem autenticação:
  https://servicodados.ibge.gov.br/api/v1/localidades/municipios
  https://servicodados.ibge.gov.br/api/v3/agregados/6579 (população estimada)
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug

CACHE = Path("config/municipios.csv")


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega o cache offline de municípios."""
    df = pl.read_csv(_root / CACHE)
    return df.with_columns(pl.col("nome").map_elements(slug, return_dtype=pl.String).alias("key"))


def refresh(root: Path = Path(".")) -> None:
    """Atualiza códigos IBGE e população a partir da API oficial.

    Requer rede. Resolve os municípios listados em config/regions.yml.
    Implementação deixada como tarefa GSD (ver GSD.md, M4):
      1. GET .../localidades/estados/{UF}/municipios  -> nome -> id
      2. GET agregado 6579 (população) por município
      3. merge no cache e reescreve config/municipios.csv
    """
    raise NotImplementedError(
        "Refresh IBGE pendente — ver GSD.md (M4). O build offline funciona sem isto."
    )
