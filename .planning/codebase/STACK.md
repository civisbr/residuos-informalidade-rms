# Technology Stack

**Analysis Date:** 2026-06-21

## Languages

**Primary:**
- Python 3.11+ (required) / 3.13.5 (runtime via uv) - All pipeline, data processing, CLI, tests
- JavaScript (ES2020+, vanilla, no transpile) - Frontend panel at `site/app.js`

**Secondary:**
- HTML5 - Static page at `site/index.html`
- CSS3 - Styles at `site/styles.css`
- YAML - Configuration at `config/coefficients.yml`, `config/regions.yml`

## Runtime

**Environment:**
- Python 3.13.5 (managed by uv; `requires-python = ">=3.11"` in `pyproject.toml`)
- Browser (any modern browser) for frontend

**Package Manager:**
- uv 0.9.8 — manages Python virtualenv and dependencies
- Lockfile: not detected (no `uv.lock` committed; deterministic via `pyproject.toml` version pins)

## Frameworks

**Core:**
- None (stdlib + Polars only; no web framework; no ORM)

**Testing:**
- pytest — test runner; config in `pyproject.toml`; tests at `tests/test_pipeline.py`

**Build/Dev:**
- hatchling — build backend declared in `pyproject.toml` `[build-system]`
- uv — task runner (`uv run obs build`, `uv run pytest -q`)
- Python's built-in `http.server` — local preview of `site/`

## Key Dependencies

**Critical:**
- `polars>=1.0` (installed: 1.41.2) — all DataFrame operations in `pipeline/transform.py`, `pipeline/sources/ibge.py`, `pipeline/sources/snis.py`; replaces pandas entirely
- `pyyaml>=6.0` — loads `config/coefficients.yml` and `config/regions.yml` in `pipeline/cli.py` and `tests/test_pipeline.py`
- `httpx>=0.27` (installed: 0.28.1) — HTTP client for future `ibge.refresh()` network calls; currently only imported when `obs refresh-ibge` is invoked (stub at `pipeline/sources/ibge.py:25`)

**Infrastructure:**
- `hatchling` — build system (build-time only, not a runtime dep)

## Configuration

**Environment:**
- No environment variables required for offline build (`obs build`)
- No `.env` file detected; no secrets in repository
- All model parameters live in `config/coefficients.yml` (version-controlled, documented)
- Region/municipality configuration in `config/regions.yml`
- IBGE municipality cache in `config/municipios.csv`

**Build:**
- `pyproject.toml` — project metadata, deps, entry point (`obs = "pipeline.cli:main"`), build config
- `.github/workflows/build.yml` — CI/CD pipeline

## Platform Requirements

**Development:**
- uv installed (`uv sync` to install deps into `.venv/`)
- Python 3.11+ (managed by uv; no `.python-version` pinfile detected)
- No network required for `obs build` (fully offline; all data in repo)
- Local preview: `cd site && python -m http.server` (file:// breaks `fetch()`)

**Production:**
- GitHub Pages (static hosting of `site/` directory)
- No server-side runtime; all logic runs at build time in CI or locally
- Build artifact: `site/data.json` (generated, committed to repo for Pages)

---

*Stack analysis: 2026-06-21*
