"""Fonte IBGE: código do município e população.

Offline (padrão): lê config/municipios.csv — build determinístico, sem rede.
Refresh (obs refresh-ibge --region <chave>): consulta a API pública do IBGE
e faz upsert idempotente no cache (D-04/D-05/D-06).

APIs usadas (sem autenticação):
  Localidades: https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios
  População:   https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022
"""
from __future__ import annotations
import difflib
import sys
from pathlib import Path
import polars as pl
import yaml

from .base import slug

CACHE = Path("config/municipios.csv")


def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega o cache offline de municípios."""
    df = pl.read_csv(_root / CACHE)
    return df.with_columns(pl.col("nome").map_elements(slug, return_dtype=pl.String).alias("key"))


def refresh(region: str, root: Path = Path(".")) -> None:
    """Atualiza códigos IBGE e população a partir da API oficial (Censo 2022).

    Requer rede. Resolve SÓ os municípios da região alvo e faz upsert
    idempotente em config/municipios.csv (D-04/D-05/D-06).

    Fontes:
      - Localidades: GET /api/v1/localidades/estados/{UF}/municipios (id + nome)
      - População:   GET /values/t/4714/n6/all/v/93/p/2022 (Censo 2022, variável 93)

    Comportamento (D-06): só preenche campos onde codigo_ibge OU populacao
    estão vazios. Linhas com ambos preenchidos são preservadas (curadoria manual).
    Idempotente: rodar 2x não altera linhas já completas.

    Erro amigável (D-09): município que não resolve gera aviso com sugestão
    via difflib.get_close_matches, sem stacktrace, continua os demais.
    """
    import httpx

    # --- 1. Carregar regions.yml e validar região ---
    regions_path = root / "config" / "regions.yml"
    regions = yaml.safe_load(regions_path.read_text(encoding="utf-8"))
    if region not in regions:
        print(
            f"Região '{region}' não existe em {regions_path}. Veja: obs regions",
            file=sys.stderr,
        )
        return
    meta = regions[region]
    uf: str = meta.get("uf", "")

    # --- 2. Baixar mapa de localidades da UF (id 7 dígitos + nome) ---
    print(f"Buscando municípios de {uf} na API IBGE localidades...")
    with httpx.Client(timeout=60) as client:
        resp = client.get(
            f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        )
        resp.raise_for_status()
        muns = resp.json()

    # slug(nome) -> dict com id (int 7 dígitos) e nome (str)
    localidades_map: dict[str, dict] = {slug(m["nome"]): m for m in muns}

    # --- 3. Baixar população Censo 2022 para todos os municípios BR (batch único) ---
    print("Buscando população Censo 2022 na API SIDRA (t/4714, ~1.4 MB)...")
    with httpx.Client(timeout=120) as client:
        resp = client.get(
            "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022"
        )
        resp.raise_for_status()
        sidra_rows = resp.json()[1:]  # data[0] é header — Pitfall 6

    # D1C (str 7 dígitos) -> populacao (int) — só onde V é dígito (Pitfall 6 / T-04-04)
    pop_map: dict[str, int] = {
        r["D1C"]: int(r["V"])
        for r in sidra_rows
        if r.get("V", "").isdigit()
    }

    # --- 4. Ler cache existente ou criar DataFrame vazio com schema correto ---
    cache_path = root / CACHE
    if cache_path.exists():
        df = pl.read_csv(cache_path)
    else:
        df = pl.DataFrame(schema={
            "nome": pl.String,
            "uf": pl.String,
            "codigo_ibge": pl.String,
            "populacao": pl.Int64,
            "fonte_pop": pl.String,
        })

    # --- 5. Upsert idempotente para cada município da região ---
    unresolved: list[str] = []
    n_preenchidos: int = 0

    for m in meta["municipios"]:
        nome_mun = m["nome"]
        key = slug(nome_mun)

        # Filtrar linha do cache por slug
        mask = df.select(
            pl.col("nome").map_elements(slug, return_dtype=pl.String) == key
        ).to_series()
        row_df = df.filter(mask)

        # D-06: se linha existe E ambos os campos estão preenchidos → preservar curadoria
        if row_df.height > 0:
            r = row_df.row(0, named=True)
            codigo = r.get("codigo_ibge")
            pop = r.get("populacao")
            if codigo and pop:
                continue  # dado curado preservado (ex: Sorocaba 709000)

        # Resolver nome via localidades_map
        loc = localidades_map.get(key)
        if loc is None:
            # D-09: sugestão de nome com difflib
            candidates_slug = list(localidades_map.keys())
            matches = difflib.get_close_matches(key, candidates_slug, n=1, cutoff=0.6)
            msg = f"Município '{nome_mun}' ({uf}) não encontrado no IBGE"
            if matches:
                sugestao_nome = localidades_map[matches[0]]["nome"]
                msg += f" — você quis dizer '{sugestao_nome}'?"
            print(f"  Aviso: {msg}", file=sys.stderr)
            unresolved.append(nome_mun)
            continue

        id_7dig = str(loc["id"])
        pop_value = pop_map.get(id_7dig)

        # Construir linha atualizada
        new_row: dict = {
            "nome": nome_mun,
            "uf": uf,
            "codigo_ibge": id_7dig,
            "populacao": pop_value,
            "fonte_pop": "IBGE Censo 2022",  # D-05: literal exato
        }

        if row_df.height > 0:
            # Atualizar linha existente: remover a linha antiga e adicionar a nova
            df = df.filter(~mask)

        # Adicionar linha nova/atualizada
        df = pl.concat(
            [df, pl.DataFrame([new_row], schema={
                "nome": pl.String,
                "uf": pl.String,
                "codigo_ibge": pl.String,
                "populacao": pl.Int64,
                "fonte_pop": pl.String,
            })],
            how="diagonal_relaxed",
        )
        n_preenchidos += 1

    # --- 6. Reescrever cache ---
    df.write_csv(cache_path)

    # --- 7. Resumo (D-09) ---
    print(f"config/municipios.csv atualizado — {n_preenchidos} municípios resolvidos")
    if unresolved:
        print(f"\nMunicípios não resolvidos ({len(unresolved)}): {unresolved}", file=sys.stderr)
