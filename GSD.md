# GSD.md — Board de milestones

Modo get-shit-done: cada milestone é um incremento shippável com **definição de
pronto** clara e um checklist executável. Faça um por vez, rode `uv run pytest`,
marque, commit. Não comece o próximo antes do anterior estar verde.

Legenda: `[x]` feito · `[ ]` a fazer · `[~]` em andamento

---

## M0 — Esqueleto que builda offline ✅
**Pronto quando:** `uv run obs build` gera `site/data.json` sem rede e os testes passam.
- [x] Estrutura de pastas + `pyproject.toml` (uv) + CLI `obs`
- [x] `config/regions.yml` com os 27 municípios da RMS
- [x] Adaptadores `sources/ibge.py` (cache) e `sources/snis.py` (CSV local)
- [x] `transform.py` (Polars) com flags real/estimativa/pendente
- [x] `model.py` + paridade com `app.js`
- [x] Painel `site/` lendo `data.json`
- [x] Testes de sanidade (`tests/`)

## M1 — Baseline real da RMS
**Pronto quando:** os 27 municípios têm linha no SNIS (real ou pendente honesto),
e Sorocaba + Porto Feliz estão completos a partir de fonte citável.
- [ ] Baixar a série histórica do SNIS-RS (ver `scripts/refresh_snis.md`)
- [ ] Extrair gravimetria real do PMGIRS de Sorocaba (substituir `composicao` por dado local)
- [ ] Extrair RSU/reciclado/cooperados de Porto Feliz do PMGIRS 2017 (SMA-SP)
- [ ] Preencher os demais 25 municípios com o que o SNIS tiver; resto fica `pendente`
- [ ] Citar a fonte em cada linha (coluna `fonte`)

## M2 — Camada de informalidade
**Pronto quando:** o painel mostra, por município, um indicador de informalidade
com fonte, separado do que é estimativa.
- [ ] `sources/ibge_informalidade.py` (PNAD/Censo: ocupação informal)
- [ ] Proxy de formalização: RAIS/CAGED vs. catadores em cooperativa
- [ ] Card/seção de informalidade no painel, com flag de qualidade
- [ ] Nota explícita de subcontagem da população catadora

## M3 — Deploy contínuo no GitHub Pages
**Pronto quando:** push na `main` reconstrói `data.json` e publica o site.
- [ ] Revisar `.github/workflows/build.yml`
- [ ] Ativar Pages (branch/Actions) no repositório
- [ ] Badge de build no README + URL pública
- [ ] `data.json` commitado para o Pages funcionar mesmo sem rebuild

## M4 — Generalizar para qualquer cidade BR
**Pronto quando:** um terceiro consegue gerar o painel de outra região só editando
`regions.yml`, sem tocar em código.
- [ ] Implementar `ibge.refresh()` (API localidades + população)
- [ ] `snis.refresh()` documentado e (se viável) automatizado
- [ ] Validação amigável de erro quando município não resolve no IBGE
- [ ] Doc "Crie o painel da sua cidade em 5 minutos" no README

## M5 — Camada viva (operacional)
**Pronto quando:** dá pra sobrepor a telemetria da operação ao baseline público.
- [ ] Esquema de telemetria (t coletadas/mês por cliente, larva, frass, partilha)
- [ ] `sources/operacao.py` lendo a telemetria (CSV/planilha exportada)
- [ ] Série temporal no painel: baseline público + medições reais lado a lado
- [ ] Painel de impacto acumulado (desvio de aterro, renda a catadores no tempo)

---

### Ideias / backlog frio
- Mapa coroplético da região (desvio de aterro por município)
- Comparação de pares (município vs. mediana da sub-região)
- Export de relatório PDF reprodutível por município
- Integração com o ecossistema CivisBR (repo público, metodologia versionada)
