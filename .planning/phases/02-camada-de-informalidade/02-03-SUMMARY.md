---
phase: 02-camada-de-informalidade
plan: "03"
subsystem: ui
tags: [vanilla-js, html, informalidade, censo-2022, rais-2023, pnad, region-strip, kpi-cards]

dependency_graph:
  requires:
    - phase: 02-02
      provides:
        - site/data.json com taxa_informalidade_pct, proxy_formalizacao, meta.pnad_contexto_regional
        - totais.taxa_inf_media_rms
  provides:
    - site/index.html com slots #kpisInf, #infSubcount, #infTags, #pnadRegional
    - site/app.js::renderInformalidade() com 3 KPIs + nota D-10 + contexto PNAD
    - site/app.js::buildRegionStrip() com célula 'Informalidade média RMS'
    - site/app.js::selectCity() chamando renderInformalidade() após renderKpis()
  affects: []

tech-stack:
  added: []
  patterns:
    - renderInformalidade() reutiliza tag()/cell() no mesmo padrão de renderKpis()
    - infSubcount injetado sempre (sem condicional) para garantir nota D-10 permanente
    - pnadRegional exibe contexto via DATA.meta (não CITY) — invariante D-02
    - flag || "pendente" como fallback seguro (T-02-13)

key-files:
  created: []
  modified:
    - site/index.html
    - site/app.js

key-decisions:
  - "infSubcount injetado sem condicional em renderInformalidade() — nota D-10 sempre visível conforme D-10/T-02-12"
  - "PNAD exibida via DATA.meta.pnad_contexto_regional, nunca via CITY — invariante D-02/T-02-11"
  - "pnadRegional usa class caveat inline para visibilidade, sem nova classe CSS"
  - "buildRegionStrip() adiciona célula após Cooperados mapeados, antes de População"

requirements-completed:
  - INFO-03
  - INFO-04

duration: ~8min
completed: 2026-06-23
---

# Phase 02 Plan 03: Painel com camada de informalidade Summary

**Seção de informalidade adicionada ao painel vanilla JS: 3 KPIs (taxa Censo 2022, empregos formais RAIS, grau de formalização proxy) com tags real/pendente, nota D-10 fixa, contexto PNAD rotulado como estimativa regional e célula de informalidade média no region-strip**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-23T17:18:36Z
- **Completed:** 2026-06-23
- **Tasks:** 2 de 2 auto + 1 checkpoint (verificação visual APROVADA pelo usuário)
- **Files modified:** 2

## Accomplishments

- `index.html` recebe 4 novos slots: `#infTags`, `#kpisInf`, `#infSubcount` (caveat, display:block), `#pnadRegional`
- `renderInformalidade()` preenche os 3 KPIs de informalidade com fallback seguro para `pendente`, nota D-10 sempre injetada e contexto PNAD com rótulo explícito de estimativa regional
- `selectCity()` chama `renderInformalidade()` após `renderKpis()` — painel muda de município sem erro
- `buildRegionStrip()` inclui célula "Informalidade média RMS" (28,8%) após "Cooperados mapeados"
- 12 testes passando, `uv run obs build --region rms` exit 0

## Task Commits

1. **Task 1: Slots HTML para seção de informalidade** - `6dad7c2` (feat)
2. **Task 2: renderInformalidade(), region-strip e selectCity() wired** - `1fed1bd` (feat)

## Files Created/Modified

- `site/index.html` — 4 novos slots HTML para a seção de informalidade (posicionados após #kpis, antes do simulador)
- `site/app.js` — renderInformalidade() (58 linhas), selectCity() wiring, buildRegionStrip() com célula informalidade

## Decisions Made

- `infSubcount` injetado sempre, sem condicional — garante nota D-10 não-colapsável (D-10/T-02-12)
- `pnadRegional` lê `DATA.meta.pnad_contexto_regional`, nunca `CITY` — invariante D-02/T-02-11 implementada no front
- `tag est` + rótulo "Estado de SP (estimativa regional)" para PNAD — distinção visual inequívoca entre dado municipal e estimativa regional
- Fallback `c.flag_informalidade || "pendente"` para dado ausente — T-02-13 mitigado

## Deviations from Plan

Nenhuma — plano executado exatamente como especificado.

## Issues Encountered

Nenhum. Dados do data.json (gerado no plano 02-02) cobrem os 27 municípios com todos os campos esperados.

## Threat Mitigations Applied

| Threat | Mitigação |
|--------|-----------|
| T-02-11 (PNAD como dado municipal) | renderInformalidade() usa DATA.meta.pnad_contexto_regional; rótulo "Estado de SP (estimativa regional)" + tag.est; nunca usa CITY.pnad |
| T-02-12 (nota D-10 colapsável) | $("infSubcount").innerHTML injetado sem condicional; slot HTML com style="display:block" sem atributo hidden |
| T-02-13 (pendente exibido como real) | flag_informalidade \|\| "pendente" como fallback seguro |

## Known Stubs

Nenhum. Todos os campos são dados reais do Censo 2022 / RAIS 2023 (flag real). PNAD é estimativa regional com flag explícito.

## Checkpoint — Verificação Visual

A Tarefa 3 (`checkpoint:human-verify`) foi APROVADA pelo usuário em 2026-06-23. Verificação visual confirmada: seção de informalidade visível, 3 KPIs com tags corretas, nota D-10 sempre visível, contexto PNAD rotulado como estimativa regional, célula de informalidade média no region-strip. Fase 2 (INFO-01..04) 100% cumprida.

## Self-Check: PASSED

Arquivos modificados:
- site/index.html: FOUND
- site/app.js: FOUND

Commits:
- 6dad7c2: FOUND (feat slots HTML)
- 1fed1bd: FOUND (feat renderInformalidade)

Testes: 12 passed (uv run pytest -q)
Build: uv run obs build --region rms → 27/27 municípios
