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

from .sources import ibge, snis, ibge_informalidade, rais, pnad_regional
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

    # Carregar todas as fontes (offline — determinístico)
    df_ibge = ibge.load(root)
    df_snis = snis.load(root)
    df_inf = ibge_informalidade.load(root)
    df_rais = rais.load(root)
    df_pnad = pnad_regional.load(root)

    df = transform.build_region(meta["municipios"], df_ibge, df_snis, df_inf, df_rais, coef)
    totals = transform.region_totals(df)
    payload = render.to_payload(args.region, meta, df, totals, coef, pnad_df=df_pnad)
    out = render.write(payload, root)

    com = totals["municipios_com_dado"]
    tot = totals["municipios_total"]
    print(f"✓ {out} — {meta['nome']}: {com}/{tot} municípios com dado público")
    print(f"  RSU total: {totals['rsu_t_ano']:,.0f} t/ano · "
          f"orgânico: {totals['organico_t_ano']:,.0f} t/ano")
    taxa_inf = totals.get("taxa_inf_media")
    if taxa_inf is not None:
        print(f"  Informalidade média {meta['nome']}: {taxa_inf:.1f}% (Censo 2022, ponderado por ocupados)")
    if com < tot:
        print(f"  {tot - com} municípios pendentes — rode o refresh do SNIS "
              f"(scripts/refresh_snis.md)")
    return 0


def cmd_regions(_args) -> int:
    regions = _load_yaml(Path("config/regions.yml"))
    for k, v in regions.items():
        print(f"  {k:14} {v['nome']} ({len(v['municipios'])} municípios)")
    return 0


def cmd_refresh_ibge(args) -> int:
    ibge.refresh(args.region, Path("."))
    return 0


def cmd_refresh_snis(args) -> int:
    snis.refresh(args.region, Path("."), ano=args.ano, exclude=args.exclude or [])
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="obs", description="Observatório de Resíduos & Informalidade")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="gera site/data.json")
    b.add_argument("--region", default="rms")
    b.set_defaults(func=cmd_build)

    sub.add_parser("regions", help="lista regiões").set_defaults(func=cmd_regions)

    ri = sub.add_parser("refresh-ibge", help="atualiza IBGE via API")
    ri.add_argument("--region", required=True, help="chave da região em config/regions.yml")
    ri.set_defaults(func=cmd_refresh_ibge)

    rs = sub.add_parser("refresh-snis", help="baixa dados SNIS-RS via scraper (requer rede)")
    rs.add_argument("--region", required=True, help="chave da região em config/regions.yml")
    rs.add_argument("--ano", default=None, help="ano de referência (padrão: mais recente do portal)")
    rs.add_argument("--exclude", nargs="*", default=[], help="municípios a pular (já têm dado citável)")
    rs.set_defaults(func=cmd_refresh_snis)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
