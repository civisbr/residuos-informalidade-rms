---
phase: 04-generalizar-para-qualquer-cidade-br
reviewed: 2026-06-24T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - pipeline/sources/ibge.py
  - pipeline/sources/snis.py
  - pipeline/cli.py
  - pipeline/transform.py
  - scripts/scrape_snis.py
  - site/app.js
  - config/regions.yml
  - README.md
  - tests/test_pipeline.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-24
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed pipeline sources (`ibge.py`, `snis.py`), transform layer, CLI, frontend (`app.js`), scraper (`scrape_snis.py`), config, README, and test suite for Phase 04 (generalização para qualquer cidade BR).

Good news: lazy-import discipline is intact (`import httpx` is inside `ibge.refresh()`, `import requests` is inside `_session()`, `import argparse` and `from scrape_snis import cmd_build` are inside `snis.refresh()` — no top-level network imports anywhere). The `taxa_inf_media` rename is complete and consistent across `transform.py`, `render.py`, `app.js`, and the test suite. The path-traversal mitigation in `snis.refresh()` (allowlist via `region not in regions`) is real and currently effective. model.py ↔ app.js formula parity is verified: `larvaSeca`, `frass`, `catadores`, `receita`, `co2e` and the `partilha_pct / 100` division all match.

One blocker exists: all three `*.load()` functions that glob CSV files return an empty `pl.DataFrame(schema=SCHEMA)` without a `key` column when no files are present. This causes `transform.build_region()` to crash with `ColumnNotFoundError` on the join, which means the first-run experience for any new region (before `refresh-snis`, `refresh-ibge` are run) is a hard traceback rather than a graceful empty build.

---

## Critical Issues

### CR-01: `snis.load()`, `ibge_informalidade.load()`, and `rais.load()` return empty DataFrames without `key` column — `transform.build_region()` crashes on join

**Files:**
- `pipeline/sources/snis.py:38-39`
- `pipeline/sources/ibge_informalidade.py:78-79`
- `pipeline/sources/rais.py:57-58`
- `pipeline/transform.py:44-46`

**Issue:** When no CSV files exist in `data/raw/snis/`, `data/raw/censo/`, or `data/raw/rais/`, each module's `load()` returns `pl.DataFrame(schema=SCHEMA)`. Those schemas do not include a `key` column. The `key` column is only added by `map_elements(slug, ...)` when files are actually read. `transform.build_region()` then calls `snis.drop("municipio", "uf")` (which works on the empty frame) but then does `.join(…, on="key", how="left")`, which raises `polars.exceptions.ColumnNotFoundError: unable to find column "key"`. The same crash occurs for `inf_sel` (from `informalidade.select(["key", ...])`) and `rais_sel` (from `rais_residuos.select(["key", ...])`).

This is the first-run experience for any new region declared in `regions.yml` before data is populated: `uv run obs build --region minha_regiao` crashes with a traceback instead of producing a valid `data.json` with all municipalities marked `pendente`.

Verified with:
```python
>>> pl.concat([df1_no_key, df2_with_key], how="vertical_relaxed")
polars.exceptions.ComputeError: schema lengths differ
# and
>>> base.join(empty_no_key, on="key", how="left")
polars.exceptions.ColumnNotFoundError: unable to find column "key"
```

**Fix:** Add the `key` column to each empty-schema return path, or add it at the call site in `transform.build_region()` before the join:

Option A — fix in each source (preferred, keeps contracts clean):

```python
# pipeline/sources/snis.py, ibge_informalidade.py, rais.py
def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        # Add key column to empty schema so joins in transform.build_region() don't crash
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    ...
```

Option B — fix in `transform.build_region()` for each join partner:

```python
# pipeline/transform.py
def _ensure_key(df: pl.DataFrame) -> pl.DataFrame:
    if "key" not in df.columns:
        return df.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    return df

snis_keyed   = _ensure_key(snis.drop("municipio", "uf") if ...)
inf_sel      = _ensure_key(informalidade).select(["key", ...])
rais_sel     = _ensure_key(rais_residuos).select(["key", ...])
```

---

## Warnings

### WR-01: D-06 upsert uses truthiness check `if pop` — incorrectly treats `populacao=0` as "empty"

**File:** `pipeline/sources/ibge.py:119-121`

**Issue:** The idempotent-upsert guard is:
```python
codigo = r.get("codigo_ibge")
pop    = r.get("populacao")
if codigo and pop:
    continue   # preserve curated data
```
`if pop` evaluates to `False` when `pop` is `0` (integer zero). A curated row with `codigo_ibge="3500758"` and `populacao=0` (hypothetically: an uninhabited island municipality) would not be skipped — the upsert would overwrite the curated population with the API value. While no current municipality in `municipios.csv` has `populacao=0`, this is a latent data-integrity defect that contradicts the stated invariant ("linhas com ambos preenchidos são preservadas").

**Fix:**
```python
# Replace the truthiness check with explicit None and empty-string guards:
codigo = r.get("codigo_ibge")
pop    = r.get("populacao")
codigo_ok = codigo is not None and codigo != ""
pop_ok    = pop is not None
if codigo_ok and pop_ok:
    continue  # ambos preenchidos — preservar curadoria (D-06)
```

---

### WR-02: Network calls in `ibge.refresh()` and `scrape_snis.py` produce unguarded stack traces on timeout, connection error, or non-JSON response

**Files:**
- `pipeline/sources/ibge.py:62-86` (both `httpx.Client` blocks)
- `scripts/scrape_snis.py:89-98, 150-175` (`_session()`, `_get_select()`, `_query_grid()`)

**Issue:** All `.get()`/`.post()`/`.json()` calls are unguarded by `try/except`. On a timeout, `httpx.TimeoutException` and `requests.Timeout` propagate as raw tracebacks. On a non-JSON response (e.g., SNIS portal returns HTML error page), `.json()` raises `JSONDecodeError` — also an unguarded traceback. On HTTP error (e.g., 503), `raise_for_status()` in `ibge.refresh()` raises `httpx.HTTPStatusError` with a traceback. In `scrape_snis.py`, line 97 (`_get_select`) and lines 157/175 (`_query_grid`) call `.json()` directly without checking `r.status_code` first.

This contradicts the stated project goal (D-09): "Erro amigável… sem stacktrace, continua os demais."

**Fix (ibge.refresh — both API calls):**
```python
try:
    with httpx.Client(timeout=60) as client:
        resp = client.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios")
        resp.raise_for_status()
        muns = resp.json()
except httpx.HTTPError as exc:
    print(f"Erro ao buscar localidades IBGE ({uf}): {exc}", file=sys.stderr)
    return
```

```python
try:
    with httpx.Client(timeout=120) as client:
        resp = client.get("https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022")
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            print(f"SIDRA retornou formato inesperado: {type(raw)}", file=sys.stderr)
            return
        sidra_rows = raw[1:]
except httpx.HTTPError as exc:
    print(f"Erro ao buscar população SIDRA: {exc}", file=sys.stderr)
    return
```

Note: `resp.json()[1:]` on line 79 also has a latent crash if SIDRA returns an error dict instead of a list (a `KeyError` on `dict[slice]`). The `isinstance(raw, list)` guard above covers this.

---

### WR-03: `snis.refresh()` unconditionally inserts `scripts/` into `sys.path` — permanent global side effect

**File:** `pipeline/sources/snis.py:71`

**Issue:**
```python
sys.path.insert(0, str(root / "scripts"))
from scrape_snis import cmd_build
```
This permanently prepends the `scripts/` directory to `sys.path` on every call. If `snis.refresh()` is called twice (e.g., for two regions), the path is inserted twice. More critically, any module named the same as a stdlib or installed package that happens to be in `scripts/` would shadow it for the rest of the process lifetime. The `sys.path` mutation is never undone.

**Fix:** Use `importlib` with a temporary path manipulation, or check before inserting:
```python
scripts_dir = str(root / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
from scrape_snis import cmd_build
```
Better alternative: restructure `scrape_snis.py` as a proper package submodule, or pass `root` to `cmd_build` and use importlib:
```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "scrape_snis", root / "scripts" / "scrape_snis.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.cmd_build(args)
```

---

### WR-04: `ibge.refresh()` silently uses empty `uf` string if the region lacks a `uf` key — API call fails with opaque HTTP error

**File:** `pipeline/sources/ibge.py:58`

**Issue:**
```python
uf: str = meta.get("uf", "")
```
If a new region in `regions.yml` omits the `uf` field, `uf` is `""`. The URL becomes `https://servicodados.ibge.gov.br/api/v1/localidades/estados//municipios`. Without error handling (WR-02), this produces either an HTTP 404 traceback or an unexpected response. There is no early validation with a helpful message.

`scrape_snis.py` has a better default (`meta.get("uf", "SP")`), but that silently queries the wrong state. `ibge.refresh()` should fail fast.

**Fix:**
```python
uf: str = meta.get("uf", "")
if not uf:
    print(
        f"Região '{region}' não tem campo 'uf' em {regions_path}. "
        "Adicione: uf: SP  (sigla do estado, 2 letras).",
        file=sys.stderr,
    )
    return
```

---

## Info

### IN-01: Path-traversal allowlist relies on `regions.yml` keys being safe — no explicit sanitization of the resulting output path

**File:** `pipeline/sources/snis.py:74`

**Issue:** The comment on lines 59-60 claims path-traversal is prevented by validating `region` against `regions.yml`. This is true only as long as the YAML keys themselves do not contain path separators. YAML allows keys like `../evil` — and Python's `pathlib` will join them freely:
```python
out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
# region = "../../../tmp/evil" → resolves outside data/raw/snis/
```
Current `regions.yml` has only `rms` (safe). But the security claim is overstated: the allowlist prevents a CLI user from injecting a region name not in the YAML, but it does not prevent a maintainer who edits `regions.yml` from inadvertently introducing a traversal key.

**Fix:** Add a path confinement assertion after constructing `out`:
```python
out = root / "data" / "raw" / "snis" / f"snis_{region}.csv"
snis_dir = (root / "data" / "raw" / "snis").resolve()
if not out.resolve().is_relative_to(snis_dir):
    print(f"Erro: caminho de saída '{out}' fora do diretório esperado.", file=sys.stderr)
    return
```

---

### IN-02: `ibge.refresh()` upsert nulls out any extra curated columns present in `municipios.csv` when updating a row

**File:** `pipeline/sources/ibge.py:149-163`

**Issue:** The upsert removes the old row and adds a new one with exactly 5 fixed columns (`nome`, `uf`, `codigo_ibge`, `populacao`, `fonte_pop`). If `municipios.csv` ever acquires additional curated columns (e.g., a `nota` or `pop_fonte_alternativa` column), those values become `null` for any row that gets updated by `refresh`. Verified:

```python
# df with 'nota' column → after upsert, nota becomes null for the updated row
result['nota'][0]  # → None
```

Currently `municipios.csv` has exactly those 5 columns, so no data is lost now. But the behaviour is surprising and undocumented.

**Fix (documentation):** Add a comment warning that `new_row` construction must be updated if the CSV schema expands. Or reconstruct `new_row` by starting from the existing row and only overwriting the fields being refreshed:
```python
# Start from existing row's values (preserves any extra curated columns)
new_row = dict(row_df.row(0, named=True)) if row_df.height > 0 else {}
new_row.update({
    "nome": nome_mun, "uf": uf,
    "codigo_ibge": id_7dig,
    "populacao": pop_value,
    "fonte_pop": "IBGE Censo 2022",
})
```

---

_Reviewed: 2026-06-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
