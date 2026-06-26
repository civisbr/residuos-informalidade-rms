# Phase 5: Camada viva (operacional) - Research

**Researched:** 2026-06-25
**Domain:** Pipeline offline determinística (Polars) + painel vanilla (SVG inline) — telemetria operacional sobreposta ao baseline público
**Confidence:** HIGH (domínio 100% interno ao codebase; nenhuma dependência externa nova)

## Summary

Esta fase NÃO é greenfield nem envolve tecnologia nova: é uma **extensão estrutural** de
uma pipeline batch offline já madura e bem testada. Todo o stack necessário (Polars,
pyyaml, JS/SVG vanilla) já está instalado e em uso. Não há pacote a instalar, nem rede,
nem framework. O trabalho é: (1) criar a fonte `sources/operacao.py` espelhando
`sources/snis.py::load()`, (2) ligar a telemetria em `transform.py` e expor `operacao` no
payload de `render.to_payload()`, (3) reusar `model.project()` para a calibração
"projetado vs. real", e (4) desenhar uma série temporal SVG à mão em `app.js`.

O risco técnico central NÃO é a telemetria em si — é a **paridade `model.py`↔`app.js`
sem teste** (CONCERNS #7: `carros_equivalente` vs `carros` já divergiram). A calibração
D-06/D-07/D-08 depende dessa paridade: o "projetado" do confronto roda a MESMA lógica de
conversão. Esta fase deve fechar esse buraco com um teste de paridade cross-language, ou a
calibração mostrará números que divergem silenciosamente entre build e painel.

O segundo eixo crítico é a **regra sagrada**: a operação ainda não roda, então a fase
entrega "esqueleto vivo" — schema + source + seção do painel com estado vazio honesto
(`operacao: []` + CSV-template só com header). Nunca inventar telemetria. O grão é
mês×município (`AAAA-MM` + slug), e a classe inteira carrega flag `real (operação)`,
visualmente inconfundível com baseline (`real`/`estimativa`/`pendente`) e simulador
(`projeção`).

**Primary recommendation:** Espelhe `snis.py` para `operacao.py::load()`; compute o
projetado da calibração no **build** (`transform.py`/`render.py`) aplicando os coeficientes
de conversão sobre o `t_org_coletada` real do mês (NÃO inverta para `clientes`/`kg_dia`);
exponha `operacao: []` no payload; e adicione um teste de paridade que assegura que
`model.project()` e `app.js::project()` retornam os mesmos campos e valores antes de
construir a calibração em cima deles.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Leitura da telemetria (CSV → DataFrame) | Sources (`operacao.py`) | — | Padrão `load()` offline; espelha `snis.py` [VERIFIED: codebase] |
| Junção telemetria↔baseline + acumulados regionais | Transform (`transform.py`) | — | `build_region`/`region_totals` já é o ponto de junção por slug [VERIFIED: codebase] |
| Projetado da calibração (real×modelo) | Build (`render.py`/`transform.py`) | Front (`app.js`) | Reusa `model.project()`; build offline preserva determinismo (D-08, Constraint) [VERIFIED: codebase] |
| Forma do payload `operacao` | Render (`to_payload`) | — | Já separa classes (`municipios` vs `coeficientes`); novo padrão segue [VERIFIED: codebase] |
| Série temporal SVG + seção "Operação ao vivo" | Front (`app.js`/`index.html`/`styles.css`) | — | Sem framework, sem build step (Constraint, D-10) [VERIFIED: codebase] |
| Paridade de conversão real×projetado | Model (`model.py`) ↔ Front (`app.js::project`) | Tests (paridade) | Contrato cross-language; risco CONCERNS #7 [VERIFIED: codebase] |

## Project Constraints (from CLAUDE.md)

Diretivas acionáveis extraídas de `CLAUDE.md` — têm a mesma autoridade das decisões
travadas em CONTEXT.md. O planner NÃO pode recomendar nada que as contrarie:

1. **Regra sagrada — nunca invente número.** Sem dado público → `pendente`; aqui, sem
   telemetria → estado vazio honesto, nunca telemetria inventada (D-01/D-02).
2. **Todo indicador carrega flag** `real | estimativa | pendente`. A telemetria adiciona
   a classe `real (operação)`; medidas derivadas (ex.: frass calculado, não pesado) devem
   ser sinalizadas, sem reintroduzir chute (D-05).
3. **Baseline × projeção × telemetria visualmente separados.** Nunca apresentar projeção
   como medição, nem medição real como baseline público (D-06).
4. **Coeficientes ficam em `config/coefficients.yml`** — a fase compara contra eles,
   **não os reescreve** (calibração automática é Deferred).
5. **Build offline e determinístico** (`uv run obs build` = mesmo resultado, sem rede).
   `operacao.py` só `load()` preserva isso (D-04). Cuidado com não-determinismo se o
   projetado for computado no render.
6. **Junção por `base.slug`** — chave do projeto (`slug(municipio)`, NÃO código IBGE).
7. **Paridade `model.py`↔`app.js::project()`** — mudou um, muda o outro e ajusta o teste.
8. **Polars, não pandas.** Python 3.11+, type hints, funções puras quando der.
9. **Front sem framework, sem build step** — HTML+CSS+JS vanilla lendo `data.json`.
   Visualização em SVG inline à mão (D-10).
10. **Texto ao usuário em PT-BR**; commits no imperativo PT-BR (sem `Co-Authored-By`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Esqueleto vivo — a operação ainda não roda; a fase NÃO commita dado real e NÃO
  inventa número. Entrega schema + `sources/operacao.py` + seção no painel.
- **D-02:** Estado vazio = placeholder honesto + contrato visível. Sem telemetria, a seção
  aparece com aviso explícito ("Operação ainda não iniciada — sem medição real"). Commitar
  CSV-template vazio com cabeçalho documentado em `data/raw/operacao/operacao_rms.csv`
  (só header).
- **D-03:** Grão = mês × município. Uma linha por (mês `AAAA-MM`, município), agregados
  daquele município no mês. Junção por `slug(nome)`.
- **D-04:** `sources/operacao.py` só tem `load()` lendo CSV commitado em
  `data/raw/operacao/*.csv`. Sem `refresh()` de rede nesta fase.
- **D-05:** Schema = medidas brutas do operador, espelhando os MESMOS quantitativos que
  `model.project()` produz. Colunas-base: `mes` (AAAA-MM), `municipio`, `n_clientes`,
  `t_org_coletada`, `larva_*` (seca/úmida), `frass_*`, `partilha_rs`. Classe inteira flag
  `real (operação)`; medidas estimadas/derivadas sinalizadas sem chute.
- **D-06:** Vista de calibração lado a lado — "projetamos X (modelo) — medimos Y (real)"
  por indicador, com cores/estilos distintos.
- **D-07:** Referência = modelo alimentado pelo real. O "projetado" do confronto roda
  `model.project()` sobre o INPUT real medido do mês (t coletada / n clientes), não sobre
  o cenário default. Objetivo: validar os coeficientes de conversão contra a realidade.
- **D-08:** Reusar `model.project()` (não reimplementar). Preservar paridade
  `model.py`↔`app.js::project()`.
- **D-09:** Seção regional dedicada ("Operação ao vivo") depois do simulador; "acende"
  quando houver dado.
- **D-10:** Série temporal em SVG inline à mão (JS vanilla). Zero dependência; cores
  distintas real×projetado.
- **D-11:** Impacto acumulado destaca 4 indicadores: (1) desvio de aterro acumulado (t,
  espelha `desviado_t_ano`), (2) renda a catadores acumulada (R$), (3) CO2e evitado
  acumulado (t + carros), (4) bioconversão acumulada (larva seca + frass).

### Claude's Discretion
- Nomes exatos das colunas do CSV e unidades (kg vs t para larva/frass) — validar contra
  `model.project()` e o que o operador realmente pesa, mantendo o espelhamento.
- Onde o "projetado da calibração" é computado (build em `render.py` vs front em `app.js`)
  — desde que reuse `model.project()` e preserve a paridade. Atenção ao build offline se
  for no render.
- Como a calibração lida com meses sem projeção possível (input incompleto) — tratamento
  honesto (célula vazia, não zero).
- Detalhe do estado vazio no payload (`operacao: []` vs ausente) e como
  `render.to_payload()` expõe a nova classe sem quebrar consumidores atuais.
- Paleta/rótulos exatos das 3 classes no painel — desde que visualmente inconfundíveis.

### Deferred Ideas (OUT OF SCOPE)
- `refresh()` de planilha externa (Google Sheets/export) para `operacao.py`.
- Calibração automática dos coeficientes (reescrever `coefficients.yml` a partir do real).
- Telemetria por cliente (grão mês×cliente).
- Telemetria por município no card (em vez de seção regional).
- Informalidade/RAIS para qualquer região (herdado da Fase 4, fora do núcleo).
- Mapa coroplético, comparação de pares município×mediana, export PDF.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-01 | Esquema de telemetria definido (t coletadas/mês, larva, frass, partilha) | Schema concreto em "Pattern 1" (colunas/unidades/dtypes) + CSV-template; espelha `model.project()` outputs [VERIFIED: codebase] |
| LIVE-02 | Fonte `sources/operacao.py` lê a telemetria (CSV commitado) | Molde `snis.py::load()` em "Pattern 2"; padrão de frame vazio com coluna `key` [VERIFIED: codebase] |
| LIVE-03 | Série temporal: baseline público + medições reais lado a lado | Calibração real×projetado em "Pattern 4"; SVG inline em "Pattern 5"; reuso de `model.project()` [VERIFIED: codebase] |
| LIVE-04 | Painel de impacto acumulado (desvio de aterro, renda a catadores no tempo) | Acumulados regionais em "Pattern 3" (`region_totals` estendido); 4 cards D-11 [VERIFIED: codebase] |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | >=1.0 (já instalado) | Leitura CSV + junção + agregação dos acumulados | Stack obrigatório do projeto (CLAUDE.md: "Polars não pandas") [VERIFIED: pyproject.toml] |
| pyyaml | >=6.0 (já instalado) | Leitura de `coefficients.yml`/`regions.yml` (se `operacao.py` precisar validar região) | Já em uso em `cli.py`, `snis.py` [VERIFIED: pyproject.toml] |
| JS/SVG vanilla | nativo do browser | Série temporal inline à mão (D-10) | Sem framework, sem build step (Constraint) [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.1.1 (dev, já instalado) | Teste offline da fonte + paridade + acumulados | Sempre — `tests/test_pipeline.py` é o padrão [VERIFIED: pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SVG inline à mão | Chart.js / D3 / Plotly | PROIBIDO — viola "sem framework, sem build step" (D-10). Não considerar. |
| Computar projetado no front | Computar no build (`render.py`) | RECOMENDADO no build — determinístico, testável, e o painel não precisa reimplementar a inversão. Front ainda precisa de `project()` para o simulador, mas a calibração pode vir pronta no payload. |

**Installation:** Nenhuma. Todas as dependências já estão em `pyproject.toml`. Esta fase não
instala nada.

## Package Legitimacy Audit

> Não aplicável — esta fase NÃO instala pacotes externos. Todas as dependências
> (`polars`, `pyyaml`, `pytest`) já estão declaradas em `pyproject.toml` e em uso.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| (nenhum novo) | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
config/regions.yml ───────────────────────┐
config/municipios.csv ─► ibge.load() ──────┤
data/raw/snis/*.csv  ─► snis.load() ───────┤
config/coefficients.yml ───────────────────┤
data/raw/operacao/*.csv ─► operacao.load() ┤   ◄── NOVO (D-04)
                                            ▼
                        transform.build_region()
                        (join baseline por slug + flag)
                                            │
                        ┌───────────────────┴────────────────────┐
                        ▼                                         ▼
            transform.region_totals()              transform.build_operacao()  ◄── NOVO
            (acumulados baseline)                  (série mensal + projetado via
                        │                           model.project() sobre real + acumulados D-11)
                        └───────────────────┬────────────────────┘
                                            ▼
                        render.to_payload() ◄── model.defaults()/model.project()
                        (adiciona chave "operacao": [] honesto)
                                            ▼
                                site/data.json  (commitado)
                                            ▼
         site/app.js (fetch) ─► painel + simulador + SEÇÃO "Operação ao vivo"
                                 (série SVG real×projetado + 4 cards acumulados)
                                 app.js::project() ≡ model.project()  (paridade testada)
```

### Recommended Project Structure
```
pipeline/
├── sources/
│   └── operacao.py       # NOVO — load() lê data/raw/operacao/*.csv (espelha snis.py)
├── transform.py          # ESTENDER — build_operacao() (série + projetado + acumulados)
├── render.py             # ESTENDER — to_payload() expõe "operacao"
├── model.py              # REUSAR project() (não tocar a lógica)
└── cli.py                # ESTENDER — cmd_build carrega operacao.load()
data/raw/operacao/
└── operacao_rms.csv      # NOVO — template só com header documentado (D-02)
site/
├── index.html            # ESTENDER — slot da seção "Operação ao vivo"
├── styles.css            # ESTENDER — classes da nova seção + tag "operação"
└── app.js                # ESTENDER — renderOperacao() + SVG; project() inalterado
tests/
└── test_pipeline.py      # ESTENDER — operacao.load(), acumulados, PARIDADE model↔app.js
```

### Pattern 1: Schema da telemetria (LIVE-01, D-05) — espelha `model.project()`

**What:** O CSV deve carregar as medidas brutas do operador que casam 1:1 com os outputs de
`model.project()`. O mapeamento exato (a pergunta #1 do planner):

| Coluna CSV (medida real) | dtype | Unidade | Output `project()` correspondente | Coef. que valida |
|--------------------------|-------|---------|-----------------------------------|------------------|
| `mes` | String | `AAAA-MM` | — (eixo temporal) | — |
| `municipio` | String | nome | — (vira `key` via slug) | — |
| `n_clientes` | Int64 | contagem | input (`clientes`) | escala |
| `t_org_coletada` | Float64 | **t/mês** | `desviado_t_ano` (÷12 para comparar) | — (é o input medido) |
| `larva_umida_t` | Float64 | **t/mês** | `larva_seca_t_ano` deriva de úmida | `conversao_larva_umida` |
| `larva_seca_t` | Float64 | **t/mês** | `larva_seca_t_ano` | `larva_seca_sobre_umida` |
| `frass_t` | Float64 | **t/mês** | `frass_t_ano` | `frass_sobre_organico` |
| `partilha_rs` | Float64 | **R$/mês** | `fundo_partilha_ano` | `partilha_padrao_pct` |
| `qualidade` | String | `real`/`estimativa` (por linha/medida) | — | flag de procedência (D-05) |
| `fonte` | String | texto livre (procedência) | — | citação (regra sagrada) |

**Unidade recomendada:** **toneladas (t)** para todas as massas, alinhando com
`project()` (que devolve `_t_ano`). O operador pesa em kg → o template deve documentar
"preencher em toneladas (kg ÷ 1000)" no header/comentário, OU usar colunas `_kg` e
converter em `load()`. **Recomendação:** colunas em `t` direto (menos conversão, casa com
o modelo); documentar no header.

**Procedência por medida (D-05):** o operador frequentemente PESA larva mas CALCULA frass
(estimativa). A coluna `qualidade` resolve no nível da linha; se for preciso granularidade
por-medida, o planner pode optar por uma convenção de sufixo ou uma coluna `frass_origem`.
**Recomendação minimalista:** uma coluna `qualidade` por linha + texto em `fonte`; não
multiplicar colunas de flag (evita complexidade; segue o padrão do SNIS que tem uma
`qualidade` por linha).

**When to use:** É o contrato LIVE-01. O planner valida os nomes finais contra `model.py`.

**Example (CSV-template — D-02, só header):**
```csv
# data/raw/operacao/operacao_rms.csv
# Telemetria REAL da operação (flag: real). Uma linha por (mes AAAA-MM, municipio).
# Massas em TONELADAS (t). partilha_rs em R$. Operação ainda não iniciada: sem linhas.
# Preencher a partir da pesagem real; nunca estimar sem marcar qualidade=estimativa + fonte.
mes,municipio,n_clientes,t_org_coletada,larva_umida_t,larva_seca_t,frass_t,partilha_rs,qualidade,fonte
```

### Pattern 2: `operacao.py::load()` — molde direto de `snis.py` (LIVE-02, D-04)

**What:** Função pura offline que lê todos os CSVs de `data/raw/operacao/`, concatena, e
devolve um DataFrame Polars com coluna `key` (slug). **Crucial:** quando não há linhas (só
o template com header), deve devolver um frame vazio MAS com a coluna `key`, senão os joins
em `transform` quebram (lição CR-01, ver CONCERNS / `test_cold_start_build`).

**When to use:** Sempre — é a fonte LIVE-02.

**Example:**
```python
# Source: espelho de pipeline/sources/snis.py::load() [VERIFIED: codebase]
"""Fonte Operação: telemetria real da coleta + bioconversão BSF.

Offline (único modo nesta fase): lê CSVs em data/raw/operacao/.
Grão = (mes AAAA-MM, municipio). Flag de classe: real (operação).
SEM refresh() de rede — operação ainda não roda (D-04).
"""
from __future__ import annotations
from pathlib import Path
import polars as pl
from .base import slug

RAW = Path("data/raw/operacao")

SCHEMA = {
    "mes": pl.String, "municipio": pl.String, "n_clientes": pl.Int64,
    "t_org_coletada": pl.Float64, "larva_umida_t": pl.Float64,
    "larva_seca_t": pl.Float64, "frass_t": pl.Float64,
    "partilha_rs": pl.Float64, "qualidade": pl.String, "fonte": pl.String,
}

def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        empty = pl.DataFrame(schema=SCHEMA)
        return empty.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0)
              for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    # filtra linhas-comentário/vazias do template; só linhas com mes preenchido
    df = df.filter(pl.col("mes").is_not_null())
    if df.height == 0:
        return df.with_columns(pl.lit(None, dtype=pl.String).alias("key"))
    return df.with_columns(
        pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")
    )
```

**Nota sobre o `#` no template:** `pl.read_csv` não pula linhas `#` por padrão. Duas
opções honestas: (a) usar `comment_prefix="#"` em `read_csv`, ou (b) NÃO commitar linhas
`#` no CSV e pôr a documentação num `data/raw/operacao/README.md` ao lado. **Recomendação:**
`comment_prefix="#"` mantém o contrato visível DENTRO do arquivo que o operador edita.

### Pattern 3: Acumulados regionais (LIVE-04, D-11) — em `transform.py`

**What:** A partir das linhas mensais, derivar a série temporal regional (somar por `mes`
sobre todos os municípios) e os 4 acumulados totais. Operação Polars `group_by`.

**When to use:** LIVE-04 — alimenta os 4 cards e o eixo X da série.

**Example:**
```python
# Source: padrão de region_totals() [VERIFIED: codebase]
def build_operacao(operacao: pl.DataFrame, coef: dict) -> dict:
    """Série mensal regional + projetado (model) + 4 acumulados (D-11).
    Estado vazio honesto: operacao sem linhas → {'serie': [], 'acumulados': None}.
    """
    if operacao.height == 0 or "mes" not in operacao.columns:
        return {"serie": [], "acumulados": None, "tem_dado": False}

    # série mensal regional: soma os municípios por mês
    serie = (
        operacao.group_by("mes")
        .agg([
            pl.col("n_clientes").sum().alias("n_clientes"),
            pl.col("t_org_coletada").sum().alias("real_desviado_t"),
            pl.col("larva_seca_t").sum().alias("real_larva_seca_t"),
            pl.col("frass_t").sum().alias("real_frass_t"),
            pl.col("partilha_rs").sum().alias("real_partilha_rs"),
        ])
        .sort("mes")
    )
    # projetado por mês: model alimentado pelo real (ver Pattern 4)
    # ... aplica coeficientes de conversão sobre real_desviado_t por linha ...

    acum = {
        "desviado_t": float(serie["real_desviado_t"].sum() or 0),
        "partilha_rs": float(serie["real_partilha_rs"].sum() or 0),
        "larva_seca_t": float(serie["real_larva_seca_t"].sum() or 0),
        "frass_t": float(serie["real_frass_t"].sum() or 0),
        # co2e e carros: derivar do desviado acumulado via coef (não medido direto)
    }
    return {"serie": serie.to_dicts(), "acumulados": acum, "tem_dado": True}
```

### Pattern 4: Calibração "modelo alimentado pelo real" (LIVE-03, D-07/D-08) — A QUESTÃO CENTRAL

**What:** O "projetado" do confronto NÃO é o cenário default do simulador. É o que o modelo
PREVERIA dado o input real do mês. **Insight matemático crítico:** todos os outputs de
conversão de `project()` são **lineares no `desviado`**:

```
desviado_t_ano   = clientes * kg_dia/1000 * 365
larva_seca_t_ano = desviado_t_ano * conversao_larva_umida * larva_seca_sobre_umida
frass_t_ano      = desviado_t_ano * frass_sobre_organico
co2e_t_ano       = desviado_t_ano * co2e_por_t_organico
```

Logo, para "alimentar o modelo com o real", **não é preciso inverter** `t_org_coletada` em
`clientes`/`kg_dia`. Basta usar o `desviado` real (= `t_org_coletada` do mês) como o
`desviado` e aplicar os MESMOS coeficientes. Isso valida exatamente os coeficientes de
conversão (D-07) e separa desvio de coeficiente de desvio de escala:

- **Projetado larva seca do mês** = `t_org_coletada * conversao_larva_umida * larva_seca_sobre_umida`
- **Real larva seca do mês** = `larva_seca_t` (medido)
- **Desvio de coeficiente** = real / projetado − 1.

**Duas formas de reusar `model.project()` (D-08), em ordem de preferência:**

1. **(RECOMENDADO) Chamar `project()` com input inverso trivial.** Como a conversão só
   depende de `desviado`, monte os args para que `desviado = t_org_coletada` (mensal). Ex.:
   `clientes=1, kg_dia = t_org_coletada * 1000 / 30.4` dá `desviado_t_ano ≈ t_org_coletada * 12`
   (anualizado). Para o confronto MENSAL, divida os `_t_ano` por 12. **Cuidado com
   anualização**: `project()` devolve t/ano; a telemetria é t/mês. Comparar maçã com maçã
   exige dividir o projetado por 12 OU multiplicar o real por 12. **Recomendação:**
   confronto em base **mensal** — divida os outputs `_t_ano` de `project()` por 12.
   `partilha` e `receita` usam `*12` (mensal→anual) e `gate_fee` — para a partilha real, o
   confronto é `partilha_rs` medido vs `n_clientes * gate_fee * partilha_pct/100` (mensal).

2. **(ALTERNATIVA, se inversão ficar artificial)** Extrair os coeficientes de `coef` e
   aplicá-los diretamente sobre `t_org_coletada` — MAS isso reimplementa a lógica de
   conversão fora de `project()`, ferindo D-08. **Só aceitável se acompanhada do teste de
   paridade** que garante que a aplicação direta == `project()`. Preferir a opção 1.

**ONDE computar (pergunta #2 do planner):** **No build (`transform.build_operacao` /
`render`)**, não no front. Razões: (a) `model.project()` em Python é a fonte canônica; (b)
o build é determinístico e testável; (c) o painel recebe a série já com `real` e
`projetado` por mês, e só desenha — não precisa reimplementar a inversão/anualização. O
front MANTÉM `project()` para o simulador interativo (inalterado), mas a calibração vem
pronta no payload. Isso minimiza superfície de divergência.

**Meses sem projeção possível (input incompleto, D-discretion):** se `t_org_coletada` é
null num mês, o projetado daquele indicador é **null** (célula vazia no gráfico/tabela),
**nunca zero** (zero seria afirmar "previmos zero", uma mentira). Mesma regra sagrada do
baseline.

**When to use:** É o coração de LIVE-03.

### Pattern 5: Série temporal SVG inline à mão (D-10) — JS vanilla

**What:** Desenhar duas séries (real × projetado) num SVG construído por string template,
sem dependência. Padrão mínimo: viewBox fixo, mapear (mes→x, valor→y) com escala linear,
emitir `<polyline>` por série + eixos + labels.

**When to use:** LIVE-03 visualização. Cores distintas real×projetado (D-06).

**Example:**
```javascript
// Source: técnica padrão de SVG inline; zero dependência (D-10)
function svgSerie(serie, campoReal, campoProj, opts = {}) {
  const W = 720, H = 240, P = 36;              // viewBox + padding
  if (!serie.length) return "";
  const xs = serie.map((_, i) => i);
  const ys = serie.flatMap(d => [d[campoReal], d[campoProj]].filter(v => v != null));
  const yMax = Math.max(1, ...ys), yMin = 0;
  const x = i => P + i * (W - 2 * P) / Math.max(1, serie.length - 1);
  const y = v => H - P - (v - yMin) / (yMax - yMin) * (H - 2 * P);
  // polyline ignora pontos null (quebra a linha honestamente)
  const path = campo => serie
    .map((d, i) => d[campo] == null ? null : `${x(i)},${y(d[campo])}`)
    .filter(Boolean).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" class="serie" role="img"
            aria-label="Série temporal real vs projetado">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" class="axis"/>
    <line x1="${P}" y1="${P}" x2="${P}" y2="${H - P}" class="axis"/>
    <polyline points="${path(campoProj)}" class="s-proj" fill="none"/>
    <polyline points="${path(campoReal)}" class="s-real" fill="none"/>
    ${serie.map((d, i) => `<text x="${x(i)}" y="${H - P + 14}"
       class="xlab">${d.mes.slice(2)}</text>`).join("")}
  </svg>`;
}
// CSS: .s-real{stroke:var(--desvio);stroke-width:2.5}
//      .s-proj{stroke:var(--ink-2);stroke-width:2;stroke-dasharray:4 3}
//      .axis{stroke:var(--line)} .xlab{font:10px monospace;fill:var(--ink-2);text-anchor:middle}
```

**Reuso de cor:** já existem vars `--desvio` (laranja) e `--ink-2` (cinza). Usar
`--desvio` para REAL (medição = destaque) e cinza tracejado para PROJETADO (modelo). Casa
com a convenção: projeção é sempre mais "apagada"/tracejada (D-06).

### Anti-Patterns to Avoid
- **Inverter `t_org_coletada` em `clientes`×`kg_dia` de forma elaborada:** desnecessário —
  a conversão é linear em `desviado`. Mantenha o input simples (Pattern 4 opção 1).
- **Computar a calibração no front reimplementando a anualização:** dobra a superfície de
  paridade. Compute no build.
- **Preencher mês sem dado com 0:** viola a regra sagrada. Use null/célula vazia.
- **Omitir a chave `operacao` do payload quando vazio:** consumidores futuros precisam de
  contrato estável → use `operacao: []` / `{serie:[], tem_dado:false}`, não ausência.
- **Adicionar `#` no CSV sem `comment_prefix`:** `read_csv` tentaria parsear o comentário.
- **Tocar a lógica de `model.project()`:** a fase compara contra coeficientes, não os muda.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conversão orgânico→larva/frass/CO2e | Recalcular coeficientes no `transform`/`app.js` | `model.project()` (D-08) | Única fonte; duplicar = divergência silenciosa (CONCERNS #7) |
| Normalização de nome de município | Regex/lower ad-hoc | `base.slug()` | Já robusto a acento/caixa; chave canônica do projeto |
| Concatenar CSVs de uma pasta | `os.walk`+csv manual | `snis.load()` pattern (`glob`+`pl.concat`) | Padrão testado, lida com frame vazio (CR-01) |
| Agregação mensal/regional | Loops Python | `pl.group_by().agg()` | Polars é o stack; determinístico e rápido |
| Gráfico de linha | Chart.js/D3 | SVG inline (Pattern 5) | Sem framework/build step é Constraint dura |

**Key insight:** O maior risco de "hand-roll" aqui é reimplementar a matemática de conversão
fora de `model.project()`. A regra D-08 existe justamente porque já houve divergência. Toda
conversão real→projetado deve passar por `project()` (ou ser provada equivalente por teste).

## Runtime State Inventory

> Esta fase NÃO é rename/refactor/migração — é adição de capacidade nova. A seção de
> inventário de estado runtime não se aplica.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — não há datastore; só CSV commitado e `data.json` gerado. | none |
| Live service config | None — build offline, sem serviço externo (D-04 sem refresh). | none |
| OS-registered state | None. | none |
| Secrets/env vars | None — `BUILD_DATE` (já existente) é o único env; não muda. | none |
| Build artifacts | `site/data.json` ganha a chave `operacao` (regerado pelo build, commitado). | rodar `obs build` e commitar o novo data.json |

## Common Pitfalls

### Pitfall 1: Divergência model.py ↔ app.js sem teste (CONCERNS #7) — RISCO CENTRAL
**What goes wrong:** A calibração D-07 confronta real com o "projetado" do modelo. Se o
projetado do build e o `project()` do front divergirem (como `carros_equivalente` vs
`carros` já divergiu), o painel mostra um número e o build outro — credibilidade quebrada.
**Why it happens:** A lógica vive em dois idiomas (Python e JS) sem contrato testado.
**How to avoid:** Adicionar um **teste de paridade** nesta fase, ANTES de construir a
calibração. Estratégia viável e offline (sem rodar JS):
- Extrair de `site/app.js` o corpo de `project()` e os campos do objeto retornado por AST/
  regex simples; OU
- Manter um JSON de casos canônicos (input→output esperado) que ambos os lados devem
  satisfazer; o teste Python valida `model.project()` contra ele, e um comentário/check
  garante que `app.js` usa os mesmos nomes de campo.
**Recomendação concreta:** um teste que (a) chama `model.project()` com inputs default e
fixados e asserta os valores, e (b) faz parse textual de `app.js` confirmando que os nomes
de campo retornados por `project()` em JS são os esperados (`desviado`, `co2e`, `carros`,
`larvaSeca`, `frass`, `receita`, `fundo`, `catadores`, `pctOrg`) — capturando renomeações
silenciosas. Documentar o mapeamento de nomes Python↔JS (eles DIFEREM: `desviado_t_ano`↔
`desviado`, `carros_equivalente`↔`carros`, `larva_seca_t_ano`↔`larvaSeca`).
**Warning signs:** Um número no card do simulador ≠ o mesmo número no build/calibração.

### Pitfall 2: Anualização (t/ano vs t/mês) no confronto
**What goes wrong:** `model.project()` devolve `_t_ano` (×365, ×12). A telemetria é
**mensal**. Comparar `desviado_t_ano` com `t_org_coletada` (mês) erra por ~12×.
**Why it happens:** Mismatch de período fácil de não notar.
**How to avoid:** Decidir a base do confronto (recomendado: MENSAL) e converter
explicitamente — dividir os outputs `_t_ano` por 12 (ou pelos dias do mês para o desviado).
Documentar a base no payload e no rótulo do painel.
**Warning signs:** Projetado ~12× o real (ou vice-versa).

### Pitfall 3: Frame vazio sem coluna `key` quebra o join (lição CR-01)
**What goes wrong:** Sem telemetria (estado normal desta fase), `operacao.load()` devolve
frame vazio; se faltar `key`, qualquer join futuro lança `ColumnNotFoundError`.
**Why it happens:** Já aconteceu no SNIS/Censo/RAIS (ver `test_cold_start_build`).
**How to avoid:** Replicar o padrão `snis.load()`: frame vazio COM coluna `key` (Pattern 2).
Mesmo que a telemetria não passe por `build_region` (ela é regional, não por município), o
`build_operacao` deve checar `height==0` e retornar estado vazio honesto.
**Warning signs:** Traceback no cold-start build de uma região nova.

### Pitfall 4: `data.json` não-determinístico / consumidores quebrados
**What goes wrong:** Adicionar `operacao` ao payload pode (a) introduzir não-determinismo se
o projetado usar `date.today()`/ordenação instável, ou (b) quebrar testes que assertam a
forma do payload.
**Why it happens:** `region_totals`/`to_payload` têm testes de forma (`test_payload_*`).
**How to avoid:** Ordenar a série por `mes` (estável); não usar relógio; adicionar a chave
sem remover/renomear as existentes (`meta`/`municipios`/`totais`/`coeficientes`/
`simulador_defaults`). Adicionar teste que asserta `"operacao" in payload` e que vazio =
`[]`/`tem_dado:false`.
**Warning signs:** Diff espúrio no `data.json` a cada build; testes de payload falhando.

### Pitfall 5: Confundir as 3 classes visualmente (regra sagrada)
**What goes wrong:** Telemetria `real (operação)` pintada como baseline `real` ou como
simulador `projeção` — o usuário lê medição como projeção ou vice-versa.
**Why it happens:** As tags `.real`/`.est`/`.proj` já existem e podem ser reusadas sem
distinção suficiente.
**How to avoid:** Nova tag/classe dedicada (ex.: `.tag.live` ou `.tag.medido`) com cor
distinta das 3 existentes; rótulo explícito "medição da operação". No SVG, real sólido
destacado, projetado tracejado apagado.
**Warning signs:** Revisão visual não distingue de relance as 3 classes.

## Code Examples

### Exposição honesta da nova classe no payload (pergunta #4)
```python
# Source: extensão de render.to_payload() [VERIFIED: codebase]
# Em cmd_build (cli.py): df_op = operacao.load(root); op = transform.build_operacao(df_op, coef)
# Em to_payload(...), adicionar ao dict retornado, SEM tocar as chaves existentes:
return {
    "meta": {...},                       # inalterado
    "coeficientes": coef,                # inalterado
    "simulador_defaults": model.defaults(coef),
    "totais": totals,
    "municipios": municipios,
    "operacao": operacao_payload,        # NOVO: {"serie":[], "acumulados":None, "tem_dado":False}
}
```

### Front: seção "Operação ao vivo" com estado vazio (D-02/D-09)
```javascript
// Source: padrão de renderInformalidade/renderFlow [VERIFIED: codebase]
function renderOperacao() {
  const op = DATA.operacao;
  if (!op || !op.tem_dado) {
    $("opSlot").innerHTML =
      `<div class="pendbox"><b>Operação ainda não iniciada — sem medição real.</b>
       Quando a coleta começar, preencha
       <code>data/raw/operacao/operacao_rms.csv</code> e rode
       <code>uv run obs build</code>. O painel acende sozinho.</div>`;
    return;
  }
  // série SVG (Pattern 5) + 4 cards de acumulado (D-11)
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Paridade model↔app por convenção (sem teste) | Teste de paridade cross-language | esta fase (recomendado) | Fecha CONCERNS #7, viabiliza calibração confiável |
| 2 classes de dado (baseline, simulador) | 3 classes (+ telemetria real) | esta fase | Nova tag visual; regra sagrada reforçada |

**Deprecated/outdated:** nada — não há tecnologia obsoleta envolvida.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Operador pesa/registra em unidades convertíveis a t; colunas em `t` no CSV | Pattern 1 | Baixo — é discrição do planner (D-discretion); só muda nomes/unidades, não a arquitetura |
| A2 | Confronto na base MENSAL é o mais legível para calibração | Pattern 4 / Pitfall 2 | Baixo — planner pode escolher anual; a math (÷12) é trivial de inverter |
| A3 | `larva_seca` é medida direto (pesada); `frass` pode ser estimado | Pattern 1 | Médio — define se precisa flag por-medida; mitigado pela coluna `qualidade`+`fonte` |
| A4 | Teste de paridade pode validar JS via parse textual de `app.js` (sem runtime JS) | Pitfall 1 | Médio — se o projeto quiser rodar JS de verdade, precisaria de node no CI; parse textual é o mínimo viável offline |

**Nota:** Todas as A* são áreas de discrição EXPLÍCITA do CONTEXT.md — o planner decide e o
usuário confirma no discuss. Nenhuma é dado factual apresentado como verdade.

## Open Questions

1. **Teste de paridade: parse textual de `app.js` vs execução real de JS no CI?**
   - O que sabemos: o CI roda pytest offline; não há node configurado. Parse textual
     (AST/regex dos nomes de campo + casos canônicos) é o mínimo viável e fecha o risco
     histórico (renomeação de campo).
   - O que é incerto: se o usuário quer a garantia mais forte (rodar `project()` JS via
     node e comparar valores numéricos).
   - Recomendação: começar com o teste textual + casos canônicos (Python). Se o usuário
     valorizar a garantia numérica cross-language, abrir tarefa separada para um harness
     node (fora do escopo mínimo desta fase).

2. **Unidade do CSV: `t` direto ou `kg` com conversão em `load()`?**
   - O que sabemos: `model.project()` opera/retorna em `t`. Operador pesa em kg.
   - Recomendação: colunas em `t` (header documenta "kg ÷ 1000"); menos código, casa com o
     modelo. Planner valida com o usuário no discuss (D-discretion).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| polars | toda a pipeline | ✓ | >=1.0 | — |
| pyyaml | leitura de config | ✓ | >=6.0 | — |
| pytest | testes | ✓ | >=9.1.1 (dev) | — |
| uv | runner (`uv run obs build`/`pytest`) | ✓ (projeto usa) | — | — |
| navegador (SVG/JS) | painel | ✓ nativo | — | — |

**Missing dependencies with no fallback:** nenhuma.
**Missing dependencies with fallback:** nenhuma — fase 100% sobre stack já presente.

## Security Domain

> `security_enforcement: true`, ASVS L1. Esta fase processa apenas CSV local commitado,
> sem rede (D-04), sem auth, sem dado pessoal, sem segredos. Superfície de segurança mínima.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Sem autenticação no projeto |
| V3 Session Management | no | Site estático sem sessão |
| V4 Access Control | no | Sem controle de acesso |
| V5 Input Validation | yes (leve) | `pl.read_csv` com `schema_overrides` tipa as colunas; `slug()` normaliza nome. CSV é commitado pelo mantenedor (não input não-confiável de terceiros). |
| V6 Cryptography | no | Nenhuma criptografia; sem segredo |

### Known Threat Patterns for {pipeline offline + CSV local}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via chave de região (se `operacao` ganhar refresh no futuro) | Tampering | NÃO aplica nesta fase (sem refresh, D-04). Se um futuro `refresh()` for adicionado, replicar o confinamento de caminho de `snis.refresh()` (IN-01: `is_relative_to`) |
| CSV malformado quebra build | Denial of Service (local) | `schema_overrides`+`infer_schema_length=0`; filtrar linhas sem `mes`; estado vazio honesto |
| Injeção de fórmula em CSV (CSV → planilha do operador) | Tampering | Baixo risco (dado é do próprio mantenedor); não renderizado como fórmula no painel (vai como número/texto em JSON) |

**Nota:** O painel injeta strings no DOM via `innerHTML` (padrão existente em `app.js`). A
telemetria adiciona campos `fonte`/`municipio` (texto). Como hoje, esses vêm de CSV
commitado pelo mantenedor (não de terceiros não-confiáveis), o risco de XSS é o mesmo do
baseline atual — fora do escopo desta fase mudar o padrão, mas o planner deve evitar
introduzir `innerHTML` de campos de telemetria sem ao menos a mesma confiança do baseline.

## Sources

### Primary (HIGH confidence)
- `pipeline/model.py`, `pipeline/render.py`, `pipeline/transform.py`, `pipeline/cli.py`,
  `pipeline/sources/{snis,base}.py` — lógica, contratos e padrões reusados [VERIFIED: codebase]
- `site/{app.js,index.html,styles.css}` — paridade `project()`, slots, vars de cor [VERIFIED: codebase]
- `tests/test_pipeline.py` — padrão de teste offline, lição CR-01 (frame vazio com `key`) [VERIFIED: codebase]
- `config/coefficients.yml`, `data/raw/snis/*.csv` — coeficientes e formato CSV real [VERIFIED: codebase]
- `.planning/codebase/{ARCHITECTURE,CONCERNS}.md` — fluxo e o risco de paridade #7 [VERIFIED: codebase]
- `.planning/phases/05-camada-viva-operacional/05-CONTEXT.md` — decisões D-01..D-11 [VERIFIED]
- `CLAUDE.md`, `.planning/REQUIREMENTS.md` — regra sagrada e LIVE-01..04 [VERIFIED]

### Secondary (MEDIUM confidence)
- (nenhuma — domínio inteiramente interno; nenhuma busca web necessária)

### Tertiary (LOW confidence)
- (nenhuma)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nenhuma dependência nova; tudo já em `pyproject.toml` e em uso.
- Architecture: HIGH — extensão direta de padrões existentes (`snis.load`, `to_payload`,
  `region_totals`, `project`), todos lidos e testados.
- Pitfalls: HIGH — derivados de CONCERNS.md e testes existentes (CR-01, paridade #7).
- Calibração math (Pattern 4): HIGH — verificada por leitura linha-a-linha de `project()`;
  a linearidade no `desviado` é direta da fórmula.

**Research date:** 2026-06-25
**Valid until:** 2026-07-25 (estável — codebase interno, sem dependências externas voláteis)
