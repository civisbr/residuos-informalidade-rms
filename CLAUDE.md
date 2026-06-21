# CLAUDE.md — Manual de operação

Você (Claude Code) está trabalhando no **Observatório de Resíduos & Informalidade**
(repositório `residuos-informalidade-rms`, org CivisBR): um painel vivo, open-source,
que mostra resíduos sólidos e informalidade por município brasileiro, e projeta o
impacto de uma operação de coleta de orgânicos + bioconversão por BSF (mosca
soldado-negro). Referência regional: RMS (27 municípios). Hospedado em GitHub Pages.

Trabalhamos em modo **GSD (get-shit-done)**: incrementos pequenos e shippáveis.
O backlog mora em `GSD.md`. Pegue a próxima tarefa não-marcada, faça, rode os
testes, marque o checkbox, commit. Um milestone por vez.

## Regra sagrada — integridade de dado
Este projeto vive da credibilidade (estilo CivisBR). **Nunca invente número.**
- Todo indicador carrega um flag: `real` | `estimativa` | `pendente`.
- Se não há dado público, o município é `pendente` — NÃO preencha com chute.
- Baseline (SNIS/IBGE/PMGIRS) e simulador (modelo BSF) ficam **visualmente
  separados** no painel. Nunca apresente projeção como medição.
- Coeficientes do modelo são conservadores e ficam em `config/coefficients.yml`,
  editáveis e documentados. Calibre com gravimetria local antes de qualquer uso externo.
- Catador informal é subcontado pelas bases oficiais — trate como piso.

Se for "melhorar" o painel reescrevendo dado a partir da sua memória: pare. O
caminho certo é extrair da fonte e rodar a pipeline.

## Mapa do repositório
```
config/
  regions.yml        # regiões -> lista de municípios (RMS já preenchida, 27)
  municipios.csv     # cache offline IBGE (nome, UF, código, população)
  coefficients.yml   # coeficientes do modelo BSF (PROJEÇÃO)
data/raw/snis/       # CSVs do SNIS (amostra commitada; refresh = trocar arquivo)
pipeline/
  cli.py             # `obs build | regions | refresh-ibge`
  sources/{ibge,snis,base}.py   # adaptadores de fonte
  transform.py       # Polars: junta região+IBGE+SNIS, deriva indicadores+flags
  model.py           # projeção de impacto BSF (espelhada em site/app.js)
  render.py          # escreve site/data.json
site/                # raiz do GitHub Pages (estático)
  index.html · styles.css · app.js · data.json (gerado, commitado)
tests/               # pytest, roda offline
```

## Comandos
```bash
uv sync                       # instala deps
uv run obs regions            # lista regiões
uv run obs build --region rms # gera site/data.json (offline, determinístico)
uv run pytest -q              # testes de sanidade
cd site && python -m http.server   # preview local (file:// quebra o fetch)
```

## Convenções de código
- Python 3.11+, **Polars** (não pandas), type hints, funções puras quando der.
- Fonte de dado = um módulo em `pipeline/sources/` com `load()` (offline) e,
  quando aplicável, `refresh()` (rede). Junção por nome normalizado (`base.slug`).
- `pipeline/model.py` e `site/app.js::project()` precisam dar o **mesmo número**.
  Mudou um, mude o outro e ajuste o teste de paridade.
- Sem framework no front: HTML + CSS + JS vanilla lendo `data.json`. Sem build step.
- Commits pequenos, mensagem no imperativo. PT-BR em texto voltado ao usuário.

## Como estender (casos comuns)
- **Novo município no painel:** adicione a linha real em `data/raw/snis/` (extraída
  do SNIS/PMGIRS) e garanta que o nome bate com `config/regions.yml`. Rode o build.
- **Nova região (qualquer cidade BR):** adicione uma chave em `config/regions.yml`
  com a lista de municípios; `obs build --region <chave>`.
- **Nova fonte (ex.: SINIR, RAIS):** crie `pipeline/sources/<fonte>.py` com `load()`,
  junte em `transform.py`, exponha no `render.py`, e adicione flag de qualidade.

Detalhes de cada milestone e a definição de pronto: ver `GSD.md`.
