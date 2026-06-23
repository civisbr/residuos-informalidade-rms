# Phase 2: Camada de informalidade - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 2-camada-de-informalidade
**Areas discussed:** Fonte e granularidade (INFO-01), O que o indicador mede, Proxy de formalização (INFO-02), Painel + nota subcontagem (INFO-03/04)

---

## Fonte e granularidade (INFO-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Censo 2022 (por município) | Base municipal real para os 27; cumpre regra sagrada; menos atual | |
| Censo 2022 + PNAD regional | Censo municipal (real) + PNAD como contexto regional (estimativa rotulada) | ✓ |
| Só PNAD Contínua | Mais atual, mas só regional/UF — não por município; forçaria pendência em massa | |

**User's choice:** Censo 2022 + PNAD regional
**Notes:** PNAD entra apenas como contexto regional rotulado como estimativa, nunca atribuída a município. Acesso via snapshot CSV commitado + refresh documentado (discrição, padrão snis/ibge).

---

## O que o indicador mede

| Option | Description | Selected |
|--------|-------------|----------|
| Geral (município) + lente catador | Taxa de informalidade geral (def. IBGE) real para os 27 + lente de catadores ligada ao proxy | ✓ |
| Só setor de resíduos/catadores | Foco em CBO/CNAE de resíduos; muitos viriam pendente no nível municipal | |
| Só informalidade geral | Apenas taxa geral, sem recorte de catadores; perde conexão com a tese | |

**User's choice:** Geral (município) + lente catador
**Notes:** Indicador-base = informalidade geral do trabalho (Censo, real); lente de catadores é complementar e conecta ao proxy INFO-02 (cooperados SNIS + RAIS).

---

## Proxy de formalização (INFO-02)

| Option | Description | Selected |
|--------|-------------|----------|
| RAIS formal + cooperados (ambos reais) | Formais (RAIS/CAGED CNAE resíduos) ÷ (formais + cooperados); tudo citado | ✓ |
| Cooperados ÷ catadores estimados | Razão sobre estimativa de total; introduz flag estimativa | |
| Só emprego formal RAIS no setor | 100% real, mas não mede lado informal/cooperado | |

**User's choice:** RAIS formal + cooperados (ambos reais)
**Notes:** Nada inventado na fórmula. Edge case (formais e cooperados ambos null/0) → proxy pendente, não 0/0.

---

## Painel + nota subcontagem (INFO-03/04)

| Option | Description | Selected |
|--------|-------------|----------|
| Seção por município + célula regional | Seção na visão do município + célula no region-strip; reusa tags | ✓ (INFO-03) |
| Só seção por município | Apenas por município, sem agregado | |
| Só célula regional | Só resumo regional; não cumpre "por município" | |
| Nota fixa sempre visível | Texto não-colapsável na seção; sempre à vista | ✓ (INFO-04) |
| Ícone/tooltip ao lado do número | Mais limpo, mas pode passar despercebido | |
| Rodapé/caveat geral | Menos destaque | |

**User's choice:** Seção por município + célula regional (INFO-03); Nota fixa sempre visível (INFO-04)
**Notes:** Reusar o sistema de tags existente (real/estimativa/pendente); não criar flag paralelo. Nota de subcontagem com linguagem de "piso".

---

## Claude's Discretion

- Códigos CNAE exatos do setor de resíduos para RAIS/CAGED (pesquisa).
- Variáveis/tabelas SIDRA do Censo 2022 para a taxa de informalidade municipal (pesquisa).
- Estrutura dos CSVs e se a fonte é um módulo único `ibge_informalidade.py` ou separados (planner).
- Layout fino da seção no app.js/index.html (respeitando D-08..D-10).

## Deferred Ideas

- Automação do refresh() das fontes → Fase 4 (GEN-02).
- Recorte municipal de catadores por CBO se surgir fonte confiável → futuro.
- Série temporal de informalidade → Fase 5 / fora do v1.
- Mapa coroplético → Out of Scope v1.
