# External Integrations

**Analysis Date:** 2026-06-21

## APIs & External Services

**IBGE (Instituto Brasileiro de Geografia e Estatística):**
- Purpose: Fetch municipality codes and population estimates for the IBGE cache
- Endpoints used (planned, not yet active):
  - `https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios` — municipality list per state
  - `https://servicodados.ibge.gov.br/api/v3/agregados/6579` — estimated population by municipality
- SDK/Client: `httpx` (async HTTP client, installed at 0.28.1)
- Auth: None — IBGE API is public, no key required
- Status: **Stub only** — `pipeline/sources/ibge.py:refresh()` raises `NotImplementedError`. Online refresh is pending (GSD.md M4). All current builds use the offline cache at `config/municipios.csv`

**Google Fonts:**
- Purpose: Typography for the frontend panel
- Loaded from: `https://fonts.googleapis.com` and `https://fonts.gstatic.com` (CDN link tags in `site/index.html`)
- Fonts: Space Grotesk, Inter, IBM Plex Mono
- Auth: None — public CDN
- Status: Active (browser loads at runtime from CDN)

**SNIS (Sistema Nacional de Informações sobre Saneamento):**
- Integration type: **Offline file-based** — not a live API call
- Data source: Annual export downloaded manually and placed in `data/raw/snis/`
- Instructions: `scripts/refresh_snis.md` (manual refresh procedure)
- Status: Active offline; sample data committed at `data/raw/snis/snis_rs_sample.csv`

## Data Storage

**Databases:**
- None — no relational or document database. All persistent state is in flat files

**File Storage:**
- Local filesystem: `data/raw/snis/*.csv` — raw input data (committed sample)
- Local filesystem: `config/municipios.csv` — IBGE municipality cache (committed)
- Local filesystem: `site/data.json` — generated build artifact (committed for GitHub Pages)
- `data/processed/` directory exists but is gitignored (`.gitkeep` committed); not currently used by pipeline

**Caching:**
- None — builds are fully deterministic; `data.json` is committed and served statically

## Authentication & Identity

**Auth Provider:**
- None — no user authentication anywhere in the system
- The site is a public read-only panel; no login, no sessions, no user data

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Python pipeline: `print()` to stdout in `pipeline/cli.py` (build summary, warnings for pending municipalities)
- Frontend: no logging; errors shown inline via DOM injection in `site/app.js:boot()`

## CI/CD & Deployment

**Hosting:**
- GitHub Pages — serves the static `site/` directory
- URL populated by the `github-pages` environment in the Actions workflow

**CI Pipeline:**
- GitHub Actions — `.github/workflows/build.yml`
- Trigger: push to `main` branch, or manual `workflow_dispatch`
- Steps in order:
  1. `actions/checkout@v4`
  2. `astral-sh/setup-uv@v3` — installs uv
  3. `uv sync` — installs Python deps
  4. `uv run pytest -q` — runs sanity tests
  5. `uv run obs build --region rms` — generates `site/data.json`
  6. `actions/upload-pages-artifact@v3` — packages `site/`
  7. `actions/deploy-pages@v4` — deploys to GitHub Pages
- Required GitHub permissions: `contents: read`, `pages: write`, `id-token: write`

## Environment Configuration

**Required env vars:**
- None for offline build or local preview
- None for CI either — no secrets required; IBGE API is public

**Secrets location:**
- No secrets detected in repository

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (IBGE refresh, when implemented, will be an outbound GET — not a webhook)

## Data Sources Referenced in UI (not yet integrated as live APIs)

The frontend footer (`site/index.html`) documents future data sources that are not yet integrated as live API calls:
- PMGIRS — Plano Municipal de Gestão Integrada de Resíduos
- RAIS / CAGED — formal employment proxy for informality
- MNCR / IPEA — informal waste picker population estimates
- Municipal transparency portals (PPP / Secretaria de Serviços Públicos)
- Future: operational telemetry (weighing, per-client organic collection) — described as the path to making the panel truly "live"

---

*Integration audit: 2026-06-21*
