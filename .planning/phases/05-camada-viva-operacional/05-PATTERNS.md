# Phase 5: Camada viva (operacional) - Pattern Map

**Mapped:** 2026-06-25
**Files analyzed:** 9 (2 new, 7 modified)
**Analogs found:** 9 / 9 (8 exact, 1 role-match)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pipeline/sources/operacao.py` | source (NEW) | file-I/O / batch | `pipeline/sources/snis.py` | exact (mesmo padrão `load()` glob+concat+`key`) |
| `data/raw/operacao/operacao_rms.csv` | data fixture (NEW) | file-I/O | `data/raw/snis/snis_rms_sp.csv` | exact (header + flag `qualidade`/`fonte`) |
| `pipeline/transform.py` | transform (MOD) | batch / transform | `transform.region_totals()` + `build_region()` | exact (junção por `key`, `group_by().agg()`) |
| `pipeline/render.py` | render (MOD) | transform → JSON | `render.to_payload()` | exact (nova chave de classe no dict) |
| `pipeline/model.py` | model (REUSE, não tocar) | transform | `model.project()` / `defaults()` | exact (reuso, não edição da lógica) |
| `site/app.js` | front (MOD) | request-response (fetch→DOM) | `renderInformalidade()` / `project()` | exact (render por seção + paridade) |
| `site/index.html` | markup (MOD) | — | seções `seclabel` + `sim` existentes | exact (slot + tag de classe) |
| `site/styles.css` | style (MOD) | — | `.tag.*` / `--desvio` / `.pendbox` | exact (nova tag + estilos SVG) |
| `tests/test_pipeline.py` | test (MOD) | request-response | `test_cold_start_*` / `test_payload_*` / `test_modelo_*` | exact |
| `pipeline/cli.py` | cli (MOD) | orchestration | `cmd_build()` | exact (carregar nova fonte no build) |

## Pattern Assignments

### `pipeline/sources/operacao.py` (source, file-I/O — NEW)

**Analog:** `pipeline/sources/snis.py` (exato; D-04 = só `load()`, SEM `refresh()`).

**Module docstring + imports + SCHEMA + RAW** — copie a forma de `snis.py` lines 1-32:
```python
from __future__ import annotations
from pathlib import Path
import polars as pl
from .base import slug

RAW = Path("data/raw/operacao")

SCHEMA = {  # dtypes explícitos, espelham model.project() (D-05)
    "mes": pl.String, "municipio": pl.String, "n_clientes": pl.Int64,
    "t_org_coletada": pl.Float64, "larva_umida_t": pl.Float64,
    "larva_seca_t": pl.Float64, "frass_t": pl.Float64,
    "partilha_rs": pl.Float64, "qualidade": pl.String, "fonte": pl.String,
}
```

**Core `load()` pattern** — copie de `snis.py` lines 35-50 (frame vazio COM coluna `key`,
glob+concat). Critical: o frame vazio DEVE ter `key` (lição CR-01 / `test_cold_start_*`).
Diferença vs SNIS: NÃO faz `.unique(subset=["key"])` (o grão é mês×município, múltiplas
linhas por `key` são esperadas — D-03). Filtrar linhas-comentário/sem `mes`:
```python
def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0,
                          comment_prefix="#") for f in files]  # comment_prefix p/ header doc (D-02)
    df = pl.concat(frames, how="vertical_relaxed").filter(pl.col("mes").is_not_null())
    if df.height == 0:
        return df.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    return df.with_columns(
        pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
```

**Junção (chave):** `base.slug()` de `pipeline/sources/base.py` lines 6-14 — chave canônica
do projeto, robusta a acento/caixa. NÃO usar regex/lower ad-hoc.

**Do NOT copy from snis.py:** a função `refresh()` (lines 53-95). D-04 proíbe rede nesta fase.

---

### `data/raw/operacao/operacao_rms.csv` (data fixture, file-I/O — NEW)

**Analog:** `data/raw/snis/snis_rms_sp.csv` (header + colunas `qualidade`,`fonte`).

**Pattern:** primeira linha = header das colunas do `SCHEMA`; SEM linhas de dado (D-01/D-02
"operação ainda não roda — nunca inventar telemetria"). Documentação em linhas `#` no topo
(lidas com `comment_prefix="#"` no `load()`). Unidade recomendada: toneladas (t) — casa com
os outputs `_t_ano` de `model.project()`.
```csv
# Telemetria REAL da operação (flag: real). Uma linha por (mes AAAA-MM, municipio).
# Massas em TONELADAS (t). partilha_rs em R$. Operação ainda não iniciada: sem linhas.
# Preencher da pesagem real; nunca estimar sem marcar qualidade=estimativa + fonte.
mes,municipio,n_clientes,t_org_coletada,larva_umida_t,larva_seca_t,frass_t,partilha_rs,qualidade,fonte
```
Procedência: coluna `qualidade` (`real`/`estimativa`) por linha + `fonte` texto livre,
exatamente como o SNIS CSV faz (regra sagrada — citar a fonte).

---

### `pipeline/transform.py` (transform, batch — MOD)

**Analog:** `region_totals()` lines 100-129 (agregação regional) + `build_region()` join por
`key` lines 42-47.

**Acumulados regionais (LIVE-04, D-11)** — NOVO `build_operacao(operacao, coef)`. Use o
padrão `group_by().agg()` + soma com `float(... or 0)` de `region_totals`:
```python
def build_operacao(operacao: pl.DataFrame, coef: dict) -> dict:
    if operacao.height == 0 or "mes" not in operacao.columns:
        return {"serie": [], "acumulados": None, "tem_dado": False}  # estado vazio honesto
    serie = (operacao.group_by("mes").agg([
        pl.col("n_clientes").sum().alias("n_clientes"),
        pl.col("t_org_coletada").sum().alias("real_desviado_t"),
        pl.col("larva_seca_t").sum().alias("real_larva_seca_t"),
        pl.col("frass_t").sum().alias("real_frass_t"),
        pl.col("partilha_rs").sum().alias("real_partilha_rs"),
    ]).sort("mes"))  # sort estável p/ determinismo (Pitfall 4)
    acum = {"desviado_t": float(serie["real_desviado_t"].sum() or 0), ...}
    return {"serie": serie.to_dicts(), "acumulados": acum, "tem_dado": True}
```

**Projetado da calibração (D-07/D-08)** — reuse `model.project()`, NÃO reimplemente. Insight
(Pattern 4 do RESEARCH): outputs são lineares em `desviado`, logo `desviado = t_org_coletada`
do mês; comparar em base MENSAL → dividir os `_t_ano` por 12. Mês sem `t_org_coletada` →
projetado `null` (célula vazia), NUNCA zero (regra sagrada).

**Constraints:** ordenar por `mes` (determinismo, sem relógio); Polars `group_by` (não loop
Python); chave `key`=`slug` (não código IBGE).

---

### `pipeline/render.py` (render, transform→JSON — MOD)

**Analog:** `to_payload()` lines 56-71 — o dict de retorno já separa classes
(`municipios`/`totais` vs `coeficientes`/`simulador_defaults`).

**Pattern:** adicionar a chave `operacao` ao dict SEM tocar/renomear as existentes
(`meta`/`coeficientes`/`simulador_defaults`/`totais`/`municipios`). Estado vazio honesto =
`{"serie": [], "acumulados": None, "tem_dado": False}`, nunca chave ausente (Pitfall 4 /
anti-pattern do RESEARCH):
```python
    return {
        "meta": {...},                       # inalterado
        "coeficientes": coef,                # inalterado
        "simulador_defaults": model.defaults(coef),
        "totais": totals,
        "municipios": municipios,
        "operacao": operacao_payload,        # NOVO
    }
```
A assinatura de `to_payload()` ganha um parâmetro `operacao_payload` (default-able, como
`pnad_df` em line 16, p/ não quebrar chamadores). `write()` (lines 74-77) inalterado.

---

### `pipeline/model.py` (model — REUSE, NÃO EDITAR)

**Analog:** ele próprio — `project()` lines 10-41, `defaults()` lines 44-51.

**Reuse, não modificação (D-08, Pitfall 1, CLAUDE.md):** a fase compara contra os
coeficientes, NÃO os reescreve. `project()` é a única fonte canônica da conversão. Mapa de
campos Python (espelhado pelo schema D-05): `desviado_t_ano`, `larva_seca_t_ano`,
`frass_t_ano`, `co2e_t_ano`, `carros_equivalente`, `fundo_partilha_ano`,
`catadores_sustentados`. **Nomes DIFEREM do JS** (ver Shared Pattern: Paridade).

---

### `site/app.js` (front, fetch→DOM — MOD)

**Analog:** `renderInformalidade()` lines 162-216 (render por seção, tag de classe,
estado pendente) + `project()` lines 219-230 (paridade) + `renderFlow()` lines 99-139
(estado vazio `pendbox` + SVG-like markup via `innerHTML`).

**Estado vazio honesto (D-02/D-09)** — copie o padrão `pendbox` de `renderFlow()` line 103:
```javascript
function renderOperacao() {
  const op = DATA.operacao;
  if (!op || !op.tem_dado) {
    $("opSlot").innerHTML =
      `<div class="pendbox"><b>Operação ainda não iniciada — sem medição real.</b>
       Quando a coleta começar, preencha <code>data/raw/operacao/operacao_rms.csv</code>
       e rode <code>uv run obs build</code>. O painel acende sozinho.</div>`;
    return;
  }
  // série SVG (Pattern 5 do RESEARCH) + 4 cards acumulados (D-11)
}
```
Chamar `renderOperacao()` em `selectCity()`/`boot()` (padrão de `renderFlow();renderKpis();
renderInformalidade();` line 93-96).

**Tag de classe (D-06, Pitfall 5):** seguir o padrão `tag(f)` de `renderInformalidade()`
lines 164-165, mas com NOVA classe `.tag.live`/`.medido` distinta das 3 existentes
(`.real`/`.est`/`.proj`).

**4 cards de impacto acumulado (D-11):** copie a estrutura `.ocard` do simulador (HTML
lines 76-87): desvio aterro (t), renda catadores (R$), CO2e (t + carros), bioconversão
(larva seca + frass).

**Série SVG inline (D-10):** Pattern 5 do RESEARCH (string template `<svg><polyline>`); zero
dependência. Reusar cores `--desvio` (real, sólido) e `--ink-2` (projetado, tracejado).

**Paridade `project()` (D-08):** se a calibração for computada no build (RECOMENDADO), NÃO
duplicar lógica no front — `project()` (lines 219-230) permanece inalterado para o simulador.

---

### `site/index.html` (markup — MOD)

**Analog:** seções `seclabel` (lines 28, 31, 37, 42) + tag de classe.

**Pattern:** adicionar APÓS o bloco `<div class="sim">` (depois do simulador, D-09) um
`<div class="seclabel">Operação ao vivo <span class="tag live">medição da operação</span>
</div>` + `<div id="opSlot"></div>`. Espelha `<div class="seclabel">... <span id="flowTags">
</span></div><div id="flowSlot"></div>` (lines 31-32).

---

### `site/styles.css` (style — MOD)

**Analog:** `.tag.*` (lines 35-37), `--desvio`/`--ink-2`/`--line` (lines 3-5), `.pendbox`
(lines 65-66), `.ocard` (lines 93-101).

**Pattern:** nova `.tag.live`/`.tag.medido` com cor distinta das 3 classes existentes
(Pitfall 5); classes do SVG `.serie/.s-real/.s-proj/.axis/.xlab` (Pattern 5 do RESEARCH):
```css
.s-real{stroke:var(--desvio);stroke-width:2.5}
.s-proj{stroke:var(--ink-2);stroke-width:2;stroke-dasharray:4 3}
.axis{stroke:var(--line)} .xlab{font:10px monospace;fill:var(--ink-2);text-anchor:middle}
```

---

### `tests/test_pipeline.py` (test — MOD)

**Analogs:** `test_cold_start_build_*` lines 458-490 (frame vazio com `key`),
`test_payload_tem_informalidade` lines 247-273 (forma do payload), `test_modelo_break_even_*`
lines 41-46 (`model.project()`).

**Testes a adicionar:**
1. `operacao.load()` vazio → frame com coluna `key` (copie a asserção line 488).
2. Payload contém `"operacao"` e vazio = `tem_dado:false`/`serie:[]` (copie a forma de
   `test_payload_tem_informalidade`, asserções lines 256-259).
3. **Paridade `model.py`↔`app.js::project()`** (CONCERNS #7, Pitfall 1 — RISCO CENTRAL):
   chamar `model.project()` com inputs fixos (padrão lines 42-43) + parse textual de
   `site/app.js` confirmando os nomes de campo JS (`desviado`,`co2e`,`carros`,`larvaSeca`,
   `frass`,`receita`,`fundo`,`catadores`,`pctOrg`). Documentar o mapa Py↔JS:
   `desviado_t_ano↔desviado`, `carros_equivalente↔carros`, `larva_seca_t_ano↔larvaSeca`,
   `frass_t_ano↔frass`, `fundo_partilha_ano↔fundo`, `catadores_sustentados↔catadores`.
   Precedente de parse AST/textual de `app.js`/source: `test_ibge_refresh_*` lines 280-326.

**Convenção dos testes:** `os.chdir(ROOT)`; `ibge.load(ROOT)` etc.; usar `REGIONS`/`COEF`
módulo-level (lines 11-12).

---

### `pipeline/cli.py` (cli — MOD)

**Analog:** `cmd_build()` lines 21-54.

**Pattern:** importar `operacao` na linha de import (line 13), carregar `df_op =
operacao.load(root)` junto das outras fontes (lines 32-36), computar
`op = transform.build_operacao(df_op, coef)` e passar a `render.to_payload(...)` (line 40).
Sem novo subcomando de rede (D-04). Build permanece offline/determinístico.

---

## Shared Patterns

### Junção por slug
**Source:** `pipeline/sources/base.py::slug` lines 6-14
**Apply to:** `operacao.py::load()`, `transform.build_operacao()`
```python
df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
```
Chave canônica do projeto (não código IBGE). Robusta a acento/caixa.

### Frame vazio com coluna `key` (lição CR-01)
**Source:** `pipeline/sources/snis.py` lines 38-41
**Apply to:** `operacao.py::load()`
```python
empty = pl.DataFrame(schema=SCHEMA)
return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
```
Sem isso, joins futuros/cold-start lançam `ColumnNotFoundError` (`test_cold_start_*`).

### Estado vazio honesto (regra sagrada)
**Source:** `transform.py` flags `pendente` (lines 58-64); `app.js::renderFlow` `pendbox`
(lines 102-106)
**Apply to:** `build_operacao()` (`tem_dado:false`), `render.to_payload()` (`operacao:[]`),
`renderOperacao()` (pendbox). Nunca preencher mês sem dado com 0 — `null`/célula vazia.

### Paridade `model.py` ↔ `app.js::project()`  (RISCO CENTRAL — CONCERNS #7)
**Source:** `pipeline/model.py::project()` lines 10-41 (canônico)  ↔  `site/app.js::project()`
lines 219-230 (espelho)
**Apply to:** toda conversão real→projetado da calibração; teste de paridade obrigatório.
**Mapa de nomes (DIFEREM entre Py e JS):**
| Python (`model.py`)      | JS (`app.js`)  |
|--------------------------|----------------|
| `desviado_t_ano`         | `desviado`     |
| `co2e_t_ano`             | `co2e`         |
| `carros_equivalente`     | `carros`       |
| `larva_seca_t_ano`       | `larvaSeca`    |
| `frass_t_ano`            | `frass`        |
| `receita_ano`            | `receita`      |
| `fundo_partilha_ano`     | `fundo`        |
| `catadores_sustentados`  | `catadores`    |
| `pct_organico_municipal` | `pctOrg`       |
Campos já divergiram historicamente (`carros_equivalente` vs `carros`) — fechar com teste
ANTES de construir a calibração em cima deles.

### Coeficientes (lidos, nunca reescritos)
**Source:** `config/coefficients.yml` (lido por `model.project()` via `coef`)
**Apply to:** `build_operacao()` recebe `coef` e passa a `model.project()`. A fase compara
contra os coeficientes; calibração automática é Deferred (não tocar `coefficients.yml`).

### Tag visual das 3 classes (Pitfall 5)
**Source:** `site/styles.css` `.tag.real`/`.tag.est`/`.tag.proj` lines 35-37
**Apply to:** nova `.tag.live`/`.medido` distinta; SVG real sólido (`--desvio`) vs projetado
tracejado apagado (`--ink-2`). Nunca confundir medição com projeção nem com baseline.

## No Analog Found

Nenhum arquivo sem analog. Todos os 9 arquivos têm padrão direto no codebase. A única
técnica sem precedente exato interno é o **SVG inline à mão** (`app.js::renderOperacao` série
temporal): não há gráfico SVG no codebase atual, mas o padrão de construir markup via string
template + `innerHTML` já existe (`renderFlow` lines 114-138) e o RESEARCH Pattern 5 fornece o
molde completo. Match: role-partial (técnica nova, mecanismo de render conhecido).

## Metadata

**Analog search scope:** `pipeline/`, `pipeline/sources/`, `site/`, `tests/`, `data/raw/`,
`config/`
**Files scanned:** snis.py, base.py, transform.py, render.py, model.py, cli.py, app.js,
index.html, styles.css, test_pipeline.py, coefficients.yml, snis_rms_sp.csv
**Pattern extraction date:** 2026-06-25
