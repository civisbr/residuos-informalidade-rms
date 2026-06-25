# Phase 5: Camada viva (operacional) - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Sobrepor a **telemetria real** da operação de coleta de orgânicos +
bioconversão BSF ao baseline público, com **série temporal** e **impacto
acumulado**. Cobre LIVE-01..04:

- **LIVE-01:** esquema de telemetria (t coletadas/mês, larva, frass, partilha).
- **LIVE-02:** `sources/operacao.py` lê a telemetria (CSV commitado).
- **LIVE-03:** série temporal no painel — baseline público + medição real lado a lado.
- **LIVE-04:** painel de impacto acumulado (desvio de aterro, renda a catadores, etc.).

**Três classes de dado que NÃO podem se confundir** (regra sagrada): `baseline
público` (SNIS/IBGE — anual, defasado), `simulador` (projeção do modelo BSF) e
agora `telemetria real` (medição operacional no tempo). Telemetria é medição,
não projeção; medição real ≠ baseline público. Cada classe é visualmente
separada no painel.

**Realidade da operação:** a operação **ainda não roda** — não há telemetria
real para commitar. Esta fase entrega o **"esqueleto vivo"**: schema + source +
painel com **estado vazio honesto**, pronto para "ligar" quando houver dado.
**Nunca inventar telemetria.**

**Fora de escopo (Out of Scope v1 / outras fases):** mapa coroplético,
comparação de pares município×mediana, export PDF; `refresh()` de planilha
externa (só `load()` nesta fase); calibração automática dos coeficientes a
partir do real (a fase só *mostra* o desvio, não reescreve `coefficients.yml`).
A discussão clarifica COMO implementar o que já está escopado — não adiciona
capacidade nova.

</domain>

<decisions>
## Implementation Decisions

### Estado da operação / seed (LIVE-01..04, regra sagrada)
- **D-01:** **Esqueleto vivo** — a operação ainda não roda; a fase NÃO commita
  dado real e NÃO inventa número. Entrega schema + `sources/operacao.py` +
  seção no painel, prontos para receber dado real depois.
- **D-02:** **Estado vazio = placeholder honesto + contrato visível.** Sem
  telemetria, a seção aparece com aviso explícito (ex.: "Operação ainda não
  iniciada — sem medição real"). Commitar um **CSV-template vazio com cabeçalho
  documentado** em `data/raw/operacao/` (ex.: `operacao_rms.csv` só com header),
  para o operador depois só preencher. Painel já "pronto para ligar".

### Origem & formato da telemetria (LIVE-01, LIVE-02)
- **D-03:** **Grão = mês × município.** Uma linha por (mês, município), com os
  agregados daquele município no mês. Casa direto com o baseline (que é por
  município) e com a série temporal; junção por `slug(nome)` (chave do projeto).
- **D-04:** **`sources/operacao.py` só tem `load()`** lendo o CSV commitado em
  `data/raw/operacao/*.csv` (operador edita/substitui à mão ou cola export da
  planilha). Sem `refresh()` de rede nesta fase — coerente com o padrão
  `load()`/`refresh()` e com "operação ainda não roda".
- **D-05:** **Schema = medidas brutas do operador**, espelhando os MESMOS
  quantitativos que `model.project()` produz, para permitir real×projetado 1:1.
  Colunas-base (planner valida nomes exatos): `mes` (AAAA-MM), `municipio`,
  `n_clientes`, `t_org_coletada`, `larva_*` (seca/úmida — planner define a
  unidade medida), `frass_*`, `partilha_rs` (R$ repassado a catadores). A classe
  inteira é flag `real (operação)`; medidas que sejam estimadas/derivadas (ex.:
  frass calculado, não pesado) devem ser sinalizadas — planner decide se via
  coluna de procedência ou convenção, sem reintroduzir chute.

### Real vs Projetado (LIVE-03, paridade)
- **D-06:** **Vista de calibração lado a lado** — o mesmo gráfico/tabela mostra
  "projetamos X (modelo) — medimos Y (real)" por indicador, com cores/estilos
  distintos para nunca confundir medição com projeção.
- **D-07:** **Referência = modelo alimentado pelo real.** O "projetado" do
  confronto roda `model.project()` sobre o INPUT real medido do mês (t coletada
  / n clientes), não sobre o cenário default do simulador. Objetivo: validar os
  **coeficientes de conversão** (larva/frass/CO2e/partilha) contra a realidade —
  separa desvio de coeficiente de desvio de escala.
- **D-08:** **Reusar `model.project()`** (não reimplementar a lógica) para o
  projetado da calibração, preservando a paridade `model.py`↔`app.js::project()`.
  Se o cálculo da calibração rodar no front, é a MESMA função do simulador;
  mudou um, muda o outro e ajusta o teste de paridade.

### Apresentação no painel (LIVE-03, LIVE-04)
- **D-09:** **Seção regional dedicada** ("Operação ao vivo") depois do
  simulador, agregando a região: série temporal mensal + cards de impacto
  acumulado. Não polui a lista de municípios; "acende" quando houver dado (D-02).
- **D-10:** **Série temporal em SVG inline à mão** (JS vanilla desenha
  linhas/barras). Zero dependência externa, respeita "sem framework, sem build
  step"; cores distintas para real×projetado (D-06).
- **D-11:** **Impacto acumulado destaca os 4 indicadores:** (1) desvio de aterro
  acumulado (t, espelha `desviado_t_ano`), (2) renda a catadores acumulada (R$,
  conecta com a informalidade da Fase 2), (3) CO2e evitado acumulado (t + carros
  equivalentes, como o modelo já faz), (4) bioconversão acumulada (larva seca +
  frass).

### Claude's Discretion
- Nomes exatos das colunas do CSV e unidades medidas (kg vs t para larva/frass)
  — planner valida contra `model.project()` e o que o operador realmente pesa
  (D-05), mantendo o espelhamento.
- Onde o "projetado da calibração" é computado (build em `render.py` vs front em
  `app.js`) — planner decide, desde que reuse `model.project()` e preserve a
  paridade (D-08). Atenção ao build offline/determinístico se for no render.
- Como a calibração lida com meses sem projeção possível (input incompleto) —
  planner define o tratamento honesto (ex.: célula vazia, não zero).
- Detalhe do estado vazio no payload (`operacao: []` vs ausente) e como o
  `render.to_payload()` expõe a nova classe sem quebrar consumidores atuais.
- Paleta/rótulos exatos das 3 classes no painel — desde que visualmente
  inconfundíveis (regra sagrada).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regra do projeto e fase
- `CLAUDE.md` — regra sagrada (nunca inventar número; flags `real`/`estimativa`/
  `pendente`; baseline×projeção visualmente separados; build offline/
  determinístico; junção por `base.slug`; paridade `model.py`↔`app.js`).
  Convenções de commit (PT-BR imperativo) e "Como estender → Nova fonte".
- `.planning/PROJECT.md` — Constraints (build offline/determinístico; `data.json`
  commitado; paridade de modelo; junção por slug); Core Value (credibilidade).
- `.planning/REQUIREMENTS.md` §"Camada viva (M5)" — LIVE-01..04 (linhas 42-45,
  86-89).
- `GSD.md` §M5 — checklist autoral "Camada viva (operacional)".

### Artefatos a estender/criar
- `pipeline/sources/operacao.py` — **NOVO** módulo de fonte; `load()` lê
  `data/raw/operacao/*.csv` (D-04). Espelha o molde de `pipeline/sources/snis.py`.
- `pipeline/sources/snis.py` — molde de fonte `load()` (concatena CSVs de pasta);
  referência de estilo para `operacao.py`.
- `pipeline/sources/base.py::slug` — chave de junção telemetria↔baseline (D-03).
- `pipeline/model.py::project()` / `defaults()` — reusar `project()` para o
  projetado da calibração (D-07/D-08). Outputs espelhados pelo schema (D-05):
  `desviado_t_ano`, `larva_seca_t_ano`, `frass_t_ano`, `co2e_t_ano`,
  `carros_equivalente`, `fundo_partilha_ano`, `catadores_sustentados`.
- `pipeline/transform.py` — junção/derivação; ponto de integração da nova fonte
  e dos acumulados (LIVE-04).
- `pipeline/render.py::to_payload()` — expor a nova classe `operacao` no payload
  sem quebrar `meta`/`municipios`/`totais`/`coeficientes`/`simulador_defaults`.
- `pipeline/cli.py` — se necessário, expor build com a nova fonte (sem novo
  comando de rede nesta fase — D-04).
- `site/app.js` — `project()` (paridade D-08) e nova seção "Operação ao vivo"
  com série temporal SVG (D-09/D-10); `site/index.html` + `site/styles.css` para
  os slots/estilos da seção e separação visual das 3 classes.
- `config/coefficients.yml` — coeficientes do modelo (lidos por `project()`); a
  fase compara contra eles, **não** os reescreve.
- `data/raw/operacao/operacao_rms.csv` — **NOVO** CSV-template (só header
  documentado) commitado (D-02).

### Codebase intel
- `.planning/codebase/ARCHITECTURE.md` — fluxo pipeline offline → `data.json` →
  painel; abstrações flag de qualidade e baseline×simulador; paridade
  `model.py`↔`app.js`.
- `.planning/codebase/CONCERNS.md` — **paridade `model.py`↔`app.js` sem teste**
  (campos já divergiram: `carros_equivalente` vs `carros`) — risco direto a D-08;
  fechar com teste de paridade é fortemente recomendado nesta fase.
- `.planning/phases/04-generalizar-para-qualquer-cidade-br/04-CONTEXT.md` —
  padrão `load()`/`refresh()` e integridade (`null`/`pendente` em vez de chute).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/model.py::project()` — única fonte da lógica de conversão; reusar
  para o projetado da calibração (D-07/D-08), nunca duplicar.
- `pipeline/sources/snis.py::load()` — molde direto para `operacao.py::load()`
  (ler CSV(s) de uma pasta, devolver DataFrame Polars).
- `pipeline/sources/base.py::slug` — normalização de nome = chave de junção
  telemetria↔baseline (D-03).
- `render.to_payload()` já separa classes no payload (`municipios`/`totais` vs
  `coeficientes`/`simulador_defaults`) — adicionar `operacao` segue o padrão.

### Established Patterns
- Pipeline batch **offline → `data.json` estático → painel vanilla**; build
  nunca toca a rede (`operacao.py` só `load()` preserva isso — D-04).
- Integridade: campo sem fonte confiável → `null`/`pendente`, nunca chute. Aqui:
  sem telemetria → estado vazio honesto, nunca dado inventado (D-01/D-02).
- Paridade `model.py`↔`app.js::project()`: mudou um, muda o outro + teste (D-08).
- Front sem framework/sem build step → visualização em SVG inline à mão (D-10).

### Integration Points
- `transform.build_region()` / `region_totals()` — onde a telemetria entra e os
  acumulados regionais (LIVE-04) são derivados.
- `render.to_payload()` — nova chave `operacao` no payload (estado vazio honesto
  quando sem dado).
- `site/app.js` + `index.html` + `styles.css` — seção "Operação ao vivo", série
  SVG e separação visual das 3 classes.
- `data/raw/operacao/` — pasta nova lida por `operacao.load()`.

</code_context>

<specifics>
## Specific Ideas

- Seção do painel: "Operação ao vivo", regional, depois do simulador (D-09).
- Estado vazio: aviso "Operação ainda não iniciada — sem medição real" (D-02).
- CSV-template commitado em `data/raw/operacao/operacao_rms.csv` (só header).
- Grão do CSV: uma linha por (mês `AAAA-MM`, município) (D-03).
- Calibração: "projetamos X — medimos Y" por indicador, modelo alimentado pelo
  input real do mês (D-06/D-07).
- 4 acumulados em destaque: desvio de aterro (t), renda a catadores (R$), CO2e
  evitado (t + carros), bioconversão (larva seca + frass) (D-11).
- Série temporal em SVG inline à mão, real×projetado em cores distintas (D-10).

</specifics>

<deferred>
## Deferred Ideas

- **`refresh()` de planilha externa para `operacao.py`** — puxar de Google
  Sheets/export publicado. Fora de escopo agora (operação não roda; D-04); faz
  sentido quando houver fluxo real e recorrente de dado.
- **Calibração automática dos coeficientes** — usar o desvio real×projetado para
  reescrever/ajustar `config/coefficients.yml`. Esta fase só *mostra* o desvio;
  recalibrar é decisão de produto/ciência, fase própria.
- **Telemetria por cliente (grão mais fino)** — grão mês×cliente com agregação no
  painel. Adiado em favor de mês×município (D-03); revisitar se a operação
  precisar de visão por cliente.
- **Telemetria por município no card** (em vez de seção regional) — granularidade
  maior na UI; adiado em favor da seção regional dedicada (D-09).
- **Informalidade/RAIS para qualquer região** — herdado da Fase 4; segue fora do
  núcleo. Não toca esta fase.

### Reviewed Todos (not folded)
None — sem todos pendentes cruzando esta fase.

</deferred>

---

*Phase: 5-camada-viva-operacional*
*Context gathered: 2026-06-25*
