# Observatório de Resíduos & Informalidade

[![Deploy](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/deploy.yml/badge.svg)](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/deploy.yml) **[Abrir o painel de Sorocaba →](https://residuos-informalidade-rms.pages.dev)** · [Sobre o projeto](https://civisbr.github.io/residuos-informalidade-rms/)

> Repositório: **`residuos-informalidade-rms`** · CivisBR · referência: Região Metropolitana de Sorocaba (RMS)

Painel **vivo e open-source** que mostra, por município brasileiro, para onde vai
o resíduo sólido urbano e quem fica de fora da cadeia formal — e projeta o impacto
de uma operação de **coleta de orgânicos + bioconversão por BSF** (mosca
soldado-negro). Estático, hospedável no GitHub Pages.

Vem pré-configurado para a **Região Metropolitana de Sorocaba (RMS — 27 municípios)**,
mas é extensível a qualquer cidade do país editando um arquivo de configuração.

## O que ele separa com rigor
- **Baseline (dado público):** SNIS/SINISA, PMGIRS, IBGE, transparência municipal.
  Anual, com defasagem típica do SNIS.
- **Simulador (projeção de modelo):** impacto BSF a partir de coeficientes
  conservadores e editáveis. **Não é medição.**
- **Lacunas (pendente):** município sem dado aparece como pendente — nunca com
  número inventado.

## Início rápido
```bash
uv sync
uv run obs build --region rms     # gera site/data.json (offline, determinístico)
uv run pytest -q                  # testes
cd site && python -m http.server  # abra http://localhost:8000
```
> Abrir `site/index.html` direto por `file://` bloqueia o `fetch` do `data.json`.
> Use um servidor local (linha acima) ou o GitHub Pages.

## Crie o painel da sua cidade em 5 minutos

### 1. Declarar a região
Edite `config/regions.yml` (campos obrigatórios: `nome` por região; `nome` + `uf` por município):

```yaml
minha_regiao:
  nome: "Região do Vale do Paraíba"
  uf: SP
  municipios:
    - { nome: "São José dos Campos", uf: SP }
    - { nome: "Jacareí", uf: SP }
```

### 2. Resolver identidade (IBGE)
```bash
uv run obs refresh-ibge --region minha_regiao
```
Resolve código IBGE e população (Censo 2022) para cada município e salva em `config/municipios.csv`.

### 3. Baixar dados de resíduos (SNIS)
```bash
uv run obs refresh-snis --region minha_regiao
```
Baixa indicadores de RSU do portal SNIS-RS e salva em `data/raw/snis/snis_minha_regiao.csv`.

### 4. Gerar o painel
```bash
uv run obs build --region minha_regiao
```

> **Aviso honesto:** informalidade e RAIS ficam `pendente` para regiões fora da RMS
> (Região Metropolitana de Sorocaba) — os dados de Censo 2022 e RAIS 2023 estão
> pré-carregados apenas para os 27 municípios da RMS. Um painel com resíduos reais
> e informalidade `pendente` é um painel **válido** — nunca inventamos número.

## Arquitetura
`config/` (regiões, municípios, coeficientes) → `pipeline/` (Polars: fontes →
transform → modelo → render) → `site/data.json` → painel estático em `site/`.

Stack: Python + Polars, uv, HTML/CSS/JS vanilla. Sem framework, sem build step no front.

## Aviso
Os números de catadores informais são subcontados pelas bases oficiais — trate-os
como piso. Calibre os coeficientes do modelo com gravimetria e dados locais antes
de publicar qualquer projeção externamente.

## Licença
MIT.
