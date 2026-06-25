# Phase 5: Camada viva (operacional) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 5-camada-viva-operacional
**Areas discussed:** Estado real da operação / seed, Origem & formato da telemetria, Real vs Projetado, Apresentação no painel

---

## Estado real da operação / seed

### Estado da operação

| Option | Description | Selected |
|--------|-------------|----------|
| Ainda não roda / sem dado | Operação não começou; fase entrega esqueleto vivo (schema+source+painel), estado vazio honesto | ✓ |
| Piloto com dado parcial | Alguns meses de medição real para commitar como seed | |
| Dado de exemplo marcado | Dado de demonstração rotulado como exemplo/fictício | |

**User's choice:** Ainda não roda / sem dado → "esqueleto vivo" (D-01).

### Estado vazio

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholder honesto + contrato visível | Seção com aviso "sem medição real" + CSV-template vazio documentado committed | ✓ |
| Seção oculta até ter dado | Camada viva só aparece quando houver ao menos uma linha real | |

**User's choice:** Placeholder honesto + contrato visível (D-02).

---

## Origem & formato da telemetria

### Granularidade

| Option | Description | Selected |
|--------|-------------|----------|
| Mês × município | Uma linha por (mês, município); casa com baseline e série temporal | ✓ |
| Mês × cliente | Uma linha por (mês, cliente) com município em coluna; agrega na UI | |
| Mês × região (agregado) | Uma linha por mês para a região inteira | |

**User's choice:** Mês × município (D-03).

### Entrada (escopo de operacao.py)

| Option | Description | Selected |
|--------|-------------|----------|
| Só load() do CSV commitado | Operador edita/substitui CSV à mão; operacao.py só load() | ✓ |
| load() + refresh() de planilha | refresh() puxa de planilha exportada e regrava o local | |

**User's choice:** Só load() do CSV commitado (D-04).

### Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Medidas brutas do operador | t coletada, larva, frass, partilha R$, n clientes; espelha model.project() p/ real×projetado 1:1 | ✓ |
| Brutas + metadados de qualidade | Medidas + procedência/flag por linha (frass calculado vs pesado) | |

**User's choice:** Medidas brutas do operador (D-05). Nota: procedência de medidas derivadas fica como discrição do planner, sem reintroduzir chute.

---

## Real vs Projetado

### Relação telemetria↔simulador

| Option | Description | Selected |
|--------|-------------|----------|
| Lado a lado (calibração) | "Projetamos X — medimos Y" por indicador, cores distintas; aproveita schema espelhado | ✓ |
| Painéis separados | Telemetria e simulador sem confronto direto; mais conservador | |
| Lado a lado, mas só acumulado | Compara real×projetado só no acumulado total, não mês a mês | |

**User's choice:** Lado a lado (calibração) (D-06).

### Referência da projeção

| Option | Description | Selected |
|--------|-------------|----------|
| Modelo alimentado pelo real | model.project() sobre o input real do mês; valida coeficientes de conversão | ✓ |
| Cenário padrão do simulador | Compara contra projeção do cenário default; confunde escala com coeficiente | |

**User's choice:** Modelo alimentado pelo real (D-07). Reuso de model.project() preserva paridade (D-08).

---

## Apresentação no painel

### Local/escopo

| Option | Description | Selected |
|--------|-------------|----------|
| Seção regional dedicada | "Operação ao vivo" após o simulador, agregando a região; acende quando há dado | ✓ |
| Por município + resumo regional | Bloco de telemetria no card dos municípios que operam + resumo no topo | |
| Aba/visão separada | Aba "Baseline" vs "Operação"; separação máxima, mas adiciona navegação | |

**User's choice:** Seção regional dedicada (D-09).

### Gráfico

| Option | Description | Selected |
|--------|-------------|----------|
| SVG inline à mão | JS vanilla desenha série; zero dependência, respeita "sem build step" | ✓ |
| Lib leve via CDN | uPlot/Chart.js via CDN; menos código, mas dependência externa | |
| Tabela + barras CSS | Tabela mensal com mini-barras CSS; máxima simplicidade | |

**User's choice:** SVG inline à mão (D-10).

### Acumulado (multi-seleção)

| Option | Description | Selected |
|--------|-------------|----------|
| Desvio de aterro (t) | Toneladas desviadas acumuladas; espelha desviado_t_ano | ✓ |
| Renda a catadores (R$) | R$ acumulados via partilha; conecta com a Fase 2 | ✓ |
| CO2e evitado (t) | t CO2e evitadas + carros equivalentes | ✓ |
| Bioconversão (larva+frass) | Larva seca e frass acumulados | ✓ |

**User's choice:** Todos os 4 indicadores (D-11).

---

## Claude's Discretion

- Nomes/unidades exatos das colunas do CSV (kg vs t para larva/frass) — validar contra model.project().
- Onde computar o projetado da calibração (render.py build vs app.js front) — reusar model.project(), preservar paridade.
- Tratamento de meses sem projeção possível (input incompleto) — honesto, não zero.
- Forma do estado vazio no payload (`operacao: []` vs ausente).
- Paleta/rótulos das 3 classes — desde que visualmente inconfundíveis.

## Deferred Ideas

- `refresh()` de planilha externa para operacao.py.
- Calibração automática dos coeficientes (recalibrar coefficients.yml a partir do real).
- Telemetria por cliente (grão mais fino).
- Telemetria por município no card (em vez de seção regional).
- Informalidade/RAIS para qualquer região (herdado da Fase 4).
