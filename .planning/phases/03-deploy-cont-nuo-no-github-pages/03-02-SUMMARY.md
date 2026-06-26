---
phase: 03-deploy-cont-nuo-no-github-pages
plan: "02"
subsystem: docs
tags: [github-pages, github-actions, readme, badge, deploy]

# Dependency graph
requires:
  - phase: 03-deploy-cont-nuo-no-github-pages
    provides: workflow build.yml finalizado (03-01) na main, com job deploy pronto
provides:
  - README com badge de status do workflow build-and-deploy (D-07)
  - README com link "Ver painel ao vivo" para a URL pública futura do Pages (D-06/D-07)
affects:
  - phase: 03-deploy-cont-nuo-no-github-pages (verificação de fase — deploy ao vivo ainda NÃO confirmado)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Badge SVG nativo do GitHub Actions (actions/workflows/build.yml/badge.svg) — status do build independente do Pages estar ativo"
    - "Link público apontando para URL estável do Pages antes da ativação — link válido assim que o usuário ativar Settings → Pages"

key-files:
  created: []
  modified:
    - README.md

key-decisions:
  - "Task 1 (ativação manual do GitHub Pages, D-04) DEFERRED por decisão do usuário — publicação adiada; usuário testará localmente via Python por enquanto"
  - "Badge de build adicionado mesmo com Pages inativo — o badge reflete status do workflow no GitHub Actions, que funciona independente do Pages"
  - "Link 'Ver painel ao vivo' aponta para a URL pública futura (civisbr.github.io/residuos-informalidade-rms) — válido assim que o usuário ativar o Pages e rodar o workflow"

patterns-established:
  - "Badge + link público no topo do README como contrato de descoberta para visitantes do repositório"

requirements-completed: [DEPLOY-03]

# Metrics
duration: 2min
completed: 2026-06-23
---

# Phase 03 Plan 02: Ativar GitHub Pages + badge e link no README — Summary

**README ganha badge de status do workflow build-and-deploy e link 'Ver painel ao vivo' para a URL pública do Pages; ativação manual do Pages (D-04) ADIADA por decisão do usuário — site ainda não está ao vivo**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-06-23T18:21:25Z
- **Completed:** 2026-06-23T18:22:40Z
- **Tasks:** 2 (1 concluída, 1 DEFERRED)
- **Files modified:** 1

## Accomplishments

- README.md: badge de build SVG nativo do GitHub Actions inserido no topo, imediatamente abaixo do H1 e antes do blockquote descritivo (D-07)
- README.md: link **[Ver painel ao vivo →]** apontando para https://civisbr.github.io/residuos-informalidade-rms/ ao lado do badge (D-06/D-07)
- Badge clicável aponta para a página de execuções do workflow (actions/workflows/build.yml)
- Caminhos relativos do front preservados: site/app.js mantém `fetch("./data.json", ...)`, site/index.html sem `base href` (D-06)

## Task Commits

1. **Task 1: Ativar GitHub Pages — Source = "GitHub Actions" (D-04)** — DEFERRED (passo manual humano não executado; ver "User Setup Required")
2. **Task 2: Adicionar badge de build e link público ao README (D-07)** — `8553cab` (docs)

## Files Created/Modified

- `README.md` — inserida linha 2 com badge de build (`actions/workflows/build.yml/badge.svg`) + link "Ver painel ao vivo →" para a URL pública do Pages; nenhuma outra linha alterada

## Decisions Made

- **Task 1 (D-04) DEFERRED:** o usuário decidiu, no checkpoint human-action, NÃO ativar o GitHub Pages por enquanto — a publicação fica adiada e o usuário testará o painel localmente via `python -m http.server`. A ativação manual de Settings → Pages → Source = "GitHub Actions" não foi realizada.
- **Badge adicionado mesmo com Pages inativo:** o badge SVG reflete o status do workflow no GitHub Actions, que é independente do Pages estar ativo. Continua válido e útil desde já.
- **Link público aponta para a URL futura:** o link "Ver painel ao vivo" usa a URL estável do Pages (civisbr.github.io/residuos-informalidade-rms). O link passa a funcionar assim que o usuário ativar o Pages e o primeiro deploy concluir.

## Deviations from Plan

None nos passos executados — Task 2 executada exatamente como especificada no plano (bloco de badge + link inserido na posição indicada, URLs exatas, caminhos relativos intactos).

A única divergência é de escopo, por decisão explícita do usuário: Task 1 (checkpoint human-action) foi marcada DEFERRED em vez de concluída. Isso não é uma deviation de implementação (Rules 1-4), e sim uma escolha do usuário no checkpoint.

## Issues Encountered

Nenhum. As 6 verificações automatizadas do plano passaram:
- badge URL: OK · link público: OK · texto link: OK · badge no topo (head -5): OK
- site/index.html sem `base href`: OK · site/app.js fetch relativo preservado: OK

## User Setup Required

**PENDENTE — DEPLOY AO VIVO AINDA NÃO CONFIRMADO.** O site só fica acessível em
https://civisbr.github.io/residuos-informalidade-rms/ após o usuário executar os passos
manuais abaixo (D-04):

1. Abrir https://github.com/civisbr/residuos-informalidade-rms
2. Settings → Pages → "Build and deployment" → Source: selecionar **"GitHub Actions"** → Save
3. Confirmar que o environment `github-pages` aparece em Settings → Environments
4. Acionar o deploy: push na main OU Actions → build-and-deploy → Run workflow (workflow_dispatch)
5. Após o job `deploy` concluir, acessar a URL pública para confirmar que o painel carrega

Enquanto o Pages não for ativado:
- O badge de build pode aparecer cinza/"no status" até a primeira execução do workflow no GitHub.
- O link "Ver painel ao vivo →" retornará 404 até o primeiro deploy bem-sucedido.

**A verificação de fase NÃO deve marcar o deploy ao vivo como confirmado** até que o usuário
ative o Pages e o primeiro deploy conclua com sucesso.

## Next Phase Readiness

- README pronto: badge + link público no topo, comunicando status do build e onde o painel ficará hospedado
- Caminhos relativos do front intactos — o deploy funcionará corretamente sob o subpath /residuos-informalidade-rms/ assim que o Pages for ativado
- Bloqueio remanescente da Fase 3: ativação manual do Pages (D-04, DEFERRED) — único passo entre o estado atual e o site ao vivo

## Self-Check: PASSED

- README.md existe e contém o badge + link (verificado via grep — todas as 6 checagens OK)
- Commit 8553cab existe no histórico (Task 2)
- Task 1 DEFERRED documentada em "User Setup Required" para a verificação de fase
