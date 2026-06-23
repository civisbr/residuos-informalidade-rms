# Roadmap: Observatório de Resíduos & Informalidade

## Overview

Espelha 1:1 o board autoral do `GSD.md`. O esqueleto que builda offline (M0)
já existe e está validado. O roadmap leva o piloto da RMS de um esqueleto a um
observatório público e confiável (baseline real → informalidade → deploy),
depois generaliza para qualquer cidade do Brasil e, por fim, sobrepõe a
telemetria da operação ao baseline público. Cada fase é um incremento
shippável, com "pronto quando" claro; não se começa a próxima antes da anterior
estar verde.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Baseline real da RMS** - 27 municípios com dado SNIS real ou pendente honesto, fonte citada
- [ ] **Phase 2: Camada de informalidade** - indicador de informalidade por município, com fonte e flag
- [ ] **Phase 3: Deploy contínuo no GitHub Pages** - push reconstrói e publica o painel
- [ ] **Phase 4: Generalizar para qualquer cidade BR** - terceiro gera o painel de outra região só editando regions.yml
- [ ] **Phase 5: Camada viva (operacional)** - telemetria real sobreposta ao baseline público

## Phase Details

### Phase 1: Baseline real da RMS

**Goal**: Os 27 municípios da RMS têm linha no SNIS (real ou pendente honesto), com Sorocaba + Porto Feliz completos a partir de fonte citável.
**Mode:** mvp
**Depends on**: Nothing (baseline sobre o esqueleto M0 já validado)
**Requirements**: BASE-01, BASE-02, BASE-03, BASE-04, BASE-05
**Success Criteria** (what must be TRUE):

  1. `uv run obs build --region rms` produz os 27 municípios; nenhum município sem fonte inventa número (fica `pendente`)
  2. Sorocaba usa gravimetria real do PMGIRS (não a `composicao` global) e Porto Feliz tem RSU/reciclado/cooperados do PMGIRS 2017
  3. Toda linha com dado exibe sua `fonte` no painel
  4. Testes de sanidade continuam verdes (`uv run pytest`)

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Gravimetria Sorocaba (SCHEMA+transform+render) + tentativa PMGIRS Porto Feliz + testes D-12

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Ingestão SNIS 25 municípios via scraper da Série Histórica oficial (scrape_snis.py) + teste real.height; 27/27 reais

### Phase 2: Camada de informalidade

**Goal**: O painel mostra, por município, um indicador de informalidade com fonte, separado do que é estimativa, com nota de subcontagem da população catadora.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: INFO-01, INFO-02, INFO-03, INFO-04
**Success Criteria** (what must be TRUE):

  1. Fonte `sources/ibge_informalidade.py` carrega ocupação informal (PNAD/Censo) por município
  2. Painel exibe card/seção de informalidade com flag de qualidade, visualmente separado de estimativa
  3. Proxy de formalização (RAIS/CAGED vs. cooperados) aparece com sua fonte
  4. Nota explícita de subcontagem da população catadora visível no painel

**Plans**: 3 plans

Plans:

**Wave 1**

- [ ] 02-01-PLAN.md — Snapshots CSV (Censo/RAIS/PNAD) + fontes offline ibge_informalidade.py / rais.py / pnad_regional.py + testes INFO-01/INFO-02

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-02-PLAN.md — Integração pipeline: transform.build_region() com joins + proxy D-06/D-07; render.to_payload() com campos de informalidade + meta.pnad; cli.py atualizado; data.json regenerado

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 02-03-PLAN.md — Painel: renderInformalidade() em app.js + slots index.html + nota fixa D-10 + célula region-strip + verificação visual

### Phase 3: Deploy contínuo no GitHub Pages

**Goal**: Push na `main` reconstrói `data.json` e publica o site automaticamente, com URL pública e badge de build.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):

  1. Push na `main` dispara o workflow que reconstrói `site/data.json` e publica no Pages
  2. O site está acessível por uma URL pública estável
  3. README mostra badge de build e o link público
  4. `site/data.json` commitado garante que o Pages funcione mesmo sem rebuild

**Plans**: TBD

Plans:

- [ ] 03-01: TBD (definido em /gsd-plan-phase 3)

### Phase 4: Generalizar para qualquer cidade BR

**Goal**: Um terceiro consegue gerar o painel de outra região só editando `regions.yml`, sem tocar em código.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04
**Success Criteria** (what must be TRUE):

  1. `ibge.refresh()` resolve códigos e população via API e regrava o cache (não mais `NotImplementedError`)
  2. `snis.refresh()` está documentado e, quando viável, automatizado
  3. Município que não resolve no IBGE gera erro amigável (não stack trace)
  4. README traz o guia "Crie o painel da sua cidade em 5 minutos" e um terceiro consegue seguir só editando `regions.yml`

**Plans**: TBD

Plans:

- [ ] 04-01: TBD (definido em /gsd-plan-phase 4)

### Phase 5: Camada viva (operacional)

**Goal**: Sobrepor a telemetria real da operação ao baseline público, com série temporal e impacto acumulado.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04
**Success Criteria** (what must be TRUE):

  1. Esquema de telemetria definido (t coletadas/mês por cliente, larva, frass, partilha)
  2. `sources/operacao.py` lê a telemetria (CSV/planilha exportada)
  3. Painel mostra série temporal com baseline público e medições reais lado a lado, visualmente separados
  4. Painel de impacto acumulado exibe desvio de aterro e renda a catadores no tempo

**Plans**: TBD

Plans:

- [ ] 05-01: TBD (definido em /gsd-plan-phase 5)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Baseline real da RMS | 2/2 | Complete | 2026-06-23 |
| 2. Camada de informalidade | 0/3 | Not started | - |
| 3. Deploy contínuo no GitHub Pages | 0/TBD | Not started | - |
| 4. Generalizar para qualquer cidade BR | 0/TBD | Not started | - |
| 5. Camada viva (operacional) | 0/TBD | Not started | - |
