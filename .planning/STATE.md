---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-21T23:22:25.545Z"
last_activity: 2026-06-21
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-21)

**Core value:** Credibilidade do dado — nunca apresentar projeção como medição, nunca inventar número.
**Current focus:** Phase 1 — Baseline real da RMS

## Current Position

Phase: 1 (Baseline real da RMS) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-06-21

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-baseline-real-da-rms P01 | 260 | 3 tasks | 8 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Roadmap GSD espelha 1:1 as milestones do GSD.md (M1→Fase 1 … M5→Fase 5); M0 validado.
- Init: v1 = M1–M5 completo; execução sequencial; pesquisa de domínio pulada.
- Init: `commit_docs: false` e `CLAUDE.md` preservado (não regenerado) — `.planning`/`CLAUDE.md`/`GSD.md` são gitignored.

### Pending Todos

None yet.

### Blockers/Concerns

From `.planning/codebase/CONCERNS.md`, relevantes às próximas fases:

- Paridade `model.py`↔`app.js` sem teste (campos divergiram: `carros_equivalente` vs `carros`) — risco à regra sagrada.
- Composição orgânica global aplicada a todos municípios sem flag próprio — Phase 1 (BASE-02) ataca isso.
- `ibge.refresh()` é `NotImplementedError` — Phase 4 (GEN-01).
- `date.today()` não-determinístico no render — atrapalha "data.json commitado" (Phase 3).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-23
Stopped at: Plano 01-02 — caminho BigQuery DESCARTADO (Base dos Dados só tem SNIS água/esgoto em br_mdr_snis; NÃO tem resíduos sólidos). Auth BigQuery funciona com billing project=residuos-github (não residuos-500302). Usuário optou por SCRAPING do portal SNIS. Investigação do app Yii (app4.cidades.gov.br/serieHistorica/residuosSolidos) em andamento.

ACHADOS do scraping — SNIS Série Histórica (app4.cidades.gov.br/serieHistorica), app Yii + jqGrid:
- SEM CSRF. search-id gerado no CLIENTE (timestamp-random). Endpoints abertos (só precisa GET prévio p/ cookie de sessão + header X-Requested-With).
- CONTROLADOR p/ resíduos por município: `consolidadoMunicipio`. Campos:
  - tipo_info: "3"=resíduos sólidos (1=todos,2=água/esgoto,4=ambos)
  - ano_ref: opções no formato "xxx2022" (mais recente=2022)
  - cod_mun: código IBGE 7 díg (ex Sorocaba=3552205); getSelectOpt retorna {Estado:{cod:"Nome/UF [cod]"}}
  - cod_fam_info (famílias RS): 30=gerais,31=financeiras(FN220/custo),32=trabalhadores,33=coleta domiciliar(CO116..RSU),34=coleta seletiva(CS026/reciclado),40=catadores(cooperados),44=indicadores coleta seletiva(IN030/IN031)
  - forms a serializar: frm_filtros + frm_colunas
- FLUXO: GET residuosSolidos/index (cookie) -> POST consolidadoMunicipio/getGridConfig {data=<form serializado>,starting=1,search-id} (prep) -> POST mesmo getGridConfig SEM starting (retorna colModel/colNames) -> POST consolidadoMunicipio/getGridData {data,search-id,page,rows,sidx=nom_mun,sord=asc} -> JSON {rows:[{cell:[...]}]}.
- Export Excel (alternativa, colunas rotuladas): POST relatorio/RelconsolidadoMunicipio {data,sidx,sord,search-id} -> {nameRel:path} p/ download.
- TABELA real revelada por erro SQL: snis_novo.sh_municipios (cols base: cod_ibge,cod_mun,nom_mun,sgl_est,ano_ref,prestadores,servicos,natureza).
- SCRAPING 100% DECIFRADO E VALIDADO (2026-06-23). Recipe completa:
  1. Sessão: GET municipio/index -> POST consolidadoMunicipio/index {ajax=1,action=index} (header X-Requested-With:XMLHttpRequest). Esse POST carrega o form e revela nomes reais.
  2. NOMES DOS CAMPOS são Yii model-prefixed: ShMunicipios[tipo_info][], ShMunicipios[ano_ref][], ShMunicipios[cod_mun][], ShMunicipios[cod_fam_info][], ShMunicipios[fk_glossario][]. (era esse o bug — eu usava cod_mun[] puro.)
  3. cod_mun = código IBGE de 6 DÍGITOS (sem dígito verificador). Ex Sorocaba=355220. Mapa via getSelectOpt element=cod_mun (agrupado por estado; SP tem 645).
  4. fk_glossario = parte numérica SEM prefixo "xxx". Códigos: CO116=39345, CO117=39178, CO142=39261, CS048=39115, CS026=39162, IN031_RS=39223, IN030_RS=39090, FN220=38502, CA002=38554, CA003=38599. ano_ref tb sem xxx (2022).
  5. FLUXO: serializa form (urlencode dos pares ShMunicipios[...]) -> POST consolidadoMunicipio/getGridConfig {data=form,starting=1,search-id=<random cliente>} -> POLL POST getGridConfig {data,search-id} até resposta ter colModel (endpoint assíncrono "Configurando matriz") -> POST getGridData {data,search-id,page,rows,sidx=nom_mun,sord=asc} -> {rows:[{cell:[...]}]}.
  6. colModel dá a ORDEM REAL das colunas (alfabética por código SNIS, NÃO ordem de envio): 8 base (cod_ibge,cod_mun,nom_mun,sgl_est,ano_ref,prestadores,servicos,natureza) + dados [ca002,ca003,co116,co117,co142,cs026,cs048,fn220,in030_rs,in031_rs]. MAPEAR por colModel name, não por send-order.
  - Validado: Sorocaba 2022 -> co117=228704.7 t/ano, fn220=136457522.82/ano, in031_rs=1.78%.
- DECISÃO INTEGRIDADE: cooperados via CA002/CA003 é não-confiável (Sorocaba ca003=1.78, fracionário) -> deixar cooperados=null (honesto). município sem nenhum dado RS -> pendente.
- Próximo: construir scripts/scrape_snis.py, rodar -> data/raw/snis/snis_rms_sp.csv (25 munic, excl sorocaba+porto feliz), validar build 27, ajustar teste pend.height, 01-02-SUMMARY.md.
- NOTA ESCOPO: fetch_snis.py (BigQuery) é beco sem saída (BD não tem RS). scrape_snis.py é a semente real de snis.py::refresh() (Fase 4/GEN-02).
Resume file: None
