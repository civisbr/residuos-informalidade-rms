---
phase: 03-deploy-cont-nuo-no-github-pages
plan: "01"
subsystem: infra
tags: [github-actions, github-pages, ci-cd, python, build-determinism]

# Dependency graph
requires:
  - phase: 02-camada-de-informalidade
    provides: pipeline/render.py com campo gerado_em + site/data.json commitado como safety net
provides:
  - Workflow build.yml revisado com actions v5, concurrency e BUILD_DATE injetado
  - gerado_em determinístico: "local" em rebuilds locais, data real ISO no CI
  - site/data.json commitado atualizado com gerado_em="local" como baseline zero-diff
affects:
  - phase: 03-deploy-cont-nuo-no-github-pages (planos 03-02 e 03-03 — README badge, Pages ativacao)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BUILD_DATE env var com sentinel local: CI injeta data ISO, local usa string fixa ('local') para evitar diff espurio"
    - "Concurrency group 'pages' com cancel-in-progress:true para evitar race condition de deploys paralelos"
    - "Tags imutaveis de versao completa para actions (v8.2.0, v5) — mitigacao supply chain (T-03-01)"

key-files:
  created: []
  modified:
    - .github/workflows/build.yml
    - pipeline/render.py
    - site/data.json

key-decisions:
  - "BUILD_DATE injetado via shell $(date -I) no step obs build — funciona em push E workflow_dispatch sem depender de contexto de evento"
  - "from datetime import date removido de render.py apos confirmar zero outros usos no arquivo"
  - "site/data.json commitado atualizado para gerado_em='local' como novo baseline determinístico"

patterns-established:
  - "gerado_em pattern: os.environ.get('BUILD_DATE', 'local')[:10] — extensivel para outros campos de timestamp de build"

requirements-completed: [DEPLOY-01, DEPLOY-04]

# Metrics
duration: 15min
completed: 2026-06-23
---

# Phase 03 Plan 01: Finalizar build.yml e determinismo de gerado_em — Summary

**Workflow GitHub Actions atualizado para actions v5 com concurrency group e BUILD_DATE injetado; gerado_em em render.py passa a usar sentinel 'local' eliminando diffs espurios em rebuilds locais**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-23T18:05:00Z
- **Completed:** 2026-06-23T18:20:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Workflow build.yml atualizado: setup-uv@v8.2.0, upload-pages-artifact@v5, deploy-pages@v5 (tags imutaveis; mitiga supply chain T-03-01)
- Bloco concurrency adicionado (group: pages, cancel-in-progress: true) — elimina race condition de deploys paralelos (T-03-04)
- BUILD_DATE injetado via `$(date -I)` no step obs build, funcionando em push e workflow_dispatch sem depender de contexto de evento
- gerado_em em render.py substituido de `date.today().isoformat()` para `os.environ.get("BUILD_DATE", "local")[:10]` — zero diff espurio em rebuild local
- site/data.json commitado atualizado com gerado_em="local" como baseline: `uv run obs build --region rms && git diff --exit-code site/data.json` retorna 0

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Finalizar build.yml — versoes v5, concurrency e BUILD_DATE** - `3ce5aba` (feat)
2. **Task 2: Corrigir determinismo de gerado_em em render.py (D-05)** - `9b5f79e` (fix)

## Files Created/Modified

- `.github/workflows/build.yml` — actions v5 (setup-uv@v8.2.0, upload-pages-artifact@v5, deploy-pages@v5), concurrency group pages, BUILD_DATE via shell $(date -I)
- `pipeline/render.py` — gerado_em usa os.environ.get("BUILD_DATE", "local")[:10]; import datetime.date removido (nao mais usado)
- `site/data.json` — gerado_em="local" como novo baseline commitado (safety net D-02, zero-diff garantido)

## Decisions Made

- `BUILD_DATE=$(date -I) uv run obs build --region rms` (forma shell inline) escolhida sobre `env: BUILD_DATE: ${{ github.event.head_commit.timestamp }}` porque funciona identicamente em eventos push e workflow_dispatch, sem depender do contexto do evento GitHub Actions
- `from datetime import date` removido apos confirmar que era o unico uso no arquivo — codigo mais limpo
- site/data.json atualizado junto ao fix do render.py para estabelecer o baseline determinístico imediatamente

## Deviations from Plan

None — plano executado exatamente como especificado.

A instrucao do plano ja indicava preferencia pela "alternativa mais robusta" com `$(date -I)` (RESEARCH.md, secao "Perguntas em Aberto"). Adotou-se essa forma, consistente com o plano.

## Issues Encountered

Durante a verificacao de Task 2: o primeiro `git diff --exit-code site/data.json` retornou diff (gerado_em mudou de "2026-06-23" para "local"). Isso era esperado — o arquivo commitado ainda tinha a data anterior. A solucao foi incluir o site/data.json atualizado no commit de Task 2, estabelecendo o baseline correto. Apos o commit, rebuilds locais produzem zero diff.

## User Setup Required

Passos manuais pendentes para completar a Fase 3 (fora do escopo deste plano):
- D-04: Ativar GitHub Pages nas Settings do repositório (Source = "GitHub Actions") antes do primeiro push com o workflow finalizado
- D-07: Adicionar badge de build e link "painel ao vivo" no README (plano 03-02 ou 03-03)

## Next Phase Readiness

- Workflow build.yml esta pronto para uso — proximo push na main dispara CI com as versoes corretas
- Pipeline Python permanece determinístico — `uv run pytest -q` verde (12 testes), zero diff local
- Restam para a Fase 3: ativacao manual do Pages (D-04) e badge no README (D-07)

---
*Phase: 03-deploy-cont-nuo-no-github-pages*
*Completed: 2026-06-23*
