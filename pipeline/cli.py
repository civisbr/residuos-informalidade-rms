"""CLI do Observatório.

  uv run obs build [--region rms]     # gera site/data.json (offline)
  uv run obs regions                  # lista regiões configuradas
  uv run obs refresh-ibge             # atualiza códigos/pop via API IBGE
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import yaml

from .sources import ibge, snis
from . import transform, render


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def cmd_build(args) -> int:
    root = Path(".")
    regions = _load_yaml(root / "config" / "regions.yml")
    coef = _load_yaml(root / "config" / "coefficients.yml")
    if args.region not in regions:
        print(f"Região '{args.region}' não existe. Veja: obs regions", file=sys.stderr)
        return 1

    meta = regions[args.region]
    df = transform.build_region(meta["municipios"], ibge.load(root), snis.load(root), coef)
    totals = transform.region_totals(df)
    payload = render.to_payload(args.region, meta, df, totals, coef)
    out = render.write(payload, root)

    com = totals["municipios_com_dado"]
    tot = totals["municipios_total"]
    print(f"✓ {out} — {meta['nome']}: {com}/{tot} municípios com dado público")
    print(f"  RSU total: {totals['rsu_t_ano']:,.0f} t/ano · "
          f"orgânico: {totals['organico_t_ano']:,.0f} t/ano")
    if com < tot:
        print(f"  {tot - com} municípios pendentes — rode o refresh do SNIS "
              f"(scripts/refresh_snis.md)")
    return 0


def cmd_regions(_args) -> int:
    regions = _load_yaml(Path("config/regions.yml"))
    for k, v in regions.items():
        print(f"  {k:14} {v['nome']} ({len(v['municipios'])} municípios)")
    return 0


def cmd_refresh_ibge(_args) -> int:
    ibge.refresh(Path("."))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="obs", description="Observatório de Resíduos & Informalidade")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="gera site/data.json")
    b.add_argument("--region", default="rms")
    b.set_defaults(func=cmd_build)

    sub.add_parser("regions", help="lista regiões").set_defaults(func=cmd_regions)
    sub.add_parser("refresh-ibge", help="atualiza IBGE via API").set_defaults(func=cmd_refresh_ibge)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
