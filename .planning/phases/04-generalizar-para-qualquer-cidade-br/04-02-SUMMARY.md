---
phase: 04-generalizar-para-qualquer-cidade-br
plan: 02
subsystem: pipeline, frontend
tags: [polars, javascript, transform, rename, d-02]

# Dependency graph
requires:
  - phase: 04-01
    provides: ibge.refresh() implementado; cli.py com label genérico e --region
provides:
  - taxa_inf_media genérico em pipeline/transform.py (sem sufixo rms)
  - sort com nulls_last=True em build_region() para suportar regiões sem sub-regiões
  - app.js com chave t.taxa_inf_media e buildCitySelect dinâmico para qualquer conjunto de sub-regiões
  - data.json com taxa_inf_media em totais (rebuild determinístico confirmado)
  - 4 novos testes de regressão D-02
affects:
  - 04-03 (ibge.refresh via CLI usa taxa_inf_media; qualquer plano que leia data.json)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Polars sort com nulls_last=True para colunas opcionais em DataFrames"
    - "JavaScript subs dinâmico via Object.keys() em vez de objeto estático hardcoded"

key-files:
  created: []
  modified:
    - pipeline/transform.py
    - site/app.js
    - tests/test_pipeline.py
    - site/data.json

key-decisions:
  - "D-02: taxa_inf_media_rms renomeada para taxa_inf_media — rename atômico em transform.py, tests e app.js"
  - "D-02: sort com nulls_last=True para municípios sem subregiao aparecerem no final (mais natural)"
  - "D-02: buildCitySelect usa somenteNull para trocar label Outros → Municípios em região sem sub-regiões"
  - "D-02: subs dinâmico resolve Assumption A2 (subregiao inteiro fora de {1,2,3} causaria TypeError)"

patterns-established:
  - "Rename de chave pública: sempre atualizar produtor (transform.py), consumidores (app.js, cli.py) e testes na mesma task"
  - "subs dinâmico em JS: Object.keys(subs).sort() em vez de array hardcoded"

requirements-completed:
  - GEN-01
  - GEN-03

# Metrics
duration: 15min
completed: 2026-06-24
---

# Phase 04 Plan 02: Desacoplamento RMS — rename taxa_inf_media e buildCitySelect dinâmico (D-02)

**Rename atômico de taxa_inf_media_rms para taxa_inf_media em transform.py e app.js com sort Polars nulls_last=True e buildCitySelect dinâmico suportando qualquer conjunto de sub-regiões**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-24T12:50:00Z
- **Completed:** 2026-06-24T13:05:00Z
- **Tasks:** 2 (Task 1 TDD com 3 commits; Task 2 com 1 commit)
- **Files modified:** 4

## Accomplishments

- Renomeação atômica de `taxa_inf_media_rms` → `taxa_inf_media` em `pipeline/transform.py`, `tests/test_pipeline.py` e `site/app.js` — zero ocorrências funcionais da chave antiga
- `build_region()` usa `sort(["subregiao","nome"], nulls_last=True)` — municípios sem sub-região não crasham e aparecem no final
- `buildCitySelect()` em `app.js` agora usa `subs` dinâmico via `Object.keys()`, suportando `subregiao` inteiro arbitrário e label "Municípios" para regiões sem sub-regiões
- `uv run obs build --region rms` gera `data.json` com `taxa_inf_media` em totais — determinístico e idêntico ao anterior exceto chave renomeada
- 23 testes passam (4 novos D-02 + 19 existentes sem regressão)

## Task Commits

1. **RED: testes D-02** - `1062d9f` (test)
2. **GREEN: rename transform.py + testes existentes + rebuild** - `50cd4ec` (feat)
3. **Task 2: app.js** - `8a41ff7` (feat)

## Files Created/Modified

- `pipeline/transform.py` — `region_totals()` devolve `taxa_inf_media`; `build_region()` usa `nulls_last=True`
- `tests/test_pipeline.py` — 4 novos testes adicionados; asserts existentes atualizados para chave nova
- `site/app.js` — linha 58: `t.taxa_inf_media` e label genérico; `buildCitySelect()` dinâmico com `somenteNull`
- `site/data.json` — rebuild com `taxa_inf_media` em totais (confirmado por teste `test_payload_usa_chave_generica`)

## Decisions Made

- `nulls_last=True` escolhido (não apenas `nulls_last=False` default) para que municípios sem sub-região apareçam após os grupos numerados — comportamento mais natural para lista plana
- Label "Municípios" (não "Outros") quando `somenteNull` — semanticamente correto para região sem sub-regiões
- Ocorrências de `taxa_inf_media_rms` em comentários e asserções negativas (`not in`) nos testes foram mantidas — são verificações de ausência, não uso operacional da chave

## Deviations from Plan

None — plano executado exatamente como escrito.

## Issues Encountered

Nenhum. O rename atômico e o sort com `nulls_last=True` foram aplicados conforme especificado. Os testes RED falharam corretamente antes das mudanças no código e passaram após (ciclo TDD cumprido).

## User Setup Required

None — nenhuma configuração externa necessária.

## Next Phase Readiness

- Pronto para Phase 04 Plan 03 (`snis.refresh()` e `obs refresh-snis`)
- `taxa_inf_media` é agora a chave canônica em todo o sistema (pipeline → data.json → app.js)
- Regiões sem sub-regiões funcionam corretamente no frontend (validado por lógica e testes)

---
*Phase: 04-generalizar-para-qualquer-cidade-br*
*Completed: 2026-06-24*
