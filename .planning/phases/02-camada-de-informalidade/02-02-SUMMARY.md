---
phase: 02-camada-de-informalidade
plan: "02"
subsystem: pipeline/transform + pipeline/render
tags: [polars, informalidade, censo-2022, rais-2023, pnad, proxy-formalizacao, data-json]

dependency_graph:
  requires:
    - phase: 02-01
      provides:
        - pipeline/sources/ibge_informalidade.py::load()
        - pipeline/sources/rais.py::load()
        - pipeline/sources/pnad_regional.py::load()
        - data/raw/censo/censo_informalidade_rms.csv
        - data/raw/rais/rais_residuos_rms_sp.csv
        - data/raw/pnad/pnad_sp_informalidade.csv
  provides:
    - pipeline/transform.build_region() com joins Censo+RAIS e proxy D-06/D-07
    - pipeline/render.to_payload() com campos de informalidade por município + meta.pnad_contexto_regional
    - pipeline/cli.py carregando as três novas fontes
    - site/data.json com camada de informalidade completa (27 municípios)
    - tests/test_pipeline.py::test_payload_tem_informalidade
  affects:
    - 02-03 (painel: renderInformalidade() lê taxa_informalidade_pct, proxy_formalizacao de data.json)

tech-stack:
  added: []
  patterns:
    - Join left por key (slug) em build_region() — padrão para novas fontes municipais
    - Renomear coluna "fonte" para "fonte_inf" antes do join (evita conflito com SNIS)
    - Proxy D-06/D-07 via pl.when encadeado com coluna auxiliar _denominador (removida via .drop)
    - pnad_contexto_regional em meta — nunca em municipios[] (invariante D-02)
    - Média ponderada por total_ocupados em region_totals() para taxa regional

key-files:
  created: []
  modified:
    - pipeline/transform.py
    - pipeline/render.py
    - pipeline/cli.py
    - site/data.json
    - tests/test_pipeline.py

key-decisions:
  - "build_region() assinatura extendida: novo argumento informalidade (ibge_informalidade.load()) e rais_residuos (rais.load())"
  - "fonte_inf renomeada antes do join para evitar conflito com coluna fonte do SNIS (T-02-09)"
  - "taxa_inf_media_rms = média ponderada de taxa_informalidade_pct por total_ocupados (apenas municípios com ambos não-null)"
  - "Sorocaba proxy=0.842 (formais=745, cooperados=140) — D-07 confirmado: proxy calculável quando formais>0"
  - "pnad_contexto_regional em meta com {uf, periodo, taxa_informalidade_pct, flag, ambito, fonte} — nunca em municipios[]"

requirements-completed:
  - INFO-01
  - INFO-02

duration: ~12min
completed: 2026-06-23
---

# Phase 02 Plan 02: Pipeline com camada de informalidade Summary

**Joins de Censo 2022 + RAIS 2023 em build_region() com proxy D-06/D-07 em Polars; to_payload() expõe taxa_informalidade_pct e pnad_contexto_regional; data.json regenerado com informalidade completa para os 27 municípios da RMS**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-23T12:00:00Z
- **Completed:** 2026-06-23
- **Tasks:** 2 (TDD: 4 commits — 2 RED + 2 GREEN)
- **Files modified:** 5

## Accomplishments

- `build_region()` estendida com dois joins (ibge_informalidade + rais) e derivação de flag_informalidade, proxy_formalizacao, flag_proxy per D-06/D-07
- `region_totals()` calcula taxa_inf_media_rms=28.8% (ponderada por total_ocupados dos 27 municípios)
- `to_payload()` expõe 10 novos campos por município + meta.pnad_contexto_regional (PNAD apenas em meta, D-02)
- `cli.py` carrega as três novas fontes e as passa para build_region/to_payload
- `site/data.json` regenerado: 27/27 municípios com informalidade, taxa_inf_media_rms=28.8%, PNAD SP=30.0%
- 12 testes passando (incluindo test_payload_tem_informalidade)

## Task Commits

1. **Task 1 RED: testes build_region() com informalidade** - `5a03026` (test)
2. **Task 1 GREEN: transform.py estendido** - `1404b68` (feat)
3. **Task 2 RED: test_payload_tem_informalidade** - `6ed5474` (test)
4. **Task 2 GREEN: render.py, cli.py, data.json** - `d329239` (feat)

## Files Created/Modified

- `pipeline/transform.py` — build_region() com 4 parâmetros adicionais + 2 joins + derivação proxy; region_totals() com taxa_inf_media_rms
- `pipeline/render.py` — to_payload() com pnad_df; 10 campos novos por município; meta.pnad_contexto_regional
- `pipeline/cli.py` — importa ibge_informalidade, rais, pnad_regional; passa para build_region/to_payload
- `site/data.json` — artefato gerado: 27 municípios com taxa_informalidade_pct, flag_informalidade, proxy_formalizacao, flag_proxy; meta.pnad_contexto_regional; totais.taxa_inf_media_rms
- `tests/test_pipeline.py` — test_build_region_com_informalidade, test_region_totals_taxa_inf_media, test_payload_tem_informalidade; atualização de test_build_offline_gera_dados para nova assinatura

## Decisions Made

- Renomear coluna `fonte` do ibge_informalidade para `fonte_inf` via `.select()` com alias antes do join — evita coluna duplicada (Pitfall da T-02-09)
- `pnad_df` aceito como parâmetro opcional `None` em `to_payload()` — retrocompatibilidade
- `taxa_inf_media_rms` calculado com filtro duplo (taxa not null AND total_ocupados not null) para robustez em deploys sem dado

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Atualização de test_build_offline_gera_dados para nova assinatura**
- **Found during:** Task 1 GREEN (após implementar build_region() com 6 argumentos)
- **Issue:** test_build_offline_gera_dados chamava build_region() com 4 argumentos (assinatura antiga), causando TypeError
- **Fix:** Atualizado para passar ibge_informalidade.load(ROOT) e rais.load(ROOT) como argumentos 4 e 5
- **Files modified:** tests/test_pipeline.py
- **Verification:** uv run pytest -q → 11 passed (antes do commit Task 2)
- **Committed in:** 1404b68 (parte do commit de implementação da Tarefa 1)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug de regressão de assinatura)
**Impact on plan:** Necessário para manter testes verdes; sem escopo adicional.

## Issues Encountered

Nenhum. Todos os pitfalls documentados no RESEARCH.md foram seguidos:
- Pitfall 2 (RAIS null vs 0): CSV já tem todos os 27 municípios com formais_residuos (0 quando ausente)
- Pitfall 4 (Sorocaba cooperados null): cooperados=140.0 no CSV do SNIS — proxy calculado como 745/(745+140)=0.842
- T-02-09 (conflito coluna "fonte"): resolvido com `.select(pl.col("fonte").alias("fonte_inf"))` antes do join

## Known Stubs

Nenhum. Todos os campos de informalidade são dados reais do Censo 2022 ou RAIS 2023 (flag real). PNAD é estimativa regional com flag explícito. `refresh()` é NotImplementedError documentado (não stub silencioso).

## Threat Mitigations Applied

| Threat | Mitigação |
|--------|-----------|
| T-02-07 (proxy D-07 violado) | pl.when encadeado verifica AMBOS null/0; test_build_region_com_informalidade + test_proxy_pendente_edge_case; Sorocaba proxy!=null confirmado |
| T-02-08 (PNAD em municipios[]) | to_payload() não itera pnad_df por município; test_payload_tem_informalidade asserta ausência; verificação inline confirma |
| T-02-09 (conflito coluna fonte) | fonte_inf renomeada antes do join via select+alias; join bem-sucedido sem coluna duplicada |
| T-02-10 (csvs ausentes) | load() retorna DataFrame vazio com SCHEMA correto; join produz null tratado como pendente |

## Self-Check: PASSED

Arquivos modificados:
- pipeline/transform.py: FOUND
- pipeline/render.py: FOUND
- pipeline/cli.py: FOUND
- site/data.json: FOUND
- tests/test_pipeline.py: FOUND

Commits:
- 5a03026: FOUND (test RED build_region)
- 1404b68: FOUND (feat transform.py)
- 6ed5474: FOUND (test RED payload)
- d329239: FOUND (feat render/cli/data.json)

Testes: 12 passed (uv run pytest -q)
Build: uv run obs build --region rms → 27/27 municípios, taxa_inf_media_rms=28.8%, PNAD ok
data.json verificações: pnad_contexto_regional.flag=estimativa, PNAD ausente em todos municipios[], taxa_inf_media_rms em totais
