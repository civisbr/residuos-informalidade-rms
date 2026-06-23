---
phase: 02-camada-de-informalidade
verified: 2026-06-23T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Verificação visual do painel no navegador"
    expected: "Seção 'Informalidade do trabalho no município' com 3 KPIs (taxa ~28,0% Sorocaba, formais=745, proxy ~84,2%), nota D-10 sempre visível, PNAD rotulada 'Estado de SP (estimativa regional)', célula 'Informalidade média RMS' no region-strip"
    why_human: "Renderização de HTML/JS no navegador não pode ser verificada por grep/python; a tarefa 3 do plano 02-03 era explicitamente um checkpoint:human-verify que foi aprovado pelo usuário durante a execução (registrado no SUMMARY), mas a aprovação do usuário durante a execução não é evidência de verificação independente de fase"
---

# Fase 2: Camada de Informalidade — Relatório de Verificação

**Meta da Fase:** O painel mostra, por município, um indicador de informalidade com fonte, separado do que é estimativa, com nota de subcontagem da população catadora.
**Verificado:** 2026-06-23
**Status:** human_needed
**Re-verificação:** Não — verificação inicial

## Alcance da Meta

### Verdades Observáveis

| #  | Verdade | Status | Evidência |
|----|---------|--------|-----------|
| 1  | Fonte `pipeline/sources/ibge_informalidade.py` carrega ocupação informal (Censo 2022) por município | VERIFICADO | Arquivo existe e tem 124 linhas; `load()` com SCHEMA completo, `glob("*.csv")`, `slug(municipio)→key`; `data/raw/censo/censo_informalidade_rms.csv` tem 28 linhas (header + 27); execução confirma 27 linhas, `taxa_informalidade_pct` sem null, Sorocaba=28,0% |
| 2  | Painel exibe card/seção de informalidade com flag de qualidade, visualmente separado de estimativa | VERIFICADO (com pendente humano) | `index.html` linhas 37-40: slots `#infTags`, `#kpisInf`, `#infSubcount` (display:block), `#pnadRegional` presentes após `#kpis` e antes do simulador; `app.js` `renderInformalidade()` preenche 3 KPIs com tags real/pendente via classes CSS existentes `.tag.real` / `.tag.pend`; renderização visual requer confirmação humana |
| 3  | Proxy de formalização (RAIS/CAGED vs. cooperados) aparece com sua fonte | VERIFICADO | `pipeline/sources/rais.py` existe (109 linhas); CSV `data/raw/rais/rais_residuos_rms_sp.csv` tem 28 linhas; `transform.py` calcula `proxy_formalizacao` via D-06/D-07 (linhas 69-95); `data.json`: 27/27 municípios têm `proxy_formalizacao` (null onde D-07, float onde há dado); Sorocaba=0.842, Alambari=None/pendente |
| 4  | Nota explícita de subcontagem da população catadora visível no painel | VERIFICADO (com pendente humano) | `app.js` linha 192-196: `$("infSubcount").innerHTML` injetado sem condicional com texto fixo "Nota sobre subcontagem de catadores..."; `index.html` linha 39: `div#infSubcount class="caveat" style="display:block"` (sem `hidden`, sem lógica de colapso); visibilidade real no browser requer confirmação humana |

**Score:** 4/4 verdades verificadas no código

### Artefatos Obrigatórios

| Artefato | Esperado | Status | Detalhes |
|----------|----------|--------|---------|
| `data/raw/censo/censo_informalidade_rms.csv` | 27 linhas, taxa_informalidade_pct sem null | VERIFICADO | 28 linhas (header+27), todos os 27 municípios com taxa; Sorocaba=28,0% |
| `data/raw/rais/rais_residuos_rms_sp.csv` | 27 linhas, formais_residuos sem null | VERIFICADO | 28 linhas (header+27), `formais_residuos` sem null; Alambari=0, Jumirim=0 |
| `data/raw/pnad/pnad_sp_informalidade.csv` | 1 linha, flag=estimativa, sem coluna municipio | VERIFICADO | 2 linhas (header+1), flag=estimativa, ambito=Estado de São Paulo, SCHEMA sem municipio |
| `pipeline/sources/ibge_informalidade.py` | load() + SCHEMA + refresh(NotImplementedError) | VERIFICADO | 124 linhas; SCHEMA dict com 8 tipos; RMS_IBGE_CODES (27 códigos); load() com glob+concat+unique+slug; refresh() com NotImplementedError documentado |
| `pipeline/sources/rais.py` | load() + SCHEMA + WASTE_CNAES + refresh() | VERIFICADO | 109 linhas; SCHEMA com 6 tipos; WASTE_CNAES (9 CNAEs); load() padrão; refresh() com SQL canônico BigQuery |
| `pipeline/sources/pnad_regional.py` | load() sem coluna municipio + refresh() | VERIFICADO | 78 linhas; SCHEMA sem municipio (invariante D-02 documentada); load() retorna CSV direto; refresh() com NotImplementedError e URL SIDRA |
| `pipeline/transform.py` | build_region() com 2 joins + derivação proxy D-06/D-07 | VERIFICADO | Linhas 25-95: inf_sel seleciona/renomeia fonte→fonte_inf; rais_sel seleciona/renomeia ano→ano_rais; 2 left joins por key; flag_informalidade derivada; proxy D-07 com _denominador auxiliar; region_totals() com taxa_inf_media_rms ponderada |
| `pipeline/render.py` | to_payload() com campos informalidade + meta.pnad_contexto_regional | VERIFICADO | Linhas 31-40: 10 campos de informalidade por município; linhas 43-54: pnad_contexto_regional em meta (nunca em municipios[]); parâmetro pnad_df opcional |
| `pipeline/cli.py` | importa e passa as 3 novas fontes | VERIFICADO | Linha 13: `from .sources import ibge, snis, ibge_informalidade, rais, pnad_regional`; linhas 34-36: carrega df_inf, df_rais, df_pnad; linhas 38-40: passa para build_region e to_payload |
| `site/data.json` | 27 municípios com taxa_informalidade_pct, meta.pnad_contexto_regional, totais.taxa_inf_media_rms | VERIFICADO | 0 municípios sem taxa_informalidade_pct; meta.pnad_contexto_regional.flag=estimativa; totais.taxa_inf_media_rms=28,8%; PNAD ausente em municipios[] |
| `site/index.html` | Slots #kpisInf, #infSubcount, #infTags, #pnadRegional | VERIFICADO | Linhas 37-40: todos os 4 slots presentes; infSubcount com `style="display:block"` sem hidden |
| `site/app.js` | renderInformalidade() + selectCity() wired + buildRegionStrip() atualizado | VERIFICADO | renderInformalidade() definida na linha 155 (58 linhas); selectCity() chama renderInformalidade() na linha 88; buildRegionStrip() inclui célula "Informalidade média RMS" na linha 58 |
| `tests/test_pipeline.py` | 12 testes passando incluindo novos de INFO-01/02 | VERIFICADO | 12 testes definidos; `uv run pytest -q` → 12 passed em 0,88s |

### Verificação de Links Chave

| De | Para | Via | Status | Detalhes |
|----|------|-----|--------|---------|
| `pipeline/sources/ibge_informalidade.py::load()` | `data/raw/censo/censo_informalidade_rms.csv` | `pl.read_csv` com `glob("*.csv")` | WIRED | Linha 77: `files = sorted((_root / RAW).glob("*.csv"))` |
| `pipeline/sources/ibge_informalidade.py::load()` | `pipeline/sources/base.slug` | `map_elements(slug, ...)` → key | WIRED | Linha 88: `pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")` |
| `pipeline/sources/rais.py::load()` | `data/raw/rais/rais_residuos_rms_sp.csv` | `pl.read_csv` com `glob("*.csv")` | WIRED | Linha 56: `files = sorted((_root / RAW).glob("*.csv"))` |
| `pipeline/transform.build_region()` | `pipeline/sources/ibge_informalidade.load()` | left join on key | WIRED | Linha 45: `.join(inf_sel, on="key", how="left")`; inf_sel construído via `informalidade.select(...)` |
| `pipeline/transform.build_region()` | `pipeline/sources/rais.load()` | left join on key | WIRED | Linha 46: `.join(rais_sel, on="key", how="left")` |
| `pipeline/render.to_payload()` | `municipios[].taxa_informalidade_pct` | `r["taxa_informalidade_pct"]` → dict | WIRED | Linha 31: `"taxa_informalidade_pct": r["taxa_informalidade_pct"]` |
| `pipeline/render.to_payload()` | `meta.pnad_contexto_regional` | pnad_df como parâmetro | WIRED | Linhas 43-54: `pnad_contexto` construído de pnad_df e colocado em meta |
| `site/app.js::selectCity()` | `site/app.js::renderInformalidade()` | chamada direta após renderKpis() | WIRED | Linha 88: `renderInformalidade();` dentro de `selectCity()` |
| `site/app.js::renderInformalidade()` | `CITY.taxa_informalidade_pct` | `c = CITY` → `c.taxa_informalidade_pct` | WIRED | Linhas 156, 168-169: `const c = CITY`; `c.taxa_informalidade_pct` acessado |
| `site/app.js::buildRegionStrip()` | `DATA.totais.taxa_inf_media_rms` | `t = DATA.totais` | WIRED | Linha 58: `t.taxa_inf_media_rms != null ? ...` |
| `site/index.html #infSubcount` | nota fixa D-10 | div com id infSubcount; `$("infSubcount").innerHTML` | WIRED | HTML linha 39; JS linha 192: injetado sem condicional |

### Rastreamento de Fluxo de Dados (Nível 4)

| Artefato | Variável de Dado | Fonte | Produz Dados Reais | Status |
|----------|-----------------|-------|-------------------|--------|
| `site/app.js::renderInformalidade()` | `CITY.taxa_informalidade_pct` | `data.json → DATA.municipios` → `data/raw/censo/*.csv` via `ibge_informalidade.load()` | Sim — CSV commitado com dados do Censo IBGE 2022 SIDRA t/10261; 27 linhas reais | FLOWING |
| `site/app.js::renderInformalidade()` | `CITY.formais_residuos` | `data.json → DATA.municipios` → `data/raw/rais/*.csv` via `rais.load()` | Sim — CSV commitado com dados da RAIS 2023 via BigQuery; 27 linhas reais | FLOWING |
| `site/app.js::renderInformalidade()` | `DATA.meta.pnad_contexto_regional` | `data.json → meta` → `data/raw/pnad/*.csv` via `pnad_regional.load()` | Sim — CSV commitado; flag=estimativa, âmbito explícito | FLOWING |
| `site/app.js::buildRegionStrip()` | `DATA.totais.taxa_inf_media_rms` | `data.json → totais` → `transform.region_totals()` com média ponderada | Sim — calculado de taxa * total_ocupados dos 27 municípios; resultado=28,8% | FLOWING |

### Verificações Comportamentais

| Comportamento | Comando | Resultado | Status |
|---------------|---------|-----------|--------|
| `uv run obs build --region rms` exit 0 com informalidade | `uv run obs build --region rms` | `27/27 municípios com dado público; Informalidade média RMS: 28,8%` | PASS |
| 12 testes passando | `uv run pytest tests/test_pipeline.py -q` | `12 passed in 0.88s` | PASS |
| data.json com taxa_informalidade_pct em 27/27 municípios | `python3 -c "..."` | 0 municípios sem taxa_informalidade_pct | PASS |
| meta.pnad_contexto_regional.flag=estimativa | `python3 -c "..."` | flag=estimativa, ambito=Estado de São Paulo, sem municipio | PASS |
| totais.taxa_inf_media_rms presente | `python3 -c "..."` | 28,787982... (≈28,8%) | PASS |
| PNAD ausente em municipios[] | `python3 -c "..."` | pnad_contexto_regional em 0 de 27 municipios | PASS |
| Sorocaba: taxa=28,0%, formais=745, proxy≈84,2% | `python3 -c "..."` | taxa_informalidade_pct=28.0, formais_residuos=745, proxy=0.8418 | PASS |
| Alambari: formais=0, proxy=None/pendente | `python3 -c "..."` | formais_residuos=0, proxy_formalizacao=None, flag_proxy=pendente | PASS |

### Cobertura de Requisitos

| Requisito | Plano | Descrição | Status | Evidência |
|-----------|-------|-----------|--------|-----------|
| INFO-01 | 02-01, 02-02 | Fonte `sources/ibge_informalidade.py` lê ocupação informal (PNAD/Censo) por município | SATISFEITO | `ibge_informalidade.py` + CSV censo existem; load() retorna 27 linhas com taxa real |
| INFO-02 | 02-01, 02-02 | Proxy de formalização (RAIS/CAGED vs. cooperados) calculado | SATISFEITO | `rais.py` + CSV rais; `transform.py` D-06/D-07; data.json com proxy_formalizacao+flag_proxy por município |
| INFO-03 | 02-03 | Painel mostra card/seção de informalidade por município, com flag de qualidade, separado de estimativa | SATISFEITO (verificação visual pendente) | `index.html` slots; `app.js` renderInformalidade() com 3 KPIs e tags; section posicionada após baseline, antes do simulador |
| INFO-04 | 02-03 | Nota explícita de subcontagem da população catadora exibida no painel | SATISFEITO (verificação visual pendente) | `app.js` linha 192: nota D-10 injetada sem condicional; slot HTML com display:block e sem hidden |

Não há requisitos órfãos: INFO-01..04 todos declarados e implementados.

### Anti-Padrões Encontrados

Nenhum. Nenhum marcador TBD/FIXME/XXX nos arquivos modificados. Nenhum stub silencioso: `refresh()` levanta `NotImplementedError` documentado explicitamente (comportamento esperado e documentado). Nenhum retorno de lista/objeto vazio sem fetch: `load()` retorna DataFrame vazio apenas como fallback de CI sem arquivos CSV (correto).

### Verificação Visual Necessária

#### 1. Verificação visual completa do painel

**Teste:** Rodar `cd site && python -m http.server 8080`, abrir `http://localhost:8080` no navegador.
1. Verificar que o region-strip exibe célula "Informalidade média RMS" com valor ~28,8%
2. Selecionar "Sorocaba": seção "Informalidade do trabalho no município" deve aparecer com tag "Censo 2022", taxa ~28,0% (real), formais=745 (real), proxy ~84,2% (real)
3. Selecionar "Alambari" ou "Jumirim": taxa com tag real, formais=0 com tag real, grau formalização com tag pendente
4. Nota D-10 deve estar sempre visível em todas as seleções, sem botão de colapso
5. Contexto PNAD deve exibir "Estado de SP (estimativa regional)" com tag "estimativa" — nunca atribuído ao município selecionado
6. Tags da seção "Linha de base do município" acima devem continuar funcionando

**Esperado:** Todos os itens acima visíveis e corretos.
**Por que humano:** Renderização DOM, estilo visual, posicionamento de seções e interação de navegação não são verificáveis por grep ou execução Python. O checkpoint:human-verify do plano 02-03 foi aprovado pelo usuário durante a execução, mas esta verificação de fase é independente.

---

## Resumo dos Gaps

Nenhum gap de código encontrado. Todos os 4 must-haves estão VERIFICADOS no codebase com evidência direta (arquivos, execução de testes, inspeção de data.json).

O status `human_needed` reflete exclusivamente que a renderização visual do painel no navegador (INFO-03 e INFO-04) requer inspeção humana para confirmação de fase independente. O checkpoint:human-verify do plano 02-03 foi marcado como "APROVADO pelo usuário" no SUMMARY, mas este verifier não pode aceitar o relato do SUMMARY como evidência de verificação independente de fase — a verificação visual precisa ser feita de novo ou o aprovador original precisa confirmar.

---

_Verificado: 2026-06-23_
_Verificador: Claude (gsd-verifier)_
