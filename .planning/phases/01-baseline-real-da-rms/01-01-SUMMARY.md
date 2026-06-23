---
phase: 01-baseline-real-da-rms
plan: 01
subsystem: pipeline
tags: [snis, gravimetria, transform, render, tests, porto-feliz, sorocaba, baseline]
dependency_graph:
  requires: []
  provides: [composicao_organico-por-municipio, composicao_fonte-em-data.json, gravimetria-sorocaba-travada-em-teste]
  affects: [pipeline/sources/snis.py, pipeline/transform.py, pipeline/render.py, tests/test_pipeline.py, data/raw/snis/snis_rs_sample.csv, site/data.json]
tech_stack:
  added: [pytest (dev dependency)]
  patterns: [pl.when(...).is_not_null().then(...).otherwise(...), r.get() para retrocompatibilidade, pdftotext para extração de PDF]
key_files:
  created: []
  modified:
    - pipeline/sources/snis.py
    - pipeline/transform.py
    - pipeline/render.py
    - tests/test_pipeline.py
    - data/raw/snis/snis_rs_sample.csv
    - site/data.json
    - pyproject.toml
    - uv.lock
decisions:
  - "D-12 implementado: pytest.approx(228000 * 0.48, rel=1e-3) trava gravimetria Sorocaba"
  - "D-02 implementado: pl.when(composicao_organico.is_not_null()) com fallback global 0.51"
  - "D-03 implementado: composicao_fonte passthrough via r.get() em render.py"
  - "Porto Feliz D-05/D-06: extração PMGIRS funcionou; qualidade=real com fonte citada (p.150)"
  - "D-11: pend.height >= 20 mantido; ajuste real no plano 02 após ingestão SNIS completa"
metrics:
  duration_seconds: 260
  completed_date: "2026-06-21"
  tasks_completed: 3
  files_modified: 8
---

# Phase 1 Plan 1: Gravimetria Sorocaba e extração PMGIRS Porto Feliz Summary

**One-liner:** Gravimetria Sorocaba 0.48 por-município via pl.when com fallback global 0.51; Porto Feliz extraído de PMGIRS 2017 (pdftotext): rsu=14213 t/ano, reciclado_pct=23.4%, cooperados=17 — ambos com flag real e fonte citada.

## What Was Built

### Task 1 — SCHEMA estendido + CSV atualizado (commit d9a1001)

Adicionados dois campos ao final do dict `SCHEMA` em `pipeline/sources/snis.py`:
- `composicao_organico: pl.Float64` — gravimetria local por-município (null = usa fallback global)
- `composicao_fonte: pl.String` — procedência da composição

Em `data/raw/snis/snis_rs_sample.csv`: novas colunas adicionadas ao header. Sorocaba preenchida com `composicao_organico=0.48` (PMGIRS Tomo 2, p.27) e fonte completa. Porto Feliz com null e "média Brasil (estimativa)". O `load()` absorveu os novos campos via `how="vertical_relaxed"` sem qualquer alteração de lógica. `config/coefficients.yml` intocado (0.51 permanece).

### Task 2 — transform.py e render.py (commit c5fb05d)

Em `pipeline/transform.py`: substituição da linha `(pl.col("rsu_t_ano") * org_pct).alias("organico_t_ano")` por `pl.when(pl.col("composicao_organico").is_not_null()).then(rsu * composicao_organico).otherwise(rsu * org_pct)`. Sorocaba: 228000 × 0.48 = 109440.0 t/ano. Porto Feliz: 14213 × 0.51 = 7248.63 t/ano.

Em `pipeline/render.py`: adicionado `"composicao_fonte": r.get("composicao_fonte")` ao dict de payload — usa `r.get()` para retrocompatibilidade com CSVs sem a coluna.

### Task 3 — Extração PMGIRS Porto Feliz + testes D-12 (commit 85ad007)

Extração autônoma bem-sucedida: `curl -L` baixou 26.4 MB do blob HTTPS; `pdftotext` extraiu 24.144 linhas de texto legível. Dados encontrados:

| Campo | Valor | Página | Fonte |
|-------|-------|--------|-------|
| RSU total | 14.213 t/ano | 67 | Tabela 04 — pesagem real no aterro sanitário terceirizado |
| reciclado_t_ano | 3.326 t/ano | 67 | Coop (13.633) + 11 recicladores particulares |
| reciclado_pct | 23,4% | 150 | "277.163 kg, ou seja, 23,4% do total" |
| cooperados | 17 | 150 | "A cooperativa possui 17 cooperados" |
| Gravimetria orgânico | 44,90% | 66 | Composição gravimétrica out/2015 (disponível mas não usada como composicao_organico — dado é de aterro, não RSU total) |

Porto Feliz mudou de `qualidade=estimativa` (rsu=17160 por estimativa de pop) para `qualidade=real` (rsu=14213 por pesagem real no aterro). Fonte cita PMGIRS Porto Feliz — SMA-SP, 2017.

Em `tests/test_pipeline.py`: adicionado `import pytest` e asserção D-12 `soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)`. Invariante sagrada `pend["rsu_t_ano"].null_count() == pend.height` intocada. `pend.height >= 20` mantida (25 pendentes atuais; ajuste no plano 02).

`pytest` instalado como dev dependency em `pyproject.toml`.

## Verification Results

```
✓ uv run obs build --region rms
  → site/data.json — Região Metropolitana de Sorocaba: 2/27 municípios com dado público
  → RSU total: 242.213 t/ano · orgânico: 116.689 t/ano
  → 25 municípios pendentes

✓ uv run pytest -q
  → 3 passed in 0.61s

✓ Sorocaba organico_t_ano = 109440.0 (228000 × 0.48)
✓ composicao_fonte presente: "PMGIRS Sorocaba — SHS Consultoria..."
✓ Porto Feliz qualidade = real; fonte cita PMGIRS p.150; cooperados = 17
✓ config/coefficients.yml intocado: composicao.organico = 0.51
```

## Deviations from Plan

### Auto-added: pytest como dev dependency (Rule 3 — blocker)

- **Found during:** Task 3 verification
- **Issue:** `uv run pytest` retornava `No module named pytest` — pytest não estava nas deps do projeto
- **Fix:** `uv add --dev pytest` — adicionado ao `[dependency-groups] dev` em pyproject.toml
- **Files modified:** pyproject.toml, uv.lock
- **Commit:** 85ad007

### Porto Feliz: extração bem-sucedida (resultado divergente do fallback planejado)

- **Situação:** O plano previa dois caminhos: extração funcionou OU manter estimativa. A extração funcionou.
- **Resultado:** `qualidade=real` com dados de pesagem real (aterro sanitário terceirizado), reciclagem e cooperados com número de página.
- **Nota:** A gravimetria orgânica de Porto Feliz (44.90%, p.66) foi identificada mas NÃO usada como `composicao_organico` — o dado se refere à composição dos resíduos dispostos no aterro (fração orgânica dos resíduos não desviados), não à gravimetria do RSU total. Usar 44.90% exigiria análise mais cuidadosa para garantir comparabilidade com Sorocaba (48%). Decisão: manter `composicao_organico=null` (fallback 0.51) e registrar como pendência.

## Known Stubs

Nenhum stub que impeça o objetivo do plano. Os 25 municípios pendentes são dados ausentes por design (aguardam ingestão do SNIS completo no plano 02), não stubs inventados — a invariante `pend["rsu_t_ano"].null_count() == pend.height` garante isso.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: resolved T-01-03 | tests/test_pipeline.py | Teste D-12 implementado: qualquer mudança em composicao_organico de Sorocaba quebra a suite |
| threat_flag: resolved T-01-04 | data/raw/snis/snis_rs_sample.csv | Porto Feliz qualidade=real com fonte citada e número de página; regra sagrada D-06 respeitada |

## Self-Check: PASSED

- [x] `pipeline/sources/snis.py` existe e contém `composicao_organico`
- [x] `pipeline/transform.py` existe e contém `pl.when(pl.col("composicao_organico").is_not_null())`
- [x] `pipeline/render.py` existe e contém `composicao_fonte`
- [x] `tests/test_pipeline.py` existe e contém `pytest.approx`
- [x] `site/data.json` existe e Sorocaba tem organico_t_ano=109440.0
- [x] Commits d9a1001, c5fb05d, 85ad007 existem
- [x] `uv run pytest -q`: 3 passed
- [x] `uv run obs build --region rms`: exit 0
