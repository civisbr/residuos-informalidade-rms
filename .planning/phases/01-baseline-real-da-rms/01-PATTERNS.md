# Phase 1: Baseline real da RMS - Pattern Map

**Mapped:** 2026-06-21
**Files analyzed:** 5 new/modified files
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `data/raw/snis/snis_rms_2022.csv` (new) | data | batch / file-I/O | `data/raw/snis/snis_rs_sample.csv` | exact |
| `pipeline/sources/snis.py` (modify SCHEMA) | source adapter | batch / file-I/O | `pipeline/sources/snis.py` (self) | exact |
| `pipeline/transform.py` (modify build_region) | transform | batch / transform | `pipeline/transform.py` (self) — padrão `pl.when` existente | exact |
| `pipeline/render.py` (add composicao_fonte passthrough) | renderer | batch / transform | `pipeline/render.py` (self) — padrão `r["fonte"]` existente | exact |
| `tests/test_pipeline.py` (update assertions) | test | batch / offline | `tests/test_pipeline.py` (self) | exact |

---

## Pattern Assignments

---

### `data/raw/snis/snis_rms_2022.csv` (data file, batch / file-I/O)

**Analog:** `data/raw/snis/snis_rs_sample.csv`

**Existing file structure** (linhas 1-3):
```csv
municipio,uf,ano,rsu_t_ano,reciclado_t_ano,reciclado_pct,coleta_seletiva_pop_pct,cooperados,custo_mensal_rs,qualidade,fonte
Sorocaba,SP,2024,228000,3960,2.0,14.8,140,12500000,real,"Prefeitura de Sorocaba (PPP RSU; Sec. Serviços Públicos); Câmara Municipal; Inst. Água e Saneamento"
Porto Feliz,SP,2024,17160,,,,,,estimativa,"Estimativa: pop x 0,9 kg/hab/dia. Reciclado/cooperados a extrair do PMGIRS 2017 (SMA-SP) + SNIS"
```

**Colunas obrigatórias no SCHEMA atual** (`pipeline/sources/snis.py` linhas 20-26):
```
municipio, uf, ano, rsu_t_ano, reciclado_t_ano, reciclado_pct,
coleta_seletiva_pop_pct, cooperados, custo_mensal_rs, qualidade, fonte
```

**Novas colunas a adicionar neste arquivo** (D-01, D-03):
```
composicao_organico, composicao_fonte
```

**Padrão das três categorias de linha a replicar:**

```csv
# Linha com dado real completo
Salto,SP,2022,XXXXX,XXX,X.X,X.X,XXX,XXXXXXX,real,"SNIS-RS 2022 — CO116+CO117+CO142+CS048; FN220/12=custo_mensal; download YYYY-MM-DD"

# Linha com dado real parcial (alguns campos ausentes)
Itu,SP,2022,XXXXX,,,,,,real,"SNIS-RS 2022 — CO116+CO117 disponíveis; reciclado/cooperados não reportados"

# Linha pendente (município não participou)
Jumirim,SP,2022,,,,,,,,pendente,"SNIS-RS 2022 — município não participou da amostra"
```

**Coluna `composicao_organico` — regra de preenchimento (D-01):**
- Sorocaba: `0.48` (gravimetria PMGIRS Tomo 2, p.27)
- Todos os demais municípios: vazio (null) → usa fallback global 0.51 em `transform.py`

**Coluna `composicao_fonte` — regra de preenchimento (D-03):**
- Sorocaba: `"PMGIRS Sorocaba — SHS Consultoria/Prefeitura de Sorocaba, 2014. Gravimetria: 48% orgânico (Tomo 2, p. 27)"`
- Municípios com dado SNIS mas sem gravimetria local: `"média Brasil (estimativa)"`
- Municípios pendentes: vazio (null) ou `"média Brasil (estimativa)"` — irrelevante pois `organico_t_ano` será null

**Regras de integridade (regra sagrada, D-08, D-09):**
- Nome do município DEVE bater com `config/regions.yml` após `slug()`. Verificar com: `uv run obs build --region rms`
- Filtrar export SNIS por UF = SP para evitar homônimos entre estados
- `custo_mensal_rs` = `FN220 / 12` — documentar conversão na coluna `fonte` (D-10)
- Campo `cooperados` só preencher se o SNIS tiver o número; caso contrário, deixar vazio (null) (D-07)
- Quando preencher `cooperados`, a `fonte` da linha deve incluir a nota `"SNIS autodeclarado — tratar como piso"` (D-07)

**Não apagar o arquivo existente:** `data/raw/snis/snis_rs_sample.csv` permanece. O novo arquivo é adicional; `snis.load()` concatena automaticamente todos os `*.csv`.

---

### `pipeline/sources/snis.py` (source adapter, batch / file-I/O)

**Analog:** `pipeline/sources/snis.py` (arquivo existente, self-pattern)

**SCHEMA atual** (linhas 20-26) — copiar e estender:
```python
SCHEMA = {
    "municipio": pl.String, "uf": pl.String, "ano": pl.Int64,
    "rsu_t_ano": pl.Float64, "reciclado_t_ano": pl.Float64,
    "reciclado_pct": pl.Float64, "coleta_seletiva_pop_pct": pl.Float64,
    "cooperados": pl.Float64, "custo_mensal_rs": pl.Float64,
    "qualidade": pl.String, "fonte": pl.String,
}
```

**Extensão necessária** — adicionar ao final do dict (D-01, D-03, cláusula "Claude's Discretion"):
```python
SCHEMA = {
    "municipio": pl.String, "uf": pl.String, "ano": pl.Int64,
    "rsu_t_ano": pl.Float64, "reciclado_t_ano": pl.Float64,
    "reciclado_pct": pl.Float64, "coleta_seletiva_pop_pct": pl.Float64,
    "cooperados": pl.Float64, "custo_mensal_rs": pl.Float64,
    "qualidade": pl.String, "fonte": pl.String,
    # por-município: composição orgânica local (null = usa fallback global em transform.py)
    "composicao_organico": pl.Float64,
    "composicao_fonte": pl.String,
}
```

**`load()` existente — NÃO MODIFICAR A LÓGICA** (linhas 29-41):
```python
def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    # mantém o ano mais recente por município
    df = (
        df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
          .sort("ano", descending=True)
          .unique(subset=["key"], keep="first")
    )
    return df
```

`how="vertical_relaxed"` já tolera CSVs com colunas ausentes (colunas extras ficam null). A única mudança obrigatória neste arquivo é o SCHEMA dict — a `load()` absorve os novos campos automaticamente.

**Importações a preservar** (linhas 12-17):
```python
from __future__ import annotations
from pathlib import Path
import polars as pl

from .base import slug
```

---

### `pipeline/transform.py` (transform, batch / transform)

**Analog:** `pipeline/transform.py` (self) — padrão `pl.when(...).then(...).otherwise(...)` já existente nas linhas 28-35.

**Assinatura da função — NÃO ALTERAR** (linhas 13-15):
```python
def build_region(municipios: list[dict], ibge: pl.DataFrame, snis: pl.DataFrame,
                 coef: dict) -> pl.DataFrame:
    org_pct = coef["composicao"]["organico"]
```

**Bloco `with_columns` atual** (linhas 28-36) — padrão a estender:
```python
df = df.with_columns([
    # fração orgânica estimada do RSU (feedstock do BSF)
    (pl.col("rsu_t_ano") * org_pct).alias("organico_t_ano"),
    # quanto vai pro aterro hoje
    (pl.col("rsu_t_ano") * (1 - pl.col("reciclado_pct").fill_null(0) / 100)).alias("aterro_t_ano"),
    # flag de qualidade: tem dado de RSU? real/estimativa : pendente
    pl.when(pl.col("rsu_t_ano").is_null()).then(pl.lit("pendente"))
      .otherwise(pl.col("qualidade").fill_null("real")).alias("flag"),
])
```

**Substituição obrigatória para `organico_t_ano`** (D-02) — copiar o padrão `pl.when` existente:
```python
df = df.with_columns([
    # fração orgânica: usa gravimetria local se disponível, senão média Brasil
    pl.when(pl.col("composicao_organico").is_not_null())
      .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
      .otherwise(pl.col("rsu_t_ano") * org_pct)
      .alias("organico_t_ano"),
    # quanto vai pro aterro hoje
    (pl.col("rsu_t_ano") * (1 - pl.col("reciclado_pct").fill_null(0) / 100)).alias("aterro_t_ano"),
    # flag de qualidade: tem dado de RSU? real/estimativa : pendente
    pl.when(pl.col("rsu_t_ano").is_null()).then(pl.lit("pendente"))
      .otherwise(pl.col("qualidade").fill_null("real")).alias("flag"),
])
```

**Coluna `composicao_fonte` vem do join do SNIS** — passthrough automático após o `.join()` nas linhas 23-26 (nenhuma lógica adicional necessária em `build_region`; o campo chega do CSV via `snis.drop("municipio", "uf")`).

**O join existente** (linhas 23-26) — NÃO ALTERAR:
```python
df = (
    base.join(ibge.select("key", "codigo_ibge", "populacao", "fonte_pop"), on="key", how="left")
        .join(snis.drop("municipio", "uf"), on="key", how="left")
)
```

`snis.drop("municipio", "uf")` mantém todas as colunas do SNIS exceto `municipio` e `uf`. Como `composicao_organico` e `composicao_fonte` vão estar no SCHEMA e no CSV, elas aparecem no DataFrame após o join automaticamente.

**Importações a preservar** (linhas 1-5):
```python
from __future__ import annotations
import polars as pl

from .sources.base import slug
```

---

### `pipeline/render.py` (renderer, batch / transform)

**Analog:** `pipeline/render.py` (self) — padrão `r["fonte"]` existente nas linhas 22-28.

**Bloco de construção do dict por município** (linhas 18-29) — padrão a estender:
```python
for r in df.iter_rows(named=True):
    municipios.append({
        "nome": r["nome"], "uf": r["uf"], "subregiao": r["subregiao"],
        "codigo_ibge": r["codigo_ibge"], "populacao": r["populacao"],
        "ano": r["ano"], "flag": r["flag"], "fonte": r["fonte"],
        "rsu_t_ano": r["rsu_t_ano"], "organico_t_ano": r["organico_t_ano"],
        "aterro_t_ano": r["aterro_t_ano"], "reciclado_t_ano": r["reciclado_t_ano"],
        "reciclado_pct": r["reciclado_pct"],
        "coleta_seletiva_pop_pct": r["coleta_seletiva_pop_pct"],
        "cooperados": r["cooperados"],
        "custo_mensal_rs": r["custo_mensal_rs"],
    })
```

**Extensão para incluir `composicao_fonte`** (D-03 — para exibição futura no painel):
```python
for r in df.iter_rows(named=True):
    municipios.append({
        "nome": r["nome"], "uf": r["uf"], "subregiao": r["subregiao"],
        "codigo_ibge": r["codigo_ibge"], "populacao": r["populacao"],
        "ano": r["ano"], "flag": r["flag"], "fonte": r["fonte"],
        "rsu_t_ano": r["rsu_t_ano"], "organico_t_ano": r["organico_t_ano"],
        "aterro_t_ano": r["aterro_t_ano"], "reciclado_t_ano": r["reciclado_t_ano"],
        "reciclado_pct": r["reciclado_pct"],
        "coleta_seletiva_pop_pct": r["coleta_seletiva_pop_pct"],
        "cooperados": r["cooperados"],
        "custo_mensal_rs": r["custo_mensal_rs"],
        "composicao_fonte": r.get("composicao_fonte"),  # procedência da composição orgânica
    })
```

**Importações a preservar** (linhas 1-11) — NÃO ALTERAR:
```python
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
import polars as pl

from . import model
```

---

### `tests/test_pipeline.py` (test, batch / offline)

**Analog:** `tests/test_pipeline.py` (self) — padrão de asserção existente.

**Teste existente `test_build_offline_gera_dados`** (linhas 16-28):
```python
def test_build_offline_gera_dados():
    import os
    os.chdir(ROOT)
    df = transform.build_region(REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT), COEF)
    assert df.height == 27
    # Sorocaba tem dado real
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag"] == "real"
    assert soro["rsu_t_ano"] == 228000
    # pendentes existem e não inventam número
    pend = df.filter(df["flag"] == "pendente")
    assert pend.height >= 20
    assert pend["rsu_t_ano"].null_count() == pend.height
```

**Mudanças obrigatórias (D-11, D-12):**

1. Atualizar `assert pend.height >= 20` para refletir o novo número real de pendentes após ingestão (D-11). O número exato depende de quantos dos 25 municípios restantes têm dado no SNIS; o executor deve verificar após o build e ajustar o limiar. Se N municípios ficaram pendentes, usar `assert pend.height == N` ou `assert pend.height >= N` com o piso honesto.

2. Adicionar asserção que trava o uso da gravimetria local de Sorocaba (D-12):
```python
# Sorocaba usa gravimetria local 0.48, não o global 0.51
assert soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)
```

**Import a adicionar no topo** (necessário para `pytest.approx`):
```python
import pytest
```

**Padrão completo do teste atualizado** — copiar estrutura existente e inserir linha nova após `assert soro["rsu_t_ano"] == 228000`:
```python
def test_build_offline_gera_dados():
    import os
    os.chdir(ROOT)
    df = transform.build_region(REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT), COEF)
    assert df.height == 27
    # Sorocaba tem dado real
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag"] == "real"
    assert soro["rsu_t_ano"] == 228000
    assert soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)  # gravimetria local
    # pendentes existem e não inventam número
    pend = df.filter(df["flag"] == "pendente")
    assert pend.height >= <N>    # atualizar após o build com o número real
    assert pend["rsu_t_ano"].null_count() == pend.height
```

**Invariante imutável** — esta asserção NÃO deve mudar:
```python
assert pend["rsu_t_ano"].null_count() == pend.height
```
Garante que nenhum pendente tem número inventado. É a implementação de teste da regra sagrada.

---

## Shared Patterns

### Padrão `pl.when(...).then(...).otherwise(...)`
**Source:** `pipeline/transform.py` linhas 34-35
**Apply to:** Toda lógica condicional de derivação de indicadores em `transform.py`
```python
pl.when(pl.col("rsu_t_ano").is_null()).then(pl.lit("pendente"))
  .otherwise(pl.col("qualidade").fill_null("real")).alias("flag")
```
Replicar exatamente para `organico_t_ano`:
```python
pl.when(pl.col("composicao_organico").is_not_null())
  .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
  .otherwise(pl.col("rsu_t_ano") * org_pct)
  .alias("organico_t_ano")
```

### Padrão de SCHEMA em source adapter
**Source:** `pipeline/sources/snis.py` linhas 20-26
**Apply to:** Qualquer extensão do SCHEMA de `snis.py`
```python
SCHEMA = {
    "coluna": pl.TipoDado,   # comentário de propósito
    ...
}
```
Tipos Polars usados no projeto: `pl.String`, `pl.Int64`, `pl.Float64`. Novos campos opcionais (podem ser null) usam `pl.Float64` (numérico) ou `pl.String` (texto).

### Padrão de passthrough de campo em render.py
**Source:** `pipeline/render.py` linhas 18-29
**Apply to:** Todo novo campo a incluir no `data.json`
```python
"campo_novo": r["campo_novo"],      # se sempre presente
"campo_novo": r.get("campo_novo"),  # se pode estar ausente (seguro para retrocompatibilidade)
```

### Padrão de integridade — coluna `fonte` obrigatória
**Source:** `data/raw/snis/snis_rs_sample.csv` linha 2; CONTEXT.md D-08
**Apply to:** Toda linha com dado em `data/raw/snis/*.csv`
- Linha com dado real: `fonte` deve citar a fonte primária (SNIS-RS ANO, campo, data de download)
- Linha pendente: `fonte` deve citar o motivo (`"SNIS-RS 2022 — município não participou"`)
- Campo `custo_mensal_rs`: incluir na `fonte` a nota `"FN220/12"` para rastreabilidade

### Padrão de junção por slug
**Source:** `pipeline/sources/base.py` linhas 6-14; `pipeline/transform.py` linhas 23-26
**Apply to:** Qualquer novo CSV em `data/raw/snis/`
```python
# base.py — NÃO reimplementar
def slug(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()
```
O nome do município no CSV precisa produzir o mesmo slug que o nome em `config/regions.yml`. Verificar com build após ingestão.

### Padrão de importação Python (ordem obrigatória)
**Source:** Todos os módulos de `pipeline/`
**Apply to:** Todo arquivo Python do projeto
```python
from __future__ import annotations    # sempre primeiro
# stdlib (pathlib, json, etc.)
# third-party (polars, yaml)
# internos relativos (from .sources.base import slug)
```

---

## No Analog Found

Nenhum arquivo sem análogo. Todos os arquivos desta fase têm padrão existente no codebase.

---

## Metadata

**Analog search scope:** `pipeline/`, `data/raw/snis/`, `tests/`, `config/`
**Files scanned:** 8 (snis.py, transform.py, render.py, base.py, test_pipeline.py, snis_rs_sample.csv, coefficients.yml, regions.yml)
**Pattern extraction date:** 2026-06-21
