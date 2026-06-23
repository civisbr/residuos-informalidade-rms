---
phase: 02-camada-de-informalidade
plan: "01"
subsystem: pipeline/sources
tags: [fontes-offline, informalidade, censo-2022, rais-2023, pnad, testes]
dependency_graph:
  requires: []
  provides:
    - pipeline/sources/ibge_informalidade.py::load()
    - pipeline/sources/rais.py::load()
    - pipeline/sources/pnad_regional.py::load()
    - data/raw/censo/censo_informalidade_rms.csv
    - data/raw/rais/rais_residuos_rms_sp.csv
    - data/raw/pnad/pnad_sp_informalidade.csv
  affects:
    - pipeline/transform.py (join ponto previsto — plano 02-02)
    - tests/test_pipeline.py
tech_stack:
  added: []
  patterns:
    - SCHEMA + load() offline + refresh(NotImplementedError) — padrão espelhado de snis.py/ibge.py
    - slug(municipio) como chave de junção (não codigo_ibge)
    - Polars concat vertical_relaxed + unique por key
key_files:
  created:
    - data/raw/censo/censo_informalidade_rms.csv
    - data/raw/rais/rais_residuos_rms_sp.csv
    - data/raw/pnad/pnad_sp_informalidade.csv
    - pipeline/sources/ibge_informalidade.py
    - pipeline/sources/rais.py
    - pipeline/sources/pnad_regional.py
  modified:
    - tests/test_pipeline.py
decisions:
  - "D-01 respeitado: Censo 2022 é a base real dos 27 municípios (flag real)"
  - "D-02 respeitado: PNAD sem coluna municipio, vai em meta.pnad_contexto_regional"
  - "D-07 testado: proxy=pendente quando formais=0 E cooperados=null"
  - "Chave de junção: slug(municipio) = key, NÃO codigo_ibge"
  - "RAIS 0 é dado real: csv já inclui as linhas com formais_residuos=0"
metrics:
  duration: "~5 minutos"
  completed: "2026-06-23"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
requirements_satisfied:
  - INFO-01
  - INFO-02
---

# Phase 02 Plan 01: Fontes offline de informalidade (Censo/RAIS/PNAD) Summary

Três módulos de fonte offline + três CSVs verificados + seis testes de sanidade cobrindo INFO-01/INFO-02 e as invariantes D-06/D-07, seguindo o padrão SCHEMA+load()+refresh(NotImplementedError) do projeto.

## What Was Built

### CSVs de Snapshot (dados verificados via API ao vivo — 2026-06-23)

**data/raw/censo/censo_informalidade_rms.csv**
- 27 linhas, uma por município da RMS
- Colunas: municipio, uf, codigo_ibge, total_ocupados, informais, taxa_informalidade_pct, ano_censo, fonte
- Fonte: Censo Demográfico 2022, IBGE, SIDRA t/10261, 5 componentes IBGE de informalidade
- Taxas variam de 13,1% (Jumirim) a 43,1% (Ibiúna); Sorocaba = 28,0%

**data/raw/rais/rais_residuos_rms_sp.csv**
- 27 linhas com formais_residuos (Int64); Alambari=0, Alumínio=0, Jumirim=0, etc.
- Fonte: RAIS 2023 via Base dos Dados BigQuery; 9 CNAEs do setor de resíduos
- Zero = ausência de estabelecimento formal no setor (não dado faltante)

**data/raw/pnad/pnad_sp_informalidade.csv**
- 1 linha: SP, 2026T1, 30.0%, flag=estimativa, ambito=Estado de São Paulo
- SEM coluna municipio — invariante D-02

### Módulos Python

**pipeline/sources/ibge_informalidade.py**
- RAW = data/raw/censo; SCHEMA com 8 campos; RMS_IBGE_CODES (27 códigos de 7 dígitos)
- load(): glob + concat + dedup por ano_censo descrescente + key via slug(municipio)
- refresh(): NotImplementedError com URL SIDRA e instrução para scripts/fetch_censo.py

**pipeline/sources/rais.py**
- RAW = data/raw/rais; SCHEMA com 6 campos; WASTE_CNAES (9 CNAEs verificados)
- load(): mesmo padrão; dedup por ano; key via slug(municipio)
- refresh(): NotImplementedError com SQL canônico BigQuery

**pipeline/sources/pnad_regional.py**
- RAW = data/raw/pnad; SCHEMA sem coluna municipio (invariante de design D-02)
- load(): retorna o DataFrame do CSV diretamente (sem key — dado não é por município)
- refresh(): NotImplementedError com URL SIDRA t/4093

### Testes (tests/test_pipeline.py)

6 novos testes adicionados ao final do arquivo existente:
1. test_informalidade_censo_27_municipios — 27 linhas, taxa sem null, coluna key
2. test_pnad_nao_por_municipio — sem coluna municipio, flag=estimativa, âmbito=Estado de São Paulo
3. test_rais_load — 27 linhas, formais_residuos sem null, Alambari/Jumirim=0
4. test_proxy_pendente_edge_case — D-07: proxy=null quando formais=0 e cooperados=null
5. test_proxy_formalizacao_calculo — D-06: proxy=100/150≈0.6667 com flag=real
6. test_informalidade_pendente_honesto — invariante sagrada: taxa null → flag=pendente

Resultado: `uv run pytest -q` → 9 passed (3 originais + 6 novos)

## Deviations from Plan

None — plano executado exatamente como especificado.

## Threat Mitigations Applied

| Threat | Mitigação |
|--------|-----------|
| T-02-01 (Adulteração CSV) | SCHEMA Polars com tipos explícitos; CSV no git (auditável) |
| T-02-02 (Repúdio — sem fonte) | Coluna fonte obrigatória em cada CSV e DataFrame |
| T-02-05 (PNAD atribuída a município) | SCHEMA de pnad_regional sem coluna municipio; teste test_pnad_nao_por_municipio |
| T-02-06 (número inventado) | test_proxy_pendente_edge_case + test_informalidade_pendente_honesto |

## Known Stubs

Nenhum stub. Os três módulos têm dados reais verificados. `refresh()` é explicitamente NotImplementedError (documentado, não stub silencioso).

## Self-Check: PASSED

Arquivos criados:
- data/raw/censo/censo_informalidade_rms.csv: FOUND
- data/raw/rais/rais_residuos_rms_sp.csv: FOUND
- data/raw/pnad/pnad_sp_informalidade.csv: FOUND
- pipeline/sources/ibge_informalidade.py: FOUND
- pipeline/sources/rais.py: FOUND
- pipeline/sources/pnad_regional.py: FOUND

Commits:
- 3b45012: feat(02-01) CSVs e módulos de fonte
- 29e1943: test(02-01) testes INFO-01/INFO-02

Testes: 9 passed (uv run pytest -q)
Build: uv run obs build --region rms → 27/27 municípios, sem regressão
