---
phase: "04-generalizar-para-qualquer-cidade-br"
plan: 1
subsystem: pipeline/sources
tags: [ibge, refresh, upsert, cli, offline-first, tdd]
dependency_graph:
  requires: []
  provides:
    - ibge.refresh(region, root) — GEN-01/D-04/D-05/D-06/D-09
    - obs refresh-ibge --region <chave> — CLI D-04
  affects:
    - config/municipios.csv (alvo do upsert)
    - pipeline/cli.py (--region obrigatório)
tech_stack:
  added: []
  patterns:
    - lazy-import de httpx dentro de refresh() para não vazar no build offline
    - upsert idempotente Polars via pl.concat após filtro por slug
    - difflib.get_close_matches para sugestão de nome amigável (D-09)
    - yaml.safe_load para leitura segura de regions.yml (T-04-02)
key_files:
  created: []
  modified:
    - pipeline/sources/ibge.py
    - pipeline/cli.py
    - tests/test_pipeline.py
decisions:
  - D-04: obs refresh-ibge --region <chave> resolve só municípios da região, upsert em municipios.csv
  - D-05: fonte_pop="IBGE Censo 2022" (literal exato — Censo fixo, mais estável que estimativa anual)
  - D-06: upsert só preenche campos vazios; linhas com codigo_ibge E populacao preservadas
  - D-09: fail-soft com difflib.get_close_matches — aviso amigável, sem stacktrace, continua demais
  - T-04-01: validar region antes de qualquer operação — evita crashe e path traversal
  - T-04-03: httpx.Client(timeout=60) localidades; timeout=120 SIDRA batch (~1.4 MB)
  - T-04-04: r.get("V","").isdigit() antes de int(r["V"]) — V não-numérico → campo vazio (pendente honesto)
metrics:
  duration_minutes: 25
  completed_date: "2026-06-24"
  tasks_completed: 2
  files_modified: 3
---

# Phase 04 Plan 01: ibge.refresh() + CLI refresh-ibge Summary

Implementação do `ibge.refresh(region, root)` usando as APIs públicas do IBGE (localidades + SIDRA Censo 2022), com upsert idempotente via Polars, erro amigável via difflib, e exposição como `obs refresh-ibge --region <chave>` no CLI.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED  | Testes TDD para ibge.refresh() | 6fdeb0e | tests/test_pipeline.py (+117 linhas) |
| 1    | ibge.refresh() implementado | 1db30e9 | pipeline/sources/ibge.py |
| 2    | CLI atualizado | 98a6a69 | pipeline/cli.py |

## What Was Built

### Task 1: ibge.refresh(region, root) — pipeline/sources/ibge.py

Implementação completa substituindo o `NotImplementedError` anterior:

1. **Lazy import httpx** dentro de `refresh()` — nunca vaza para o build offline
2. **yaml.safe_load** para ler `regions.yml`; valida que `region` existe (T-04-01, fail-soft)
3. **API Localidades** `GET /api/v1/localidades/estados/{UF}/municipios` com `timeout=60`; constrói `localidades_map: dict[slug(nome), dict]`
4. **API SIDRA** `GET /values/t/4714/n6/all/v/93/p/2022` com `timeout=120`; pula `data[0]` (header); constrói `pop_map: dict[str_7dig, int]` com condição `r.get("V","").isdigit()` (T-04-04)
5. **Upsert idempotente D-06**: para cada município da região — verifica slug no cache; se linha existe e ambos campos preenchidos → `continue` (preserva curadoria); caso contrário, remove linha antiga e faz `pl.concat` com linha nova
6. **Erro amigável D-09**: se `localidades_map.get(key)` retorna `None` → `difflib.get_close_matches` com `cutoff=0.6`; aviso com sugestão (ou sem) para stderr; adiciona a `unresolved`; continua os demais
7. **fonte_pop="IBGE Censo 2022"** (literal exato D-05)
8. Resumo final: `N municípios resolvidos` + lista de não-resolvidos

`load()` permanece intacto — build 100% offline preservado.

### Task 2: CLI — pipeline/cli.py

Três mudanças cirúrgicas:

1. `cmd_refresh_ibge(args)` chama `ibge.refresh(args.region, Path("."))`
2. Sub-parser `refresh-ibge` recebe `--region required=True`
3. `cmd_build` usa `totals.get("taxa_inf_media")` e label `"Informalidade média {meta['nome']}"` (remove hardcode RMS)

### TDD Cycle (RED → GREEN)

7 testes adicionados a `tests/test_pipeline.py`:
- `test_ibge_refresh_signature_e_sem_not_implemented`: assinatura `region+root`, ausência de NotImplementedError
- `test_ibge_refresh_contem_fonte_pop_literal`: literal `"IBGE Censo 2022"` (D-05)
- `test_ibge_refresh_usa_difflib`: `get_close_matches` presente (D-09)
- `test_upsert_preserva_dado_curado`: Sorocaba com ambos preenchidos NÃO é sobrescrita (D-06)
- `test_upsert_preenche_linha_vazia`: Alambari totalmente vazio → deve preencher (D-06)
- `test_upsert_preenche_codigo_ibge_vazio`: Votorantim sem codigo_ibge → deve preencher (D-06)
- `test_ibge_load_permanece_intacto`: `load()` offline continua com 27 linhas e coluna `key`

## Verification Results

```
uv run pytest -q → 19 passed in 0.63s
uv run obs build --region rms → ✓ site/data.json — 27/27 municípios com dado público
uv run obs refresh-ibge --help → mostra --region (obrigatório)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tipo de codigo_ibge em test_ibge_load_permanece_intacto**
- **Found during:** RED phase
- **Issue:** Polars lê `codigo_ibge` como Int64 do CSV (não String). O assert `== "3552205"` falhava por tipo.
- **Fix:** Mudado para `str(soro["codigo_ibge"][0]) == "3552205"` — correto e robusto.
- **Files modified:** tests/test_pipeline.py
- **Commit:** 6fdeb0e (incluído no RED commit)

### Scope Boundary Observations

- A renomeação `taxa_inf_media_rms` → `taxa_inf_media` em `transform.py`, `app.js` e nos testes existentes (`test_region_totals_taxa_inf_media`, `test_payload_tem_informalidade`) está fora do escopo deste plano — será tratada em 04-02 ou 04-03 conforme mapa de acoplamentos RESEARCH.md Pitfall 2. O cli.py já usa a nova chave; até a renomeação em transform.py, a linha de informalidade no output do build fica silenciosa (nenhum crash, `totals.get("taxa_inf_media")` retorna None).

## Known Stubs

Nenhum stub neste plano. O refresh requer rede (by design) e não foi executado no ambiente de CI — o comportamento offline foi validado via testes unitários que simulam as condições D-06 sem rede.

## Threat Flags

Nenhuma superfície nova além do mapeado no `<threat_model>` do plano.

## Self-Check: PASSED

- [x] `pipeline/sources/ibge.py` existe com `def refresh(region: str, root: Path = Path(".")) -> None`
- [x] `pipeline/cli.py` tem `args.region`, `required=True`, `taxa_inf_media`, sem `Informalidade média RMS`
- [x] Commits `6fdeb0e`, `1db30e9`, `98a6a69` existem
- [x] `uv run pytest -q` → 19 passed
- [x] `uv run obs build --region rms` → ✓ 27/27
