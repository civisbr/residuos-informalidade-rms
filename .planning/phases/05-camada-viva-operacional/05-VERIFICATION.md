---
phase: 05-camada-viva-operacional
verified: 2026-06-25T00:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Camada viva (operacional) Verification Report

**Phase Goal:** Sobrepor a telemetria real da operação ao baseline público, com série temporal e impacto acumulado.
**Verified:** 2026-06-25
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

A fase entrega o "esqueleto vivo" end-to-end: o cano `operacao.load()` → `build_operacao()` → payload `operacao` → `renderOperacao()` está completo, provado com ZERO telemetria real (estado vazio honesto — o resultado correto, não um gap, já que a operação ainda não roda) E provado COM dado via fixtures sintéticas em memória (calibração real×projetado, acumulados derivados). A regra sagrada é respeitada em todos os pontos.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | LIVE-01: schema de telemetria definido, espelhando `model.project()` | ✓ VERIFIED | `data/raw/operacao/operacao_rms.csv` header `mes,municipio,n_clientes,t_org_coletada,larva_umida_t,larva_seca_t,frass_t,partilha_rs,qualidade,fonte` + comentários `#` documentando unidades (toneladas/R$) e procedência; `SCHEMA` em `operacao.py:29-40` com dtypes explícitos. ZERO linhas de dado (confirmado: `grep -vE "^#|^mes," → 0 data rows`). |
| 2 | LIVE-02: `sources/operacao.py::load()` lê o CSV offline, frame vazio COM coluna `key`, sem rede | ✓ VERIFIED | `operacao.py:43-67`: glob+concat, `comment_prefix="#"`, filtro `mes.is_not_null()`, frame vazio com `pl.lit(None).alias("key")`. Sem `refresh()`/requests/urllib (grep: NONE). Teste `test_operacao_load_vazio_tem_key` passa. |
| 3 | Build gera `data.json` com chave `operacao` em estado vazio honesto, offline e determinístico | ✓ VERIFIED | `cli.py:37,41-43` wira `operacao.load()`+`build_operacao()`+`operacao_payload`. Build executado: 27/27 municípios, sem rede. `operacao = {serie:[], acumulados:None, tem_dado:False}`. Rebuild 2× → diff vazio (determinístico). Chaves existentes preservadas (meta/coeficientes/simulador_defaults/totais/municipios). |
| 4 | LIVE-03: paridade `model.py`↔`app.js::project()` travada por teste (CONCERNS #7) | ✓ VERIFIED | `tests/test_pipeline.py:581-666`: `PARIDADE_PY_JS` (9 pares), congela contrato numérico Python com valores canônicos, e valida por regex ancorada o `return {...}` de `project()` em `app.js` (nomes JS `desviado,co2e,carros,larvaSeca,frass,receita,fundo,catadores,pctOrg`). 3 testes passam; capturam renomeação silenciosa cross-language. |
| 5 | LIVE-03: calibração reusa `model.project()` em base mensal (÷12); mês sem input → projetado null, nunca zero | ✓ VERIFIED | `transform.py:133-163` `_projetado_mensal()` reusa `model.project()` (D-08), ÷12 (Pitfall 2); `desviado_t_mes is None → projetado_* None`. `_soma_honesta` (`transform.py:191-197`) preserva null em group_by (corrige `.sum()→0`). Testes `test_build_operacao_projetado_reusa_model_project` e `test_build_operacao_mes_incompleto_projetado_null_nunca_zero` passam (asserção `!= 0`). |
| 6 | LIVE-03: série temporal real×projetado em SVG inline à mão, cores distintas, ignora null | ✓ VERIFIED | `app.js:103-125` `svgSerie()`: SVG inline (zero dependência), polyline filtra pontos null (linha quebra honestamente), `.s-real` sólido vs `.s-proj` tracejado. CSS `styles.css:135-138`: `.s-real` stroke `var(--desvio)`, `.s-proj` stroke `var(--ink-2)` + `stroke-dasharray`. |
| 7 | LIVE-04: 4 cards de impacto acumulado (desvio aterro, renda catadores, CO2e+carros, larva+frass) | ✓ VERIFIED | `app.js:139-152` 4 cards: desvio de aterro (`desviado_t`), renda a catadores (`partilha_rs`), CO₂e evitado + carros (`co2e_evitado_t_derivado`/`carros_equivalente_derivado`, rotulado `derivado`), bioconversão (`larva_seca_t`+`frass_t`). Acumulados computados em `transform.py:212-235`. Teste `test_build_operacao_acumulados_derivados_co2e_carros` passa. |
| 8 | Estado vazio honesto no painel: aviso "Operação ainda não iniciada — sem medição real" | ✓ VERIFIED | `app.js:127-136` `renderOperacao()`: `!op.tem_dado` → pendbox com a mensagem D-02 exata + instrução de preencher o CSV e rodar build. Seção em `index.html:96-97` (`seclabel` "Operação ao vivo" + `opSlot`), posicionada APÓS o simulador (`</div>` linha 94 fecha `.sim`, D-09). |
| 9 | As 3+1 classes visuais de dado são inconfundíveis (regra sagrada) | ✓ VERIFIED | `styles.css:36-39`: `.tag.real` verde, `.tag.est` dourado, `.tag.proj/.pend` laranja, `.tag.live` teal (#d6e6ec) — 4 cores distintas. Checkpoint visual humano registrado como aprovado em 05-02-SUMMARY D6; código substancia as classes distintas. |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pipeline/sources/operacao.py` | `load()` apenas, sem refresh (D-04) | ✓ VERIFIED | 68 linhas, `load()` + `SCHEMA` + `RAW`; sem `refresh()`. Tracked. |
| `data/raw/operacao/operacao_rms.csv` | template só header + comentários, sem dado | ✓ VERIFIED | 16 linhas comentário/doc + 1 header; 0 linhas de telemetria. Tracked. |
| `transform.build_operacao()` | dict `{serie,acumulados,tem_dado}`, estado vazio honesto | ✓ VERIFIED | `transform.py:166-237`; frame vazio → `{serie:[],acumulados:None,tem_dado:False}`. |
| `render.to_payload(...operacao_payload)` | chave `operacao` sempre presente | ✓ VERIFIED | `render.py:17,74-75`; default-able, chave nunca omitida. |
| Seção painel + `renderOperacao()` + estilos | seção, SVG, cards, tag dedicada | ✓ VERIFIED | `index.html:96-97`, `app.js:103-170`, `styles.css:39,125-138`. |
| Teste de paridade `model.py`↔`app.js` | trava nomes/valores cross-language | ✓ VERIFIED | `tests/test_pipeline.py:594-666`, 3 testes. |
| Cálculo projetado reusando `model.project()` | base mensal, sem reimplementar | ✓ VERIFIED | `transform.py:133-163` `_projetado_mensal()`. |
| Série SVG + 4 cards | SVG inline, 4 cards | ✓ VERIFIED | `app.js:103-170`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `operacao.load()` | `build_operacao()` | `cli.py:37,41` `df_op=operacao.load(root)` → `transform.build_operacao(df_op,coef)` | WIRED | Confirmado no build (27/27, offline). |
| `build_operacao()` | payload `operacao` | `cli.py:42-43` `operacao_payload=op` → `render.py:74-75` | WIRED | `data.json` contém `operacao`. |
| `data.json` | `renderOperacao()` | `app.js:96,128` `DATA.operacao` | WIRED | Chamado em `selectCity()`. |
| `model.project()` | `_projetado_mensal()` | `transform.py:157` `model.project(1,kg_dia,...)` ÷12 | WIRED | Reuso, não reimplementação (D-08). Teste de coerência passa. |
| paridade Py↔JS | teste | regex em `app.js` + assert chaves Python | WIRED | Quebra sob renomeação (negativo validado no SUMMARY). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Suíte completa verde | `uv run pytest -q` | 35 passed in 0.81s | ✓ PASS |
| Build offline 27/27 | `uv run obs build --region rms` | 27/27 municípios, "operação: sem medição real ainda" | ✓ PASS |
| Determinismo | rebuild 2× + diff | diff vazio (idêntico) | ✓ PASS |
| Chave operacao estado vazio | `python -c json.load` | `{serie:[],acumulados:None,tem_dado:False}` | ✓ PASS |
| operacao.load() vazio tem key | (test_operacao_load_vazio_tem_key) | key presente, height 0 | ✓ PASS |
| Sem rede em operacao.py | grep refresh/requests/urllib | NONE | ✓ PASS |
| CSV sem dado inventado | grep linhas de dado | 0 data rows | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| LIVE-01 | 05-01 | Esquema de telemetria definido | ✓ SATISFIED | CSV-template + SCHEMA (Truth 1) |
| LIVE-02 | 05-01 | `sources/operacao.py` lê a telemetria | ✓ SATISFIED | `load()` offline + wiring (Truths 2,3) |
| LIVE-03 | 05-02 | Série temporal baseline+real lado a lado | ✓ SATISFIED | Paridade + calibração + SVG (Truths 4,5,6) |
| LIVE-04 | 05-02 | Painel de impacto acumulado | ✓ SATISFIED | 4 cards + acumulados derivados (Truth 7) |

Todos os 4 IDs declarados nos PLANs (05-01: LIVE-01,02; 05-02: LIVE-03,04) constam em REQUIREMENTS.md (linhas 42-45, 86-89) e estão satisfeitos. Nenhum ID órfão.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (nenhum) | — | TBD/FIXME/XXX | — | Scan limpo nos arquivos modificados |

Nota: `app.js:137` contém um comentário "TODO" inexistente — não há marcadores de débito; os "branch vazio aqui" descritos no plano 05-01 foram completados no plano 05-02 (caminho COM dado implementado). Confirmado: sem `return null`/`return []`/handlers vazios voltados a render. Os `acumulados:None` e `projetado_*:None` são intencionais (regra sagrada — ausência honesta, não stub).

### Invariantes da regra sagrada

| Invariante | Status | Evidência |
| --- | --- | --- |
| Build offline/determinístico | ✓ | Sem rede; rebuild 2× idêntico |
| `data.json operacao` nunca ausente, estado vazio honesto | ✓ | `render.py:74-75` chave sempre presente |
| CSV commitado só header (sem número inventado) | ✓ | 0 linhas de dado |
| Mês sem medição → null, nunca zero | ✓ | `_soma_honesta` + `_projetado_mensal(None)`; teste dedicado |
| Paridade `model.py`↔`app.js` travada por teste | ✓ | 3 testes de paridade (CONCERNS #7 fechado) |
| `model.project()` e `coefficients.yml` inalterados | ✓ | `test_build_operacao_nao_altera_coefficients_yml` passa |
| 4 classes visuais distintas | ✓ | `.tag.real/.est/.proj/.live` 4 cores |

### Human Verification Required

Nenhum item pendente. O único item de julgamento humano (separação visual inconfundível das 3+1 classes, 05-02 Task 3 `<human-check>`) já foi aprovado no checkpoint registrado em 05-02-SUMMARY (coverage D6, status pass) e o código verificado substancia as classes visuais distintas e o estilo real-sólido × projetado-tracejado. Conforme escopo da fase (offline, operação ainda não roda), nenhum teste humano de rede se aplica.

### Gaps Summary

Nenhum gap. A fase entrega o esqueleto vivo completo: schema (LIVE-01), fonte offline (LIVE-02), série real×projetado calibrada com paridade travada (LIVE-03) e impacto acumulado em 4 cards (LIVE-04). O estado vazio honesto é o resultado correto (a operação ainda não roda) e foi verificado end-to-end; o caminho COM dado foi provado por fixtures sintéticas em memória. A regra sagrada é respeitada em todos os pontos: nenhum número inventado, mês sem medição vira null (nunca zero), build offline/determinístico, e as classes de dado são visualmente inconfundíveis.

---

_Verified: 2026-06-25_
_Verifier: Claude (gsd-verifier)_
