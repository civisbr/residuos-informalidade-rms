# Coding Conventions

**Analysis Date:** 2026-06-21

## Naming Patterns

**Files:**
- Python modules use `snake_case`: `transform.py`, `render.py`, `cli.py`
- Source adapters live under `pipeline/sources/` and are named after their data origin: `ibge.py`, `snis.py`, `base.py`
- Config files use `snake_case` with descriptive names: `coefficients.yml`, `regions.yml`, `municipios.csv`
- Frontend files use conventional lowercase: `app.js`, `styles.css`, `index.html`
- Data output: `site/data.json` (generated, committed)

**Functions:**
- Python: `snake_case` throughout — `build_region`, `region_totals`, `to_payload`, `cmd_build`
- CLI command handlers are prefixed with `cmd_`: `cmd_build`, `cmd_regions`, `cmd_refresh_ibge`
- Private/internal helpers are prefixed with `_`: `_load_yaml`
- Source module interface is standardized: `load()` for offline, `refresh()` for network
- JavaScript: `camelCase` — `buildRegionStrip`, `buildCitySelect`, `selectCity`, `renderFlow`, `recalc`
- JS DOM shortcuts use single-char `$`: `const $ = id => document.getElementById(id)`
- JS formatter shorthand: `const fmt = (n, d = 0) => ...`

**Variables:**
- Python: `snake_case` — `org_pct`, `com_dado`, `region_key`, `coef`
- JS global state: `UPPERCASE` for module-level singletons — `DATA`, `COEF`, `CITY`
- JS local: `camelCase` — `cli`, `kg`, `sh`, `fee`, `orgMun`

**Types/Keys:**
- Join key for municipality names: `key` (slugified, lowercase, no accents)
- Data quality flag values: string literals `"real"` | `"estimativa"` | `"pendente"`
- Indicator columns: `snake_case` with unit suffix — `rsu_t_ano`, `reciclado_pct`, `custo_mensal_rs`

## Code Style

**Formatting:**
- No auto-formatter configured (no Black, Ruff, or Prettier config detected)
- Line length follows PEP 8 convention implicitly (~88–100 chars)
- Chained Polars operations use parenthesized multi-line blocks with 8-space indent on continuation

**Linting:**
- No linter configured (no `.flake8`, `ruff.toml`, `.eslintrc`, or `[tool.ruff]` in `pyproject.toml`)
- Code quality enforced through project conventions and PR review

## Import Organization

**Python order (observed pattern):**
1. `from __future__ import annotations` — always first in every pipeline module
2. Standard library (`argparse`, `sys`, `pathlib`, `json`, `datetime`, `unicodedata`)
3. Third-party (`polars`, `yaml`)
4. Internal relative imports (`from .sources.base import slug`, `from . import transform, render`)

**Path Aliases:**
- No path aliases; imports use relative notation within `pipeline/` package (`.` and `..`)

## Error Handling

**Patterns:**
- Network/unimplemented operations raise `NotImplementedError` with actionable message pointing to documentation: `pipeline/sources/ibge.py:34`
- CLI commands return integer exit codes (`0` for success, `1` for config error); errors print to `sys.stderr`
- Missing data is represented as `null` in the dataframe, never filled with invented values — this is a domain invariant, not just a code style choice
- Frontend: `fetch` errors caught in `try/catch`, rendered as inline error HTML with instructions for the user (`site/app.js:13`)
- No custom exception classes; standard Python exceptions used directly

**Data quality guard:**
- Every municipality row carries a `flag` column (`"real"` | `"estimativa"` | `"pendente"`)
- Null RSU data → `"pendente"` flag; this mapping is done in `pipeline/transform.py:34`
- Downstream code (JS, render) must check `flag` before displaying numbers as facts

## Logging

**Framework:** `print()` to stdout; errors to `sys.stderr` via `print(..., file=sys.stderr)`

**Patterns:**
- CLI success messages use `✓` prefix: `print(f"✓ {out} — ...")` in `pipeline/cli.py:37`
- Actionable follow-up instructions are included in output (e.g., directing user to run `obs refresh-ibge`)
- No structured logging library used

## Comments and Docstrings

**Module-level docstrings:**
- Every Python module has a module-level docstring explaining purpose, offline/online split, and expected schema (see `pipeline/sources/snis.py`, `pipeline/model.py`)
- Docstrings use plain prose in PT-BR domain terminology mixed with English code terms

**Inline comments:**
- Used on Polars column expressions to explain the business meaning of derived columns: `pipeline/transform.py:29–35`
- YAML config files have inline comments documenting source of each coefficient and calibration notes: `config/coefficients.yml`
- JS file has a section separator comment: `// ---- simulador: espelha pipeline/model.py ----`

**Warning convention:**
- Projection-vs-measurement distinction is enforced in comments, docstrings, and UI text. Any model output file or function must note `PROJEÇÃO, NÃO MEDIÇÃO` — see `pipeline/model.py:3`

## Function Design

**Size:** Functions are short and focused (10–30 lines); longest is `renderFlow` in JS at ~30 lines of HTML construction

**Parameters:**
- `root: Path = Path(".")` is the standard signature for file-loading functions to make them testable with a custom root
- `coef: dict` passed explicitly through the call chain — not stored as global state
- Python functions use type hints: `def build_region(municipios: list[dict], ibge: pl.DataFrame, snis: pl.DataFrame, coef: dict) -> pl.DataFrame`

**Return Values:**
- Source adapters return `pl.DataFrame`
- Aggregation functions return `dict` with named scalar keys
- CLI handlers return `int` (exit code)
- `model.project()` returns a flat `dict` of rounded floats

## Module Design

**Exports:**
- No `__all__` defined; modules export everything at the top level
- `pipeline/__init__.py` is empty — package init is minimal

**Source Adapter Contract:**
- Each source module in `pipeline/sources/` exposes `load(_root: Path) -> pl.DataFrame` for offline use
- Network sources additionally expose `refresh(root: Path) -> None`
- Join key is always added as column `"key"` using `slug()` from `pipeline/sources/base.py`

**Model parity constraint:**
- `pipeline/model.py::project()` and `site/app.js::project()` must implement identical arithmetic — this is explicitly documented and tested

---

*Convention analysis: 2026-06-21*
