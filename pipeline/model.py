"""Modelo de impacto Coleta + BSF.

PROJEÇÃO, NÃO MEDIÇÃO. Recebe parâmetros operacionais e coeficientes e
devolve o impacto estimado. A mesma lógica roda no painel (app.js) para o
simulador interativo; aqui ela serve ao build e a testes.
"""
from __future__ import annotations


def project(clientes: int, kg_dia: float, partilha_pct: float, gate_fee: float,
            coef: dict, organico_municipal_t_ano: float | None = None) -> dict:
    bsf = coef["bsf"]
    clima = coef["clima"]
    op = coef["operacao"]

    desviado_t_ano = clientes * kg_dia / 1000 * 365
    co2e_t_ano = desviado_t_ano * clima["co2e_por_t_organico"]
    larva_umida = desviado_t_ano * bsf["conversao_larva_umida"]
    larva_seca = larva_umida * bsf["larva_seca_sobre_umida"]
    frass = desviado_t_ano * bsf["frass_sobre_organico"]

    receita_ano = clientes * gate_fee * 12
    fundo_partilha = receita_ano * partilha_pct / 100
    catadores = fundo_partilha / (op["renda_alvo_catador_mes"] * 12)

    pct_organico = (
        desviado_t_ano / organico_municipal_t_ano * 100
        if organico_municipal_t_ano else None
    )

    return {
        "desviado_t_ano": round(desviado_t_ano, 1),
        "pct_organico_municipal": round(pct_organico, 2) if pct_organico is not None else None,
        "co2e_t_ano": round(co2e_t_ano, 1),
        "carros_equivalente": round(co2e_t_ano / clima["co2e_por_carro_ano"], 1),
        "larva_seca_t_ano": round(larva_seca, 1),
        "frass_t_ano": round(frass, 1),
        "receita_ano": round(receita_ano, 2),
        "fundo_partilha_ano": round(fundo_partilha, 2),
        "catadores_sustentados": round(catadores, 1),
    }


def defaults(coef: dict) -> dict:
    op = coef["operacao"]
    return {
        "clientes": op["break_even_clientes"],
        "kg_dia": op["organico_por_cliente_kg_dia"],
        "partilha_pct": op["partilha_padrao_pct"],
        "gate_fee": op["gate_fee_padrao_mes"],
    }
