"""Renderização: monta site/data.json — o artefato que o painel consome.

O painel (site/index.html) é estático e lê este JSON. Commitar o data.json
gerado faz o GitHub Pages funcionar sem rebuild no servidor.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import polars as pl

from . import model


def to_payload(region_key: str, region_meta: dict, df: pl.DataFrame,
               totals: dict, coef: dict, pnad_df: pl.DataFrame | None = None,
               operacao_payload: dict | None = None) -> dict:
    municipios = []
    for r in df.iter_rows(named=True):
        municipios.append({
            "nome": r["nome"], "uf": r["uf"], "subregiao": r["subregiao"],
            "codigo_ibge": r["codigo_ibge"], "populacao": r["populacao"],
            "ano": r["ano"], "flag": r["flag"], "fonte": r["fonte"],
            "rsu_t_ano": r["rsu_t_ano"], "organico_t_ano": r["organico_t_ano"],
            "aterro_t_ano": r["aterro_t_ano"], "reciclado_t_ano": r["reciclado_t_ano"],
            "reciclado_pct": r["reciclado_pct"],
            "coleta_seletiva_pop_pct": r["coleta_seletiva_pop_pct"],
            "cooperados": r["cooperados"],
            "custo_mensal_rs": r["custo_mensal_rs"],
            "composicao_fonte": r.get("composicao_fonte"),  # procedência da composição orgânica
            # Camada de informalidade (Fase 2 — Censo 2022 / RAIS 2023)
            "taxa_informalidade_pct": r["taxa_informalidade_pct"],
            "flag_informalidade": r["flag_informalidade"],
            "total_ocupados": r["total_ocupados"],
            "informais": r["informais"],
            "ano_censo": r["ano_censo"],
            "formais_residuos": r["formais_residuos"],
            "ano_rais": r["ano_rais"],
            "proxy_formalizacao": r["proxy_formalizacao"],
            "flag_proxy": r["flag_proxy"],
            "fonte_inf": r.get("fonte_inf"),
        })

    # Contexto PNAD regional — vai APENAS em meta (D-02: PNAD nunca por município)
    pnad_contexto = None
    if pnad_df is not None and pnad_df.height > 0:
        row = pnad_df.row(0, named=True)
        pnad_contexto = {
            "uf": row["uf"],
            "periodo": row["periodo"],
            "taxa_informalidade_pct": row["taxa_informalidade_pct"],
            "flag": row["flag"],
            "ambito": row["ambito"],
            "fonte": row["fonte"],
        }

    return {
        "meta": {
            "regiao_key": region_key,
            "regiao_nome": region_meta["nome"],
            "destaque": region_meta.get("destaque"),
            "gerado_em": os.environ.get("BUILD_DATE", "local")[:10],
            "fonte_baseline": "SNIS/SINISA, PMGIRS, IBGE, transparência municipal",
            "aviso": ("Baseline = dado público (defasagem anual do SNIS). "
                      "Simulador = projeção de modelo; calibre antes de publicar."),
            "pnad_contexto_regional": pnad_contexto,
        },
        "coeficientes": coef,
        "simulador_defaults": model.defaults(coef),
        "totais": totals,
        "municipios": municipios,
        # Telemetria real da operação (LIVE). Chave SEMPRE presente — estado vazio
        # honesto quando não há medição (nunca omitir a chave, nunca inventar número).
        "operacao": operacao_payload if operacao_payload is not None
                    else {"serie": [], "acumulados": None, "tem_dado": False},
    }


def write(payload: dict, root: Path = Path(".")) -> Path:
    out = root / "site" / "data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
