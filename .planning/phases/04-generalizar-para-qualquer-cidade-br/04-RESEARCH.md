# Phase 4: Generalizar para qualquer cidade BR — Research

**Researched:** 2026-06-24
**Domain:** IBGE APIs (localidades + SIDRA Censo 2022), SNIS scraper promotion, Polars sort-with-nulls, difflib similarity
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Para uma região NOVA, "painel gerado com sucesso" = identidade automática + resto `pendente` honesto. `ibge.refresh()` resolve código+população; SNIS/informalidade/RAIS ficam `pendente` até o usuário rodar os refreshes correspondentes. Painel válido = estrutura correta + flags honestos, mesmo majoritariamente `pendente`. **Não** buscar tudo online no build (quebraria o build offline/determinístico).

**D-02:** Robustez mínima, não desacoplamento total: (1) tolerar `subregiao` ausente/`null` sem quebrar — `sort(["subregiao","nome"])` em `transform.py:97` e emissão de `subregiao` em `render.py:20` devem funcionar para região sem sub-regiões (resultado: lista plana); (2) renomear `taxa_inf_media_rms` (em `transform.py` ~L115/128 e consumido em `cli.py:48-50`) para nome genérico (ex.: `taxa_inf_media`). **Não** reescrever `ibge_informalidade.py`/`rais.py` — para região nova, join por slug não casa → informalidade vira `pendente` honesto.

**D-03:** Contrato mínimo de `regions.yml`: por município — `nome` e `uf` obrigatórios, `subregiao` opcional. Na região — `nome` obrigatório, `destaque` e `fonte` opcionais.

**D-04:** `obs refresh-ibge --region <chave>` resolve só os municípios daquela região e faz upsert em `config/municipios.csv`. Build continua 100% offline.

**D-05:** Fonte de população = Censo 2022. Gravar `fonte_pop = "IBGE Censo 2022"`. Evita instabilidade da estimativa anual.

**D-06:** Upsert SÓ preenche vazios — não sobrescreve linhas já preenchidas. Idempotente. Matching por nome normalizado dentro da UF.

**D-07:** `snis.refresh(region)` promove `scripts/scrape_snis.py`. Exposto por `obs refresh-snis --region <chave>`. Recipe 100% decifrado e validado.

**D-08:** `snis.refresh()` grava um CSV por região: `data/raw/snis/snis_<chave-regiao>.csv`. `snis.load()` já concatena todos os CSVs da pasta.

**D-09:** Fail-soft + sugestão quando município não resolve no IBGE: "Município X (UF) não encontrado no IBGE — você quis dizer Y?", continua com os demais, lista não-resolvidos no fim.

**D-10:** Seção dedicada no README — fluxo honesto de 4 passos: editar `regions.yml`, `obs refresh-ibge --region X`, `obs refresh-snis --region X`, `obs build --region X`. Deixar explícito que informalidade/RAIS ficam `pendente` fora da RMS.

### Claude's Discretion

- Detalhes da API IBGE (qual endpoint de localidades por UF, qual agregado do Censo 2022 para população, formato de chamada).
- Algoritmo de similaridade para a sugestão de nome (D-09).
- Estrutura interna de `snis.refresh()` ao promover `scrape_snis.py`.
- Conjunto exato de campos opcionais em `regions.yml`.

### Deferred Ideas (OUT OF SCOPE)

- Generalizar `ibge_informalidade.py`/`rais.py` para resolver códigos da região ativa.
- Comparação de pares (município vs. mediana sub-região).
- Check de CI em pull requests.
- Cache de população por estimativa anual (agregado 6579).

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | `ibge.refresh()` implementado (API localidades + população) regrava o cache | API localidades VERIFICADA (endpoint + formato); SIDRA t/4714 VERIFICADO para Censo 2022; upsert pattern documentado |
| GEN-02 | `snis.refresh()` documentado e automatizado | `scripts/scrape_snis.py` já funcional; assinatura de promoção documentada; UF_NOMES completo documentado |
| GEN-03 | Erro amigável quando município não resolve no IBGE | `difflib.get_close_matches` VERIFICADO (stdlib, sem nova dep); padrão de uso documentado |
| GEN-04 | Doc "Crie o painel da sua cidade em 5 minutos" no README; terceiro gera outra região só editando `regions.yml` | Campos obrigatórios/opcionais mapeados; fluxo de 4 passos D-10 mapeado para artefatos reais |

</phase_requirements>

---

## Summary

Esta fase tem quatro entregáveis independentes: implementar `ibge.refresh()` usando as APIs públicas do IBGE, promover `scrape_snis.py` a `snis.refresh()`, corrigir acoplamentos de nome (`taxa_inf_media_rms`, `subregiao` hardcoded no front), e escrever o guia de 5 min. As principais lacunas técnicas foram confirmadas via chamada real às APIs.

**API IBGE localidades** (`servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios`): retorna JSON com campos `id` (int, 7 dígitos, ex: `3552205`) e `nome` (string). Matching por `slug(nome)` dentro da UF. Confirmado: SP tem 645 municípios. [VERIFIED via curl]

**API IBGE população Censo 2022** (`apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022`): tabela SIDRA 4714 ("População residente"), variável 93, período 2022. Retorna JSON com `D1C` (código 7 dígitos), `D1N` (nome), `V` (população). Batch `n6/all` retorna todos os 5.570 municípios em ~1.4MB em uma única chamada — estratégia recomendada (baixa uma vez, filtra localmente). Confirmado: Sorocaba → 723.682 pessoas (Censo 2022). [VERIFIED via curl]

**`scrape_snis.py` → `snis.refresh(region)`**: o scraper é funcional e totalmente validado (STATE.md). A promoção é basicamente: extrair a lógica de `cmd_build()` para uma função `refresh(region_key, root, ano=None, exclude=None)`, corrigir o caminho de saída para `data/raw/snis/snis_{region_key}.csv`, e expandir `UF_NOMES` para cobrir os 27 estados. O scraper usa `requests` (dev dep) — isso é aceitável pois `refresh` é passo consciente de rede, não parte do build offline.

**Primary recommendation:** Implementar em 3 tasks sequenciais: (1) `ibge.refresh()` com as duas APIs IBGE + upsert idempotente + difflib para erros amigáveis; (2) `snis.refresh()` promovendo `scrape_snis.py` + `obs refresh-snis`; (3) desacoplamento RMS no código e guia no README.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Resolver código IBGE + pop por nome+UF | Pipeline/Sources (`ibge.refresh`) | — | Rede só no refresh; build lê cache offline |
| Upsert idempotente em `municipios.csv` | Pipeline/Sources (`ibge.refresh`) | — | `ibge.load()` já lê esse arquivo |
| Scraping SNIS por região | Pipeline/Sources (`snis.refresh`) | scripts/ (delegado) | Promover lógica existente; `snis.load()` já consome a saída |
| Sugestão de nome (D-09) | Pipeline/Sources (`ibge.refresh`) | — | Erro acontece no momento do refresh |
| Sort com `subregiao` null | Pipeline/Transform | — | `df.sort(["subregiao","nome"])` Polars — funciona sem mudança |
| Agrupamento por sub-região no front | Frontend (`site/app.js`) | — | Hardcoded `{1,2,3,"null"}` — precisa de ajuste mínimo para D-02 |
| Label "Informalidade média RMS" | Frontend (`site/app.js`) | CLI (`cli.py`) | Dois pontos de label hardcoded a generalizar |
| Guia de 5 min | Docs (`README.md`) | — | Seção nova; não exige código |

---

## Standard Stack

### Core (sem novas dependências)

| Biblioteca | Versão disponível | Propósito | Por que é o padrão |
|------------|-------------------|-----------|-------------------|
| `httpx` | 0.28.1 [VERIFIED: pyproject.toml] | Chamadas às APIs IBGE (refresh) | Já na dep principal; síncrono ou async |
| `polars` | 1.41.2 [VERIFIED: uv run] | Leitura/escrita de CSVs, upsert do cache | Padrão do projeto (CLAUDE.md) |
| `pyyaml` | ≥6.0 [VERIFIED: pyproject.toml] | Leitura de `regions.yml` | Padrão do projeto |
| `difflib` (stdlib) | Python 3.11+ | Similaridade de nomes para D-09 | Sem nova dependência |
| `unicodedata` (stdlib) | Python 3.11+ | Normalização de nomes (slug) | Já usado em `base.slug()` |
| `requests` | 2.34.2 [VERIFIED: pyproject.toml dev] | HTTP session com cookies para SNIS | O scraper já usa; é dev dep |

### Por que NÃO mudar de `requests` para `httpx` no `snis.refresh()`

O scraper SNIS usa `requests.Session()` com cookies gerenciados automaticamente. `httpx` tem uma API de sessão diferente (`httpx.Client`) e não é drop-in. Como o scraper já está 100% validado com `requests`, e `requests` está presente (dev dep), a promoção deve manter `requests`. Alternativamente: `import requests` dentro da função (lazy import), assim não vaza para o build offline que não usa rede.

**Nenhum pacote novo a instalar.** Todas as dependências já estão em `pyproject.toml`.

---

## Package Legitimacy Audit

> Fase não instala pacotes novos — todos os pacotes utilizados já estão em `pyproject.toml`.

Sem auditoria necessária.

---

## Architecture Patterns

### Fluxo GEN-01: `ibge.refresh(region, root)`

```
regions.yml[region].municipios
        │
        ▼
API localidades: GET /estados/{UF}/municipios
    → dict[slug(nome)] -> id_7dig
        │
        ▼
API SIDRA: GET /values/t/4714/n6/all/v/93/p/2022
    → dict[id_7dig] -> populacao (Censo 2022)
        │
        ▼
Para cada município da região:
  1. resolver slug -> id_7dig (via API localidades)
  2. resolver id_7dig -> populacao (via SIDRA batch)
  3. upsert em config/municipios.csv SÓ se linha está vazia (D-06)
     → não sobrescrever linhas com dado curado (ex: Sorocaba 709000)
  4. se não resolvido: difflib.get_close_matches -> mensagem amigável (D-09)
        │
        ▼
Reescreve config/municipios.csv (preserva linhas não-alvo da região)
```

### Fluxo GEN-02: `snis.refresh(region, root, ano=None, exclude=None)`

```
regions.yml[region]
        │
        ▼
snis.refresh() == lógica de cmd_build() em scrape_snis.py
  → _session() (GET + POST para cookie)
  → _cod_mun_map(s, UF_NOMES[uf])  # UF_NOMES completo para 27 estados
  → _query_grid(s, codes, ano)      # protocolo jqGrid já validado
  → escreve data/raw/snis/snis_{region_key}.csv
        │
        ▼
snis.load() já consome automaticamente (glob "*.csv")
```

### Recommended Project Structure

Nenhuma pasta nova necessária. Mudanças:

```
pipeline/
  sources/
    ibge.py           # refresh() implementado (GEN-01)
    snis.py           # refresh(region) adicionado (GEN-02)
    base.py           # sem mudança
  transform.py        # taxa_inf_media_rms -> taxa_inf_media (D-02)
  render.py           # sem mudança (r["subregiao"] emite null normalmente)
  cli.py              # --region em refresh-ibge; refresh-snis novo; labels (D-02)
scripts/
  scrape_snis.py      # sem mudança (lógica fica aqui, refresh chama-a)
  refresh_snis.md     # atualizar para doc de uso do novo refresh-snis
config/
  regions.yml         # formalizar campos mínimos no comentário de exemplo
site/
  app.js              # 2 ajustes D-02: "Informalidade média RMS"→genérico; subregiao loop
README.md             # seção "Crie o painel da sua cidade em 5 min" (D-10)
tests/
  test_pipeline.py    # novos testes: build_region com subregiao=null; taxa_inf_media genérico
```

### Pattern 1: Upsert Idempotente em CSV (GEN-01, D-06)

**O que:** Ler o CSV atual, resolver os municípios da região via API, preencher APENAS células vazias, reescrever.

**Quando usar:** Sempre que `ibge.refresh()` é chamado.

```python
# Source: padrão do projeto (polars + CLAUDE.md)
def refresh(region: str, root: Path = Path(".")) -> None:
    import httpx

    regions = yaml.safe_load((root / "config/regions.yml").read_text(encoding="utf-8"))
    if region not in regions:
        raise ValueError(f"Região '{region}' não existe. Veja: obs regions")
    meta = regions[region]

    # 1. Baixar mapa de municípios da UF via localidades
    uf = meta["uf"]
    with httpx.Client(timeout=60) as client:
        resp = client.get(
            f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        )
        resp.raise_for_status()
        muns = resp.json()
    # slug(nome) -> {"id": 7dig int, "nome": str}
    localidades_map: dict[str, dict] = {slug(m["nome"]): m for m in muns}

    # 2. Baixar população Censo 2022 para todos os municípios BR (batch)
    with httpx.Client(timeout=120) as client:
        resp = client.get(
            "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022"
        )
        resp.raise_for_status()
        sidra_rows = resp.json()[1:]  # pular header
    # id_7dig (str) -> populacao (int)
    pop_map: dict[str, int] = {
        r["D1C"]: int(r["V"]) for r in sidra_rows if r.get("V", "").isdigit()
    }

    # 3. Upsert no cache
    cache_path = root / CACHE
    df = pl.read_csv(cache_path) if cache_path.exists() else pl.DataFrame(schema=...)

    unresolved: list[str] = []
    for m in meta["municipios"]:
        key = slug(m["nome"])
        row = df.filter(pl.col("nome").map_elements(slug, ...) == key)
        # D-06: pular se já preenchido
        if row.height > 0:
            r = row.row(0, named=True)
            if r["codigo_ibge"] and r["populacao"]:
                continue  # dado curado preservado
        loc = localidades_map.get(key)
        if loc is None:
            # D-09: sugestão de nome
            candidates = list(localidades_map.keys())
            suggestions = difflib.get_close_matches(key, candidates, n=1, cutoff=0.6)
            sugestao = localidades_map[suggestions[0]]["nome"] if suggestions else None
            msg = f"Município '{m['nome']}' ({uf}) não encontrado no IBGE"
            if sugestao:
                msg += f" — você quis dizer '{sugestao}'?"
            print(f"  Aviso: {msg}")
            unresolved.append(m["nome"])
            continue
        id_7dig = str(loc["id"])
        pop = pop_map.get(id_7dig)
        # ... upsert df ...

    if unresolved:
        print(f"\nMunicípios não resolvidos ({len(unresolved)}): {unresolved}")
```

### Pattern 2: `snis.refresh(region, root, ano=None, exclude=None)`

**O que:** Wrapper fino que chama a lógica existente de `scrape_snis.cmd_build()` com os parâmetros corretos.

**Quando usar:** `obs refresh-snis --region <chave>`.

```python
# Source: scripts/scrape_snis.py (código validado — este é apenas o wrapper)
def refresh(region: str, root: Path = Path("."),
            ano: str | None = None, exclude: list[str] | None = None) -> None:
    """Baixa dados SNIS-RS para a região e grava data/raw/snis/snis_{region}.csv."""
    import argparse
    # Reutiliza cmd_build do scraper
    sys.path.insert(0, str(root / "scripts"))
    from scrape_snis import cmd_build, _load_region, _session, _latest_ano, _cod_mun_map, _query_grid
    # ... ou chama subprocess para isolar requests do import path de produção

    out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
    # Delegar para scrape_snis.cmd_build com args sintéticos
    args = argparse.Namespace(region=region, ano=ano, exclude=exclude or [], out=out)
    cmd_build(args)
```

**Alternativa limpa:** chamar `subprocess.run(["uv", "run", "python", "scripts/scrape_snis.py", "--build", ...])`  para isolar completamente o `requests` do namespace de produção. Decisão para o planner — ambas funcionam.

### Pattern 3: Novo Comando CLI `refresh-snis`

```python
# Source: cli.py — espelho de cmd_refresh_ibge
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

### Anti-Patterns to Avoid

- **Chamar a API IBGE dentro de `build`:** quebra o build offline (D-04). Refresh é passo de rede separado, explícito.
- **Sobrescrever linhas preenchidas no upsert:** viola D-06 e apaga curadoria manual (ex.: Sorocaba com `populacao=709000` medida por SINISA).
- **Usar `httpx` no scraper SNIS:** o scraper usa `requests.Session()` com cookie. Manter `requests`; não é drop-in.
- **Usar `taxa_inf_media_rms` como chave pública no JSON:** é o label a renomear (D-02). Chave → `taxa_inf_media`; label de display também.

---

## Don't Hand-Roll

| Problema | Não construir | Usar | Por quê |
|----------|--------------|------|---------|
| Similaridade de nome | Levenshtein customizado | `difflib.get_close_matches` (stdlib) | Zero deps; funciona bem para nomes BR com acento (após slug); confirmado em testes |
| Normalização de nomes | Regex de acento | `base.slug()` já existente | Padrão do projeto; usado em todos os joins |
| HTTP com retry/timeout | Loop manual | `httpx.Client(timeout=N)` | Já em dep principal; sem nova dep |
| Scraping SNIS | Reescrever protocolo jqGrid | `scripts/scrape_snis.py` | Protocolo 100% decifrado e validado; só promover |
| Batch fetch de populações | N chamadas (uma por município) | SIDRA `n6/all` (todos 5570 municípios em 1 chamada, ~1.4MB) | 1 chamada >> N chamadas; resposta completa em ~5s |

---

## APIs IBGE — Referência Técnica

### API Localidades: Municípios por Estado

```
GET https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios
```

Parâmetros opcionais: `?orderBy=nome`

**Resposta (array de objetos):**
```json
[
  {
    "id": 3552205,
    "nome": "Sorocaba",
    "microrregiao": { ... },
    "regiao-imediata": { ... }
  }
]
```

- `id`: inteiro de 7 dígitos (código IBGE completo com dígito verificador). [VERIFIED via curl]
- `nome`: nome sem acento em alguns casos, com acento em outros — usar `slug()` para matching. [VERIFIED via curl]
- SP retorna 645 municípios. [VERIFIED via curl]
- **Conversão SNIS:** SNIS usa código de 6 dígitos (`id // 10` ou `str(id)[:-1]`). Confirmado: Sorocaba IBGE=3552205, SNIS=355220. [VERIFIED: STATE.md + curl]
- Sem autenticação necessária. [VERIFIED via curl]

### API SIDRA: População Censo 2022 por Município

```
GET https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022
```

- Tabela: **4714** ("População residente") — Censo Demográfico 2022. [VERIFIED via curl retornando D3C="2022"]
- Variável: **93** (população residente total). [VERIFIED via curl]
- Nível: **n6** (município). [VERIFIED via curl]
- `/all` retorna todos os 5.570 municípios do Brasil em uma única chamada (~1.4MB). [VERIFIED via curl]
- Resposta: JSON array onde `data[0]` é o header e `data[1:]` são os dados.
- Campos relevantes: `D1C` (código 7 dígitos, string), `D1N` (nome município com UF entre parênteses), `V` (população como string numérica). [VERIFIED via curl]
- Sorocaba: `D1C="3552205"`, `V="723682"` [VERIFIED via curl]
- Sem autenticação necessária. [VERIFIED via curl]

**Estratégia recomendada:** baixar `n6/all` uma vez e filtrar localmente pelo `D1C` dos municípios da região. Evita N chamadas à API e é rápido.

---

## Common Pitfalls

### Pitfall 1: Código IBGE 7 dígitos vs. SNIS 6 dígitos

**O que vai errado:** usar o `id` retornado pela API localidades (7 dígitos, ex: 3552205) diretamente como `cod_mun` no SNIS (que espera 6 dígitos, ex: 355220).

**Por que acontece:** IBGE inclui dígito verificador; SNIS não usa. Os valores são diferentes.

**Como evitar:** ao gravar `codigo_ibge` no cache, gravar o valor de 7 dígitos (padrão IBGE). Ao chamar o SNIS, usar `str(codigo_ibge)[:-1]` para obter 6 dígitos. Já implementado em `scrape_snis.py` via `_cod_mun_map()` que mapeia `slug(nome) -> cod_mun_6dig` diretamente — não passa pelo `municipios.csv`.

**Sinais de alerta:** município resolve no IBGE mas retorna linha vazia no SNIS.

### Pitfall 2: `taxa_inf_media_rms` em dois lugares (transform.py E cli.py E app.js)

**O que vai errado:** renomear só em `transform.py::region_totals()` e esquecer `cli.py:48-50` e `site/app.js:58`.

**Por que acontece:** a chave está em 3 arquivos distintos: `transform.py` (onde é produzida), `cli.py` (onde é consumida no print), `app.js` (onde é consumida no display).

**Como evitar:** renomear `taxa_inf_media_rms` → `taxa_inf_media` em todos os 3 arquivos **e** nos testes (`test_pipeline.py:240,241,244,272,273`). Fazer em uma única task.

**Sinais de alerta:** `totals.get("taxa_inf_media_rms")` retornando `None` no cli.py após a renomeação (chave mudou, .get() retorna None silenciosamente).

### Pitfall 3: `sort(["subregiao","nome"])` — comportamento default com nulls

**O que vai errado:** assumir que `nulls_last=True` é o padrão.

**Por que acontece:** em Polars 1.41.2, o default de `sort()` é `nulls_last=False` — nulls ficam PRIMEIRO. [VERIFIED via `inspect.signature`]

**Comportamento confirmado para o caso D-02:**
- Região com `subregiao` misto (alguns null, alguns inteiros): nulls aparecem antes dos grupos numerados. [VERIFIED via Python]
- Região com todos null (`subregiao` coluna `Null` dtype): sort retorna a lista na ordem de `nome` corretamente. [VERIFIED via Python]
- Ambos os casos não crasham. [VERIFIED via Python]

**Para D-02:** o comportamento existente (`nulls_last=False`, nulls primeiro) pode ser mudado para `nulls_last=True` se quisermos que municípios sem sub-região apareçam no final. Decisão estética — não é bug. O planner deve escolher e fixar.

**O que o `app.js` faz com `subregiao=null`:** a lógica `subs[m.subregiao ?? "null"].push(m)` já coloca municípios sem sub-região no grupo "null", rotulado "Outros". Para uma região totalmente sem sub-regiões, todos vão para "Outros" — funciona mas o label é estranho. Ajuste mínimo recomendado: se só existe o grupo "null", omitir o header de seção (lista plana) ou trocar label. Isso está dentro do escopo D-02.

### Pitfall 4: `UF_NOMES` incompleto no scraper

**O que vai errado:** `snis.refresh()` chamado para região fora de SP falha em `_cod_mun_map()` porque `UF_NOMES = {"SP": "São Paulo"}` não tem o estado.

**Por que acontece:** o scraper original foi desenvolvido para RMS (SP only). O fallback `UF_NOMES.get(uf, uf)` passa a sigla pura ("MG") para a chave do dict do SNIS — que agrupa por nome completo ("Minas Gerais") e não retorna nada.

**Como evitar:** expandir `UF_NOMES` para todos os 27 estados. Mover o dict para `pipeline/sources/base.py` ou para o topo de `scrape_snis.py`. [ASSUMED: nomes completos são conhecimento geográfico padrão — confirmado para SP e MG via `_cod_mun_map`]

**Dict completo (27 estados):**
```python
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

### Pitfall 5: Upsert silencioso (linha existente mas campos todos vazios)

**O que vai errado:** município existe em `municipios.csv` mas com `codigo_ibge=""` e `populacao=""` — o refresh deveria preencher, mas a lógica de "só preenche vazios" (D-06) usa a presença da linha como critério, não a presença dos campos.

**Como evitar:** a condição correta de D-06 é: preencher quando `codigo_ibge` OU `populacao` está vazio/null — não quando a linha está ausente. Pseudo-código:
```python
if not (r["codigo_ibge"] and r["populacao"]):
    # preencher
```

### Pitfall 6: Header row do SIDRA API

**O que vai errado:** tratar `data[0]` como dado (é o dicionário de cabeçalhos das colunas).

**Como evitar:** `sidra_rows = resp.json()[1:]` (pular índice 0). [VERIFIED via curl — confirmado que data[0] sempre é o header]

---

## Code Examples

### Exemplo 1: Resolver municípios de uma região via API localidades

```python
# Source: VERIFIED via curl (2026-06-24)
import httpx
from pipeline.sources.base import slug

uf = "SP"
with httpx.Client(timeout=60) as client:
    resp = client.get(
        f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    )
    resp.raise_for_status()
    muns = resp.json()

# {slug(nome): id_7dig_int}
localidades: dict[str, int] = {slug(m["nome"]): m["id"] for m in muns}
# Exemplo: localidades["sorocaba"] == 3552205
```

### Exemplo 2: Buscar população Censo 2022 para todos os municípios (batch)

```python
# Source: VERIFIED via curl (2026-06-24)
import httpx

with httpx.Client(timeout=120) as client:
    resp = client.get(
        "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022"
    )
    resp.raise_for_status()
    rows = resp.json()[1:]  # pular header em rows[0]

# {codigo_ibge_7dig_str: populacao_int}
pop_by_code: dict[str, int] = {
    r["D1C"]: int(r["V"])
    for r in rows
    if r.get("V", "").isdigit()
}
# Exemplo: pop_by_code["3552205"] == 723682
```

### Exemplo 3: Sugestão de nome com difflib (D-09)

```python
# Source: VERIFIED via Python (2026-06-24)
import difflib
from pipeline.sources.base import slug

def sugerir_municipio(nome_query: str, candidatos_slug: list[str],
                      candidatos_nome: list[str]) -> str | None:
    """Retorna o nome mais próximo ou None se nenhum acima do cutoff."""
    q = slug(nome_query)
    matches = difflib.get_close_matches(q, candidatos_slug, n=1, cutoff=0.6)
    if not matches:
        return None
    idx = candidatos_slug.index(matches[0])
    return candidatos_nome[idx]

# Uso em ibge.refresh():
# sugestao = sugerir_municipio("Sorocab", slugs, nomes)
# -> "Sorocaba"
```

Testes confirmados [VERIFIED via Python 2026-06-24]:
- `"Sorocab"` → `"sorocaba"` ✓
- `"Sao Roque"` → `"são roque"` ✓ (slug remove acento antes de comparar)
- `"salto pirapora"` → `"salto de pirapora"` ✓
- `"Sarrpuhi"` → `"sarapuí"` ✓

### Exemplo 4: Polars sort com subregiao null (D-02)

```python
# Source: VERIFIED via Python/Polars 1.41.2 (2026-06-24)

# Região SEM sub-regiões (todos null) — funciona sem crash
# dtype "Null" quando todos os valores são None
df = pl.DataFrame([{"nome": m["nome"], "uf": m["uf"],
                    "subregiao": m.get("subregiao")}
                   for m in municipios])
# .sort(["subregiao","nome"]) com nulls_last padrão (False) = nulls primeiro
# .sort(["subregiao","nome"], nulls_last=True) = nulls no fim
# Ambos funcionam sem exceção para coluna Null dtype ou Int64 com null
result = df.sort(["subregiao", "nome"], nulls_last=True)
```

**Recomendação:** adicionar `nulls_last=True` para que municípios sem sub-região apareçam no final (comportamento mais natural para lista plana).

### Exemplo 5: Campos de regions.yml para nova região (contrato mínimo D-03)

```yaml
# Mínimo funcional — 2 campos por município, 1 campo de região
minha_regiao:
  nome: "Região do Vale do Paraíba"   # obrigatório
  uf: SP                               # obrigatório (para refresh-snis)
  # destaque: "São José dos Campos"   # opcional
  # fonte: "..."                      # opcional
  municipios:
    - { nome: "São José dos Campos", uf: SP }   # obrigatórios: nome, uf
    - { nome: "Jacareí", uf: SP }               # subregiao: ausente = null = ok
    - { nome: "Taubaté", uf: SP, subregiao: 1 } # subregiao: opcional
```

---

## Pontos de Acoplamento RMS a Generalizar

Mapeamento exato de onde há label/chave "RMS" hardcoded:

| Arquivo | Linha | Trecho atual | Mudança |
|---------|-------|-------------|---------|
| `pipeline/transform.py` | L115 | `taxa_inf_media_rms = soma_ponderada / ...` | → `taxa_inf_media` |
| `pipeline/transform.py` | L117 | `taxa_inf_media_rms = None` | → `taxa_inf_media` |
| `pipeline/transform.py` | L128 | `"taxa_inf_media_rms": taxa_inf_media_rms` | → `"taxa_inf_media": taxa_inf_media` |
| `pipeline/cli.py` | L48 | `taxa_inf = totals.get("taxa_inf_media_rms")` | → `"taxa_inf_media"` |
| `pipeline/cli.py` | L50 | `print(f"  Informalidade média RMS: ...")` | → usar `meta.get("nome")` ou label genérico |
| `site/app.js` | L58 | `"Informalidade média RMS"` (label de display) | → `"Informalidade média da região"` |
| `site/app.js` | L58 | `t.taxa_inf_media_rms` (chave JSON) | → `t.taxa_inf_media` |
| `tests/test_pipeline.py` | L240,241,244,272,273 | `"taxa_inf_media_rms"` | → `"taxa_inf_media"` |

**Acoplamentos de `subregiao` no `app.js`:**

| Arquivo | Linha | Trecho atual | Situação |
|---------|-------|-------------|---------|
| `site/app.js` | L66 | `const subs = { 1: [], 2: [], 3: [], "null": [] }` | Funciona para nova região (todos vão para "null"); ajuste estético recomendado |
| `site/app.js` | L70 | `for (const sr of [1, 2, 3, "null"])` | Idem — funciona, mas iterando 4 keys onde apenas 1 tem dados |
| `site/app.js` | L72 | `const lbl = sr === "null" ? "Outros" : ...` | Label "Outros" para região sem sub-regiões — ok por D-02 |

**Nota sobre `app.js`:** D-02 diz "robustez mínima" — o comportamento atual JÁ funciona para nova região (todos os municípios caem em "null" → "Outros"). O ajuste do label é cosmético, não bloqueante. O rename de `taxa_inf_media_rms` → `taxa_inf_media` no JS É bloqueante (a chave não existirá no JSON novo).

---

## State of the Art

| Abordagem antiga | Abordagem atual | Quando mudou | Impacto |
|-----------------|-----------------|--------------|---------|
| Tabela 6579 (estimativas populacionais anuais) | Tabela 4714 (Censo 2022, dado fixo) | Censo 2022 publicado em 2023 | Pop. mais estável para commit; alinhada ao dado de informalidade (D-05) |
| Scraping manual via portal SNIS (refresh_snis.md) | `obs refresh-snis --region` (automatizado) | Phase 4 (GEN-02) | Terceiro roda um comando ao invés de decifrar o portal manualmente |
| `refresh-ibge` sem `--region` (NotImplementedError) | `obs refresh-ibge --region X` (upsert idempotente) | Phase 4 (GEN-01) | Resolve apenas a região alvo; não sobrescreve curadoria existente |

**Deprecated/outdated:**
- Tabela SIDRA 6579: estimativas anuais — mais instável para dado commitado; substituída pela 4714 (Censo 2022) neste projeto.
- Tabela SIDRA 9514: outra variante do Censo 2022 (com filtros de cor/sexo/idade); 4714 é mais simples para o caso de uso de população total.

---

## Assumptions Log

| # | Claim | Section | Risk se errado |
|---|-------|---------|---------------|
| A1 | Nomes de estados no `getSelectOpt` do SNIS correspondem ao dict `UF_NOMES` completo proposto | Pitfall 4; GEN-02 | `_cod_mun_map()` retorna dict vazio para estado → todos os municípios ficam "não resolvidos"; refresh-snis falha silenciosamente. Verificar com `--inspect` para um estado não-SP antes de declarar pronto |
| A2 | `app.js:66` aceita `subregiao` com valor inteiro diferente de 1/2/3 sem crash (ex: 4, 5) em nova região | Architecture Patterns | Nova região com `subregiao: 4` vai para `subs[4]` que é `undefined.push()` → TypeError. Testar com nova região que tem sub-regiões numeradas diferentemente |

**Se esta tabela tiver só A1 e A2:** todas as demais claims foram verificadas via ferramentas nesta sessão.

---

## Open Questions

1. **Label "Outros" no `app.js` para região sem sub-regiões (D-02 escopo exato)**
   - O que sabemos: tecnicamente funciona; estéticamente exibe "Outros" para todos os municípios.
   - O que está indefinido: se o planner deve ajustar o label para "Municípios" quando nenhuma sub-região está definida (mudança em `app.js:72`).
   - Recomendação: incluir na task de D-02 como ajuste de 1 linha: `const lbl = sr === "null" ? (somenteNull ? "Municípios" : "Outros") : \`Sub-região ${sr}\``.

2. **`snis.refresh()` via import direto vs. subprocess**
   - O que sabemos: `scrape_snis.py` usa `requests` (dev dep); `pipeline/` usa `httpx` (main dep).
   - O que está indefinido: se `snis.refresh()` deve importar `cmd_build` diretamente de `scripts/` (simples mas vaza `requests` para o namespace de produção quando o módulo é importado) ou chamar via subprocess (limpo mas mais pesado).
   - Recomendação: import direto com lazy `import requests` dentro de `_session()` (já é assim no scraper — `import requests` está dentro da função). Isso já resolve o problema: `requests` só é importado quando `_session()` é chamada, e `snis.load()` nunca chama `_session()`.

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|------------|--------|---------|
| `httpx` | `ibge.refresh()` | ✓ | 0.28.1 | — |
| `requests` | `snis.refresh()` (via scrape_snis) | ✓ | 2.34.2 | — |
| `polars` | `ibge.refresh()` (upsert CSV) | ✓ | 1.41.2 | — |
| `pyyaml` | Leitura de regions.yml | ✓ | ≥6.0 | — |
| `difflib` | Sugestão de nome D-09 | ✓ | stdlib | — |
| API IBGE localidades | `ibge.refresh()` | ✓ (testada 2026-06-24) | v1 | — |
| API SIDRA t/4714 | `ibge.refresh()` pop | ✓ (testada 2026-06-24) | — | — |
| Portal SNIS serieHistorica | `snis.refresh()` | ✓ (validado fase 1) | — | Manual via refresh_snis.md |

**Missing com fallback:**
- Portal SNIS (app4.cidades.gov.br): se o portal sair do ar, o fallback é a instrução manual em `scripts/refresh_snis.md`.

---

## Security Domain

> `security_enforcement: true` em `.planning/config.json`. ASVS Level 1.

### Applicable ASVS Categories

| ASVS Category | Aplica | Controle |
|---------------|--------|---------|
| V2 Authentication | Não | APIs IBGE/SNIS são públicas sem auth |
| V3 Session Management | Mínimo | SNIS usa session cookie sem state sensível |
| V4 Access Control | Não | CLI local, sem controle de acesso |
| V5 Input Validation | Sim | `regions.yml` lido pelo usuário — validar chave `region` e campos obrigatórios antes de chamar API |
| V6 Cryptography | Não | Sem segredo ou dado sensível |

### Known Threat Patterns

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| Path traversal via `region` key | Tampering | Validar que `region` existe em `regions.yml` antes de montar caminho de arquivo (`snis_<region>.csv`) — evitar caracteres `../` |
| Conteúdo malicioso em `regions.yml` | Tampering | `yaml.safe_load()` (já usado no projeto) — não `yaml.load()` |
| Timeout de rede não tratado | Denial of Service | `httpx.Client(timeout=N)` com valor razoável (60s localidades, 120s SIDRA batch) |
| Dados de API IBGE corrompidos gravados no CSV | Tampering/Spoofing | Validar que `V.isdigit()` antes de parsear população; flag `pendente` se inválido |

---

## Sources

### Primary (HIGH confidence)

- `servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios` — endpoint confirmado via curl 2026-06-24; estrutura de resposta com campos `id` (7 dígitos) e `nome` verificada.
- `apisidra.ibge.gov.br/values/t/4714/n6/{code}/v/93/p/2022` — Censo 2022 population confirmado via curl 2026-06-24; Sorocaba retornou V="723682", D3C="2022".
- `apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022` — batch completo (5570 municípios, ~1.4MB) confirmado via curl 2026-06-24.
- `scripts/scrape_snis.py` — protocolo SNIS 100% validado (STATE.md HISTÓRICO 01-02); código lido e analisado.
- `pipeline/transform.py`, `pipeline/cli.py`, `pipeline/render.py`, `site/app.js` — todos lidos; acoplamentos RMS mapeados com números de linha exatos.
- `pyproject.toml` — dependências verificadas: `httpx>=0.27` (main), `requests>=2.34.2` (dev).
- Polars 1.41.2 `sort()` signature — verificado via `inspect.signature`; `nulls_last=False` é o default.
- `difflib.get_close_matches` — comportamento verificado via Python com casos de teste reais de nomes de municípios brasileiros.

### Secondary (MEDIUM confidence)

- dkko.me/posts/coletando-ibge-sidra-populacao-municipios/ — confirmou tabela 9514 (alternativa ao 4714); preferimos 4714 por ser mais simples (sem filtros de classificação).

### Tertiary (LOW confidence)

- Nomes completos dos 26 estados + DF para `UF_NOMES` — conhecimento geográfico padrão; verificado para SP e MG; não testado para os demais 25 UFs via SNIS API [A1].

---

## Metadata

**Confidence breakdown:**
- API IBGE (localidades + SIDRA): HIGH — verificado via curl com resultado real
- Polars sort com nulls: HIGH — verificado via Python com versão exata do projeto
- Promoção do scraper SNIS: HIGH — código lido completamente; lógica clara
- difflib para D-09: HIGH — testado com casos reais de nomes BR
- UF_NOMES completo: MEDIUM — SP verificado; demais [ASSUMED]
- app.js subregiao edge case (subs[4] = undefined): MEDIUM — comportamento lógico confirmado pela leitura do código; não testado com inteiro fora de 1/2/3

**Research date:** 2026-06-24
**Valid until:** 2026-09-24 (APIs IBGE são estáveis; SNIS pode mudar de domínio como já aconteceu)
