---
phase: 05-camada-viva-operacional
plan: 01
subsystem: pipeline
tags: [polars, telemetria, operacao, data-json, vanilla-js, offline-build]

# Dependency graph
requires:
  - phase: 02-camada-informalidade
    provides: "padrão de classe de dado separada no payload (municipios/totais vs coeficientes/simulador_defaults) e tag visual por classe"
  - phase: 04-generalizar-para-qualquer-cidade-br
    provides: "lição CR-01 (frame vazio com coluna key) e padrão load()/refresh() das fontes"
provides:
  - "pipeline/sources/operacao.py::load() — fonte offline da telemetria operacional (sem refresh, D-04)"
  - "data/raw/operacao/operacao_rms.csv — CSV-template documentado (header + comentários #, zero dado)"
  - "transform.build_operacao(operacao, coef) → {serie, acumulados, tem_dado} com estado vazio honesto"
  - "render.to_payload(..., operacao_payload=None) — chave operacao sempre presente no payload"
  - "seção 'Operação ao vivo' no painel (renderOperacao + opSlot + tag.live) com placeholder honesto"
affects: [05-02, calibracao, serie-temporal, impacto-acumulado]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fonte offline só com load() (D-04): glob+concat de CSVs, comment_prefix para header documentado, frame vazio COM coluna key"
    - "Estado vazio honesto end-to-end: chave operacao SEMPRE presente como {serie:[], acumulados:None, tem_dado:false}, nunca ausente nem inventada"
    - "Classe visual dedicada .tag.live, inconfundível das 3 existentes (real/est/proj-pend)"

key-files:
  created:
    - pipeline/sources/operacao.py
    - data/raw/operacao/operacao_rms.csv
  modified:
    - pipeline/transform.py
    - pipeline/render.py
    - pipeline/cli.py
    - site/index.html
    - site/app.js
    - site/styles.css
    - tests/test_pipeline.py
    - site/data.json

key-decisions:
  - "Schema da telemetria em TONELADAS (mes, municipio, n_clientes, t_org_coletada, larva_umida_t, larva_seca_t, frass_t, partilha_rs, qualidade, fonte) — casa 1:1 com os outputs _t_ano de model.project() (D-05)"
  - "Grão mês×município sem .unique(subset=['key']) — múltiplas linhas por key são esperadas (D-03), diferente de snis.load()"
  - "operacao.py só tem load() — sem refresh() de rede (D-04); build permanece offline/determinístico"
  - "Acumulados deste plano = desviado_t, partilha_rs, larva_seca_t, frass_t; projetado da calibração e co2e/carros ficam para o Plano 05-02 (dependem do teste de paridade)"

patterns-established:
  - "Telemetria como 4ª classe de dado visualmente separada das outras três (regra sagrada)"
  - "comment_prefix='#' no read_csv para ler header documentado em CSV-template"

requirements-completed: [LIVE-01, LIVE-02]

coverage:
  - id: D1
    description: "operacao.load() lê o CSV-template offline e devolve frame vazio COM coluna key (LIVE-02, CR-01)"
    requirement: "LIVE-02"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_operacao_load_vazio_tem_key"
        status: pass
    human_judgment: false
  - id: D2
    description: "CSV-template define o schema de telemetria documentado, sem nenhuma linha de dado inventada (LIVE-01)"
    requirement: "LIVE-01"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_operacao_load_vazio_tem_key"
        status: pass
    human_judgment: false
  - id: D3
    description: "data.json contém a chave operacao com estado vazio honesto e preserva as chaves existentes; build offline/determinístico, 27/27 municípios"
    requirement: "LIVE-02"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_payload_tem_operacao"
        status: pass
      - kind: integration
        ref: "uv run obs build --region rms (rodado 2x → mesmo data.json, diff vazio)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Painel servido localmente mostra a seção 'Operação ao vivo' com o aviso de estado vazio e a tag visual distinta das demais classes"
    verification:
      - kind: manual_procedural
        ref: "cd site && python -m http.server → seção 'Operação ao vivo' com pendbox honesto e tag.live distinta"
        status: unknown
    human_judgment: true
    rationale: "Separação visual inconfundível da nova classe e legibilidade do estado vazio exigem julgamento humano (regra sagrada)"

# Metrics
duration: 14min
completed: 2026-06-25
status: complete
---

# Phase 5 Plan 01: Camada viva (operacional) — esqueleto vivo end-to-end Summary

**Telemetria operacional flui da fonte ao painel COM ZERO dado: nova fonte operacao.py (só load), CSV-template documentado, chave operacao no payload e seção "Operação ao vivo" com estado vazio honesto — pronto para "ligar" sem inventar número.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-06-25T14:52:00Z (aprox.)
- **Completed:** 2026-06-25T14:55:15Z
- **Tasks:** 3
- **Files modified:** 10 (2 criados, 8 modificados — inclui site/data.json regenerado)

## Accomplishments
- `pipeline/sources/operacao.py` com `load()` (sem `refresh()`, D-04): lê `data/raw/operacao/*.csv` offline, devolve frame vazio COM coluna `key` (lição CR-01), grão mês×município sem `.unique()` (D-03).
- `data/raw/operacao/operacao_rms.csv`: CSV-template com header do schema + comentários `#` documentando unidades/procedência, ZERO linhas de telemetria (D-01/D-02).
- `transform.build_operacao()`: agrega a série mensal regional via `group_by("mes")` + 4 acumulados; estado vazio honesto `{serie:[], acumulados:None, tem_dado:false}` quando não há dado.
- `render.to_payload()` ganhou `operacao_payload` (default-able, padrão de `pnad_df`); chave `operacao` SEMPRE presente no payload, sem tocar nas chaves existentes.
- `cli.py` wira `operacao.load()` no build offline/determinístico; `site/data.json` regenerado com a chave `operacao`.
- Painel: seção "Operação ao vivo" (`seclabel` + `tag.live` + `opSlot`), `renderOperacao()` com pendbox honesto chamado em `selectCity()`; CSS `.tag.live` com cor distinta das 3 classes.
- 2 testes novos (`test_operacao_load_vazio_tem_key`, `test_payload_tem_operacao`); suíte 27/27 verde.

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Fonte operacao.py + CSV-template** - `f8530d1` (feat)
2. **Task 2: build_operacao() + chave operacao no payload + wiring no cli** - `93045b9` (feat)
3. **Task 3: Seção "Operação ao vivo" no painel + testes** - `bdbee52` (feat)

**Plan metadata:** não commitado em git — `commit_docs: false` em `.planning/config.json` (`.planning/` fora do histórico do projeto).

## Files Created/Modified
- `pipeline/sources/operacao.py` - NOVA fonte offline da telemetria (só `load()`, `SCHEMA`, `RAW`).
- `data/raw/operacao/operacao_rms.csv` - NOVO CSV-template documentado (header + comentários `#`, sem dado).
- `pipeline/transform.py` - NOVO `build_operacao(operacao, coef)` com série mensal + 4 acumulados + estado vazio honesto.
- `pipeline/render.py` - `to_payload()` ganhou `operacao_payload` e a chave `operacao` (sempre presente).
- `pipeline/cli.py` - importa/carrega `operacao`, computa `build_operacao`, passa ao `to_payload`; print de status PT-BR.
- `site/index.html` - seção "Operação ao vivo" após o simulador + `opSlot`.
- `site/app.js` - `renderOperacao()` com pendbox honesto; chamado em `selectCity()`. `project()` intocado (paridade preservada para 05-02).
- `site/styles.css` - `.tag.live` (classe visual dedicada da telemetria).
- `tests/test_pipeline.py` - importa `operacao`; 2 testes novos.
- `site/data.json` - regenerado com a chave `operacao` (estado vazio).

## Decisions Made
- Unidade de massa do schema = toneladas, para casar 1:1 com os outputs `_t_ano` de `model.project()` (resolve a discrição D-05).
- Acumulados deste plano restritos a desviado_t/partilha_rs/larva_seca_t/frass_t reais; o projetado da calibração e co2e/carros são do Plano 05-02 (que carrega o teste de paridade `model.py`↔`app.js`).
- `renderOperacao()` deixa só o branch de estado vazio implementado; a série SVG + cards de impacto acumulado ficam para o Plano 05-02 (escopo explícito do plano).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. (`user_setup: []` no plano; fonte offline sem rede/segredo.)

## Next Phase Readiness
- Esqueleto vivo pronto: o cano operacao.load() → build_operacao() → payload → renderOperacao() está completo e provado com ZERO dado.
- Plano 05-02 deve: implementar o projetado da calibração reusando `model.project()` (D-07/D-08) + teste de paridade `model.py`↔`app.js`; renderizar a série temporal SVG e os 4 cards de impacto acumulado quando `tem_dado=true`; e adicionar co2e/carros aos acumulados.
- `build_operacao()` já carrega `coef` na assinatura, preparado para o projetado da calibração sem mudança de chamadores.

## Self-Check: PASSED

---
*Phase: 05-camada-viva-operacional*
*Completed: 2026-06-25*
