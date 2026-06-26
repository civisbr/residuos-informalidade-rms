---
phase: 04-generalizar-para-qualquer-cidade-br
plan: 03
subsystem: pipeline
tags: [snis, scraper, cli, python, yaml, requests, polars]

# Dependency graph
requires:
  - phase: 04-01
    provides: ibge.refresh() e refresh-ibge --region no CLI
  - phase: 04-02
    provides: rename taxa_inf_media, buildCitySelect dinâmico
provides:
  - snis.refresh(region, root, ano, exclude) em pipeline/sources/snis.py
  - obs refresh-snis --region <chave> no CLI
  - UF_NOMES com 27 estados em scripts/scrape_snis.py
affects:
  - 04-04-doc-readme
  - qualquer fase que use snis.refresh() ou obs refresh-snis

# Tech tracking
tech-stack:
  added: []
  patterns:
    - wrapper fino que delega para cmd_build() via import direto com sys.path.insert
    - validação de region via yaml.safe_load antes de montar caminho (T-04-09 path traversal)
    - lazy import de requests dentro de _session() — não vaza para build offline

key-files:
  created: []
  modified:
    - scripts/scrape_snis.py
    - pipeline/sources/snis.py
    - pipeline/cli.py

key-decisions:
  - "D-07: snis.refresh() promove scripts/scrape_snis.py via import direto com sys.path.insert — requests lazy dentro de _session()"
  - "D-08: snis.refresh() grava data/raw/snis/snis_{region}.csv; snis.load() glob *.csv consome automaticamente"
  - "T-04-09: region validada contra regions.yml via yaml.safe_load antes de montar caminho — path traversal prevenido"
  - "UF_NOMES expandido para 27 estados BR — Pitfall 4 corrigido"

patterns-established:
  - "Pattern refresh(region): validar region em YAML antes de qualquer I/O de arquivo"
  - "Pattern lazy import: requests e outros pacotes de rede importados dentro da função de rede, nunca no topo do módulo"

requirements-completed: [GEN-02]

# Metrics
duration: 2min
completed: 2026-06-24
---

# Phase 04 Plan 03: Promover scraper SNIS a snis.refresh() + refresh-snis CLI Summary

**snis.refresh() exposto como `obs refresh-snis --region <chave>`, com UF_NOMES para 27 estados e validação de path traversal via yaml.safe_load**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-24T12:50:59Z
- **Completed:** 2026-06-24T12:52:50Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `snis.refresh(region, root, ano, exclude)` implementado em `pipeline/sources/snis.py`: delega para `scrape_snis.cmd_build()` via import direto; region validada contra `regions.yml` antes de montar `snis_{region}.csv` (path traversal prevenido); `import requests` permanece lazy dentro de `_session()` — importar `snis` offline não puxa rede
- `UF_NOMES` expandido de `{"SP": "São Paulo"}` para todos os 27 estados BR em `scripts/scrape_snis.py`, corrigindo Pitfall 4 que causava falha silenciosa para regiões fora de SP
- `obs refresh-snis --region <chave>` disponível com `--ano` e `--exclude` opcionais; `uv run obs build --region rms` e `uv run pytest -q` (23 testes) passam sem regressão

## Task Commits

1. **Task 1: Expandir UF_NOMES e adicionar snis.refresh()** - `830e3d6` (feat)
2. **Task 2: Adicionar cmd_refresh_snis e sub-parser refresh-snis ao CLI** - `0cfaf31` (feat)

## Files Created/Modified

- `scripts/scrape_snis.py` - UF_NOMES expandido para 27 estados (AC..TO incluindo DF, MG, etc.)
- `pipeline/sources/snis.py` - refresh() adicionado após load(); load() intacto; import yaml adicionado ao topo; validação de region + delegação para cmd_build
- `pipeline/cli.py` - cmd_refresh_snis(args) e sub-parser refresh-snis com --region required, --ano, --exclude

## Decisions Made

- Import direto de `scrape_snis.cmd_build` via `sys.path.insert(0, str(root/"scripts"))` em vez de subprocess — requests já é lazy dentro de `_session()`, logo não vaza para o namespace de produção quando apenas `snis.load()` é chamada (Open Question 2 do RESEARCH.md, recomendação adotada)
- Validação de `region` contra `regions.yml` antes de montar `f"snis_{region}.csv"` — região com `../` não existe no YAML e é rejeitada com mensagem amigável em vez de stack trace (T-04-09)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Nenhum. O portal SNIS não foi acionado nesta execução (operação offline de promoção do scraper existente). Testes de rede ficam pendentes até o usuário rodar `obs refresh-snis --region rms` em ambiente com acesso ao portal SNIS (app4.cidades.gov.br).

## Known Stubs

Nenhum. load() permanece intacto e consome os CSVs existentes; refresh() não foi invocado contra a rede nesta execução (bloqueio esperado — rede do portal SNIS pode não estar disponível no ambiente de CI/execução automatizada). O comportamento offline foi validado: sanitização de chave via regions.yml, UF_NOMES completo, snis.load() concatenando CSVs existentes, importação sem puxar rede.

## Threat Flags

Nenhum. A superficie de segurança introduzida (escrita de arquivo com nome derivado de `region`) foi mitigada via validação obrigatória em `regions.yml` antes de montar o caminho (T-04-09). Não há nova superficie não mapeada no threat model.

## Next Phase Readiness

- `obs refresh-snis --region <chave>` pronto para uso por terceiros
- Plan 04-04 (doc README "5 minutos") pode referenciar `obs refresh-snis` como passo 3 do fluxo D-10

---
*Phase: 04-generalizar-para-qualquer-cidade-br*
*Completed: 2026-06-24*
