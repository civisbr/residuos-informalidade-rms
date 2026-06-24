"""Transformação: junta região + IBGE + SNIS e deriva indicadores.

Saída: uma linha por município da região, com indicadores e um flag de
qualidade ('real' | 'estimativa' | 'pendente') que o painel usa para separar
visualmente dado público de lacuna.
"""
from __future__ import annotations
import polars as pl

from .sources.base import slug


def build_region(municipios: list[dict], ibge: pl.DataFrame, snis: pl.DataFrame,
                 informalidade: pl.DataFrame, rais_residuos: pl.DataFrame,
                 coef: dict) -> pl.DataFrame:
    org_pct = coef["composicao"]["organico"]

    base = pl.DataFrame([
        {"nome": m["nome"], "uf": m["uf"], "subregiao": m.get("subregiao"),
         "key": slug(m["nome"])}
        for m in municipios
    ])

    # Preparar ibge_informalidade: renomear "fonte" → "fonte_inf" para evitar
    # conflito com coluna "fonte" do SNIS (T-02-09)
    inf_sel = informalidade.select([
        "key",
        "taxa_informalidade_pct",
        "total_ocupados",
        "informais",
        "ano_censo",
        pl.col("fonte").alias("fonte_inf"),
    ])

    # Preparar rais_residuos: renomear "ano" → "ano_rais" para evitar ambiguidade
    rais_sel = rais_residuos.select([
        "key",
        "formais_residuos",
        pl.col("ano").alias("ano_rais"),
    ])

    df = (
        base.join(ibge.select("key", "codigo_ibge", "populacao", "fonte_pop"), on="key", how="left")
            .join(snis.drop("municipio", "uf"), on="key", how="left")
            .join(inf_sel, on="key", how="left")
            .join(rais_sel, on="key", how="left")
    )

    df = df.with_columns([
        # fração orgânica: usa gravimetria local se disponível, senão média Brasil
        pl.when(pl.col("composicao_organico").is_not_null())
          .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
          .otherwise(pl.col("rsu_t_ano") * org_pct)
          .alias("organico_t_ano"),
        # quanto vai pro aterro hoje
        (pl.col("rsu_t_ano") * (1 - pl.col("reciclado_pct").fill_null(0) / 100)).alias("aterro_t_ano"),
        # flag de qualidade RSU: tem dado de RSU? real/estimativa : pendente
        pl.when(pl.col("rsu_t_ano").is_null()).then(pl.lit("pendente"))
          .otherwise(pl.col("qualidade").fill_null("real")).alias("flag"),
        # flag de qualidade informalidade: Censo 2022 é real para todos os 27
        pl.when(pl.col("taxa_informalidade_pct").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_informalidade"),
    ])

    # Proxy de formalização D-06/D-07 (ver Exemplo 3 do RESEARCH.md)
    # Passo 1: denominador auxiliar (formais + cooperados, null→0)
    df = df.with_columns([
        (
            pl.col("formais_residuos").fill_null(0) +
            pl.col("cooperados").fill_null(0)
        ).alias("_denominador"),
    ])

    # Passo 2: proxy e flag_proxy
    df = df.with_columns([
        # D-07: pendente quando AMBOS são null/0
        pl.when(
            ((pl.col("formais_residuos").is_null()) | (pl.col("formais_residuos") == 0)) &
            ((pl.col("cooperados").is_null()) | (pl.col("cooperados") == 0))
        ).then(pl.lit(None, dtype=pl.Float64))
        .when(pl.col("_denominador") > 0)
        .then(
            pl.col("formais_residuos").fill_null(0).cast(pl.Float64) /
            pl.col("_denominador").cast(pl.Float64)
        )
        .otherwise(pl.lit(None, dtype=pl.Float64))
        .alias("proxy_formalizacao"),
    ]).with_columns([
        pl.when(pl.col("proxy_formalizacao").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_proxy"),
    ]).drop("_denominador")

    return df.sort(["subregiao", "nome"], nulls_last=True)


def region_totals(df: pl.DataFrame) -> dict:
    """Agrega a região inteira (só municípios com dado)."""
    com_dado = df.filter(pl.col("rsu_t_ano").is_not_null())

    # Média ponderada de taxa_informalidade_pct por total_ocupados
    # apenas municípios com ambos os campos não-null
    inf_df = df.filter(
        pl.col("taxa_informalidade_pct").is_not_null() &
        pl.col("total_ocupados").is_not_null()
    )
    if inf_df.height > 0:
        soma_ponderada = float(
            (inf_df["taxa_informalidade_pct"] * inf_df["total_ocupados"]).sum()
        )
        soma_ocupados = float(inf_df["total_ocupados"].sum())
        taxa_inf_media = soma_ponderada / soma_ocupados if soma_ocupados > 0 else None
    else:
        taxa_inf_media = None

    return {
        "municipios_total": df.height,
        "municipios_com_dado": com_dado.height,
        "rsu_t_ano": float(com_dado["rsu_t_ano"].sum() or 0),
        "organico_t_ano": float(com_dado["organico_t_ano"].sum() or 0),
        "aterro_t_ano": float(com_dado["aterro_t_ano"].sum() or 0),
        "reciclado_t_ano": float(com_dado["reciclado_t_ano"].sum() or 0),
        "cooperados": float(com_dado["cooperados"].sum() or 0),
        "populacao": float(df["populacao"].sum() or 0),
        "taxa_inf_media": taxa_inf_media,
    }
