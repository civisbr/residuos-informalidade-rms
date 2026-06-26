---
phase: 05-camada-viva-operacional
plan: 02
subsystem: pipeline
tags: [polars, calibracao, paridade, svg-inline, vanilla-js, telemetria, model-project, offline-build]

# Dependency graph
requires:
  - phase: 05-camada-viva-operacional
    provides: "esqueleto vivo do Plano 05-01: operacao.load(), build_operacao() com série mensal + 4 acumulados reais + estado vazio honesto, chave operacao no payload, seção 'Operação ao vivo' (renderOperacao com placeholder), CSV-template"
  - phase: 01-fundacao
    provides: "model.project() canônico (conversão orgânico→larva/frass/CO2e/partilha) e config/coefficients.yml"
  - phase: 02-camada-informalidade
    provides: "padrão de classe de dado visualmente separada + tag por classe; renda a catadores conecta com a informalidade"
provides:
  - "Teste de paridade cross-language model.py↔app.js::project() (CONCERNS #7 fechado): congela contrato numérico Python + valida nomes JS por parse textual"
  - "build_operacao() estendido: projetado_* por mês reusando model.project() em base mensal (÷12); mês incompleto → projetado null (nunca zero)"
  - "Acumulados derivados co2e_evitado_t_derivado + carros_equivalente_derivado via model.project() sobre o desviado real total"
  - "svgSerie() — série temporal SVG inline à mão (real sólido × projetado tracejado); renderOperacao() caminho com dado + 4 cards de impacto acumulado"
  - "Classes CSS da série (.serie/.s-real/.s-proj/.axis/.xlab) e do wrapper/legenda da operação"
affects: [06, calibracao-automatica, serie-temporal, dashboard-operacional]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Calibração real×projetado reusando model.project() (D-08): conversão linear em desviado → desviado=t_org_coletada do mês, outputs _t_ano ÷ 12 para base mensal; NUNCA reimplementar a conversão"
    - "Soma honesta que preserva null em group_by (pl.when(col.is_not_null().any())): mês todo-null fica null, não 0 (regra sagrada) — corrige o default 0.0 de Polars .sum()"
    - "Teste de paridade cross-language offline: parse textual/regex do return de project() em app.js confirma nomes de campo sem rodar JS (CI só tem pytest)"
    - "Série temporal SVG inline à mão via string template: polyline ignora pontos null (linha quebra honestamente em mês sem dado)"

key-files:
  created: []
  modified:
    - pipeline/transform.py
    - site/app.js
    - site/styles.css
    - tests/test_pipeline.py

key-decisions:
  - "Projetado da calibração computado no BUILD (transform.build_operacao), não no front — determinístico, testável, e o painel só desenha (minimiza superfície de paridade). project() do front permanece intocado para o simulador."
  - "Confronto em base MENSAL: model.project() devolve _t_ano; dividir por 12 para casar com a telemetria mensal (Pitfall 2). Inversão trivial: clientes=1, kg_dia = t_org_coletada*12*1000/365 → desviado_t_ano = t_org_coletada*12."
  - "co2e/carros acumulados são DERIVADOS (via project() sobre o desviado real total), claramente rotulados como derivados no payload/card — não são medidos diretamente."
  - "Mês sem t_org_coletada → projetado_* e real_* null (célula vazia, linha quebra); nunca 0 — exigiu soma que preserva null no group_by."

patterns-established:
  - "Paridade model.py↔app.js travada por teste ANTES de construir a calibração sobre project() (ordem obrigatória da fase)"
  - "Calibração 'modelo alimentado pelo real' sem reimplementar conversão (reuso de model.project, provado por teste de coerência)"
  - "SVG inline à mão para gráfico de linha (zero dependência, sem build step), real sólido --desvio × projetado tracejado --ink-2"

requirements-completed: [LIVE-03, LIVE-04]

coverage:
  - id: D1
    description: "Teste de paridade model.py↔app.js::project() congela contrato numérico Python e captura renomeação silenciosa de campo JS (CONCERNS #7)"
    requirement: "LIVE-03"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_paridade_project_contrato_python_congelado"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_paridade_project_nomes_js_existem_em_app_js"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_paridade_mapa_py_js_cobre_chaves_do_modelo"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_operacao() produz projetado_* por mês reusando model.project() em base mensal (÷12), coerente com project() sobre o mesmo desviado"
    requirement: "LIVE-03"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_build_operacao_projetado_reusa_model_project"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mês sem t_org_coletada → projetado_* = None (nunca zero); série ordenada por mês (determinismo)"
    requirement: "LIVE-03"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_build_operacao_mes_incompleto_projetado_null_nunca_zero"
        status: pass
    human_judgment: false
  - id: D4
    description: "Acumulados incluem co2e evitado + carros equivalentes derivados via model.project() sobre o desviado real total (D-11)"
    requirement: "LIVE-04"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_build_operacao_acumulados_derivados_co2e_carros"
        status: pass
    human_judgment: false
  - id: D5
    description: "model.project() e config/coefficients.yml permanecem inalterados; estado vazio honesto preservado; build offline/determinístico, 27/27, data.json sem número inventado"
    requirement: "LIVE-04"
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_build_operacao_nao_altera_coefficients_yml"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_build_operacao_estado_vazio_sem_dado"
        status: pass
      - kind: integration
        ref: "uv run obs build --region rms (rodado 2x → data.json idêntico, operacao={serie:[],acumulados:null,tem_dado:false})"
        status: pass
    human_judgment: false
  - id: D6
    description: "Painel desenha a série SVG real (sólido) × projetado (tracejado) + 4 cards de impacto acumulado, com as 3 classes de dado visualmente inconfundíveis"
    requirement: "LIVE-04"
    verification:
      - kind: manual_procedural
        ref: "preview com telemetria sintética (em memória, não commitada) servido em :8126 — série com gap honesto em mês sem dado + 4 cards; estado vazio em :8125"
        status: pass
    human_judgment: true
    rationale: "Separação visual inconfundível das 3 classes (baseline público × projeção do simulador × medição da operação) e distinção real-sólido × projetado-tracejado exigem julgamento humano (regra sagrada). Checkpoint visual aprovado pelo usuário."

# Metrics
duration: 12min
completed: 2026-06-25
status: complete
---

# Phase 5 Plan 02: Calibração real×projetado + impacto acumulado Summary

**Confronto real×projetado calibrado reusando model.project() em base mensal (÷12) com paridade model.py↔app.js travada por teste (CONCERNS #7 fechado), série temporal SVG inline à mão (real sólido × projetado tracejado) e 4 cards de impacto acumulado — sem nunca apresentar projeção como medição nem preencher mês sem dado com zero.**

## Performance

- **Duration:** ~12 min (inclui checkpoint visual)
- **Started:** 2026-06-25T18:01:00Z
- **Completed:** 2026-06-25T18:14:00Z (aprox.)
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- **Teste de paridade cross-language (CONCERNS #7 fechado, RISCO CENTRAL da fase):** congela o contrato numérico de `model.project()` (9 campos, valores canônicos) e valida por parse textual de `site/app.js` que `project()` em JS retorna exatamente os nomes esperados (`desviado, co2e, carros, larvaSeca, frass, receita, fundo, catadores, pctOrg`). Uma renomeação silenciosa em qualquer lado quebra o teste — exatamente o que `carros_equivalente` vs `carros` causou no passado. Construído e verde **antes** de a calibração ser erguida sobre `project()`.
- **Projetado da calibração em `build_operacao()` (LIVE-03):** para cada mês com `t_org_coletada`, computa `projetado_*` reusando `model.project()` (D-08 — não reimplementa a conversão), em base **mensal** (outputs `_t_ano` ÷ 12, Pitfall 2). A inversão é trivial porque a conversão é linear em `desviado`. Mês sem `t_org_coletada` → `projetado_* = None` (nunca 0).
- **Acumulados derivados (LIVE-04, D-11):** `co2e_evitado_t_derivado` e `carros_equivalente_derivado` vêm de `model.project()` sobre o desviado real acumulado, rotulados como **derivados** (não medidos direto).
- **Série SVG inline + 4 cards (LIVE-03/LIVE-04, D-10/D-11):** `svgSerie()` desenha real sólido (`--desvio`) × projetado tracejado (`--ink-2`); ponto null quebra a linha honestamente. 4 cards: desvio de aterro, renda a catadores, CO₂e evitado (derivado), bioconversão. Classe visual `.tag.live` inconfundível das 3 classes.
- Suíte 35/35 verde (27 baseline + 8 novos: 3 paridade, 5 calibração). Build offline/determinístico, 27/27, `data.json` no estado vazio honesto (sem número inventado). Checkpoint visual aprovado.

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Teste de paridade model.py↔app.js::project()** - `cc41395` (test)
2. **Task 2: Projetado da calibração em build_operacao() reusando model.project()** - `47028b8` (feat)
3. **Task 3: Série SVG real×projetado + 4 cards de impacto acumulado** - `14b84ba` (feat)

**Plan metadata:** não commitado em git — `commit_docs: false` em `.planning/config.json` (`.planning/` fora do histórico do projeto).

_Task 2 incluiu 2 fixes inline durante a verificação (ver Issues Encountered) — corrigidos dentro do mesmo commit antes do teste passar._

## Files Created/Modified
- `pipeline/transform.py` - `build_operacao()` estendido com `_projetado_mensal()` (reusa `model.project()`, base mensal ÷12), soma honesta que preserva null no `group_by`, e acumulados derivados co2e/carros. `model.project()` e `coefficients.yml` intocados.
- `site/app.js` - nova função `svgSerie()` (SVG inline à mão); `renderOperacao()` caminho com dado (série + legenda + 4 cards). `project()` (paridade) intocado.
- `site/styles.css` - classes da série (`.serie/.s-real/.s-proj/.axis/.xlab/.ymax`) + wrapper/legenda da operação (`.opwrap/.op-head/.op-leg/.op-cap`).
- `tests/test_pipeline.py` - 3 testes de paridade (mapa `PARIDADE_PY_JS`) + 5 testes de calibração (fixture de telemetria sintética em memória, sem CSV).

## Decisions Made
- **Projetado computado no build, não no front:** determinístico/testável e minimiza a superfície de paridade — o painel só desenha o que vem pronto no payload; `project()` do front fica para o simulador interativo.
- **Base mensal (÷12):** confronto maçã-com-maçã com a telemetria mensal; inversão trivial `clientes=1, kg_dia = t_org_coletada*12*1000/365`.
- **co2e/carros acumulados rotulados como derivados:** não são medidos — vêm do modelo sobre o desviado real; honestidade visual (não passar projeção por medição).

## Deviations from Plan

None - plan executed exactly as written. (Os dois ajustes da Task 2 foram correções de verificação dentro do próprio escopo da task, não desvios de plano — ver Issues Encountered.)

## Issues Encountered
- **co2e acumulado 12× errado (anualização dupla):** a primeira versão multiplicava `projetado_co2e_t * 12` para anualizar o acumulado, mas `_projetado_mensal(desviado_total)` já devolve o valor correto (o ×12 da anualização e o ÷12 do retorno se cancelam quando se passa o total). Removido o `*12`. Pego pelo teste `test_build_operacao_acumulados_derivados_co2e_carros`.
- **Mês todo-null virava 0 (Polars `.sum()`):** `group_by().agg(pl.col(x).sum())` de um grupo inteiramente null devolve `0.0`, violando a regra sagrada (mês sem medição não pode ser zero). Substituído por uma soma honesta `pl.when(col.is_not_null().any()).then(sum).otherwise(None)`. Pego pelo teste `test_build_operacao_mes_incompleto_projetado_null_nunca_zero`.
- **Regex de parse do `app.js` capturava falso-positivo:** a versão inicial capturava identificadores dentro de expressões de valor (ex.: `co2e_por_carro_ano`) e perdia chaves shorthand seguidas de `}` (ex.: `pctOrg`). Corrigido ancorando em `{`/`,` à esquerda e lookahead `[:,}]`. Validado também o caminho negativo (detecta campo renomeado).

## User Setup Required
None - no external service configuration required. (`user_setup: []` no plano; pipeline offline sem rede/segredo.)

## Next Phase Readiness
- Calibração real×projetado e impacto acumulado prontos e provados com telemetria sintética — o painel "acende" automaticamente quando o operador preencher `data/raw/operacao/operacao_rms.csv` e rodar `uv run obs build`.
- CONCERNS #7 fechado: a paridade `model.py`↔`app.js` agora é travada por teste no CI; qualquer futura mudança em `project()` (Python ou JS) exige ajuste do mapa `PARIDADE_PY_JS` e quebra cedo.
- **Deferred (fora do escopo, intencional):** calibração automática dos coeficientes (a fase só *mostra* o desvio real×projetado, não reescreve `coefficients.yml`); `refresh()` de planilha externa para `operacao.py`. Ambos registrados no 05-CONTEXT.md.

## Self-Check: PASSED

---
*Phase: 05-camada-viva-operacional*
*Completed: 2026-06-25*
