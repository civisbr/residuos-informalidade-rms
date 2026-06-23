---
phase: 01-baseline-real-da-rms
plan: 02
subsystem: pipeline
tags: [snis, scraping, serie-historica, ingestao, baseline, rms, refresh]
dependency_graph:
  requires: [composicao_organico-por-municipio, gravimetria-sorocaba-travada-em-teste]
  provides: [snis-rms-25-municipios-real, baseline-rms-27-27-real, scraper-snis-serie-historica]
  affects: [data/raw/snis/snis_rms_sp.csv, scripts/scrape_snis.py, tests/test_pipeline.py, site/data.json, pyproject.toml]
tech_stack:
  added: [requests (dev dependency), basedosdados (dev — beco sem saída)]
  patterns: [engenharia reversa Yii/jqGrid, getGridConfig polling assíncrono, mapeamento por colModel, sessão requests com X-Requested-With]
key_files:
  created:
    - scripts/scrape_snis.py
    - data/raw/snis/snis_rms_sp.csv
  modified:
    - tests/test_pipeline.py
    - scripts/refresh_snis.md
    - scripts/fetch_snis.py
    - site/data.json
    - pyproject.toml
    - uv.lock
decisions:
  - "Caminho do dado mudou: BigQuery/Base dos Dados é beco sem saída (BD só tem SNIS água/esgoto, não resíduos). Scraping da Série Histórica oficial é a fonte real."
  - "fk_glossario sem prefixo 'xxx'; campos do form Yii-prefixados ShMunicipios[...]; cod_mun = IBGE de 6 dígitos; colunas vêm em ordem do colModel (alfabética), não de envio."
  - "rsu_t_ano = CO116+CO117+CO142+CS048 (conforme plano); cada componente citado na fonte para auditabilidade."
  - "cooperados deixado null: SNIS-RS não tem campo de cooperados confiável (CA002/CA003 ambíguos, ex. Sorocaba ca003=1.78). Honra regra sagrada (não inventar)."
  - "D-11 reinterpretado: scraper trouxe dado para os 25 -> 0 pendentes. Teste passou a travar real.height >= 25, mantendo o invariante pend.rsu null."
metrics:
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_created: 2
  files_modified: 6
---

# Phase 1 Plan 2: Ingestão SNIS dos 25 municípios da RMS via scraping Summary

**One-liner:** Os 27 municípios da RMS têm dado SNIS-RS real (2022): os 25 restantes
foram raspados da Série Histórica oficial via `scripts/scrape_snis.py` (engenharia
reversa do backend jqGrid), cada linha citando seus campos SNIS e a data de download;
build 27/27 sem nenhum número inventado, testes verdes.

## What Was Built

### Desvio de abordagem: o checkpoint humano virou scraper automatizado

O plano original (Task 1) era um **checkpoint humano** (download manual do portal
SNIS). Antes desta sessão, tentou-se a Base dos Dados (BigQuery) — descartada porque
a BD **não tem o SNIS de resíduos sólidos** (só água/esgoto em `br_mdr_snis`). A
pedido do usuário, o caminho passou a ser **scraping da Série Histórica oficial**, o
que resultou num script automatizado reutilizável (semente do `refresh()` da Fase 4).

### Task 1 (substituída) — `scripts/scrape_snis.py`

Engenharia reversa do app Yii + jqGrid em `app4.cidades.gov.br/serieHistorica`:

- **Controlador**: `consolidadoMunicipio` com `tipo_info=3` (resíduos sólidos).
- **Sessão**: GET `municipio/index` → POST `consolidadoMunicipio/index` `{ajax,action}`
  (header `X-Requested-With: XMLHttpRequest`) — esse POST carrega o form e revela os
  nomes reais dos campos.
- **Campos** Yii-prefixados: `ShMunicipios[tipo_info|ano_ref|cod_mun|cod_fam_info|fk_glossario][]`.
- **cod_mun** = código IBGE de **6 dígitos** (sem dígito verificador); mapa nome→código
  via `getSelectOpt`.
- **fk_glossario** = id numérico do indicador **sem** o prefixo `xxx` da UI
  (CO116=39345, CO117=39178, CO142=39261, CS048=39115, CS026=39162, IN031_RS=39223,
  IN030_RS=39090, FN220=38502).
- **Fluxo**: `getGridConfig {starting=1}` → **polling** de `getGridConfig` até a
  resposta conter `colModel` (endpoint assíncrono) → `getGridData` (paginado, `rows`
  do `rowList`) → linhas mapeadas pelo **nome de coluna do colModel** (a ordem é
  alfabética por código SNIS, não a de envio).

### Task 2 — Ingestão, integridade e teste

- `data/raw/snis/snis_rms_sp.csv`: 25 municípios (exceto Sorocaba e Porto Feliz, já no
  sample), todos `qualidade=real`, ano 2022. `rsu_t_ano = CO116+CO117+CO142+CS048`;
  `reciclado_t_ano=CS026`; `reciclado_pct=IN031_RS`; `coleta_seletiva_pop_pct=IN030_RS`
  (null onde o SNIS não reportou); `custo_mensal_rs=FN220/12`. `cooperados` null
  (sem campo confiável). Cada `fonte` lista os componentes e a data de download.
- `tests/test_pipeline.py`: a asserção D-11 `pend.height >= 20` (cenário de download
  manual incompleto) foi substituída por `real.height >= 25`, refletindo a realidade
  pós-scraping. O invariante sagrado `pend["rsu_t_ano"].null_count() == pend.height`
  foi mantido.
- `requests` adicionado como dev dependency.

## Verification Results

```
✓ uv run python scripts/scrape_snis.py --build --region rms --exclude sorocaba "porto feliz"
  → 25 municípios: 25 com dado real, 0 pendentes (ano 2022)

✓ uv run obs build --region rms
  → site/data.json — RMS: 27/27 municípios com dado público
  → RSU total: 637.200 t/ano · orgânico: 318.132 t/ano

✓ Integridade: total=27 | pendentes=0 | inventados=0 | com dado sem fonte=0

✓ uv run pytest -q → 3 passed
```

## Deviations from Plan

### Fonte do dado: BigQuery → scraping da Série Histórica (mudança de caminho)

- **Issue:** O plano previa download manual; a tentativa via Base dos Dados falhou
  (BD não tem resíduos sólidos, só água/esgoto).
- **Fix:** Scraper automatizado da Série Histórica oficial (`scrape_snis.py`),
  escolhido pelo usuário. Resultado é reproduzível e reutilizável (refresh).
- **Bônus:** entrega antecipa parte de GEN-02 (Fase 4) — a semente do `refresh()`.

### 0 pendentes em vez de ~20 (resultado melhor que o planejado)

- **Situação:** O plano assumia que o download manual deixaria muitos municípios
  pendentes (`pend.height >= 20`). O scraper trouxe dado para os 25 → **0 pendentes**.
- **Resultado:** Teste ajustado para `real.height >= 25`. Os 27/27 têm dado real.

### cooperados deixado null (integridade)

- **Situação:** O plano (D-07) previa preencher `cooperados` "só se o SNIS tiver".
- **Decisão:** O SNIS-RS não tem campo de cooperados confiável (CA002/CA003 são
  ambíguos — Sorocaba retornou ca003=1.78, fracionário). Para não inventar número,
  `cooperados` fica null em todos os raspados. Porto Feliz mantém 17 (do PMGIRS).

## Known Stubs

`scripts/fetch_snis.py` (BigQuery) permanece como referência mas é um beco sem saída
para resíduos (documentado no topo do arquivo e em `refresh_snis.md`). `basedosdados`
ficou como dev dependency; pode ser removido num cleanup da Fase 4.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: resolved T-02-01 | scripts/scrape_snis.py | Pós-ingestão: 0 inventados, 0 com dado sem fonte; invariante pend.rsu null travado em teste |
| threat_flag: resolved T-02-02 | data/raw/snis/snis_rms_sp.csv | custo_mensal_rs documenta FN220/12 na fonte de cada linha |
| threat_flag: resolved T-02-03 | scripts/scrape_snis.py | cooperados null (não autodeclarado como total); fonte cita "tratar como piso" |
| threat_flag: resolved T-02-04 | scripts/scrape_snis.py | Filtro tipo_info=3 + UF SP + cod_mun por código IBGE evita homônimos |

## Self-Check: PASSED

- [x] `scripts/scrape_snis.py` existe e roda (`--build`)
- [x] `data/raw/snis/snis_rms_sp.csv` existe com 25 municípios reais
- [x] `uv run obs build --region rms`: 27/27 municípios, exit 0
- [x] `site/data.json`: 27 municípios; 0 inventados; 0 com dado sem fonte
- [x] `tests/test_pipeline.py`: `real.height >= 25`; invariante pend.rsu null mantido
- [x] `uv run pytest -q`: 3 passed
- [x] `data/raw/snis/snis_rs_sample.csv` intocado (Sorocaba 2024 + Porto Feliz 2015)
