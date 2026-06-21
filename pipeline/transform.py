"""Transformação: junta região + IBGE + SNIS e deriva indicadores.

Saída: uma linha por município da região, com indicadores e um flag de
qualidade ('real' | 'estimativa' | 'pendente') que o painel usa para separar
visualmente dado público de lacuna.
"""
from __future__ import annotations
import polars as pl

from .sources.base import slug


def build_region(municipios: list[dict], ibge: pl.DataFrame, snis: pl.DataFrame,
                 coef: dict) -> pl.DataFrame:
    org_pct = coef["composicao"]["organico"]

    base = pl.DataFrame([
        {"nome": m["nome"], "uf": m["uf"], "subregiao": m.get("subregiao"),
         "key": slug(m["nome"])}
        for m in municipios
    ])

    df = (
        base.join(ibge.select("key", "codigo_ibge", "populacao", "fonte_pop"), on="key", how="left")
            .join(snis.drop("municipio", "uf"), on="key", how="left")
    )

    df = df.with_columns([
        # fração orgânica: usa gravimetria local se disponível, senão média Brasil
        pl.when(pl.col("composicao_organico").is_not_null())
          .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
          .otherwise(pl.col("rsu_t_ano") * org_pct)
          .alias("organico_t_ano"),
        # quanto vai pro aterro hoje
        (pl.col("rsu_t_ano") * (1 - pl.col("reciclado_pct").fill_null(0) / 100)).alias("aterro_t_ano"),
        # flag de qualidade: tem dado de RSU? real/estimativa : pendente
        pl.when(pl.col("rsu_t_ano").is_null()).then(pl.lit("pendente"))
          .otherwise(pl.col("qualidade").fill_null("real")).alias("flag"),
    ])

    return df.sort(["subregiao", "nome"])


def region_totals(df: pl.DataFrame) -> dict:
    """Agrega a região inteira (só municípios com dado)."""
    com_dado = df.filter(pl.col("rsu_t_ano").is_not_null())
    return {
        "municipios_total": df.height,
        "municipios_com_dado": com_dado.height,
        "rsu_t_ano": float(com_dado["rsu_t_ano"].sum() or 0),
        "organico_t_ano": float(com_dado["organico_t_ano"].sum() or 0),
        "aterro_t_ano": float(com_dado["aterro_t_ano"].sum() or 0),
        "reciclado_t_ano": float(com_dado["reciclado_t_ano"].sum() or 0),
        "cooperados": float(com_dado["cooperados"].sum() or 0),
        "populacao": float(df["populacao"].sum() or 0),
    }
