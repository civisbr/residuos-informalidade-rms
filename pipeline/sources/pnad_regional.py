"""Fonte PNAD Contínua: taxa de informalidade regional (estado SP).

Offline (padrão): lê data/raw/pnad/pnad_sp_informalidade.csv.
Refresh: consulta apisidra.ibge.gov.br/values/t/4093/n3/35/v/12466/p/last.

ATENÇÃO — Restrição de uso (D-02 de 02-CONTEXT.md):
  Este dado NÃO é representativo no nível municipal.
  A PNAD só vai no campo 'meta.pnad_contexto_regional' do data.json,
  NUNCA em 'municipios[]'. Exibir com âmbito explícito: "Estado de SP".

Flag: 'estimativa' — contexto regional, não medição por município.

Esquema esperado (colunas):
  uf, periodo, taxa_informalidade_pct, flag, ambito, fonte
Não há coluna 'municipio' neste módulo (invariante de design).
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

RAW = Path("data/raw/pnad")

SCHEMA: dict[str, type] = {
    "uf": pl.String,
    "periodo": pl.String,
    "taxa_informalidade_pct": pl.Float64,
    "flag": pl.String,          # sempre 'estimativa'
    "ambito": pl.String,        # sempre 'Estado de São Paulo'
    "fonte": pl.String,
}
# Nota: SCHEMA não inclui 'municipio' — invariante do módulo (D-02).


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega snapshot offline da PNAD Contínua — contexto regional SP.

    Retorna DataFrame com 1 linha (estado SP, trimestre mais recente disponível).
    flag='estimativa', ambito='Estado de São Paulo'.
    NÃO retorna coluna 'municipio' — dado não é representativo no nível municipal.

    Se o arquivo não existir, retorna DataFrame vazio com SCHEMA correto.
    """
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [
        pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0)
        for f in files
    ]
    df = pl.concat(frames, how="vertical_relaxed")
    return df


def refresh(root: Path = Path(".")) -> None:  # noqa: ARG001
    """Baixa dado mais recente via SIDRA API e regrava data/raw/pnad/.

    URL:
      https://apisidra.ibge.gov.br/values/t/4093/n3/35/v/12466/p/last/c2/6794

    Parâmetros:
      t/4093  — PNAD Contínua Trimestral (taxa de informalidade)
      n3/35   — nível UF, código SP=35
      v/12466 — taxa de informalidade das pessoas ocupadas
      p/last  — trimestre mais recente disponível
      c2/6794 — sexo=Total (obrigatório para evitar duplicatas)

    ATENÇÃO: Região Metropolitana de Sorocaba NÃO tem representatividade
    amostral na PNAD (código 05301 retorna erro no nível N7/N14).
    O nível UF (N3) é o mais específico disponível.

    Implementação completa: ver scripts/fetch_pnad.py (Fase 4, GEN-02).
    """
    raise NotImplementedError(
        "Refresh PNAD não implementado nesta fase. "
        "Ver scripts/fetch_pnad.py (planejado para Fase 4, GEN-02). "
        "URL: https://apisidra.ibge.gov.br/values/t/4093/n3/35/v/12466/p/last/c2/6794"
    )
