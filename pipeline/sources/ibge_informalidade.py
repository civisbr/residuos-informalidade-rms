"""Fonte Censo 2022 IBGE: indicador de informalidade do trabalho por município.

Offline (padrão): lê todos os CSVs em data/raw/censo/.
Refresh: chama apisidra.ibge.gov.br/values/t/10261 e recalcula a taxa com os
5 componentes da definição IBGE (sem carteira + conta própria sem CNPJ + familiar).
Ver scripts/fetch_censo.py (Fase 4, GEN-02). Build permanece offline e determinístico.

Esquema esperado (colunas):
  municipio, uf, codigo_ibge, total_ocupados, informais, taxa_informalidade_pct,
  ano_censo, fonte
Campos extras no CSV são ignorados por Polars.
Chave de junção: key = slug(municipio) — NÃO usar codigo_ibge para join.
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug

RAW = Path("data/raw/censo")

SCHEMA: dict[str, type] = {
    "municipio": pl.String,
    "uf": pl.String,
    "codigo_ibge": pl.String,           # 7 dígitos (ex: "3552205")
    "total_ocupados": pl.Int64,
    "informais": pl.Int64,
    "taxa_informalidade_pct": pl.Float64,
    "ano_censo": pl.Int64,              # sempre 2022 no snapshot atual
    "fonte": pl.String,
}

# Códigos IBGE 7 dígitos dos 27 municípios da RMS (SP)
# Verificados via servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios
# Usados em refresh() — NÃO alterar sem verificar na API.
RMS_IBGE_CODES: list[str] = [
    "3500758",  # Alambari
    "3501152",  # Alumínio
    "3502754",  # Araçariguama
    "3502903",  # Araçoiaba da Serra
    "3507001",  # Boituva
    "3510302",  # Capela do Alto
    "3511508",  # Cerquilho
    "3511607",  # Cesário Lange
    "3519709",  # Ibiúna
    "3521002",  # Iperó
    "3522307",  # Itapetininga
    "3523909",  # Itu
    "3525854",  # Jumirim
    "3528403",  # Mairinque
    "3537800",  # Piedade
    "3537909",  # Pilar do Sul
    "3540606",  # Porto Feliz
    "3545209",  # Salto
    "3545308",  # Salto de Pirapora
    "3551108",  # Sarapuí
    "3552205",  # Sorocaba
    "3550209",  # São Miguel Arcanjo
    "3550605",  # São Roque
    "3553500",  # Tapiraí
    "3554003",  # Tatuí
    "3554508",  # Tietê
    "3557006",  # Votorantim
]


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega snapshot offline do Censo 2022 — informalidade por município.

    Retorna DataFrame com 27 linhas (uma por município da RMS) quando o CSV
    de snapshot existe. Retorna DataFrame vazio com SCHEMA correto se não
    houver arquivos (ex.: ambiente CI sem dados).

    Chave de junção: coluna 'key' = slug(municipio). Usar key para joins,
    não codigo_ibge (pitfall 1 — ver RESEARCH.md).
    """
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [
        pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0)
        for f in files
    ]
    df = pl.concat(frames, how="vertical_relaxed")
    # dedup: mantém ano_censo mais recente por município
    df = (
        df.with_columns(
            pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")
        )
        .sort("ano_censo", descending=True)
        .unique(subset=["key"], keep="first")
    )
    return df


def refresh(root: Path = Path(".")) -> None:  # noqa: ARG001
    """Baixa dados via SIDRA API e regrava data/raw/censo/.

    URL de referência (5 componentes de informalidade IBGE):
      https://apisidra.ibge.gov.br/values/t/10261/n6/{RMS_CODES}/v/4090/p/2022/
        c11913/96165,31723,79368,45935,45937,31731/c2/6794/c86/95251

    Componentes informais (c11913):
      31723  — empregado setor privado sem carteira
      79368  — trabalhador doméstico sem carteira
      45935  — empregador sem CNPJ
      45937  — conta própria sem CNPJ
      31731  — trabalhador familiar auxiliar
    Total (denominador): 96165

    Filtros obrigatórios: c2/6794 (sexo=Total) e c86/95251 (raça=Total)
    para evitar duplicatas na resposta SIDRA.

    Fonte autoritativa: https://sidra.ibge.gov.br/tabela/10261
    Implementação completa: ver scripts/fetch_censo.py (Fase 4, GEN-02).
    """
    raise NotImplementedError(
        "Refresh Censo 2022 não implementado nesta fase. "
        "Ver scripts/fetch_censo.py (planejado para Fase 4, GEN-02). "
        f"URL base: https://apisidra.ibge.gov.br/values/t/10261/n6/"
        f"{','.join(RMS_IBGE_CODES)}/v/4090/p/2022"
        "/c11913/96165,31723,79368,45935,45937,31731/c2/6794/c86/95251"
    )
