---
phase: 03-deploy-cont-nuo-no-github-pages
verified: 2026-06-24T00:00:00Z
status: human_needed
score: 6/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Ativar GitHub Pages nas Settings do repositório (Source = 'GitHub Actions') e confirmar primeiro deploy bem-sucedido"
    expected: "Settings → Pages mostra 'Your site is ready to be published' com Source = GitHub Actions; environment github-pages aparece em Settings → Environments; https://civisbr.github.io/residuos-informalidade-rms/ exibe o painel ao vivo após o primeiro deploy"
    why_human: "Ativação do Pages é um clique manual no GitHub UI — não é código versionável e não pode ser verificado programaticamente. O job deploy do workflow depende desse environment existir; sem ele, o job falha com 'environment not found'. Decisão explícita do usuário de diferir essa ação (checkpoint human-action DEFERRED no plano 03-02)."
---

# Phase 03: Deploy Contínuo no GitHub Pages — Relatório de Verificação

**Phase Goal:** Push na `main` reconstrói `data.json` e publica o site automaticamente, com URL pública e badge de build.
**Verified:** 2026-06-24T00:00:00Z
**Status:** human_needed
**Re-verification:** Não — verificação inicial

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Push na `main` dispara workflow que roda pytest + `obs build` e faz deploy (DEPLOY-01) | VERIFIED | `.github/workflows/build.yml` existe com trigger `on: push: branches: [main]` + `workflow_dispatch`. Gate `uv run pytest -q` presente antes do upload. Job `deploy` encadeado com `needs: build` usando `actions/deploy-pages@v5`. |
| 2 | Rebuild local com `uv run obs build --region rms` NÃO gera diff em `site/data.json` (determinismo) | VERIFIED | `uv run obs build --region rms && git diff --exit-code site/data.json` retornou exit code 0. `site/data.json` tem `"gerado_em": "local"` como baseline commitado. |
| 3 | Deploy no CI exibe data real de publicação em `gerado_em` quando `BUILD_DATE` está setada | VERIFIED | `BUILD_DATE=2026-06-24 uv run obs build --region rms` produziu `"gerado_em": "2026-06-24"`. Lógica: `os.environ.get("BUILD_DATE", "local")[:10]` em `pipeline/render.py` linha 61. |
| 4 | Workflows concorrentes são cancelados pelo mais recente (concurrency group) | VERIFIED | `.github/workflows/build.yml` contém bloco `concurrency: group: pages / cancel-in-progress: true`. |
| 5 | README mostra badge de status do workflow build-and-deploy (DEPLOY-03) | VERIFIED | README linha 3: `[![Build](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg)](...)`. Badge nas primeiras 5 linhas confirmado por grep. |
| 6 | README mostra link "Ver painel ao vivo" apontando para a URL pública (DEPLOY-03) | VERIFIED | README linha 3: `**[Ver painel ao vivo →](https://civisbr.github.io/residuos-informalidade-rms/)**` presente na mesma linha do badge. |
| 7 | GitHub Pages ativado e site acessível em https://civisbr.github.io/residuos-informalidade-rms/ (DEPLOY-02) | HUMAN NEEDED | Ativação manual pendente por decisão explícita do usuário (checkpoint human-action DEFERRED no plano 03-02). Não é um defeito de código — o workflow e o artifact estão corretos. |

**Score:** 6/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/build.yml` | Workflow com actions v5, concurrency e BUILD_DATE | VERIFIED | setup-uv@v8.2.0, upload-pages-artifact@v5, deploy-pages@v5; concurrency group pages; `BUILD_DATE=$(date -I) uv run obs build --region rms`; permissions scoped (contents:read, pages:write, id-token:write); environment github-pages presente. |
| `pipeline/render.py` | `gerado_em` via `os.environ.get("BUILD_DATE", "local")[:10]` | VERIFIED | Linha 61 contém exatamente `os.environ.get("BUILD_DATE", "local")[:10]`. `date.today()` ausente. `from datetime import date` removido. `import os` presente. |
| `site/data.json` | Commitado com `gerado_em="local"` como baseline zero-diff | VERIFIED | Campo `"gerado_em": "local"` confirmado. Rebuild local produz zero diff (`git diff --exit-code` exit 0). |
| `README.md` | Badge de workflow + link público no topo (primeiras 5 linhas) | VERIFIED | Linha 3 do README contém badge SVG e link "Ver painel ao vivo →". Ambos apontam para URLs corretas. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `.github/workflows/build.yml` | `pipeline/render.py` | env `BUILD_DATE` injetado no step `obs build` | VERIFIED | Step: `BUILD_DATE=$(date -I) uv run obs build --region rms` — variável disponível para `os.environ.get("BUILD_DATE", "local")` em render.py. |
| `pipeline/render.py` | `site/data.json` | `to_payload()` → campo `gerado_em` | VERIFIED | `to_payload()` inclui `"gerado_em": os.environ.get("BUILD_DATE", "local")[:10]`; `write()` serializa o payload para `site/data.json`. |
| `README.md badge` | `github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml` | URL do badge SVG nativa do GitHub Actions | VERIFIED | Badge URL confirmada: `https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg` com link para a página de execuções. |
| `README.md link` | `https://civisbr.github.io/residuos-informalidade-rms/` | Markdown link explícito | VERIFIED | `civisbr.github.io/residuos-informalidade-rms` presente no README linha 3. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `site/data.json` | `gerado_em` | `os.environ.get("BUILD_DATE", "local")` em `pipeline/render.py` | Sim — no CI: data real do runner via `$(date -I)`; local: string fixa `"local"` (determinística) | FLOWING |
| `site/data.json` | `municipios[]` | Pipeline Polars (SNIS + IBGE + PMGIRS) em `pipeline/transform.py` | Sim — 27 municípios com dados reais, confirmados por `totais.municipios_com_dado: 27` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| pytest verde (gate CI) | `uv run pytest -q` | 12 passed | PASS |
| Rebuild local: zero diff em `site/data.json` | `uv run obs build --region rms && git diff --exit-code site/data.json` | exit 0, sem diff | PASS |
| BUILD_DATE injeta data real em `gerado_em` | `BUILD_DATE=2026-06-24 uv run obs build --region rms` + ler `gerado_em` | `"2026-06-24"` | PASS |
| Sem `base href` em `site/index.html` | `grep "base href" site/index.html` | nenhum resultado | PASS |
| Caminho relativo `./data.json` preservado em `site/app.js` | `grep 'fetch.*data.json' site/app.js` | `fetch("./data.json", { cache: "no-store" })` | PASS |

---

### Requirements Coverage

| Requirement | Fonte (REQUIREMENTS.md) | Descrição | Status | Evidence |
|-------------|------------------------|-----------|--------|----------|
| DEPLOY-01 | Phase 3 | Workflow `.github/workflows/build.yml` revisado e reconstrói `data.json` no push à `main` | SATISFIED | Workflow atualizado com trigger push/main, gate pytest, step obs build com BUILD_DATE, deploy job com actions v5. Commits 3ce5aba + 9b5f79e. |
| DEPLOY-02 | Phase 3 | GitHub Pages ativado (branch/Actions) e servindo o site | PENDING — HUMAN ACTION | Ativação manual Settings → Pages → Source = "GitHub Actions" ainda não realizada (decisão explícita do usuário). |
| DEPLOY-03 | Phase 3 | README com badge de build e URL pública | SATISFIED | Badge SVG + link "Ver painel ao vivo →" nas primeiras 5 linhas do README. Commit 8553cab. |
| DEPLOY-04 | Phase 3 | `site/data.json` commitado para o Pages funcionar mesmo sem rebuild | SATISFIED | `site/data.json` commitado com `gerado_em="local"`. Zero diff em rebuild local confirmado. |

**Nota sobre REQUIREMENTS.md:** A tabela de Traceability no REQUIREMENTS.md já reflete o estado correto:
- DEPLOY-01: Complete
- DEPLOY-02: Pending
- DEPLOY-03: Complete
- DEPLOY-04: Complete

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | Nenhum anti-padrão encontrado nos arquivos modificados na fase. |

Scan executado em: `.github/workflows/build.yml`, `pipeline/render.py`, `README.md`.
Sem marcadores TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER. Sem retornos vazios (`return null`, `return []`).

---

### Human Verification Required

#### 1. Ativar GitHub Pages e confirmar primeiro deploy

**Test:** Abrir https://github.com/civisbr/residuos-informalidade-rms → Settings → Pages → "Build and deployment" → Source: selecionar "GitHub Actions" → Save. Em seguida, acionar o deploy via push na `main` ou "Actions → build-and-deploy → Run workflow" e aguardar o job `deploy` concluir.

**Expected:**
- Settings → Pages exibe "Your site is ready to be published" com Source = GitHub Actions
- Environment `github-pages` aparece em Settings → Environments
- Job `deploy` na aba Actions conclui com status verde (não falha com "environment not found")
- https://civisbr.github.io/residuos-informalidade-rms/ carrega o painel com os dados da RMS
- Badge de build no README exibe status verde

**Why human:** Ativação do Pages é uma ação no GitHub UI — não é versionável e não pode ser verificada por grep ou CLI. O workflow está correto e pronto; só falta o clique humano que cria o environment `github-pages` necessário para o job `deploy` funcionar.

**Passos exatos:**
1. Abrir https://github.com/civisbr/residuos-informalidade-rms
2. Settings → Pages → "Build and deployment" → Source: selecionar **"GitHub Actions"** → Save
3. Confirmar que `github-pages` aparece em Settings → Environments
4. Acionar o workflow: Actions → build-and-deploy → Run workflow (ou push na main)
5. Aguardar job `deploy` concluir com sucesso
6. Acessar https://civisbr.github.io/residuos-informalidade-rms/ para confirmar o painel

---

### Gaps Summary

Nenhum gap de código. O único item pendente é a ativação manual do GitHub Pages (DEPLOY-02), que foi explicitamente adiada por decisão do usuário no checkpoint human-action do plano 03-02. Toda a infraestrutura de código necessária para o deploy funcionar está implementada, verificada e commitada:

- Workflow build.yml: completo, actions v5, concurrency, BUILD_DATE, gate pytest, permissions corretas, environment github-pages declarado.
- pipeline/render.py: gerado_em determinístico; local em rebuild local, data ISO real no CI.
- site/data.json: baseline commitado com gerado_em="local"; zero diff em rebuild local.
- README.md: badge de build + link "Ver painel ao vivo →" no topo.

O único passo entre o estado atual e o site ao vivo é o clique humano em Settings → Pages → Source = "GitHub Actions".

---

_Verified: 2026-06-24T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
