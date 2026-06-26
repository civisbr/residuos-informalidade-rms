# Phase 3: Deploy contínuo no GitHub Pages - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 3-deploy-cont-nuo-no-github-pages
**Areas discussed:** Modelo de publicação, Determinismo do build, URL pública / domínio, Badge + README

---

## Modelo de publicação

| Option | Description | Selected |
|--------|-------------|----------|
| Actions-artifact (atual) | Mantém build.yml: a cada push, pytest + build e deploy do artifact fresco; data.json commitado = fallback/preview + safety net | ✓ |
| Actions + commit de volta | Workflow commita o data.json regenerado de volta na main antes do deploy; exige build determinístico | |
| Deploy from branch | Pages serve o site/ commitado direto, sem Action de deploy; perde o rebuild automático | |

**User's choice:** Actions-artifact (atual)
**Notes:** DEPLOY-04 reinterpretado: data.json commitado é safety net + preview local; o "sem rebuild" é satisfeito pelo próprio Action rebuildando a cada push.

### Sub-pergunta: Gate / cobertura do workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Adicionar check em PR | Roda pytest + build em PRs (sem deploy) | |
| Manter mínimo (só main) | Disparo atual: push na main + workflow_dispatch | ✓ |
| Você decide | Planner escolhe | |

**User's choice:** Manter mínimo (só main)
**Notes:** Check de PR adiado para quando abrir contribuição externa (Fase 4).

---

## Determinismo do build

| Option | Description | Selected |
|--------|-------------|----------|
| Injetar via env, fallback hoje | render lê data de env (CI injeta data do build); local cai no fallback determinístico | |
| Manter date.today() | Aceita não-determinismo; rebuild local muda gerado_em | |
| Você decide | Planner escolhe respeitando a meta | ✓ |

**User's choice:** Você decide
**Notes:** Meta fixa registrada (D-05): deploy mostra data útil E rebuild local não gera diff espúrio no data.json commitado.

---

## URL pública / domínio

| Option | Description | Selected |
|--------|-------------|----------|
| github.io default | civisbr.github.io/residuos-informalidade-rms/ — zero config, subpath funciona | ✓ |
| Domínio custom (CNAME) | Domínio próprio CivisBR + DNS + arquivo CNAME | |

**User's choice:** github.io default
**Notes:** fetch relativo no app.js já cobre o subpath; sem CNAME nesta fase.

---

## Badge + README

| Option | Description | Selected |
|--------|-------------|----------|
| Badge status + link no topo | Badge do workflow build-and-deploy + link "painel ao vivo" no topo do README | ✓ |
| Só badge, sem link destacado | Badge + menção ao Pages no texto existente | |
| Você decide | Planner escolhe formato/posição | |

**User's choice:** Badge status + link no topo
**Notes:** Padrão open-source; visibilidade imediata de build + site.

---

## Claude's Discretion

- Determinismo do `gerado_em` (D-05) — abordagem livre, respeitando as duas metas.
- Robustez do workflow (concurrency, pin de versões de actions) — planner decide.
- Texto/posição exata do bloco badge+link no README, mantendo ambos no topo.

## Deferred Ideas

- Check de CI em pull requests (build sem deploy) → Fase 4 (contribuição externa).
- Domínio custom / CNAME → fora do escopo desta fase.
- Automação de `ibge.refresh()` / `snis.refresh()` → Fase 4 (GEN-01/GEN-02).
