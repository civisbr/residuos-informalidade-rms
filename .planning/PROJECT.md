# Observatório de Resíduos & Informalidade

## What This Is

Painel vivo, open-source (org CivisBR), que mostra resíduos sólidos e
informalidade por município brasileiro e projeta o impacto de uma operação de
coleta de orgânicos + bioconversão por BSF (mosca soldado-negro). Combina
**baseline de dado público** (SNIS/IBGE/PMGIRS) com um **simulador de impacto**
(modelo BSF, projeção). Referência regional: RMS — Região Metropolitana de
Sorocaba (27 municípios). Hospedado em GitHub Pages, estático.

## Core Value

Credibilidade do dado. O painel só vale se nunca apresentar projeção como
medição e nunca inventar número: todo indicador carrega um flag
`real` | `estimativa` | `pendente`, e baseline público fica visualmente separado
do simulador. Se a credibilidade falha, o produto inteiro falha.

## Requirements

### Validated

<!-- Inferido do código existente + GSD.md M0 (✅). Build offline passa, testes verdes. -->

- ✓ Esqueleto que builda offline e determinístico (`uv run obs build` gera `site/data.json` sem rede) — M0
- ✓ Pipeline Polars: junção região+IBGE+SNIS com flags `real`/`estimativa`/`pendente` (`transform.py`) — M0
- ✓ Modelo de impacto BSF (`model.py`) com paridade espelhada em `site/app.js` — M0
- ✓ Painel estático lendo `data.json` (`site/`) com baseline e simulador separados — M0
- ✓ `config/regions.yml` com os 27 municípios da RMS + adaptadores `sources/ibge.py` (cache) e `sources/snis.py` (CSV local) — M0
- ✓ Testes de sanidade offline (`tests/test_pipeline.py`) — M0
- ✓ **Deploy contínuo (CI)**: workflow `build.yml` reconstrói `site/data.json` e publica no Pages a cada push na `main`; `render.py` determinístico (`gerado_em` via `BUILD_DATE`); README com badge de build + link público; `data.json` commitado — Validado na Fase 3 (M3). *Ressalva: ativação do GitHub Pages (URL ao vivo, DEPLOY-02) adiada por decisão do usuário — rastreada em `03-HUMAN-UAT.md`.*

### Validated

<!-- Shipped no milestone v1.0 (Fases 1-5). -->

- ✓ **M1 — Baseline real da RMS** — v1.0: 27 municípios com SNIS-RS 2022 real; Sorocaba (gravimetria PMGIRS 0.48) e Porto Feliz (PMGIRS 2017) completos com `fonte` citada.
- ✓ **M2 — Camada de informalidade** — v1.0: informalidade por município (Censo 2022) + proxy de formalização (RAIS 2023), separados de estimativa, com contexto PNAD regional e nota fixa de subcontagem (D-10).
- ✓ **M3 — Deploy contínuo no GitHub Pages** — v1.0 *(código completo; URL ao vivo pendente de ativação manual do Pages — ver `03-HUMAN-UAT.md` / STATE.md Deferred Items)*: workflow reconstrói `data.json` e publica; badge + link; `data.json` commitado; render determinístico.
- ✓ **M4 — Generalizar para qualquer cidade BR** — v1.0 *(UAT de rede pendente — ver `04-HUMAN-UAT.md`)*: `ibge.refresh()`/`snis.refresh()` por `--region`, erro amigável com sugestão, guia "5 minutos" no README; terceiro gera outra região só editando `regions.yml`.
- ✓ **M5 — Camada viva (operacional)** — v1.0: esquema de telemetria (CSV-template), `sources/operacao.py` (load), seção "Operação ao vivo" com série temporal SVG real×projetado (calibração reusando `model.project()`) e 4 cards de impacto acumulado — "esqueleto vivo" em estado vazio honesto até a primeira medição.

### Active

<!-- Próximo milestone (v1.1) — definir via /gsd-new-milestone. Candidatos abaixo. -->

- [ ] Fechar as ressalvas do v1.0: ativar GitHub Pages (URL ao vivo) e rodar o UAT de rede das Fases 3 e 4 (`/gsd-verify-work 3` e `4`).
- [ ] Backlog frio (ver Out of Scope): mapa coroplético, comparação de pares município×mediana, export PDF por município.
- [ ] Informalidade/RAIS para qualquer região (hoje RMS-only; fora da RMS = `pendente`).

### Out of Scope

<!-- Backlog frio do GSD.md — reconhecido, fora do escopo v1. -->

- Mapa coroplético da região — diferenciador visual, depois do baseline confiável
- Comparação de pares (município vs. mediana da sub-região) — depende de cobertura ampla de dado (pós-M4)
- Export de relatório PDF reprodutível por município — feature de saída, não core
- Inventar/estimar número para preencher município sem dado — **proibido pela regra sagrada**; município sem fonte fica `pendente`
- Uso externo do simulador sem calibração com gravimetria local — coeficientes são conservadores e exigem calibração antes de publicar projeção

## Context

- **Estilo CivisBR**: o projeto vive da credibilidade. Integridade de dado é a
  regra sagrada (ver `CLAUDE.md`): flags de qualidade, separação baseline×projeção,
  coeficientes documentados em `config/coefficients.yml`, catador informal tratado
  como piso (subcontado pelas bases oficiais).
- **Modo de trabalho GSD**: incrementos pequenos e shippáveis; o board autoral
  está em `GSD.md` (M0✅→M5), cada milestone com "pronto quando" e checklist.
- **Codebase já mapeada** em `.planning/codebase/` (local): arquitetura pipeline
  batch offline → `data.json` estático → painel vanilla; sem framework, sem build step.
- **Dívida técnica conhecida** (ver `.planning/codebase/CONCERNS.md`): paridade
  `model.py`↔`app.js` sem teste (campos já divergiram: `carros_equivalente` vs `carros`),
  composição orgânica global aplicada a todos municípios sem flag próprio,
  `date.today()` não-determinístico no render, `ibge.refresh()` não implementado,
  `os.chdir` nos testes quebra isolamento, acoplamento à RMS (`subregiao` hardcoded).
- **Fontes públicas e abertas**: APIs IBGE/SNIS sem autenticação; sem dados
  pessoais; sem segredos no repo.

## Constraints

- **Tech stack**: Python 3.11+, **Polars** (não pandas), type hints, funções puras quando der. Front em HTML+CSS+JS vanilla lendo `data.json`, sem framework e sem build step.
- **Integridade de dado**: nunca inventar número; todo indicador com flag; baseline e simulador visualmente separados; coeficientes conservadores e documentados.
- **Reprodutibilidade**: build offline e determinístico; `data.json` commitado para o Pages funcionar sem rebuild.
- **Paridade de modelo**: `pipeline/model.py` e `site/app.js::project()` devem dar o mesmo número; mudou um, muda o outro e ajusta o teste.
- **Junção de fontes**: por nome normalizado (`base.slug`).
- **Planejamento local**: `.planning/`, `CLAUDE.md` e `GSD.md` são gitignored — artefatos GSD não vão para o versionamento (`commit_docs: false`).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Roadmap GSD espelha 1:1 as milestones do `GSD.md` (M1→Fase 1 … M5→Fase 5) | `GSD.md` já é a especificação autoral com "pronto quando" e checklists | — Pending |
| v1 = M1–M5 completo | Visão de produto vai do piloto RMS confiável até a camada viva operacional | — Pending |
| Pular pesquisa de domínio | Domínio (SNIS/IBGE/PMGIRS/BSF) já dominado; `GSD.md` é a spec | ✓ Good |
| `commit_docs: false`; preservar `CLAUDE.md` (não regenerar) | `.planning`/`CLAUDE.md`/`GSD.md` já gitignored; manual existente é precioso | ✓ Good |
| Execução sequencial | Regra do `GSD.md`: não começar a próxima milestone antes da anterior estar verde | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
**Current state:** 🎉 **Milestone v1.0 (MVP — Observatório RMS) completo** — 5 fases, 13 planos, ~3185 LOC (Python/Polars + front vanilla), 21→25/06/2026. O painel leva a RMS de um esqueleto a um observatório com baseline público real (SNIS/IBGE/PMGIRS), camada de informalidade (Censo/RAIS/PNAD), deploy contínuo, generalização para qualquer cidade BR e a camada viva operacional (telemetria real×projetada em estado vazio honesto). Fechamento foi **override closeout**: URL pública do Pages ainda não ativada e UAT de rede das Fases 3/4 pendente (ver STATE.md Deferred Items). Próximo: `/gsd-new-milestone` (v1.1).

*Last updated: 2026-06-26 after v1.0 milestone completion*
