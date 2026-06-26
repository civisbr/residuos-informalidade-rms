---
status: partial
phase: 04-generalizar-para-qualquer-cidade-br
source: [04-VERIFICATION.md]
started: 2026-06-24T00:00:00Z
updated: 2026-06-24T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. ibge.refresh() — chamada de rede real (GEN-01)
expected: `uv run obs refresh-ibge --region rms` resolve os 27 municípios da RMS via `servicodados.ibge.gov.br/api/v1/localidades` + `apisidra.ibge.gov.br` (tabela 4714, Censo 2022) e faz upsert em `config/municipios.csv` com `fonte_pop="IBGE Censo 2022"`. Rodar uma segunda vez é no-op para linhas já preenchidas (idempotência D-06; git diff vazio na 2ª execução). Curadoria preservada (Sorocaba populacao=709000).
result: [pending]

### 2. Erro amigável com typo real (GEN-03 / D-09)
expected: renomear temporariamente "Sorocaba" → "Sorocab" em `config/regions.yml` e rodar `uv run obs refresh-ibge --region rms` — aparece em stderr "Município ... não encontrado no IBGE — você quis dizer ...?" (sugestão difflib), os demais municípios continuam, e os não-resolvidos são listados ao final. NUNCA stack trace.
result: [pending]

### 3. snis.refresh() — chamada de rede real (GEN-02)
expected: `uv run obs refresh-snis --region rms` faz scraping de `app4.cidades.gov.br/serieHistorica` e grava `data/raw/snis/snis_rms.csv`; `snis.load()` continua concatenando todos os CSVs da pasta. Município sem dado SNIS → linha `pendente` honesta (nunca chute).
result: [pending]

### 4. Fluxo end-to-end do terceiro (GEN-04)
expected: adicionar uma região nova ao `config/regions.yml` (só `nome`+`uf` por município) e rodar os 3 comandos do guia — `obs refresh-ibge --region X` → `obs refresh-snis --region X` → `obs build --region X` — gera `site/data.json` válido sem tocar em código. Informalidade/RAIS aparecem `pendente` fora da RMS (honestidade D-01/D-02).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
