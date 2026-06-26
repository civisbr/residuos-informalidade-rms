---
phase: "04-generalizar-para-qualquer-cidade-br"
plan: 4
subsystem: docs
tags: [readme, regions-yml, guia, contrato, d-10, d-03, honestidade]
dependency_graph:
  requires:
    - "04-01: obs refresh-ibge --region <chave> entregue"
    - "04-03: obs refresh-snis --region <chave> entregue"
  provides:
    - README.md com guia de 5 minutos (D-10)
    - config/regions.yml com contrato mínimo comentado (D-03)
  affects:
    - Terceiros que queiram gerar painel de outra região
tech_stack:
  added: []
  patterns:
    - Aviso honesto em blockquote Markdown (T-04-14 mitigado)
    - Campos OBRIGATÓRIO em comentário YAML (T-04-15 mitigado)
key_files:
  created: []
  modified:
    - README.md
    - config/regions.yml
decisions:
  - "D-10: guia de 4 passos no README (editar regions.yml, refresh-ibge, refresh-snis, build)"
  - "D-03: contrato mínimo formalizado como comentário em regions.yml — nome+uf OBRIGATÓRIO; subregiao+destaque+fonte opcionais"
  - "D-01/D-02: aviso honesto em blockquote que informalidade/RAIS ficam pendente fora da RMS"
metrics:
  duration_minutes: 5
  completed_date: "2026-06-24"
  tasks_completed: 1
  files_modified: 2
---

# Phase 04 Plan 04: Guia "5 minutos" no README e contrato mínimo em regions.yml Summary

Documentação de fechamento do GEN-04: guia de 4 passos no README com comandos reais (`obs refresh-ibge`, `obs refresh-snis`, `obs build`) e aviso honesto sobre informalidade/RAIS pendente fora da RMS; contrato mínimo de `regions.yml` formalizado como comentário YAML com campos OBRIGATÓRIOS explícitos.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1    | Guia 5 minutos no README e contrato mínimo em regions.yml | 27aa3f6 | README.md, config/regions.yml |

## What Was Built

### README.md — seção "Crie o painel da sua cidade em 5 minutos"

A seção placeholder de 4 linhas foi expandida para o guia completo de 4 passos (D-10):

1. **Declarar a região** — snippet YAML editável de `config/regions.yml` com campos `nome`, `uf`, `municipios` (mínimo)
2. **Resolver identidade (IBGE)** — `uv run obs refresh-ibge --region minha_regiao` com descrição do que faz (código IBGE + população Censo 2022 → `config/municipios.csv`)
3. **Baixar dados de resíduos (SNIS)** — `uv run obs refresh-snis --region minha_regiao` com descrição (`data/raw/snis/snis_minha_regiao.csv`)
4. **Gerar o painel** — `uv run obs build --region minha_regiao`

Seguido de blockquote de aviso honesto (D-01/D-02):
> **Aviso honesto:** informalidade e RAIS ficam `pendente` para regiões fora da RMS (Região Metropolitana de Sorocaba) — os dados de Censo 2022 e RAIS 2023 estão pré-carregados apenas para os 27 municípios da RMS. Um painel com resíduos reais e informalidade `pendente` é um painel **válido** — nunca inventamos número.

### config/regions.yml — contrato mínimo comentado

Bloco de comentário expandido de 6 linhas para 10 linhas com D-03 explícito:
- `nome` e `uf` marcados como **OBRIGATÓRIO** (nível região)
- `destaque` e `fonte` marcados como **opcional**
- Por município: `nome + uf` mínimo, `subregiao` opcional com nota "ausente = lista plana"
- Bloco da RMS (27 municípios, linhas 8-44) inteiramente preservado

## Verification Results

```
python -c "..." → README.md OK / config/regions.yml OK
uv run obs build --region rms → ✓ site/data.json — Região Metropolitana de Sorocaba: 27/27 municípios com dado público
uv run pytest -q → 23 passed in 0.58s

grep refresh-ibge README.md → 1
grep refresh-snis README.md → 1
grep pendente README.md → 3
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

Nenhum. O guia descreve comandos reais já entregues nos planos 04-01 e 04-03. Todos os 4 passos são executáveis pelo terceiro sem modificação de código.

## Threat Flags

Nenhum. As ameaças T-04-14 (induzir publicação de painel com dado fictício) e T-04-15 (omissão de campos obrigatórios em regions.yml) foram mitigadas conforme o threat model do plano:
- T-04-14: blockquote de aviso honesto visível na seção do guia
- T-04-15: marcação "OBRIGATÓRIO" explícita no comentário YAML de regions.yml

## Self-Check: PASSED

- [x] `README.md` contém "5 minutos", "refresh-ibge", "refresh-snis", "pendente", "informalidade"
- [x] `config/regions.yml` contém "OBRIGATÓRIO", "subregiao", "rms:", "Sorocaba"
- [x] Commit `27aa3f6` existe
- [x] `uv run pytest -q` → 23 passed
- [x] `uv run obs build --region rms` → 27/27
