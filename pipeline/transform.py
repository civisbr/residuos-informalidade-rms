"""Transformação: junta região + IBGE + SNIS e deriva indicadores.

Saída: uma linha por município da região, com indicadores e um flag de
qualidade ('real' | 'estimativa' | 'pendente') que o painel usa para separar
visualmente dado público de lacuna.
"""
from __future__ import annotations
import polars as pl

from .sources.base import slug
from . import model


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


def _projetado_mensal(desviado_t_mes: float | None, coef: dict) -> dict:
    """Roda model.project() sobre o desviado REAL do mês e devolve os derivados
    de conversão em base MENSAL (LIVE-03, D-07/D-08).

    Insight (RESEARCH Pattern 4): os outputs de conversão de project() são
    LINEARES em desviado_t_ano. Logo, para "alimentar o modelo com o real" não
    se inverte t_org_coletada em clientes×kg_dia de forma elaborada — basta
    montar a chamada para que desviado_t_ano == desviado_t_mes × 12 e dividir os
    _t_ano por 12 (anualização, Pitfall 2). NÃO reimplementa a conversão: reusa
    model.project() (D-08), preservando a paridade com app.js.

    Mês sem t_org_coletada (None) → todos os projetados são None (célula vazia),
    NUNCA zero (regra sagrada — zero afirmaria "previmos zero").
    """
    if desviado_t_mes is None:
        return {
            "projetado_larva_seca_t": None,
            "projetado_frass_t": None,
            "projetado_co2e_t": None,
        }
    # desviado_t_ano = clientes*kg_dia/1000*365; queremos = desviado_t_mes*12.
    # Com clientes=1: kg_dia = desviado_t_mes*12*1000/365.
    kg_dia = desviado_t_mes * 12 * 1000 / 365
    d = model.defaults(coef)
    p = model.project(1, kg_dia, d["partilha_pct"], d["gate_fee"], coef)
    return {
        # ÷12: outputs _t_ano de project() → base mensal p/ confrontar a telemetria
        "projetado_larva_seca_t": round(p["larva_seca_t_ano"] / 12, 4),
        "projetado_frass_t": round(p["frass_t_ano"] / 12, 4),
        "projetado_co2e_t": round(p["co2e_t_ano"] / 12, 4),
    }


def build_operacao(operacao: pl.DataFrame, coef: dict) -> dict:
    """Agrega a telemetria REAL da operação numa série mensal regional + o
    projetado da calibração reusando model.project() (LIVE-03/LIVE-04).

    Estado vazio honesto (D-04, regra sagrada): sem telemetria → série vazia,
    acumulados None, tem_dado False. Nunca lança, nunca inventa número. Mês ou
    medida ausente nunca vira 0 — aparece como ausência, não como zero medido.

    Com dado: soma os municípios por mês (group_by, não loop) e ordena por mês
    para determinismo (Pitfall 4 — sem relógio, ordenação estável). Para cada
    mês, computa o projetado_* via model.project() sobre o desviado real do mês
    (÷12, base mensal — D-07/D-08, Pitfall 2). Mês sem t_org_coletada →
    projetado_* = None (nunca zero).

    Os 4 acumulados (D-11): desvio de aterro (t), renda a catadores (R$), larva
    seca (t) e frass (t) — somados do REAL. Acrescenta os derivados que dependem
    de coeficiente sobre o desviado real acumulado (co2e evitado t + carros
    equivalentes), via model.project(), claramente rotulados como DERIVADOS (não
    medidos direto). coefficients.yml e model.project() permanecem inalterados.
    """
    if operacao.height == 0 or "mes" not in operacao.columns:
        return {"serie": [], "acumulados": None, "tem_dado": False}

    # Soma que PRESERVA null: mês com todas as medidas ausentes fica null, não 0
    # (regra sagrada — Polars .sum() de grupo all-null devolve 0; aqui não pode).
    def _soma_honesta(col: str, alias: str) -> pl.Expr:
        return (
            pl.when(pl.col(col).is_not_null().any())
              .then(pl.col(col).sum())
              .otherwise(pl.lit(None))
              .alias(alias)
        )

    serie_df = operacao.group_by("mes").agg([
        _soma_honesta("n_clientes", "n_clientes"),
        _soma_honesta("t_org_coletada", "real_desviado_t"),
        _soma_honesta("larva_seca_t", "real_larva_seca_t"),
        _soma_honesta("frass_t", "real_frass_t"),
        _soma_honesta("partilha_rs", "real_partilha_rs"),
    ]).sort("mes")

    # Enriquecer cada mês com o projetado da calibração (model alimentado pelo real).
    serie = serie_df.to_dicts()
    for linha in serie:
        linha.update(_projetado_mensal(linha.get("real_desviado_t"), coef))

    desviado_total = float(serie_df["real_desviado_t"].sum() or 0)
    acumulados = {
        "desviado_t": desviado_total,
        "partilha_rs": float(serie_df["real_partilha_rs"].sum() or 0),
        "larva_seca_t": float(serie_df["real_larva_seca_t"].sum() or 0),
        "frass_t": float(serie_df["real_frass_t"].sum() or 0),
    }
    # Derivados de coeficiente sobre o desviado REAL acumulado (D-11): co2e
    # evitado e carros equivalentes não são medidos direto — vêm de project()
    # sobre o total desviado, rotulados como derivados no payload/painel.
    if desviado_total > 0:
        # _projetado_mensal devolve co2e em base "mensal" para um desviado mensal;
        # como a conversão é linear em desviado, passar o TOTAL acumulado e ler o
        # campo mensal dá exatamente co2e = desviado_total * co2e_por_t_organico
        # (o ×12 da anualização e o ÷12 do retorno se cancelam). NÃO multiplicar.
        deriv = _projetado_mensal(desviado_total, coef)
        acumulados["co2e_evitado_t_derivado"] = round(deriv["projetado_co2e_t"], 2)
        # carros: co2e / co2e_por_carro_ano (mesma equivalência de project())
        acumulados["carros_equivalente_derivado"] = round(
            acumulados["co2e_evitado_t_derivado"] / coef["clima"]["co2e_por_carro_ano"], 1
        )
    else:
        acumulados["co2e_evitado_t_derivado"] = None
        acumulados["carros_equivalente_derivado"] = None

    return {"serie": serie, "acumulados": acumulados, "tem_dado": True}
