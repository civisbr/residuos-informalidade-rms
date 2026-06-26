# Phase 3: Deploy contínuo no GitHub Pages - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Tornar o painel **público e auto-publicável**: push na `main` reconstrói
`site/data.json` e publica o site no GitHub Pages, com URL pública estável e
badge de build no README. Cobre DEPLOY-01..04.

O workflow `.github/workflows/build.yml` **já existe e funciona** (modelo
GitHub Actions: pytest → `obs build` → `upload-pages-artifact` →
`deploy-pages`), e `site/data.json` já está commitado. Esta fase **revisa e
finaliza** esse fluxo, ativa o Pages, ajusta determinismo do build e atualiza o
README — não reescreve a pipeline.

**Fora de escopo (outras fases):** `ibge.refresh()` / `snis.refresh()`
automatizados e o guia "crie o painel da sua cidade" (Fase 4); telemetria viva
(Fase 5); mapa coroplético e export PDF (Out of Scope v1, PROJECT.md).
Discussão clarifica COMO publicar o que já está escopado — não adiciona
capacidade nova.

</domain>

<decisions>
## Implementation Decisions

### Modelo de publicação (DEPLOY-01, DEPLOY-02, DEPLOY-04)
- **D-01:** **Manter o modelo "GitHub Actions" (artifact fresco)** do
  `build.yml` atual: a cada push na `main`, o workflow roda `pytest` + `obs
  build --region rms` e faz deploy do `site/` recém-gerado via
  `upload-pages-artifact` + `deploy-pages`. O Pages serve **o que o build
  acabou de gerar**, não o arquivo commitado.
- **D-02:** **Interpretação de DEPLOY-04 sob este modelo:** o `site/data.json`
  commitado é **safety net + preview local** (abrir o site sem rodar a
  pipeline), não a fonte servida pelo Pages. "Funciona sem rebuild" se cumpre
  porque o próprio Action rebuilda automaticamente a cada push; o arquivo
  commitado garante que o repo nunca esteja sem um `data.json` válido.
- **D-03:** **Gate mínimo, sem mudar o disparo:** manter `on: push (main)` +
  `workflow_dispatch`. **Não** adicionar check em PR nesta fase (entra quando
  abrir contribuição externa, alinhado à Fase 4). `pytest` continua
  pré-requisito do deploy (job `build` falha → `deploy` não roda).
- **D-04 (passo manual, NÃO é código):** DEPLOY-02 exige **ativar o GitHub
  Pages nas Settings do repositório com Source = "GitHub Actions"**. É ação no
  GitHub (não versionável). O plano deve documentar isso explicitamente como
  passo de operação/verificação, não como tarefa de código.

### Determinismo do build (`gerado_em`)
- **D-05 (Claude's Discretion com meta fixa):** `pipeline/render.py:61` usa hoje
  `date.today().isoformat()` em `gerado_em` → não-determinístico. O planner
  escolhe a abordagem, mas com **duas metas obrigatórias**:
  1. **Deploy mostra data útil** — o `gerado_em` publicado deve refletir quando
     o site foi publicado (timestamp informativo no ar).
  2. **Rebuild local não gera diff espúrio** — rodar `obs build` localmente
     para preview **não** deve criar um diff gratuito no `site/data.json`
     commitado só por causa da data.
  Abordagem candidata (não obrigatória): ler a data de uma env var
  (ex. `SOURCE_DATE_EPOCH` / `BUILD_DATE`) que o CI injeta, com fallback
  determinístico local. Decisão final fica para pesquisa/planejamento, desde
  que respeite as duas metas. Item rastreado em `CONCERNS.md` como dívida
  atribuída à Fase 3.

### URL pública (DEPLOY-03)
- **D-06:** **URL default do GitHub Pages:**
  `https://civisbr.github.io/residuos-informalidade-rms/`. **Sem domínio custom
  / CNAME** nesta fase. O `app.js` usa `fetch("./data.json")` e o `index.html`
  referencia `app.js`/`styles.css` por caminho relativo → o subpath do Pages
  funciona sem ajuste de base path. **Não** introduzir `<base href>` nem
  caminhos absolutos que quebrem o subpath.

### README — badge + link (DEPLOY-03)
- **D-07:** **Badge de status do workflow `build-and-deploy` (Actions) +
  link "painel ao vivo" no topo do README**, apontando para a URL de D-06.
  Ambos visíveis logo no início (padrão open-source). O badge usa o endpoint
  padrão de status de workflow do GitHub Actions (`actions/workflows/build.yml/badge.svg`).

### Claude's Discretion
- **D-05** (determinismo do `gerado_em`): abordagem livre, respeitando as duas
  metas acima.
- Detalhes de robustez do workflow (ex.: `concurrency` para evitar deploys
  concorrentes, pin de versões de actions) — planner decide, mantendo o disparo
  de D-03 e o modelo de D-01.
- Texto/posição exata do bloco de badge+link no README, desde que ambos
  (status do build + URL pública) apareçam no topo conforme D-07.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regra do projeto e fase
- `CLAUDE.md` — regra sagrada (build offline/determinístico, `data.json`
  commitado, separação baseline×simulador), convenções de commit (PT-BR
  imperativo). Relevante a DEPLOY-04 e ao determinismo (D-05).
- `.planning/PROJECT.md` — Constraints: "build offline e determinístico;
  `data.json` commitado para o Pages funcionar sem rebuild". Out of Scope.
- `.planning/REQUIREMENTS.md` — DEPLOY-01..04 (linhas 28–31, 78–81).
- `GSD.md` §M3 — checklist autoral "Deploy contínuo no GitHub Pages"
  (revisar build.yml; ativar Pages; badge + URL; data.json commitado).

### Artefatos a revisar/estender
- `.github/workflows/build.yml` — workflow existente (DEPLOY-01). Modelo
  Actions-artifact a manter (D-01); disparo a preservar (D-03); permissões
  `contents: read` / `pages: write` / `id-token: write` já corretas.
- `pipeline/render.py` (linha 61, `gerado_em = date.today()`) — alvo do ajuste
  de determinismo (D-05).
- `README.md` — onde entram badge + link (D-07); já menciona Pages na linha 29.
- `site/index.html` (`app.js`/`styles.css` relativos; `<script src="app.js">`
  linha 118) e `site/app.js` (`fetch("./data.json")` linha 10) — confirmam que
  o subpath do Pages funciona sem base path (D-06). **Não** quebrar isso.
- `site/data.json` — artefato commitado (safety net/preview, D-02).

### Codebase intel
- `.planning/codebase/INTEGRATIONS.md` §CI/CD & Deployment — descreve o
  pipeline Actions passo a passo (já mapeado).
- `.planning/codebase/CONCERNS.md` — registra `date.today()` não-determinístico
  como dívida ligada à Fase 3 (origem de D-05).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/build.yml` já implementa o fluxo completo
  build→artifact→deploy. A fase é majoritariamente **revisão + finalização**,
  não criação do zero.
- `site/data.json` commitado serve de preview local e safety net (D-02).

### Established Patterns
- Pipeline batch offline → `data.json` estático → painel vanilla, sem framework
  e sem build step. O deploy não introduz build de front; só roda a pipeline
  Python e empacota `site/`.
- Caminhos relativos no front (`./data.json`, `app.js`, `styles.css`) → compatível
  com subpath `/residuos-informalidade-rms/` do Pages sem ajuste (D-06).
- `pytest` como gate antes do deploy (job `build` → `needs: build` no `deploy`).

### Integration Points
- `pipeline/render.py::to_payload()` — único ponto que escreve `gerado_em`;
  alvo do ajuste de determinismo (D-05).
- GitHub repo Settings → Pages (Source = GitHub Actions) — ativação manual
  (D-04), fora do código.
- `README.md` topo — inserção de badge + link (D-07).

</code_context>

<specifics>
## Specific Ideas

- URL alvo literal: `https://civisbr.github.io/residuos-informalidade-rms/`.
- Badge: status do workflow `build-and-deploy` via
  `actions/workflows/build.yml/badge.svg`, no topo do README, ao lado de um
  link destacado "Ver painel ao vivo →".
- `gerado_em`: deploy deve exibir a data de publicação; rebuild local não pode
  poluir o git com diff só-de-data.

</specifics>

<deferred>
## Deferred Ideas

- Check de CI em pull requests (build sem deploy) → quando abrir contribuição
  externa, alinhado à Fase 4 (open-source / "qualquer cidade BR").
- Domínio custom / CNAME para o painel → fora do escopo desta fase; revisitar
  se a CivisBR quiser marca própria de URL.
- Automação de `ibge.refresh()` / `snis.refresh()` → Fase 4 (GEN-01/GEN-02).

None — discussão permaneceu dentro do escopo da fase (deploy/publicação).

</deferred>

---

*Phase: 3-deploy-cont-nuo-no-github-pages*
*Context gathered: 2026-06-23*
