"""Extrai o SNIS-RS (Resíduos Sólidos) da Série Histórica oficial para uma região.

Por que este script existe: o portal oficial do SNIS (app4.cidades.gov.br) não
tem API de download pública, e a Base dos Dados (BigQuery) só espelha SNIS de
água/esgoto — NÃO tem resíduos sólidos. Este script conversa com o backend
jqGrid da Série Histórica (controlador `consolidadoMunicipio`, tipo_info=3) para
obter os indicadores de RSU por município. É a semente do
`pipeline/sources/snis.py::refresh()` (ver GSD.md, M4 / GEN-02).

REGRA SAGRADA (CLAUDE.md): nunca inventar número. Município sem linha no SNIS
sai como `pendente` (rsu_t_ano vazio). Todo dado real cita sua `fonte`, listando
os campos SNIS usados e a data de download.

Pré-requisitos:
    uv add --group dev requests   (já feito)

Uso:
    python scripts/scrape_snis.py --region rms \
        --exclude sorocaba "porto feliz"   # já têm dado citável no sample
    # -> escreve data/raw/snis/snis_rms_sp.csv

Depois: `uv run obs build --region rms && uv run pytest -q`.

Mapa do protocolo (decifrado por engenharia reversa do app Yii + jqGrid):
  1. Sessão: GET municipio/index -> POST consolidadoMunicipio/index {ajax,action}.
  2. Campos do form são Yii-prefixados: ShMunicipios[<campo>][].
  3. cod_mun = código IBGE de 6 dígitos (sem dígito verificador).
  4. fk_glossario = id numérico do indicador (sem o prefixo "xxx" da UI).
  5. getGridConfig é assíncrono: chamar com starting=1, depois fazer POLL até a
     resposta conter colModel (a ordem real das colunas).
  6. getGridData devolve {rows:[{cell:[...]}]}; mapear por colModel name.
"""
from __future__ import annotations

import argparse
import sys
import time
import random
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.sources.base import slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ROOT / "config" / "regions.yml"
OUT_DEFAULT = ROOT / "data" / "raw" / "snis" / "snis_rms_sp.csv"

BASE = "https://app4.cidades.gov.br/serieHistorica/"
MODEL = "ShMunicipios"  # prefixo Yii dos campos do form consolidadoMunicipio

# Indicador do projeto -> (código SNIS legível, nome da coluna no colModel,
# id fk_glossario sem o prefixo "xxx"). Resolvido por --inspect contra o portal.
FK = {
    "co116": ("CO116", "co116", "39345"),  # RDO+RPU coletada pelo agente público
    "co117": ("CO117", "co117", "39178"),  # RDO+RPU coletada pelos agentes privados
    "co142": ("CO142", "co142", "39261"),  # RDO+RPU coletada por outros agentes
    "cs048": ("CS048", "cs048", "39115"),  # coleta seletiva por coop. c/ apoio
    "cs026": ("CS026", "cs026", "39162"),  # total recolhido coleta seletiva
    "in031_rs": ("IN031_RS", "in031_rs", "39223"),  # taxa recuperação recicláveis
    "in030_rs": ("IN030_RS", "in030_rs", "39090"),  # cobertura coleta seletiva
    "fn220": ("FN220", "fn220", "38502"),  # despesa total manejo RSU (anual)
}
# Famílias de informações RS (necessárias para o servidor validar os indicadores).
COD_FAM_INFO = ["30", "31", "33", "34", "40", "44"]
TIPO_INFO_RS = "3"  # "Municípios com informações de resíduos sólidos"


def _load_region(region_key: str) -> dict:
    regions = yaml.safe_load(REGIONS.read_text(encoding="utf-8"))
    if region_key not in regions:
        sys.exit(f"Região '{region_key}' não existe em {REGIONS}. Veja: uv run obs regions")
    return regions[region_key]


def _session():
    import requests

    s = requests.Session()
    s.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (observatorio-residuos; scrape_snis.py)",
        "Referer": BASE + "municipio/index",
    })
    # Estabelece sessão e carrega o contexto do form consolidado por município.
    s.get(BASE + "municipio/index", timeout=60)
    s.post(BASE + "consolidadoMunicipio/index",
           data={"ajax": "1", "action": "index"}, timeout=60)
    return s


def _get_select(s, element: str, **extra) -> dict:
    data = {"element": element, "ajax": "1", **extra}
    r = s.post(BASE + "consolidadoMunicipio/getSelectOpt", data=data, timeout=120).json()
    return r.get("arrSelect", {}).get(element, {})


def _cod_mun_map(s, uf_nome: str) -> dict[str, str]:
    """slug(nome) -> código de 6 dígitos, para os municípios do estado."""
    allmun = _get_select(s, "cod_mun")
    estado = allmun.get(uf_nome, {})
    out = {}
    for code, label in estado.items():
        nome = label.split("/")[0].strip()
        out[slug(nome)] = code
    return out


def _latest_ano(s) -> str:
    anos = _get_select(s, "ano_ref")  # {"xxx2022": "2022", ...}
    vals = sorted((v for v in anos.values()), reverse=True)
    return vals[0] if vals else "2022"


UF_NOMES = {"SP": "São Paulo"}  # estende conforme novas regiões


def _to_float(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _query_grid(s, codes: list[str], ano: str) -> list[dict]:
    """Roda o fluxo getGridConfig(poll) + getGridData e devolve linhas mapeadas
    por nome de coluna do colModel (não pela ordem de envio)."""
    pairs = [(f"{MODEL}[tipo_info][]", TIPO_INFO_RS), (f"{MODEL}[ano_ref][]", ano)]
    pairs += [(f"{MODEL}[cod_mun][]", c) for c in codes]
    pairs += [(f"{MODEL}[cod_fam_info][]", f) for f in COD_FAM_INFO]
    pairs += [(f"{MODEL}[fk_glossario][]", fk) for _, _, fk in FK.values()]
    form = urlencode(pairs)
    sid = f"{int(time.time() * 1000)}-{random.randint(1, 9999999)}"

    s.post(BASE + "consolidadoMunicipio/getGridConfig",
           data={"data": form, "starting": "1", "search-id": sid}, timeout=120)

    # getGridConfig é assíncrono ("Configurando matriz"): poll até vir colModel.
    cfg = None
    for _ in range(30):
        r = s.post(BASE + "consolidadoMunicipio/getGridConfig",
                   data={"data": form, "search-id": sid}, timeout=120).json()
        if r.get("colModel"):
            cfg = r
            break
        time.sleep(1)
    if not cfg:
        sys.exit("getGridConfig não retornou colModel (timeout do polling).")
    col_names = [c["name"] for c in cfg["colModel"]]
    # jqGrid só aceita valores de página presentes no rowList; pegar o maior.
    row_list = [int(x) for x in (cfg.get("rowList") or []) if str(x).isdigit()]
    per_page = max(row_list) if row_list else 50

    rows: list[dict] = []
    page = 1
    while True:
        gd = s.post(BASE + "consolidadoMunicipio/getGridData",
                    data={"data": form, "search-id": sid, "page": str(page),
                          "rows": str(per_page), "sidx": "nom_mun", "sord": "asc"},
                    timeout=120).json()
        if gd.get("status") == "erro":
            sys.exit(f"getGridData falhou: {gd.get('msg')}")
        for r in gd.get("rows", []):
            rows.append(dict(zip(col_names, r["cell"])))
        total = int(gd.get("total", 1) or 1)
        if page >= total:
            break
        page += 1
    return rows


def cmd_inspect(args) -> int:
    s = _session()
    print("✓ Sessão estabelecida.")
    print("\nano_ref (mais recente):", _latest_ano(s))
    uf = _load_region(args.region).get("uf", "SP")
    cmap = _cod_mun_map(s, UF_NOMES.get(uf, uf))
    print(f"cod_mun de {uf}: {len(cmap)} municípios resolvidos.")
    print("\nMapeamento de colunas (uma consulta de teste em Sorocaba 355220):")
    rows = _query_grid(s, ["355220"], "2022")
    if rows:
        for k, v in rows[0].items():
            print(f"  {k:14} = {v}")
    return 0


def cmd_build(args) -> int:
    import polars as pl

    meta = _load_region(args.region)
    uf = meta.get("uf", "SP")
    exclude = {slug(x) for x in (args.exclude or [])}
    wanted = {slug(m["nome"]): m for m in meta["municipios"]
              if slug(m["nome"]) not in exclude}

    s = _session()
    ano = args.ano or _latest_ano(s)
    cmap = _cod_mun_map(s, UF_NOMES.get(uf, uf))

    code2key, unresolved = {}, []
    for key in wanted:
        code = cmap.get(key)
        if code:
            code2key[code] = key
        else:
            unresolved.append(wanted[key]["nome"])
    if unresolved:
        print(f"⚠ Municípios não resolvidos no SNIS (verifique o nome em regions.yml): {unresolved}")

    grid = _query_grid(s, list(code2key), ano) if code2key else []
    by_key = {}
    for row in grid:
        key = code2key.get(str(row.get("cod_mun")))
        if key:
            by_key[key] = row

    download = date.today().isoformat()
    fonte_base = (f"SNIS-RS {ano} via Série Histórica oficial "
                  f"(app4.cidades.gov.br, consolidadoMunicipio tipo_info=3); download {download}")

    schema_cols = [
        "municipio", "uf", "ano", "rsu_t_ano", "reciclado_t_ano", "reciclado_pct",
        "coleta_seletiva_pop_pct", "cooperados", "custo_mensal_rs", "qualidade",
        "fonte", "composicao_organico", "composicao_fonte",
    ]
    rows: list[dict] = []
    n_real = n_pend = 0
    for key, m in wanted.items():
        rec = {c: "" for c in schema_cols}
        rec["municipio"], rec["uf"] = m["nome"], m["uf"]
        data = by_key.get(key)

        comps = {}
        if data:
            for proj_col in ("co116", "co117", "co142", "cs048", "cs026",
                             "in031_rs", "in030_rs", "fn220"):
                comps[proj_col] = _to_float(data.get(FK[proj_col][1]))

        # rsu = CO116 + CO117 + CO142 + CS048 (plano 01-02); null se nenhum presente
        rsu_parts = [comps.get(k) for k in ("co116", "co117", "co142", "cs048")]
        rsu = sum(p for p in rsu_parts if p is not None) if any(p is not None for p in rsu_parts) else None
        custo_anual = comps.get("fn220")
        custo_mensal = round(custo_anual / 12, 2) if custo_anual is not None else None

        tem_dado = data is not None and (rsu is not None or comps.get("cs026") is not None
                                         or custo_mensal is not None)
        if tem_dado:
            n_real += 1
            rec["ano"] = ano
            rec["rsu_t_ano"] = "" if rsu is None else rsu
            rec["reciclado_t_ano"] = "" if comps.get("cs026") is None else comps["cs026"]
            rec["reciclado_pct"] = "" if comps.get("in031_rs") is None else comps["in031_rs"]
            rec["coleta_seletiva_pop_pct"] = "" if comps.get("in030_rs") is None else comps["in030_rs"]
            rec["cooperados"] = ""  # SNIS-RS não traz campo de cooperados confiável (CA002/CA003 ambíguos)
            rec["custo_mensal_rs"] = "" if custo_mensal is None else custo_mensal
            rec["qualidade"] = "real"
            partes = "+".join(f"{FK[k][0]}={comps[k]}" for k in ("co116", "co117", "co142", "cs048")
                              if comps.get(k) is not None)
            rec["fonte"] = (f"{fonte_base}. rsu_t_ano={partes or '—'}; "
                            f"reciclado=CS026; reciclado_pct=IN031_RS; "
                            f"coleta_seletiva_pop_pct=IN030_RS; custo_mensal_rs=FN220/12. "
                            f"Autodeclarado pela prefeitura — tratar como piso")
            rec["composicao_fonte"] = "média Brasil (estimativa)"
        else:
            n_pend += 1
            rec["qualidade"] = "pendente"
            rec["fonte"] = f"{fonte_base} — município sem dado de resíduos sólidos no SNIS-RS {ano}"
        rows.append(rec)

    out = pl.DataFrame([{c: r[c] for c in schema_cols} for r in rows]).sort("municipio")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.write_csv(args.out)

    print(f"\n✓ {args.out}")
    print(f"  {len(rows)} municípios: {n_real} com dado real, {n_pend} pendentes "
          f"(ano {ano}; excluídos: {sorted(exclude)})")
    print("  Rode: uv run obs build --region rms && uv run pytest -q")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extrai SNIS-RS da Série Histórica oficial")
    p.add_argument("--inspect", action="store_true", help="testa sessão e mostra mapeamento de colunas")
    p.add_argument("--build", action="store_true", help="monta o CSV no schema do projeto")
    p.add_argument("--region", default="rms", help="chave da região em config/regions.yml")
    p.add_argument("--ano", default=None, help="ano de referência (padrão: mais recente)")
    p.add_argument("--exclude", nargs="*", default=[], help="municípios a pular (já têm dado citável)")
    p.add_argument("--out", type=Path, default=OUT_DEFAULT, help="caminho do CSV de saída")
    args = p.parse_args(argv)

    if args.inspect:
        return cmd_inspect(args)
    if args.build:
        return cmd_build(args)
    p.error("informe --inspect ou --build")


if __name__ == "__main__":
    raise SystemExit(main())
