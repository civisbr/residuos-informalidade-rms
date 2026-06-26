---
phase: 04-generalizar-para-qualquer-cidade-br
verified: 2026-06-24T12:00:00Z
status: human_needed
score: 9/9
overrides_applied: 0
human_verification:
  - test: "Rodar uv run obs refresh-ibge --region rms em ambiente com rede e confirmar que resolve 27/27 municípios sem stacktrace, grava config/municipios.csv com fonte_pop='IBGE Censo 2022', e que uma segunda execução não altera o arquivo (idempotência real)"
    expected: "Saída: 'config/municipios.csv atualizado — N municípios resolvidos', sem erros no stderr para nomes válidos; segunda execução sem alteração no CSV"
    why_human: "Requer rede (servicodados.ibge.gov.br + apisidra.ibge.gov.br). O code path foi verificado offline via AST, os testes de idempotência são sintéticos."
  - test: "Rodar uv run obs refresh-ibge --region rms com um typo proposital em um município de regions.yml (ex.: 'Sorocab') e confirmar que o aviso amigável com sugestão aparece no stderr (não um stacktrace)"
    expected: "Aviso: 'Sorocab' não encontrado no IBGE — você quis dizer 'Sorocaba'? Sem exceção levantada."
    why_human: "O difflib.get_close_matches em ibge.refresh() só roda após a chamada de rede; não pode ser exercitado offline."
  - test: "Rodar uv run obs refresh-snis --region rms em ambiente com rede e confirmar que grava data/raw/snis/snis_rms.csv com dados RSU do portal SNIS Série Histórica"
    expected: "CSV gerado com linhas de municípios da RMS; snis.load() após o refresh concatena os CSVs; uv run obs build --region rms ainda passa 27/27"
    why_human: "snis.refresh() delega para scrape_snis.cmd_build que requer sessão HTTP com app4.cidades.gov.br. Não é exercitável offline."
  - test: "Seguir o guia 'Crie o painel da sua cidade em 5 minutos' do README com uma região nova (ex.: adicionar Campinas em config/regions.yml) e confirmar que os 4 passos (editar, refresh-ibge, refresh-snis, build) produzem um data.json válido sem tocar em código"
    expected: "uv run obs build --region campinas gera site/data.json com municípios da nova região; informalidade marcada como pendente; sem crash"
    why_human: "Verifica a experiência de um terceiro de ponta a ponta — requer rede para os dois refreshes e não pode ser simulado com dados locais da RMS."
---

# Phase 04: Generalizar para Qualquer Cidade BR — Verification Report

**Phase Goal:** Um terceiro consegue gerar o painel de outra região só editando `config/regions.yml`, sem tocar em código.
**Verified:** 2026-06-24T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ibge.refresh() resolve códigos e população via API e regrava o cache (não mais NotImplementedError) | VERIFIED | `pipeline/sources/ibge.py:29` — `def refresh(region, root)` implementado; `NotImplementedError` removido; `import httpx` lazy dentro da função (AST confirmado); `fonte_pop="IBGE Censo 2022"` literal presente; test `test_ibge_refresh_signature_e_sem_not_implemented` PASSOU |
| 2 | snis.refresh() documentado e, quando viável, automatizado | VERIFIED | `pipeline/sources/snis.py:53` — `def refresh(region, root, ano, exclude)` implementado; delega para `scrape_snis.cmd_build`; `import requests` lazy (dentro de `_session()` no scrape_snis.py); `obs refresh-snis --help` mostra `--region` required; `scripts/scrape_snis.py` com `UF_NOMES` completo de 27 estados incluindo TO/DF/MG |
| 3 | Município que não resolve no IBGE gera erro amigável (não stack trace) | VERIFIED | `ibge.refresh()` linhas 159-168: `difflib.get_close_matches` + mensagem "não encontrado no IBGE — você quis dizer '...'?" impressa em stderr; sem raise; `unresolved.append` e continua. Região inexistente: `if region not in regions: print(..., file=sys.stderr); return`. Confirmado offline: chamada com `regiao_inexistente` retorna graciosamente com mensagem amigável no stderr |
| 4 | README traz guia "Crie o painel da sua cidade em 5 minutos" e terceiro consegue seguir só editando regions.yml | VERIFIED | README.md linhas 33-67: seção "## Crie o painel da sua cidade em 5 minutos" com 4 sub-seções (1. Declarar, 2. refresh-ibge, 3. refresh-snis, 4. Gerar); aviso honesto em blockquote sobre informalidade/RAIS pendente fora da RMS; comandos literais com `--region minha_regiao`; config/regions.yml com bloco de comentário OBRIGATÓRIO e subregiao opcional |
| 5 | uv run obs build --region rms continua funcionando 100% offline — 27/27 municípios com dado | VERIFIED | Executado: `uv run obs build --region rms` → `Região Metropolitana de Sorocaba: 27/27 municípios com dado público` |
| 6 | taxa_inf_media (sem sufixo rms) em transform.py, cli.py, app.js e data.json — taxa_inf_media_rms ausente | VERIFIED | `grep -r "taxa_inf_media_rms" pipeline/ site/` → sem resultados. `data.json totais` contém `taxa_inf_media`; `taxa_inf_media_rms` ausente. `app.js` usa `t.taxa_inf_media` e "Informalidade média da região" |
| 7 | Cold-start (nova região sem CSVs) produz data.json com municípios pendente, não crash | VERIFIED | `test_cold_start_build_sem_csvs_snis_censo_rais` PASSOU: `snis.load()`, `ibge_informalidade.load()`, `rais.load()` retornam DataFrames com coluna `key` ao encontrar diretórios vazios; `transform.build_region()` não lança `ColumnNotFoundError`; todos os municípios saem com `flag='pendente'` |
| 8 | build permanece offline/determinístico — imports de rede são lazy | VERIFIED | `import httpx` não executado ao importar `pipeline.sources.ibge`; `import requests` não executado ao importar `pipeline.sources.snis`. Verificado com `sys.modules` check pós-import |
| 9 | uv run pytest -q passa — 25 testes, sem regressões | VERIFIED | `25 passed in 0.46s` — inclui CR-01, WR-01, D-02, D-05, D-06, D-09, GEN-01 tests |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline/sources/ibge.py` | `def refresh(region, root)` implementado; GEN-01/D-04/D-05/D-06/D-09 | VERIFIED | 206 linhas; refresh() com httpx lazy, yaml.safe_load, difflib, upsert idempotente D-06 (check explícito de None, WR-01 corrigido), tratamento de erros de rede (WR-02 corrigido), validação de campo `uf` vazio (WR-04 corrigido) |
| `pipeline/cli.py` | refresh-ibge com --region required; refresh-snis com --region required; taxa_inf_media genérico | VERIFIED | `cmd_refresh_ibge(args)` chama `ibge.refresh(args.region, Path("."))`;  `cmd_refresh_snis(args)` chama `snis.refresh(args.region, ...)`;  subparsers com `--region required=True`; label "Informalidade média {meta['nome']}" |
| `pipeline/transform.py` | taxa_inf_media (sem sufixo); nulls_last=True | VERIFIED | `region_totals()` retorna `"taxa_inf_media"`; `build_region()` usa `.sort(["subregiao", "nome"], nulls_last=True)` |
| `site/app.js` | t.taxa_inf_media; subs dinâmico com somenteNull | VERIFIED | Linha 58: `t.taxa_inf_media != null`; `buildCitySelect()` com `subs = {}` dinâmico; `somenteNull` controla label "Municípios" vs "Outros" |
| `tests/test_pipeline.py` | 4 novos testes D-02; cold-start CR-01; WR-01 | VERIFIED | `test_sort_com_subregiao_null`, `test_region_totals_chave_generica`, `test_upsert_preserva_dado_curado_d02`, `test_payload_usa_chave_generica`, `test_cold_start_build_sem_csvs_snis_censo_rais`, `test_upsert_preserva_populacao_zero` — todos PASSAM |
| `scripts/scrape_snis.py` | UF_NOMES com 27 estados | VERIFIED | `UF_NOMES` contém AC..TO; 27 UFs todas presentes; `Tocantins`, `Distrito Federal`, `Minas Gerais` confirmados |
| `README.md` | Guia 4 passos D-10; aviso honesto pendente | VERIFIED | Seção "## Crie o painel da sua cidade em 5 minutos" com sub-seções 1-4; blockquote "Aviso honesto"; `refresh-ibge` e `refresh-snis` literais; "pendente" mencionado |
| `config/regions.yml` | Bloco de comentário D-03 com OBRIGATÓRIO; RMS intacto | VERIFIED | Linhas 45-55: comentário expandido com "OBRIGATÓRIO" para nome e uf; "subregiao opcional"; bloco rms com 27 municípios intacto |
| `pipeline/sources/snis.py` | def refresh() com validação region; load() intacto; requests lazy | VERIFIED | `def refresh(region, root, ano, exclude)` com yaml.safe_load antes de montar caminho; path confinement `.is_relative_to(snis_dir)` (IN-01 corrigido); sys.path guard `if scripts_dir not in sys.path` (WR-03 corrigido); `load()` intacto com `key` em empty DataFrame |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline/cli.py::cmd_refresh_ibge` | `pipeline/sources/ibge.py::refresh` | `ibge.refresh(args.region, Path("."))` | WIRED | Linha 65: `ibge.refresh(args.region, Path("."))` presente |
| `pipeline/sources/ibge.py::refresh` | `config/municipios.csv` | upsert idempotente Polars | WIRED | `pl.read_csv(cache_path)` + `df.write_csv(cache_path)` — upsert no arquivo de cache |
| `pipeline/cli.py::cmd_refresh_snis` | `pipeline/sources/snis.py::refresh` | `snis.refresh(args.region, Path("."))` | WIRED | Linha 70: `snis.refresh(args.region, Path("."), ano=args.ano, ...)` presente |
| `pipeline/sources/snis.py::refresh` | `scripts/scrape_snis.py::cmd_build` | `from scrape_snis import cmd_build` | WIRED | Linhas 76-77 em snis.py; guarded com `if scripts_dir not in sys.path` |
| `pipeline/transform.py::region_totals` | `site/data.json::totais.taxa_inf_media` | `render.to_payload -> json.dumps` | WIRED | `"taxa_inf_media"` em transform.py; confirmado em data.json |
| `site/app.js::renderTotals/buildRegionStrip` | `data.json::totais.taxa_inf_media` | `t.taxa_inf_media` | WIRED | Linha 58 em app.js: `t.taxa_inf_media != null` |
| `README.md::Crie o painel` | `obs refresh-ibge --region / obs refresh-snis --region / obs build --region` | comandos literais em code blocks | WIRED | Code blocks com `uv run obs refresh-ibge --region minha_regiao`, `refresh-snis`, `build` presentes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `site/app.js::buildRegionStrip` | `t.taxa_inf_media` | `data.json` gerado por `transform.region_totals()` | Sim — média ponderada de `taxa_informalidade_pct × total_ocupados` do Censo 2022 | FLOWING |
| `site/app.js::buildCitySelect` | `DATA.municipios` | `data.json` via `render.to_payload()` | Sim — 27 municípios RMS com flags reais | FLOWING |
| `pipeline/sources/ibge.py::refresh` | `df` (municipios.csv) | `pl.read_csv(cache_path)` | Sim — lê CSV real; upsert com dados da API IBGE | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| RMS build 27/27 offline | `uv run obs build --region rms` | `27/27 municípios com dado público` | PASS |
| taxa_inf_media em data.json | `python3 -c "import json; d=json.load(open('site/data.json')); print('taxa_inf_media' in d['totais'])"` | `True` | PASS |
| taxa_inf_media_rms ausente de data.json | `python3 -c "import json; d=json.load(open('site/data.json')); print('taxa_inf_media_rms' not in d['totais'])"` | `True` | PASS |
| refresh-ibge --help mostra --region | `uv run obs refresh-ibge --help` | `--region REGION` na saída | PASS |
| refresh-snis --help mostra --region | `uv run obs refresh-snis --help` | `--region REGION` na saída | PASS |
| Região inexistente → mensagem amigável, sem crash | Python offline: `ibge.refresh('regiao_inexistente', root)` | `"Região 'regiao_inexistente' não existe..."` no stderr; return sem exceção | PASS |
| snis importado não carrega requests | `python3 -c "import pipeline.sources.snis; print('requests' not in __import__('sys').modules)"` | `True` | PASS |
| ibge importado não carrega httpx | `python3 -c "import pipeline.sources.ibge; print('httpx' not in __import__('sys').modules)"` | `True` | PASS |
| cold-start build sem CSVs → pendente | `uv run pytest tests/test_pipeline.py::test_cold_start_build_sem_csvs_snis_censo_rais` | `1 passed` | PASS |
| pytest suite completa | `uv run pytest -q` | `25 passed in 0.46s` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| GEN-01 | 04-01 | `ibge.refresh()` implementado (API localidades + população) regrava o cache | SATISFIED | `pipeline/sources/ibge.py::refresh()` implementado; NotImplementedError removido; upsert idempotente; D-06/D-09 |
| GEN-02 | 04-03 | `snis.refresh()` documentado e, se viável, automatizado | SATISFIED | `pipeline/sources/snis.py::refresh()` implementado; delega para `scrape_snis.cmd_build`; `obs refresh-snis --region` funcional |
| GEN-03 | 04-01 | Erro amigável quando município não resolve no IBGE | SATISFIED | difflib + mensagem em stderr sem raise; região inexistente → return gracioso; uf vazio → mensagem explicativa |
| GEN-04 | 04-04 | Doc "Crie o painel da sua cidade em 5 minutos"; terceiro gera outra região só editando regions.yml | SATISFIED | README.md com guia completo de 4 passos; regions.yml com contrato mínimo D-03 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | Nenhum anti-padrão encontrado. Sem TBD/FIXME/XXX nos arquivos modificados. |

### Code Review Findings Status (04-REVIEW.md)

Todos os findings do code review foram corrigidos antes da verificação:

| Finding | Severidade | Status |
|---------|-----------|--------|
| CR-01: snis/ibge_informalidade/rais.load() sem coluna 'key' ao retornar vazio | Critical | CORRIGIDO — cada load() adiciona `pl.lit(None).alias("key")` no path vazio; cold-start test PASSA |
| WR-01: upsert com truthiness check `if pop` trata populacao=0 como vazio | Warning | CORRIGIDO — check explícito `pop is not None`; `test_upsert_preserva_populacao_zero` PASSA |
| WR-02: chamadas de rede em ibge.refresh() sem try/except | Warning | CORRIGIDO — try/except `httpx.HTTPError` + `Exception` em ambos os blocos HTTP; `isinstance(raw, list)` guard |
| WR-03: sys.path.insert sem guard em snis.refresh() | Warning | CORRIGIDO — `if scripts_dir not in sys.path: sys.path.insert(...)` |
| WR-04: uf="" não validado antes da chamada HTTP | Warning | CORRIGIDO — `if not uf: print(..., file=sys.stderr); return` |
| IN-01: path traversal allowlist insuficiente | Info | CORRIGIDO — `out.resolve().is_relative_to(snis_dir)` confinamento de caminho |
| IN-02: upsert nulifica colunas extras do CSV | Info | Documentado no código (comportamento atual; schema tem exatamente 5 colunas) |

### Human Verification Required

#### 1. ibge.refresh() com rede real — resolução e idempotência

**Test:** Rodar `uv run obs refresh-ibge --region rms` em ambiente com acesso a `servicodados.ibge.gov.br` e `apisidra.ibge.gov.br`. Executar uma segunda vez.
**Expected:** Primeira execução: `config/municipios.csv atualizado — N municípios resolvidos` (sem stacktrace). Segunda execução: sem alteração em municipios.csv para linhas já preenchidas (idempotência D-06 real).
**Why human:** Requer rede. Os testes offline verificam o code path e a lógica de idempotência via dados sintéticos, mas não exercitam as chamadas HTTP reais.

#### 2. ibge.refresh() — mensagem amigável com typo real de nome de município

**Test:** Modificar temporariamente regions.yml para trocar "Sorocaba" por "Sorocab". Rodar `uv run obs refresh-ibge --region rms`.
**Expected:** Aviso no stderr: `Município 'Sorocab' (SP) não encontrado no IBGE — você quis dizer 'Sorocaba'?`. Sem stacktrace. Os demais municípios são resolvidos normalmente.
**Why human:** O difflib.get_close_matches opera sobre chaves do localidades_map que vem da API; não pode ser exercitado offline.

#### 3. snis.refresh() com rede real

**Test:** Rodar `uv run obs refresh-snis --region rms` em ambiente com acesso a `app4.cidades.gov.br`.
**Expected:** `data/raw/snis/snis_rms.csv` gerado com linhas dos municípios da RMS. Após o refresh: `uv run obs build --region rms` continua 27/27.
**Why human:** scrape_snis.cmd_build requer sessão HTTP com o portal SNIS Série Histórica.

#### 4. Fluxo completo de terceiro — nova região do zero

**Test:** Adicionar uma nova região em `config/regions.yml` (ex.: 2-3 municípios de qualquer estado). Rodar `obs refresh-ibge --region nova_regiao`, `obs refresh-snis --region nova_regiao`, `obs build --region nova_regiao`.
**Expected:** `site/data.json` gerado com municípios da nova região; RSU com dados do SNIS ou `pendente` honesto; informalidade `pendente` (não há dados de Censo fora da RMS pré-carregados). Sem necessidade de tocar em código.
**Why human:** Verifica a experiência end-to-end do terceiro descrita em GEN-04. Requer rede para os dois refreshes.

### Gaps Summary

Não há gaps bloqueadores. Todos os 9 must-haves estão VERIFIED pelo código. Os 4 itens de verificação humana acima dependem de rede externa (IBGE API, SNIS portal) e não podem ser confirmados em ambiente offline — são classificados como `human_needed`, não `failed`.

---

_Verified: 2026-06-24T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
