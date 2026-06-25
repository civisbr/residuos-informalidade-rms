"""Fonte operacao: telemetria REAL da operação de coleta + bioconversão BSF.

Offline (D-04): lê todos os CSVs em data/raw/operacao/. NÃO tem refresh() de
rede — a operação ainda não roda e, quando rodar, o operador edita/substitui o
CSV à mão (ou cola um export da planilha) e roda `uv run obs build`.

Grão = mês × município (D-03): uma linha por (mes AAAA-MM, municipio), com os
agregados daquele município naquele mês. Junção com o baseline público por
`slug(municipio)` (chave canônica do projeto).

Classe de dado: 'real (operação)' — MEDIÇÃO, não projeção e não baseline
público (regra sagrada: as três classes nunca se confundem). Medidas derivadas
(ex.: frass calculado, não pesado) devem ser marcadas com qualidade=estimativa
e a coluna fonte preenchida — nunca chutar número.

Esquema esperado (espelha os outputs de model.project(), D-05; massas em
TONELADAS para casar com os outputs _t_ano):
  mes (AAAA-MM), municipio, n_clientes, t_org_coletada, larva_umida_t,
  larva_seca_t, frass_t, partilha_rs, qualidade, fonte
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug

RAW = Path("data/raw/operacao")

SCHEMA = {  # dtypes explícitos, espelham model.project() (D-05); massas em toneladas
    "mes": pl.String,
    "municipio": pl.String,
    "n_clientes": pl.Int64,
    "t_org_coletada": pl.Float64,
    "larva_umida_t": pl.Float64,
    "larva_seca_t": pl.Float64,
    "frass_t": pl.Float64,
    "partilha_rs": pl.Float64,
    "qualidade": pl.String,
    "fonte": pl.String,
}


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Lê a telemetria operacional offline de data/raw/operacao/*.csv.

    Com ZERO telemetria (só o CSV-template documentado), devolve um frame vazio
    MAS com a coluna 'key' presente — sem isso joins/cold-start lançam
    ColumnNotFoundError (lição CR-01). NÃO faz .unique() por key: o grão é
    mês×município, múltiplas linhas por key são esperadas (D-03).
    """
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        # Inclui coluna 'key' para que cold-start (sem CSV) não quebre downstream.
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    # comment_prefix="#": ignora o cabeçalho documentado em linhas # do template (D-02).
    frames = [
        pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0, comment_prefix="#")
        for f in files
    ]
    df = pl.concat(frames, how="vertical_relaxed").filter(pl.col("mes").is_not_null())
    if df.height == 0:
        # Template sem linhas de dado → estado vazio honesto, mas com coluna key.
        return df.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    return df.with_columns(
        pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")
    )
