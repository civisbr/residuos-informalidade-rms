# Observatório de Resíduos & Informalidade

[![Build](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg)](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml) **[Ver painel ao vivo →](https://civisbr.github.io/residuos-informalidade-rms/)**

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

## Crie o painel da sua cidade
Edite `config/regions.yml`, adicione uma região com a lista de municípios e rode
`uv run obs build --region <sua_chave>`. Os dados de resíduos entram em
`data/raw/snis/` (ver `scripts/refresh_snis.md`). Sem dado, fica pendente.

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
