# Phase 4: Generalizar para qualquer cidade BR — Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pipeline/sources/ibge.py` | source/service | request-response (refresh) + file-I/O (load) | `pipeline/sources/snis.py` (load pattern) + `scripts/scrape_snis.py` (network pattern) | role-match |
| `pipeline/sources/snis.py` | source/service | file-I/O (load) + request-response (refresh) | `scripts/scrape_snis.py` (cmd_build lógica completa) | exact |
| `scripts/scrape_snis.py` | script/utility | request-response (jqGrid protocol) | self — é o analog; sem mudança nesta fase | exact |
| `pipeline/cli.py` | CLI/controller | request-response | `pipeline/cli.py` itself — extensão dos comandos existentes | exact |
| `pipeline/transform.py` | transform/utility | batch/transform | `pipeline/transform.py` itself — renomear variável + fix sort | exact |
| `pipeline/render.py` | render/utility | transform | `pipeline/render.py` itself — tolerar null já funciona; sem mudança | exact |
| `config/regions.yml` | config | — | `config/regions.yml` itself — formalizar campos opcionais | exact |
| `config/municipios.csv` | data/cache | file-I/O | `config/municipios.csv` itself — alvo do upsert | exact |
| `README.md` | docs | — | `README.md` itself — adicionar seção ao doc existente | exact |
| `tests/test_pipeline.py` | test | batch | `tests/test_pipeline.py` itself — mesma estrutura; novos testes offline | exact |

---

## Pattern Assignments

### `pipeline/sources/ibge.py` — implementar `refresh()` (GEN-01)

**Analog:** `pipeline/sources/snis.py` (padrão load/refresh), `scripts/scrape_snis.py` (padrão de sessão de rede)

**Imports pattern** (ibge.py lines 1-16 existentes + novas adições):
```python
from __future__ import annotations
import difflib
from pathlib import Path
import polars as pl
import yaml

from .base import slug

CACHE = Path("config/municipios.csv")
```

**load() pattern — manter intacto** (ibge.py lines 19-22):
```python
def load(_root: Path = Path(".")) -> pl.DataFrame:
    """Carrega o cache offline de municípios."""
    df = pl.read_csv(_root / CACHE)
    return df.with_columns(pl.col("nome").map_elements(slug, return_dtype=pl.String).alias("key"))
```

**refresh() signature — substituir o NotImplementedError** (ibge.py lines 25-36):
```python
def refresh(region: str, root: Path = Path(".")) -> None:
    """Atualiza códigos IBGE e população a partir da API oficial (Censo 2022).

    Requer rede. Resolve SÓ os municípios da região alvo e faz upsert
    idempotente em config/municipios.csv (D-04/D-05/D-06).
    """
    import httpx

    regions = yaml.safe_load((root / "config/regions.yml").read_text(encoding="utf-8"))
    if region not in regions:
        print(f"Região '{region}' não existe. Veja: obs regions", file=sys.stderr)
        return
    meta = regions[region]
    # ... implementação conforme RESEARCH.md Pattern 1 ...
```

Nota: a assinatura muda de `refresh(root)` para `refresh(region, root)` — atualizar chamada em `cli.py:65`.

**Upsert idempotente — lógica central** (D-06, RESEARCH.md Pattern 1 linhas 232-258):
```python
# Ler o cache atual; criar DataFrame vazio com schema correto se não existir
cache_path = root / CACHE
if cache_path.exists():
    df = pl.read_csv(cache_path)
else:
    df = pl.DataFrame(schema={
        "nome": pl.String, "uf": pl.String,
        "codigo_ibge": pl.String, "populacao": pl.Int64, "fonte_pop": pl.String,
    })

# D-06: só preenche onde codigo_ibge OU populacao estão vazios
# Condição correta: checar CAMPOS, não apenas presença da linha
row = df.filter(pl.col("nome").map_elements(slug, return_dtype=pl.String) == key)
if row.height > 0:
    r = row.row(0, named=True)
    if r["codigo_ibge"] and r["populacao"]:
        continue  # dado curado preservado (ex: Sorocaba 709000)
# ... preencher e fazer upsert ...
```

**Erro amigável via difflib** (D-09, RESEARCH.md Exemplo 3):
```python
import difflib

candidates_slug = list(localidades_map.keys())
candidates_nome = [localidades_map[k]["nome"] for k in candidates_slug]
matches = difflib.get_close_matches(slug(nome_query), candidates_slug, n=1, cutoff=0.6)
if matches:
    idx = candidates_slug.index(matches[0])
    sugestao = candidates_nome[idx]
    print(f"  Aviso: Município '{nome_query}' ({uf}) não encontrado no IBGE"
          f" — você quis dizer '{sugestao}'?")
else:
    print(f"  Aviso: Município '{nome_query}' ({uf}) não encontrado no IBGE")
unresolved.append(nome_query)
continue
```

**Resumo ao final do refresh** (D-09):
```python
if unresolved:
    print(f"\nMunicípios não resolvidos ({len(unresolved)}): {unresolved}")
print(f"✓ config/municipios.csv atualizado — {n_preenchidos} municípios resolvidos")
```

**Fonte de população obrigatória** (D-05):
```python
# Ao gravar no upsert: sempre registrar fonte_pop
"fonte_pop": "IBGE Censo 2022"  # D-05: gravar literal exato
```

---

### `pipeline/sources/snis.py` — adicionar `refresh()` (GEN-02)

**Analog:** `scripts/scrape_snis.py` — função `cmd_build()` (lines 192-283) é o núcleo

**load() pattern — manter intacto** (snis.py lines 32-44):
```python
def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    df = (
        df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
          .sort("ano", descending=True)
          .unique(subset=["key"], keep="first")
    )
    return df
```

**refresh() signature** (D-07/D-08):
```python
def refresh(region: str, root: Path = Path("."),
            ano: str | None = None,
            exclude: list[str] | None = None) -> None:
    """Baixa dados SNIS-RS para a região via scraper e grava
    data/raw/snis/snis_{region}.csv (D-08).

    Requer rede. O build offline usa apenas load().
    """
    import sys as _sys
    _sys.path.insert(0, str(root / "scripts"))
    from scrape_snis import cmd_build, _load_region  # noqa: PLC0415
    import argparse

    out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
    args = argparse.Namespace(
        region=region, ano=ano, exclude=exclude or [], out=out
    )
    cmd_build(args)
```

Nota: `requests` fica lazy-imported dentro de `_session()` em `scrape_snis.py` — não vaza para o namespace de produção quando apenas `snis.load()` é chamada.

**Caminho de saída do CSV** (D-08) — convenção de nome:
```python
out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
# Exemplo: snis_rms.csv, snis_campinas.csv
# snis.load() já faz glob("*.csv") — consome automaticamente
```

---

### `scripts/scrape_snis.py` — expandir `UF_NOMES` (Pitfall 4)

**Analog:** self (arquivo sem mudança estrutural — só expandir o dict na line 118)

**Padrão atual a expandir** (scrape_snis.py line 118):
```python
# ANTES (SP only):
UF_NOMES = {"SP": "São Paulo"}  # estende conforme novas regiões

# DEPOIS (27 estados — copiar literal do RESEARCH.md Pitfall 4):
UF_NOMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}
```

**Padrão existente de uso** (scrape_snis.py lines 182-183 e 203):
```python
# UF_NOMES usado em cmd_build() e cmd_inspect():
cmap = _cod_mun_map(s, UF_NOMES.get(uf, uf))
# UF_NOMES.get(uf, uf) — fallback passa a sigla se não encontrar,
# que quebra silenciosamente (_cod_mun_map retorna dict vazio).
# Com UF_NOMES completo, o fallback nunca dispara para região BR válida.
```

---

### `pipeline/cli.py` — adicionar comandos e corrigir labels (D-02/D-04/D-07)

**Analog:** `pipeline/cli.py` itself — padrão estabelecido por `cmd_refresh_ibge` e `cmd_build`

**Padrão de comando existente a espelhar** (cli.py lines 64-66 e 77-78):
```python
# Padrão: função cmd_<verbo>_<objeto>(args) -> int
def cmd_refresh_ibge(_args) -> int:
    ibge.refresh(Path("."))
    return 0

# Padrão de registro no sub-parser:
sub.add_parser("refresh-ibge", help="atualiza IBGE via API").set_defaults(func=cmd_refresh_ibge)
```

**Mudança 1: adicionar `--region` ao `refresh-ibge`** (D-04):
```python
# ANTES (cli.py lines 64-66, 78):
def cmd_refresh_ibge(_args) -> int:
    ibge.refresh(Path("."))
    return 0
# ...
sub.add_parser("refresh-ibge", ...).set_defaults(func=cmd_refresh_ibge)

# DEPOIS:
def cmd_refresh_ibge(args) -> int:
    ibge.refresh(args.region, Path("."))
    return 0
# ...
ri = sub.add_parser("refresh-ibge", help="atualiza IBGE via API")
ri.add_argument("--region", required=True)
ri.set_defaults(func=cmd_refresh_ibge)
```

**Mudança 2: novo comando `refresh-snis`** (D-07) — espelhar padrão de `refresh-ibge`:
```python
def cmd_refresh_snis(args) -> int:
    snis.refresh(args.region, Path("."), ano=args.ano, exclude=args.exclude or [])
    return 0

# Em main():
rs = sub.add_parser("refresh-snis", help="baixa dados SNIS-RS via scraper")
rs.add_argument("--region", required=True)
rs.add_argument("--ano", default=None)
rs.add_argument("--exclude", nargs="*", default=[])
rs.set_defaults(func=cmd_refresh_snis)
```

**Mudança 3: renomear label hardcoded** (D-02, cli.py lines 48-50):
```python
# ANTES:
taxa_inf = totals.get("taxa_inf_media_rms")
if taxa_inf is not None:
    print(f"  Informalidade média RMS: {taxa_inf:.1f}% (Censo 2022, ponderado por ocupados)")

# DEPOIS:
taxa_inf = totals.get("taxa_inf_media")
if taxa_inf is not None:
    print(f"  Informalidade média {meta['nome']}: {taxa_inf:.1f}% (Censo 2022, ponderado por ocupados)")
```

---

### `pipeline/transform.py` — renomear `taxa_inf_media_rms` e fix sort (D-02)

**Analog:** `pipeline/transform.py` itself — mudanças cirúrgicas em 4 linhas

**Mudança 1: sort com `nulls_last=True`** (transform.py line 97):
```python
# ANTES:
return df.sort(["subregiao", "nome"])

# DEPOIS (RESEARCH.md Exemplo 4 — Polars 1.41.2 default é nulls_last=False):
return df.sort(["subregiao", "nome"], nulls_last=True)
# Municípios sem subregiao aparecem no final (comportamento mais natural)
```

**Mudança 2: renomear variável e chave** (transform.py lines 115, 117, 128):
```python
# ANTES (lines 115, 117, 128):
taxa_inf_media_rms = soma_ponderada / soma_ocupados if soma_ocupados > 0 else None
# ...
taxa_inf_media_rms = None
# ...
"taxa_inf_media_rms": taxa_inf_media_rms,

# DEPOIS:
taxa_inf_media = soma_ponderada / soma_ocupados if soma_ocupados > 0 else None
# ...
taxa_inf_media = None
# ...
"taxa_inf_media": taxa_inf_media,
```

**Invariante a preservar:** `build_region()` já trata `subregiao` como `m.get("subregiao")` (line 19) — retorna None para município sem sub-região. O sort com nulls funciona sem crash (RESEARCH.md Pitfall 3 verificado com Polars 1.41.2).

---

### `pipeline/render.py` — tolerar `subregiao` null (D-02)

**Analog:** `pipeline/render.py` itself — verificação revela que já funciona sem mudança

**Padrão atual** (render.py line 20):
```python
"subregiao": r["subregiao"],  # emite null para município sem subregiao
```

`json.dumps` serializa `None` Python como `null` JSON normalmente. O `app.js` usa `m.subregiao ?? "null"` para lidar com isso. **Sem mudança de código necessária aqui.**

---

### `site/app.js` — corrigir acoplamentos RMS (D-02)

**Analog:** `site/app.js` itself — 3 pontos cirúrgicos

**Mudança 1: chave JSON `taxa_inf_media_rms` → `taxa_inf_media`** (app.js line 58):
```javascript
// ANTES:
["Informalidade média RMS", t.taxa_inf_media_rms != null ? `${fmt(t.taxa_inf_media_rms, 1)}<small>%</small>` : "—"],

// DEPOIS:
["Informalidade média da região", t.taxa_inf_media != null ? `${fmt(t.taxa_inf_media, 1)}<small>%</small>` : "—"],
```

**Mudança 2: `buildCitySelect()` — suporte a regiões sem sub-regiões** (app.js lines 66-77):
```javascript
// ANTES:
const subs = { 1: [], 2: [], 3: [], "null": [] };
DATA.municipios.forEach(m => (subs[m.subregiao ?? "null"].push(m)));
// ...
for (const sr of [1, 2, 3, "null"]) {
    if (!subs[sr].length) continue;
    const lbl = sr === "null" ? "Outros" : `Sub-região ${sr}`;

// DEPOIS (dinâmico — funciona para qualquer subregiao inclusive inteiros > 3):
const subs = {};
DATA.municipios.forEach(m => {
    const k = m.subregiao ?? "null";
    (subs[k] = subs[k] || []).push(m);
});
const somenteNull = Object.keys(subs).every(k => k === "null");
const keys = Object.keys(subs).sort((a, b) =>
    a === "null" ? 1 : b === "null" ? -1 : Number(a) - Number(b)
);
for (const sr of keys) {
    if (!subs[sr].length) continue;
    const lbl = sr === "null" ? (somenteNull ? "Municípios" : "Outros") : `Sub-região ${sr}`;
```

Nota: a versão dinâmica resolve o Assumption A2 do RESEARCH.md (subregiao com inteiro fora de {1,2,3}).

---

### `config/regions.yml` — formalizar contrato mínimo (D-03)

**Analog:** `config/regions.yml` itself — adicionar comentário de exemplo expandido

**Padrão atual a expandir** (regions.yml lines 45-51):
```yaml
# Exemplo de outra região (descomente e edite):
# minha_cidade:
#   nome: "Meu município"
#   uf: SP
#   destaque: "Cidade X"
#   municipios:
#     - { nome: "Cidade X", uf: SP }
```

**Novo bloco de comentário — contrato mínimo D-03:**
```yaml
# Como criar o painel da sua cidade (ver README — guia de 5 minutos):
#
# minha_regiao:                        # chave da região (sem espaços, sem acentos)
#   nome: "Nome da Região"             # OBRIGATÓRIO — aparece no painel
#   uf: SP                             # OBRIGATÓRIO — para refresh-snis e refresh-ibge
#   destaque: "Cidade Principal"       # opcional (default: primeiro município)
#   fonte: "Lei Complementar 123/20XX" # opcional
#   municipios:
#     - { nome: "Cidade A", uf: SP }           # mínimo: nome + uf
#     - { nome: "Cidade B", uf: SP }           # subregiao ausente = lista plana
#     - { nome: "Cidade C", uf: SP, subregiao: 1 }  # subregiao opcional (int)
```

---

### `config/municipios.csv` — alvo do upsert

**Analog:** `config/municipios.csv` itself — estrutura já correta

**Schema atual** (municipios.csv line 1):
```
nome,uf,codigo_ibge,populacao,fonte_pop
```

Exemplos de estados do cache (lines 2-5):
```
Sorocaba,SP,3552205,709000,"IBGE/SINISA (pop. urbana)"   <- codigo_ibge preenchido, NÃO sobrescrever
Votorantim,SP,,124000,"IBGE ~2022 (aprox.)"              <- codigo_ibge vazio -> refresh pode preencher
Alambari,SP,,,                                           <- tudo vazio -> refresh preenche
```

**Padrão D-06:** ao fazer upsert, só preencher `codigo_ibge` e `populacao` onde `r["codigo_ibge"]` OU `r["populacao"]` estão vazios/null. `fonte_pop` gravada como `"IBGE Censo 2022"` (D-05) para linhas resolvidas pelo refresh.

---

### `README.md` — seção "Crie o painel da sua cidade em 5 minutos" (D-10)

**Analog:** `README.md` itself — inserir após a seção "Crie o painel da sua cidade" (line 33)

**Seção atual (placeholder, line 33-36):**
```markdown
## Crie o painel da sua cidade
Edite `config/regions.yml`, adicione uma região com a lista de municípios e rode
`uv run obs build --region <sua_chave>`. Os dados de resíduos entram em
`data/raw/snis/` (ver `scripts/refresh_snis.md`). Sem dado, fica pendente.
```

**Substituir por seção expandida com fluxo de 4 passos (D-10):**
```markdown
## Crie o painel da sua cidade em 5 minutos

### 1. Declarar a região
Edite `config/regions.yml` (campos obrigatórios: `nome` por região; `nome` + `uf` por município):

\```yaml
minha_regiao:
  nome: "Região do Vale do Paraíba"
  uf: SP
  municipios:
    - { nome: "São José dos Campos", uf: SP }
    - { nome: "Jacareí", uf: SP }
\```

### 2. Resolver identidade (IBGE)
\```bash
uv run obs refresh-ibge --region minha_regiao
\```
Resolve código IBGE e população (Censo 2022) para cada município e salva em `config/municipios.csv`.

### 3. Baixar dados de resíduos (SNIS)
\```bash
uv run obs refresh-snis --region minha_regiao
\```
Baixa indicadores de RSU do portal SNIS-RS e salva em `data/raw/snis/snis_minha_regiao.csv`.

### 4. Gerar o painel
\```bash
uv run obs build --region minha_regiao
\```

> **Aviso honesto:** informalidade e RAIS ficam `pendente` para regiões fora da RMS
> (Região Metropolitana de Sorocaba) — os dados de Censo 2022 e RAIS 2023 estão
> pré-carregados apenas para os 27 municípios da RMS. Um painel com resíduos reais
> e informalidade `pendente` é um painel **válido** — nunca inventamos número.
```

---

### `tests/test_pipeline.py` — novos testes (GEN-01, GEN-02, D-02)

**Analog:** `tests/test_pipeline.py` itself — mesmos padrões: offline, DataFrame sintético, `os.chdir(ROOT)`

**Padrão estabelecido de teste offline com DataFrame sintético** (test_pipeline.py lines 96-131):
```python
def test_proxy_pendente_edge_case():
    """D-07: proxy=pendente quando formais_residuos=0 E cooperados=null (ou 0)."""
    # DataFrame sintético — não depende de CSV real nem de transform.py
    df = pl.DataFrame({
        "formais_residuos": pl.Series([0], dtype=pl.Int64),
        "cooperados": pl.Series([None], dtype=pl.Float64),
    })
    # ... lógica isolada ...
    row = df.to_dicts()[0]
    assert row["proxy_formalizacao"] is None, "mensagem descritiva"
```

**Padrão de teste com build_region() real** (test_pipeline.py lines 19-38):
```python
def test_build_offline_gera_dados():
    import os
    os.chdir(ROOT)
    df = transform.build_region(
        REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT),
        ibge_informalidade.load(ROOT), rais.load(ROOT), COEF
    )
    assert df.height == 27
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag"] == "real"
```

**Novos testes a adicionar — padrões a copiar:**

```python
# Teste 1: sort com subregiao null não quebra (D-02 — usar DataFrame sintético)
def test_sort_com_subregiao_null():
    """D-02: build_region() com municipios sem subregiao retorna lista plana sem crash."""
    df = pl.DataFrame([
        {"nome": "Cidade A", "uf": "MG", "subregiao": None, "key": "cidade a"},
        {"nome": "Cidade B", "uf": "MG", "subregiao": None, "key": "cidade b"},
    ])
    # Verificar que sort com nulls_last=True não levanta exceção
    result = df.sort(["subregiao", "nome"], nulls_last=True)
    assert result.height == 2
    assert result["nome"][0] == "Cidade A"  # ordenado por nome quando subregiao é null

# Teste 2: taxa_inf_media (chave genérica, não mais taxa_inf_media_rms)
def test_region_totals_chave_generica():
    """D-02: region_totals() usa chave 'taxa_inf_media' sem sufixo 'rms'."""
    import os
    os.chdir(ROOT)
    # ... build_region RMS ...
    totals = transform.region_totals(df)
    assert "taxa_inf_media" in totals, "chave deve ser taxa_inf_media (sem sufixo rms)"
    assert "taxa_inf_media_rms" not in totals, "chave antiga não deve mais existir"

# Teste 3: upsert idempotente (ibge.refresh) — testar lógica isolada sem rede
def test_upsert_preserva_dado_curado():
    """D-06: upsert não sobrescreve linha com codigo_ibge e populacao preenchidos."""
    # DataFrame sintético com linha já preenchida (Sorocaba)
    df = pl.DataFrame({
        "nome": ["Sorocaba"],
        "uf": ["SP"],
        "codigo_ibge": ["3552205"],
        "populacao": [709000],
        "fonte_pop": ["IBGE/SINISA (pop. urbana)"],
    })
    r = df.filter(pl.col("nome") == "Sorocaba").row(0, named=True)
    # Condição D-06: não preencher se ambos estão presentes
    deve_preencher = not (r["codigo_ibge"] and r["populacao"])
    assert not deve_preencher, "Sorocaba com dados curados NÃO deve ser sobrescrita"

# Teste 4: data.json com chave taxa_inf_media (não rms)
def test_payload_usa_chave_generica():
    """D-02: data.json gerado tem 'taxa_inf_media' em totais (não 'taxa_inf_media_rms')."""
    import json
    data_path = ROOT / "site" / "data.json"
    assert data_path.exists()
    d = json.loads(data_path.read_text())
    assert "taxa_inf_media" in d["totais"], "taxa_inf_media ausente em totais"
    assert "taxa_inf_media_rms" not in d["totais"], "chave antiga taxa_inf_media_rms não deve existir"
```

---

## Shared Patterns

### Padrão load() / refresh() — separação offline/rede

**Fonte:** `pipeline/sources/snis.py` (load, lines 32-44) + `pipeline/sources/ibge.py` (load, lines 19-22)

**Aplica a:** `ibge.refresh()`, `snis.refresh()`

```python
# load() — sempre offline, sem argumentos de rede
def load(_root: Path = Path(".")) -> pl.DataFrame:
    # Lê arquivo(s) local(is) e retorna DataFrame com coluna "key" (slug)
    ...

# refresh() — rede explícita, região-alvo obrigatória
def refresh(region: str, root: Path = Path("."), ...) -> None:
    # Requer rede; lazy-import de pacotes de rede (requests, httpx) dentro da função
    # para não vazar para o namespace de produção quando load() é chamada
    import httpx  # ou: import requests (dentro de _session())
    ...
```

### Padrão de slug para junção de dados

**Fonte:** `pipeline/sources/base.py` (lines 6-14)

**Aplica a:** `ibge.refresh()` (matching IBGE por nome), `snis.refresh()` via `scrape_snis._cod_mun_map()`

```python
from pipeline.sources.base import slug

# Normalização: 'São Miguel Arcanjo' -> 'sao miguel arcanjo'
# Matching: slug(nome_ibge) == slug(nome_regions_yml)
localidades_map = {slug(m["nome"]): m for m in muns}
key = slug(municipio["nome"])
loc = localidades_map.get(key)
```

### Padrão de validação de região no CLI

**Fonte:** `pipeline/cli.py` (lines 25-27) + `scripts/scrape_snis.py` (lines 73-76)

**Aplica a:** `cmd_refresh_ibge`, `cmd_refresh_snis`

```python
# cli.py (lines 25-27):
if args.region not in regions:
    print(f"Região '{args.region}' não existe. Veja: obs regions", file=sys.stderr)
    return 1

# scrape_snis.py (lines 73-76):
if region_key not in regions:
    sys.exit(f"Região '{region_key}' não existe em {REGIONS}. Veja: uv run obs regions")
```

### Padrão de flag de qualidade (real/estimativa/pendente)

**Fonte:** `pipeline/transform.py` (lines 58-65) + `scripts/scrape_snis.py` (lines 261-272)

**Aplica a:** `snis.refresh()` ao gerar linhas `pendente` para municípios sem dado

```python
# Município sem dado no SNIS → linha pendente honesta (D-08):
rec["qualidade"] = "pendente"
rec["fonte"] = f"{fonte_base} — município sem dado de resíduos sólidos no SNIS-RS {ano}"
# Campos de dado ficam "" (string vazia) → null após schema_overrides em snis.load()
```

### Padrão de saída CSV com schema fixo

**Fonte:** `scripts/scrape_snis.py` (lines 226-277)

**Aplica a:** `snis.refresh()` ao gravar `data/raw/snis/snis_{region}.csv`

```python
schema_cols = [
    "municipio", "uf", "ano", "rsu_t_ano", "reciclado_t_ano", "reciclado_pct",
    "coleta_seletiva_pop_pct", "cooperados", "custo_mensal_rs", "qualidade",
    "fonte", "composicao_organico", "composicao_fonte",
]
# Campos ausentes gravam "" (string vazia) — viram null via schema_overrides em snis.load()
out = pl.DataFrame([{c: r[c] for c in schema_cols} for r in rows]).sort("municipio")
args.out.parent.mkdir(parents=True, exist_ok=True)
out.write_csv(args.out)
```

### Padrão de yaml.safe_load

**Fonte:** `pipeline/cli.py` (lines 17-18)

**Aplica a:** `ibge.refresh()`, `snis.refresh()` ao ler `regions.yml`

```python
import yaml

def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))

# Nunca usar yaml.load() — somente yaml.safe_load() (segurança D-03)
```

---

## Pitfalls Críticos a Registrar no PLAN.md

| Pitfall | Arquivo | Detalhe |
|---------|---------|---------|
| `taxa_inf_media_rms` em 3 arquivos + testes | `transform.py`, `cli.py`, `app.js`, `test_pipeline.py` | Renomear tudo na mesma task; `.get()` silencioso em cli.py linha 48 mascara erro |
| IBGE 7 dígitos vs SNIS 6 dígitos | `ibge.refresh()`, `scrape_snis._cod_mun_map()` | Gravar 7 dígitos no cache; SNIS usa `str(id)[:-1]`. Não misturar |
| Header row SIDRA API | `ibge.refresh()` | `resp.json()[1:]` — data[0] é cabeçalho, não dado |
| `UF_NOMES` incompleto | `scrape_snis.py` | Dict atual tem só SP; expandir para 27 estados antes de qualquer teste não-SP |
| `subs[sr]` undefined no app.js | `site/app.js` | subregiao inteiro fora de {1,2,3} → `subs[4].push()` TypeError; a versão dinâmica resolve |
| Validar `region` antes de montar caminho | `snis.refresh()` | Evitar path traversal: checar que `region` existe em `regions.yml` antes de `f"snis_{region}.csv"` |

---

## No Analog Found

Nenhum arquivo desta fase ficou sem analog. Todos os 10 arquivos têm padrão equivalente no codebase.

---

## Metadata

**Analog search scope:** `pipeline/sources/`, `pipeline/`, `scripts/`, `tests/`, `config/`, `site/`
**Files scanned:** 10 source files lidos diretamente
**Pattern extraction date:** 2026-06-24
