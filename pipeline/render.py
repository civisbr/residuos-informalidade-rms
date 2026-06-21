"""Renderização: monta site/data.json — o artefato que o painel consome.

O painel (site/index.html) é estático e lê este JSON. Commitar o data.json
gerado faz o GitHub Pages funcionar sem build no servidor.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import polars as pl

from . import model


def to_payload(region_key: str, region_meta: dict, df: pl.DataFrame,
               totals: dict, coef: dict) -> dict:
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
        })

    return {
        "meta": {
            "regiao_key": region_key,
            "regiao_nome": region_meta["nome"],
            "destaque": region_meta.get("destaque"),
            "gerado_em": date.today().isoformat(),
            "fonte_baseline": "SNIS/SINISA, PMGIRS, IBGE, transparência municipal",
            "aviso": ("Baseline = dado público (defasagem anual do SNIS). "
                      "Simulador = projeção de modelo; calibre antes de publicar."),
        },
        "coeficientes": coef,
        "simulador_defaults": model.defaults(coef),
        "totais": totals,
        "municipios": municipios,
    }


def write(payload: dict, root: Path = Path(".")) -> Path:
    out = root / "site" / "data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
