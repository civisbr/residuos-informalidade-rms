# Phase 2: Camada de informalidade - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Adicionar uma **camada de informalidade** sobre o baseline já real dos 27
municípios da RMS: um indicador de informalidade por município (INFO-01), um
proxy de formalização do setor de resíduos (INFO-02), exibição no painel
visualmente separada de estimativa (INFO-03) e uma nota explícita de
subcontagem da população catadora (INFO-04). Cobre INFO-01..04.

**Fora de escopo (outras fases):** deploy contínuo no Pages (Fase 3),
generalização para outras cidades e `refresh()` automatizado das fontes
(Fase 4), telemetria operacional (Fase 5). Mapa coroplético e comparação de
pares seguem fora do escopo v1 (PROJECT.md). Discussão clarifica COMO
implementar o que já está escopado — não adiciona capacidade nova.

</domain>

<decisions>
## Implementation Decisions

### Fonte e granularidade do indicador (INFO-01)
- **D-01:** **Censo 2022 (IBGE) é a base municipal** do indicador de informalidade
  — tem granularidade municipal para os 27 (ocupação, vínculo, rendimento),
  cumpre a regra sagrada (dado municipal real) e dá cobertura total. Flag `real`.
- **D-02:** **PNAD Contínua entra como contexto regional** (RMS/UF), mais atual,
  porém **claramente rotulada como estimativa regional** — NÃO por município. A
  PNAD não é representativa no nível municipal; usá-la por município feriria a
  regra sagrada. Flag `estimativa`, com âmbito (regional) explícito.
- **D-03:** Acesso às fontes segue o padrão existente: **snapshot CSV commitado**
  em `data/raw/` + `refresh()` documentado (espelha `sources/snis.py` /
  `sources/ibge.py`). Build permanece offline e determinístico. (Automação do
  refresh é Fase 4.)

### O que o indicador mede
- **D-04:** O indicador municipal exibido é a **taxa de informalidade do trabalho
  em geral**, definição IBGE (ocupados sem carteira + conta própria sem CNPJ +
  trabalhador familiar auxiliar), disponível real para os 27. NÃO restringir ao
  setor de resíduos no indicador-base (Censo não publica ocupação por CBO no
  nível municipal de forma confiável → viraria pendente em massa).
- **D-05:** Adicionar uma **lente específica de catadores** que conecta ao proxy
  de formalização (INFO-02), usando os dados de setor de resíduos onde existirem
  (cooperados do SNIS + emprego formal RAIS). A lente é complementar ao indicador
  geral, não o substitui.

### Proxy de formalização (INFO-02)
- **D-06:** **Grau de formalização = empregos formais ÷ (formais + cooperados)**,
  onde:
  - **formais** = empregos formais no(s) CNAE de resíduos (RAIS/CAGED), real por
    município;
  - **cooperados** = campo já existente do SNIS (Fase 1, D-07), real, tratado como
    piso.
  Ambos os termos são dados citados — **nada inventado**. Nenhuma estimativa de
  "total de catadores" entra na fórmula (evita o flag estimativa no proxy).
- **D-07 (edge case / regra sagrada):** Município onde **formais E cooperados são
  ambos null/0** → o proxy fica **`pendente`** (não calcular 0/0 nem assumir 0).
  Documentar na `fonte` do indicador.

### Exibição no painel (INFO-03)
- **D-08:** Informalidade aparece em **dois lugares**: (a) uma **seção própria na
  visão do município** (junto às KPIs, ao selecionar a cidade) e (b) uma **célula
  no `region-strip`** agregado do topo. Reusa o sistema de tags existente
  (`dado público` / `estimativa` / `pendente`) para separar visualmente real de
  estimativa — não criar um sistema de flag paralelo.
- **D-09:** A separação visual entre baseline e estimativa segue o padrão já
  estabelecido no painel (tags `real`/`estimativa`/`pendente` em `app.js`). O
  indicador Censo é `real`; o contexto PNAD regional é `estimativa` com âmbito
  regional rotulado.

### Nota de subcontagem da população catadora (INFO-04)
- **D-10:** Nota de subcontagem é **texto fixo, sempre visível e não-colapsável**
  na seção de informalidade, explicando que as bases oficiais (SNIS/Censo)
  subcontam a população catadora — tratar como **piso**. É regra do projeto; não
  pode depender de hover/tooltip nem ficar diluída no rodapé.

### Claude's Discretion
- Códigos CNAE exatos do "setor de resíduos" para a RAIS/CAGED (ex.: 3811, 3812,
  3821, 3822, 3831, 3832, 3839, 3900) — a pesquisa define e documenta no
  RESEARCH.md; escolher os que representam coleta/tratamento/recuperação de RSU.
- Variáveis/tabelas exatas do Censo 2022 (SIDRA) que produzem a taxa de
  informalidade municipal — pesquisa define.
- Nomes/estrutura dos novos CSVs em `data/raw/` e se a fonte vira um único módulo
  `sources/ibge_informalidade.py` (INFO-01) ou módulos separados para Censo/PNAD/RAIS
  — decisão do planner, respeitando o padrão de `load()`/`refresh()` existente.
- Layout fino da seção de informalidade no `app.js`/`index.html` (rótulos, ordem),
  desde que respeite D-08/D-09/D-10.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regra do projeto e fase anterior
- `CLAUDE.md` — regra sagrada de integridade (flag `real`/`estimativa`/`pendente`,
  catador como piso, baseline×estimativa separados), Polars (não pandas), junção
  por `base.slug`, fonte por linha, paridade `model.py`↔`app.js`.
- `.planning/PROJECT.md` — visão, constraints (build offline/determinístico,
  `data.json` commitado), Out of Scope.
- `.planning/phases/01-baseline-real-da-rms/01-CONTEXT.md` — D-07 (cooperados como
  piso, base do INFO-04), padrão de composição/flag por-município.
- `GSD.md` §M2 — checklist autoral da milestone "Camada de informalidade".

### Código e dado a estender
- `pipeline/sources/snis.py` — `cooperados` (entra na fórmula do proxy D-06);
  padrão `SCHEMA` + `load()` (concatena CSVs, dedup por ano) a espelhar na nova fonte.
- `pipeline/sources/ibge.py` — padrão `load()` offline + `refresh()` (a fonte de
  informalidade segue este molde; INFO-01 cita `sources/ibge_informalidade.py`).
- `pipeline/sources/base.py` — `slug()` (chave de junção; não reimplementar).
- `pipeline/transform.py` — `build_region()` é o ponto único de junção/derivação;
  é onde os indicadores de informalidade/proxy se juntam por `key` e ganham flag.
- `pipeline/render.py` — `to_payload()` adiciona os novos campos ao `site/data.json`.
- `site/app.js` — `renderKpis()`/`buildRegionStrip()`/sistema de tags
  (`real`/`estimativa`/`pendente`) e `caveat`; pontos de exibição (D-08..D-10).
- `site/index.html` — `region-strip`, seção do município (`kpis`/`flowSlot`), `caveat`.
- `config/regions.yml` — 27 municípios da RMS (nomes-âncora da junção).
- `tests/test_pipeline.py` — adicionar asserções da camada de informalidade
  (real/estimativa/pendente; invariante: sem dado municipal → pendente, não inventa).

### Fontes externas (a confirmar na pesquisa)
- IBGE Censo 2022 via SIDRA (informalidade/ocupação por município) — INFO-01 base.
- IBGE PNAD Contínua (informalidade regional/UF, mais atual) — INFO-01 contexto.
- RAIS/CAGED (PDET / Ministério do Trabalho) — emprego formal por CNAE de resíduos
  por município, INFO-02.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sources/ibge.py` e `sources/snis.py` definem o molde `load()` (offline) +
  `SCHEMA` + (futuro) `refresh()` — a fonte de informalidade copia esse padrão.
- `base.slug()` resolve a junção nome→município; reusar.
- Campo `cooperados` (SNIS) já existe e é insumo direto do proxy (D-06).
- Sistema de tags `real`/`estimativa`/`pendente` em `app.js` (`renderKpis`,
  `buildRegionStrip`) — reusar para separar informalidade real de estimativa.

### Established Patterns
- Pipeline batch offline → `data.json` estático → painel vanilla. Sem framework,
  sem build step. Build precisa permanecer offline e determinístico.
- Coluna `fonte` é passthrough do CSV até o `data.json`; proveniência por linha.
- `transform.build_region()` faz `join` por `key` (left join) e deriva flags com
  `pl.when(...).then(...).otherwise(...)` — a informalidade entra como mais um
  join + derivação de flag.

### Integration Points
- `transform.build_region()` — ponto único onde os indicadores de informalidade
  e o proxy se juntam aos municípios e ganham flag de qualidade.
- `render.to_payload()` — precisa expor os novos campos (informalidade, proxy,
  âmbito/flag) no `data.json`.
- `app.js` — `selectCity()`/`renderKpis()` (seção por município) e
  `buildRegionStrip()` (célula regional); `caveat`/seção para a nota fixa (INFO-04).

</code_context>

<specifics>
## Specific Ideas

- Indicador municipal = taxa de informalidade do trabalho (definição IBGE: sem
  carteira + conta própria sem CNPJ + trabalhador familiar), do Censo 2022.
- PNAD sempre rotulada como **contexto regional (estimativa)**, nunca atribuída a
  um município específico.
- Proxy de formalização exibido como razão `formais ÷ (formais + cooperados)`, com
  os dois números brutos visíveis e citados; `pendente` quando ambos faltarem.
- Nota de subcontagem com linguagem de "piso" (coerente com D-07 da Fase 1).

</specifics>

<deferred>
## Deferred Ideas

- Automação do `refresh()` das fontes de informalidade (Censo/PNAD/RAIS) → Fase 4
  (GEN-02). Nesta fase: snapshot commitado + refresh documentado.
- Recorte municipal de catadores por CBO (ocupação específica) caso surja fonte
  municipal confiável → incremento futuro; nesta fase a lente de catadores usa
  cooperados (SNIS) + RAIS por CNAE.
- Série temporal de informalidade (evolução entre censos/PNADs) → fora do escopo
  v1; a camada viva/temporal é tema da Fase 5.
- Mapa coroplético da informalidade → Out of Scope v1 (PROJECT.md).

</deferred>

---

*Phase: 02-camada-de-informalidade*
*Context gathered: 2026-06-23*
