# Structure

*Mapped: 2026-06-21*

## Directory layout

```
residuos-informalidade-rms/
├── CLAUDE.md              # manual de operação (regra sagrada de dado, mapa, comandos)
├── GSD.md                 # board de milestones (M0✅ → M5), autoral do projeto
├── README.md              # apresentação pública
├── LICENSE
├── pyproject.toml         # deps + script `obs` (uv)
├── uv.lock
├── .github/workflows/
│   └── build.yml          # CI: build offline + pytest
├── config/
│   ├── regions.yml        # regiões → lista de municípios (RMS: 27)
│   ├── municipios.csv     # cache offline IBGE (nome, UF, código, população)
│   └── coefficients.yml   # coeficientes do modelo BSF (PROJEÇÃO)
├── data/
│   ├── raw/snis/
│   │   └── snis_rs_sample.csv   # amostra commitada; refresh = trocar arquivo
│   └── processed/.gitkeep
├── scripts/
│   └── refresh_snis.md    # runbook manual de atualização do SNIS
├── pipeline/
│   ├── cli.py             # `obs build | regions | refresh-ibge`
│   ├── transform.py       # Polars: junção + indicadores + flags
│   ├── model.py           # projeção BSF (espelha app.js)
│   ├── render.py          # escreve site/data.json
│   └── sources/
│       ├── base.py        # slug() — normalização de nome
│       ├── ibge.py        # load() offline / refresh() (pendente)
│       └── snis.py        # load() dos CSVs
├── site/                  # raiz do GitHub Pages (estático)
│   ├── index.html
│   ├── styles.css
│   ├── app.js             # painel + simulador; project() espelha model.py
│   └── data.json          # GERADO e commitado
└── tests/
    └── test_pipeline.py   # pytest, offline
```

## Key locations

| Preciso de... | Vá para |
|---------------|---------|
| Adicionar município/região | `config/regions.yml` |
| Dado SNIS real de um município | `data/raw/snis/*.csv` |
| Ajustar coeficientes do modelo | `config/coefficients.yml` |
| Lógica de indicadores/flags | `pipeline/transform.py` |
| Lógica de projeção BSF | `pipeline/model.py` **e** `site/app.js::project()` |
| Forma do JSON de saída | `pipeline/render.py` |
| Nova fonte de dado | novo módulo em `pipeline/sources/` + junção em `transform.py` |
| Visual do painel | `site/index.html`, `site/styles.css`, `site/app.js` |
| Testes | `tests/test_pipeline.py` |

## Naming conventions

- Módulos e funções: `snake_case`. Funções de fonte: `load()` / `refresh()`.
- Chave de junção entre fontes: `key` = `slug(nome)` (NFKD, sem acento, lower).
- Indicadores no payload em português: `rsu_t_ano`, `organico_t_ano`,
  `aterro_t_ano`, `reciclado_pct`, `cooperados`, `custo_mensal_rs`.
- Flag de qualidade: strings `"real"` | `"estimativa"` | `"pendente"`.
- Configs em YAML; cache tabular em CSV; artefato de saída em JSON.

## Onde adicionar código novo (casos comuns)

- **Novo município no painel**: linha real em `data/raw/snis/` + nome batendo
  com `config/regions.yml`. Rode o build.
- **Nova região (qualquer cidade BR)**: chave nova em `config/regions.yml`;
  `obs build --region <chave>`.
- **Nova fonte (SINIR, RAIS…)**: `pipeline/sources/<fonte>.py` com `load()`,
  junte em `transform.py`, exponha em `render.py`, e adicione flag de qualidade.
