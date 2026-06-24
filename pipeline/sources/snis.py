"""Fonte SNIS-RS: indicadores de resíduos sólidos por município.

Offline (padrão): lê todos os CSVs em data/raw/snis/.
Refresh (requer rede): use `obs refresh-snis --region <chave>` para baixar
dados do portal SNIS Série Histórica e gravar data/raw/snis/snis_<chave>.csv.
A pipeline reprocessa tudo de forma determinística.

Esquema esperado (colunas):
  municipio, uf, ano, rsu_t_ano, reciclado_t_ano, reciclado_pct,
  coleta_seletiva_pop_pct, cooperados, custo_mensal_rs, qualidade, fonte
Campos vazios viram null -> o município aparece como 'pendente' no painel.
"""
from __future__ import annotations
import sys
from pathlib import Path
import polars as pl
import yaml

from .base import slug

RAW = Path("data/raw/snis")

SCHEMA = {
    "municipio": pl.String, "uf": pl.String, "ano": pl.Int64,
    "rsu_t_ano": pl.Float64, "reciclado_t_ano": pl.Float64,
    "reciclado_pct": pl.Float64, "coleta_seletiva_pop_pct": pl.Float64,
    "cooperados": pl.Float64, "custo_mensal_rs": pl.Float64,
    "qualidade": pl.String, "fonte": pl.String,
    # por-município: composição orgânica local (null = usa fallback global em transform.py)
    "composicao_organico": pl.Float64,
    "composicao_fonte": pl.String,
}


def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        # Inclui coluna 'key' para que os joins em transform.build_region() não falhem
        # quando nenhum CSV existe (ex.: cold-start antes do primeiro refresh-snis)
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    # mantém o ano mais recente por município
    df = (
        df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
          .sort("ano", descending=True)
          .unique(subset=["key"], keep="first")
    )
    return df


def refresh(region: str, root: Path = Path("."),
            ano: str | None = None,
            exclude: list[str] | None = None) -> None:
    """Baixa dados SNIS-RS para a região via scraper e grava
    data/raw/snis/snis_{region}.csv (D-08). Requer rede.

    O build offline usa apenas load(). Import de requests é lazy
    (ocorre dentro de _session() em scrape_snis.py — não vaza ao importar snis).

    Segurança (T-04-09): region é validada contra regions.yml via yaml.safe_load
    ANTES de montar o caminho do arquivo — evita path traversal.
    """
    import argparse

    # Validar region via yaml.safe_load antes de montar caminho (T-04-09/T-04-10)
    regions_path = root / "config" / "regions.yml"
    regions = yaml.safe_load(regions_path.read_text(encoding="utf-8"))
    if region not in regions:
        print(f"Região '{region}' não existe. Veja: obs regions", file=sys.stderr)
        return

    scripts_dir = str(root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from scrape_snis import cmd_build  # noqa: PLC0415

    out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
    # IN-01: confinamento de caminho — garante que o arquivo de saída
    # permanece dentro de data/raw/snis/, mesmo que a chave no YAML
    # contenha separadores de caminho (ex.: "../evil").
    snis_dir = (root / "data" / "raw" / "snis").resolve()
    if not out.resolve().is_relative_to(snis_dir):
        print(
            f"Erro: caminho de saída '{out.resolve()}' fora do diretório permitido "
            f"'{snis_dir}'. Chave de região inválida.",
            file=sys.stderr,
        )
        return
    args = argparse.Namespace(
        region=region, ano=ano, exclude=exclude or [], out=out,
    )
    cmd_build(args)
