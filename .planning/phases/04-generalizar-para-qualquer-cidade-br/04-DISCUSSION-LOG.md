# Phase 4: Generalizar para qualquer cidade BR - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 4-generalizar-para-qualquer-cidade-br
**Areas discussed:** Fronteira "sem código", ibge.refresh() (GEN-01), snis.refresh() (GEN-02), Erro amigável + guia 5min (GEN-03/04)

---

## Fronteira "sem código" — sucesso para região nova

| Option | Description | Selected |
|--------|-------------|----------|
| Identidade auto, resto pendente | ibge.refresh resolve código+pop; SNIS/informalidade/RAIS pendente honesto; painel válido = estrutura+flags corretos | ✓ |
| Tudo auto via rede | Build busca IBGE+SNIS+informalidade online; quebra build offline/determinístico | |
| Só baseline (IBGE+SNIS) | Generaliza identidade+resíduos; informalidade/RAIS explicitamente RMS-only | |

**User's choice:** Identidade auto, resto pendente (D-01)
**Notes:** Alinha com a regra sagrada; painel majoritariamente pendente ainda é válido.

## Desacoplamento da RMS

| Option | Description | Selected |
|--------|-------------|----------|
| Robustez mínima | Tolerar subregiao null; renomear taxa_inf_media_rms→genérico; informalidade hardcoded fica (não casa por slug → pendente) | ✓ |
| Desacoplamento total | Generalizar ibge_informalidade.py e rais.py para a região ativa | |
| Deixar como está | Não mexer; risco de stack trace / rótulo "RMS" vazando | |

**User's choice:** Robustez mínima (D-02)
**Notes:** Informalidade-para-todos vira fase futura (Deferred).

## Contrato de regions.yml

| Option | Description | Selected |
|--------|-------------|----------|
| Só nome+uf obrigatórios | Município: nome+uf; subregiao opcional. Região: nome obrigatório; destaque/fonte opcionais | ✓ |
| Manter campos atuais | Exigir destaque+fonte na região como hoje | |
| Você decide | Planner define o mínimo conforme transform/render | |

**User's choice:** Só nome+uf obrigatórios (D-03)

---

## ibge.refresh() — disparo e escopo

| Option | Description | Selected |
|--------|-------------|----------|
| Explícito, região-alvo | `obs refresh-ibge --region X`, upsert; build offline | ✓ |
| Explícito, cache inteiro | Reresolve todas as regiões, reescreve municipios.csv | |
| Auto no build | Build busca município faltante na hora; quebra build offline | |

**User's choice:** Explícito, região-alvo (D-04)

## ibge.refresh() — fonte de população

| Option | Description | Selected |
|--------|-------------|----------|
| Censo 2022 | Pop. oficial do Censo 2022; fonte_pop = "IBGE Censo 2022"; consistente com informalidade | ✓ |
| Estimativa anual (6579) | Estimativa populacional; mais atual mas instável/determinismo | |
| Você decide | Planner escolhe agregado conforme API | |

**User's choice:** Censo 2022 (D-05)

## ibge.refresh() — upsert de linhas curadas

| Option | Description | Selected |
|--------|-------------|----------|
| Só preenche vazios | Resolve codigo_ibge/populacao só onde faltam; preserva curadoria (Sorocaba SINISA); idempotente | ✓ |
| Sobrescreve tudo | Sempre regrava com Censo 2022; perde pop. urbana curada | |
| Sobrescreve com flag | Sobrescreve exceto linhas com pop_manual: true | |

**User's choice:** Só preenche vazios (D-06)

---

## snis.refresh() — nível de automação

| Option | Description | Selected |
|--------|-------------|----------|
| Automatizar via scraper | Promover scrape_snis.py a snis.refresh(region); `obs refresh-snis --region X`; recipe já decifrado | ✓ |
| Só documentar | Manter script avulso + refresh_snis.md; sem snis.refresh() | |
| Automatizar + fallback doc | Automatizar com doc de fallback para fragilidade do portal | |

**User's choice:** Automatizar via scraper (D-07)
**Notes:** refresh_snis.md vira doc de uso/fallback de qualquer forma.

## snis.refresh() — formato de saída

| Option | Description | Selected |
|--------|-------------|----------|
| Um CSV por região | snis_<chave-regiao>.csv; load() concatena; município sem dado → pendente | ✓ |
| Um CSV por município | Mais granular mas explode número de arquivos | |
| Você decide | Planner define conforme scrape_snis.py produz hoje | |

**User's choice:** Um CSV por região (D-08)

---

## Erro amigável (GEN-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-soft + sugestão | Não aborta; sugere nome próximo; lista não resolvidos; build vira pendente | ✓ |
| Abortar com mensagem clara | Para no primeiro inválido, sem stack trace | |
| Você decide | Planner define, sem stack trace | |

**User's choice:** Fail-soft + sugestão (D-09)

## Guia "5 minutos" (GEN-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Seção no README | Fluxo honesto de 4 passos; deixa claro o que é auto vs pendente | ✓ |
| Doc separado (docs/) | Arquivo próprio linkado do README | |
| Você decide | Planner escolhe local | |

**User's choice:** Seção no README (D-10)

---

## Claude's Discretion

- Detalhes da API IBGE (endpoint de localidades por UF, agregado do Censo 2022, formato de chamada) — respeitar D-05 e build offline.
- Algoritmo de similaridade para sugestão de nome (D-09).
- Estrutura interna de snis.refresh() ao promover scrape_snis.py (D-07/D-08).
- Conjunto exato de campos opcionais em regions.yml (D-03).

## Deferred Ideas

- Informalidade/RAIS para qualquer região (generalizar ibge_informalidade.py/rais.py) — fase futura.
- Comparação de pares (já Out of Scope v1).
- Check de CI em pull requests (build sem deploy) — herdado da Fase 3.
- Cache de população por estimativa anual (agregado 6579) — descartado em favor de Censo 2022.
