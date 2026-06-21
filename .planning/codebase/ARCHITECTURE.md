# Architecture

*Mapped: 2026-06-21*

## Pattern

**Pipeline batch offline → artefato JSON estático → painel no navegador.**

Não há servidor, banco, nem build step no front. A pipeline Python (Polars)
lê fontes locais, deriva indicadores com flags de qualidade, e escreve um único
`site/data.json`. O painel (`site/index.html` + `app.js` vanilla) consome esse
JSON. Determinístico e reprodutível: `uv run obs build` gera o mesmo resultado
sem rede.

## Layers

1. **Sources** (`pipeline/sources/`) — adaptadores de fonte. Cada um expõe
   `load()` (offline, lê arquivo local) e, quando aplicável, `refresh()` (rede).
   - `ibge.py` — código IBGE + população (cache `config/municipios.csv`)
   - `snis.py` — indicadores de resíduos (CSVs em `data/raw/snis/`)
   - `base.py` — `slug()` para normalizar nome de município (chave de junção)
2. **Transform** (`pipeline/transform.py`) — junta região + IBGE + SNIS por
   `key` (nome normalizado), deriva indicadores (`organico_t_ano`,
   `aterro_t_ano`) e o **flag de qualidade** (`real` | `estimativa` | `pendente`).
3. **Model** (`pipeline/model.py`) — projeção de impacto BSF (PROJEÇÃO, não
   medição). Espelhada em `site/app.js::project()` para o simulador interativo.
4. **Render** (`pipeline/render.py`) — monta o dicionário e escreve `site/data.json`.
5. **CLI** (`pipeline/cli.py`) — orquestra: `build`, `regions`, `refresh-ibge`.
6. **Front** (`site/`) — HTML/CSS/JS vanilla lendo `data.json`. Sem framework.

## Data flow

```
config/regions.yml  (lista de municípios por região)
config/municipios.csv ─► ibge.load() ──┐
data/raw/snis/*.csv  ─► snis.load() ───┤
config/coefficients.yml ───────────────┤
                                        ▼
                          transform.build_region()
                          (join por slug + indicadores + flag)
                                        ▼
                          transform.region_totals()
                                        ▼
                          render.to_payload() ◄── model.defaults()
                                        ▼
                              site/data.json  (commitado)
                                        ▼
            site/app.js (fetch) ─► render do painel + simulador
                                    app.js::project() == model.project()
```

## Key abstractions

- **Flag de qualidade** (`real`/`estimativa`/`pendente`): a abstração central do
  projeto. Separa visualmente dado público medido de lacuna. Derivada em
  `transform.py`: sem `rsu_t_ano` → `pendente`; senão usa coluna `qualidade`
  (default `real`). Nunca se inventa número para preencher pendente.
- **Baseline vs. Simulador**: baseline = dado público (SNIS/IBGE/PMGIRS);
  simulador = projeção do modelo BSF. Ficam separados no payload (`municipios`/
  `totais` vs. `coeficientes`/`simulador_defaults`) e no painel.
- **Paridade model.py ↔ app.js**: a mesma lógica de projeção em dois lugares.
  Mudou um, muda o outro e ajusta o teste.
- **Coeficientes externalizados** (`config/coefficients.yml`): o modelo não
  hardcoda número; lê coeficientes documentados e conservadores.

## Entry points

- `uv run obs build [--region rms]` → `cli.cmd_build` → escreve `site/data.json`
- `uv run obs regions` → `cli.cmd_regions`
- `uv run obs refresh-ibge` → `cli.cmd_refresh_ibge` (atualmente `NotImplementedError`)
- `cd site && python -m http.server` → preview do painel (file:// quebra o fetch)
- `.github/workflows/build.yml` → CI: roda build + pytest

## Anti-patterns / tensões observadas

- **CWD-dependente**: `cli.py` usa `Path(".")` como raiz; o build só funciona
  rodado da raiz do repo. Testes fazem `os.chdir(ROOT)` para contornar.
- **Não-determinismo no render**: `date.today()` em `render.py` injeta a data no
  `data.json` → diffs espúrios no git a cada build.
- **Generalização incompleta**: `subregiao` e suposições de região ainda
  enviesadas pela RMS (ver CONCERNS.md). M4 trata disso.
