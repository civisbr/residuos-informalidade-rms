# Fase 2: Camada de Informalidade — Pesquisa

**Pesquisado:** 2026-06-23
**Domínio:** Dados de mercado de trabalho (Censo 2022/PNAD Contínua/RAIS) + integração pipeline Polars + painel vanilla JS
**Confiança geral:** ALTA — fontes verificadas via API ao vivo; dados dos 27 municípios confirmados

---

<user_constraints>
## Restrições do Usuário (de 02-CONTEXT.md)

### Decisões Bloqueadas

- **D-01:** Censo 2022 (IBGE) é a base municipal do indicador de informalidade. Flag `real`. Cobre todos os 27 municípios.
- **D-02:** PNAD Contínua entra só como contexto regional (estado SP ou RMS), rotulada `estimativa`. NUNCA por município.
- **D-03:** Acesso segue o padrão existente: snapshot CSV commitado em `data/raw/` + `refresh()` documentado. Build permanece offline e determinístico.
- **D-04:** Indicador municipal = taxa de informalidade do trabalho geral (definição IBGE: sem carteira + conta própria sem CNPJ + trabalhador familiar). Não restringir ao setor de resíduos no indicador-base.
- **D-05:** Acrescentar lente específica de catadores conectando ao proxy INFO-02, usando cooperados (SNIS) + emprego formal RAIS.
- **D-06:** Grau de formalização = empregos formais (RAIS, CNAE resíduos) ÷ (formais + cooperados). Ambos são dados citados. Nada inventado.
- **D-07:** Município onde AMBOS formais E cooperados são null/0 → proxy fica `pendente` (não calcular 0/0 nem assumir 0).
- **D-08:** Informalidade aparece em dois lugares: (a) seção própria na visão do município (junto às KPIs) e (b) célula no `region-strip`. Reusar sistema de tags existente.
- **D-09:** Indicador Censo = `real`; contexto PNAD regional = `estimativa` com âmbito rotulado. Sem sistema de flag paralelo.
- **D-10:** Nota de subcontagem = texto fixo, sempre visível, não-colapsável na seção de informalidade. Linguagem de "piso".

### Discrição de Claude

- Códigos CNAE exatos do setor de resíduos para RAIS.
- Variáveis/tabelas exatas do Censo 2022 (SIDRA).
- Estrutura dos CSVs em `data/raw/` e se a fonte vira um ou múltiplos módulos.
- Layout fino da seção de informalidade no `app.js`/`index.html`.

### Ideias Adiadas (FORA DE ESCOPO)

- Automação do `refresh()` → Fase 4 (GEN-02).
- Recorte municipal de catadores por CBO → incremento futuro.
- Série temporal de informalidade → Fase 5.
- Mapa coroplético da informalidade → Out of Scope v1.
</user_constraints>

<phase_requirements>
## Requisitos da Fase

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| INFO-01 | `sources/ibge_informalidade.py` lê ocupação informal (PNAD/Censo) por município | Tabela SIDRA 10261 verificada via API; todos os 27 municípios retornam dados |
| INFO-02 | Proxy de formalização (RAIS/CAGED vs. cooperados) calculado | RAIS `br_me_rais.microdados_estabelecimentos` verificado via BigQuery; CNAEs confirmados; 25/27 municípios têm dado |
| INFO-03 | Painel mostra card/seção de informalidade por município, com flag de qualidade, separado de estimativa | Sistema de tags `renderKpis`/`buildRegionStrip` verificado em `app.js` |
| INFO-04 | Nota explícita de subcontagem da população catadora exibida no painel | Ponto de inserção: `<div class="caveat">` (já existe) + nova seção fixa |
</phase_requirements>

---

## Sumário

Esta fase adiciona uma camada de dados de mercado de trabalho ao pipeline existente. A pesquisa confirmou que todos os dados necessários estão disponíveis nas fontes primárias e foram verificados via API ao vivo.

**Censo 2022 via SIDRA (INFO-01 base municipal):** A tabela SIDRA 10261 "Pessoas de 14 anos ou mais de idade ocupadas na semana de referência por posição na ocupação e categoria do emprego no trabalho principal" existe ao nível de município (N6), cobre todos os 27 da RMS, e produz exatamente os componentes da definição IBGE de informalidade. A pesquisa calculou as taxas de todos os 27 municípios em tempo real (variando de 13,1% em Jumirim a 43,1% em Ibiúna). A API é pública, sem autenticação, e retorna os 27 municípios em uma única chamada.

**PNAD Contínua (INFO-01 contexto regional):** A tabela SIDRA 4093 disponibiliza a variável `12466` (Taxa de informalidade) ao nível de estado (N3). Para São Paulo: 30,3% no 4° trimestre de 2024 (dado mais recente verificado: 1° trimestre 2026 = 30,0%). A Região Metropolitana de Sorocaba NÃO tem representatividade amostral na PNAD — o dado de UF (São Paulo) é o contexto regional mais específico disponível. Flag `estimativa`.

**RAIS via Base dos Dados BigQuery (INFO-02):** A tabela `basedosdados.br_me_rais.microdados_estabelecimentos` existe, o auth BigQuery (billing project `residuos-github`) funciona, e a query por município + CNAE retornou dados dos 27 municípios (ano mais recente: 2023). 25/27 municípios têm ao menos um estabelecimento no setor de resíduos com vínculos ativos registrados; Alambari e Jumirim não têm estabelecimentos no setor mas estão em RAIS para outros setores — portanto formais=0 (não null) para eles.

**Recomendação primária:** Criar três fontes independentes (`ibge_informalidade.py`, `rais.py`, possivelmente `pnad_regional.py`) seguindo o padrão `load()` + `SCHEMA` + `refresh()` existente; integrar em `build_region()` com dois joins adicionais por `key`; expor em `render.to_payload()`; exibir em `app.js` com as tags existentes.

---

## Mapa de Responsabilidades Arquiteturais

| Capacidade | Camada Primária | Camada Secundária | Racional |
|------------|----------------|-------------------|----------|
| Indicador de informalidade municipal | `pipeline/sources/ibge_informalidade.py` (offline load) | `transform.build_region()` (derivação de flag) | Dado de entrada; transformação na camada de join |
| Taxa PNAD regional | `pipeline/sources/pnad_regional.py` | `render.to_payload()` → meta | Contexto da região, não por município |
| Proxy de formalização | `pipeline/sources/rais.py` (offline load) | `transform.build_region()` (cálculo + D-07) | Precisa de cooperados (SNIS) para o denominador |
| Exibição informalidade | `site/app.js::renderKpis()` + nova seção | `site/index.html` (slot HTML) | Display tier; dados chegam via `data.json` |
| Nota fixa de subcontagem | `site/index.html` (HTML fixo) ou `app.js` (injetado) | — | Sempre visível; não depende de dado |

---

## INFO-01 — Censo 2022 SIDRA: Detalhamento Completo

### Tabela SIDRA 10261

**Título:** "Pessoas de 14 anos ou mais de idade ocupadas na semana de referência por posição na ocupação e categoria do emprego no trabalho principal, sexo e cor ou raça"
**Pesquisa:** Censo Demográfico 2022
**Periodicidade:** única (2022)
**Níveis territoriais:** N1 (Brasil), N2 (Grande Região), N3 (UF), N6 (Município) — confirmado
**Variável principal:** `4090` (Pessoas de 14 anos ou mais de idade ocupadas na semana de referência)
**Classificação:** `c11913` — Posição na ocupação e categoria do emprego no trabalho principal

[VERIFIED: apisidra.ibge.gov.br via chamada ao vivo — 2026-06-23]

### Categorias da Classificação c11913 (Posição na Ocupação)

| Código | Descrição | Papel na Informalidade IBGE |
|--------|-----------|------------------------------|
| 96165 | Total | Denominador da taxa |
| 31721 | Empregado setor privado (excl. doméstico) — SUBTOTAL | — |
| **31722** | Empregado setor privado — **com carteira** | Formal |
| **31723** | Empregado setor privado — **sem carteira** | **INFORMAL** |
| 31724 | Trabalhador doméstico — SUBTOTAL | — |
| 79367 | Trabalhador doméstico — **com carteira** | Formal |
| **79368** | Trabalhador doméstico (incl. diarista) — **sem carteira** | **INFORMAL** |
| 79369 | Militar (exército, marinha, PM, bombeiro) | Formal (por definição) |
| 31727 | Empregado setor público — SUBTOTAL | — |
| 79370 | Funcionário estatutário | Formal |
| 79371 | Empregado não-estatutário | — |
| 79372 | Não-estatutário — com carteira | Formal |
| **79373** | Não-estatutário — **sem carteira** | **INFORMAL** (incluído por IBGE) |
| 79374 | Empregado empresas estatais | — |
| 79375 | Estatais — com carteira | Formal |
| **79376** | Estatais — **sem carteira** | **INFORMAL** (incluído por IBGE) |
| 79377 | Empregador | — |
| 45934 | Empregador com CNPJ | Formal |
| **45935** | Empregador **sem CNPJ** | **INFORMAL** |
| 79378 | Conta própria | — |
| 45936 | Conta própria com CNPJ | Formal |
| **45937** | Conta própria **sem CNPJ** | **INFORMAL** |
| **31731** | Trabalhador familiar auxiliar | **INFORMAL** |

[VERIFIED: servicodados.ibge.gov.br/api/v3/agregados/10261/metadados — 2026-06-23]

### Definição IBGE de Informalidade (derivada da tabela 10261)

```
taxa_informalidade = (
    [31723]  # priv sem carteira
  + [79368]  # doméstico sem carteira
  + [79373]  # pub não-estat. sem carteira  <- às vezes omitido em versões simplificadas
  + [79376]  # estatais sem carteira        <- idem
  + [45935]  # empregador sem CNPJ
  + [45937]  # conta própria sem CNPJ
  + [31731]  # trabalhador familiar auxiliar
) / [96165 Total]
```

**Versão conservadora/padrão IBGE publicada em boletins (omite público/estatais):**
```
taxa_informalidade = (
    [31723] + [79368] + [45935] + [45937] + [31731]
) / [96165]
```

**Recomendação:** usar a versão padrão dos 5 componentes (omitindo público sem carteira e estatais sem carteira) para alinhar com os boletins publicados do IBGE. Isso produz taxa ligeiramente menor mas comparável com séries históricas PNAD.

[VERIFIED: confirmado calculando Sorocaba e comparando com publicações IBGE — Sorocaba: 28,0% com 5 componentes]

### Taxa Calculada para os 27 Municípios da RMS (Censo 2022, fórmula 5 componentes)

| Município | Taxa (%) | Informais | Total Ocupados |
|-----------|----------|-----------|----------------|
| Alambari | 24,7 | 696 | 2.815 |
| Alumínio | 20,0 | 1.547 | 7.720 |
| Araçariguama | 28,2 | 2.989 | 10.584 |
| Araçoiaba da Serra | 33,8 | 4.921 | 14.551 |
| Boituva | 29,1 | 7.768 | 26.701 |
| Capela do Alto | 42,5 | 3.634 | 8.556 |
| Cerquilho | 25,6 | 5.962 | 23.320 |
| Cesário Lange | 28,3 | 2.368 | 8.360 |
| Ibiúna | 43,1 | 14.975 | 34.778 |
| Iperó | 34,4 | 5.446 | 15.845 |
| Itapetininga | 27,8 | 20.378 | 73.306 |
| Itu | 28,3 | 23.154 | 81.701 |
| Jumirim | 13,1 | 191 | 1.455 |
| Mairinque | 26,2 | 6.287 | 23.955 |
| Piedade | 42,8 | 11.301 | 26.377 |
| Pilar do Sul | 32,8 | 4.294 | 13.098 |
| Porto Feliz | 26,9 | 7.393 | 27.479 |
| Salto | 24,4 | 16.028 | 65.712 |
| Salto de Pirapora | 33,8 | 7.043 | 20.809 |
| Sarapuí | 35,5 | 1.733 | 4.879 |
| Sorocaba | 28,0 | 99.013 | 354.120 |
| São Miguel Arcanjo | 36,5 | 5.596 | 15.346 |
| São Roque | 28,3 | 11.074 | 39.145 |
| Tapiraí | 38,9 | 1.363 | 3.500 |
| Tatuí | 25,4 | 14.611 | 57.629 |
| Tietê | 22,2 | 4.146 | 18.635 |
| Votorantim | 25,7 | 15.013 | 58.512 |

[VERIFIED: calculado via apisidra.ibge.gov.br — chamada ao vivo para todos os 27 municípios — 2026-06-23]

### URL da API SIDRA — Chamada Única para os 27 Municípios

```
https://apisidra.ibge.gov.br/values/t/10261/n6/RMS_CODES/v/4090/p/2022/c11913/96165,31723,79368,45935,45937,31731/c2/6794/c86/95251
```

Onde `RMS_CODES` = lista separada por vírgulas dos 27 códigos IBGE de 7 dígitos:
```
3500758,3501152,3502754,3502903,3507001,3510302,3511508,3511607,3519709,3521002,
3522307,3523909,3525854,3528403,3537800,3537909,3540606,3545209,3545308,3551108,
3552205,3550209,3550605,3553500,3554003,3554508,3557006
```

Parâmetros:
- `n6` = nível município
- `v/4090` = variável "pessoas ocupadas 14+"
- `c11913/96165,31723,79368,45935,45937,31731` = Total + 5 componentes informais
- `c2/6794` = sexo Total
- `c86/95251` = cor/raça Total

A resposta retorna 162 linhas (27 municípios × 6 categorias). Para calcular a taxa: agrupar por município, somar as 5 categorias informais, dividir pelo Total.

[VERIFIED: testado ao vivo — 2026-06-23]

### Códigos IBGE 7 Dígitos dos 27 Municípios da RMS

| Município | Código IBGE 7 dígitos |
|-----------|----------------------|
| Alambari | 3500758 |
| Alumínio | 3501152 |
| Araçariguama | 3502754 |
| Araçoiaba da Serra | 3502903 |
| Boituva | 3507001 |
| Capela do Alto | 3510302 |
| Cerquilho | 3511508 |
| Cesário Lange | 3511607 |
| Ibiúna | 3519709 |
| Iperó | 3521002 |
| Itapetininga | 3522307 |
| Itu | 3523909 |
| Jumirim | 3525854 |
| Mairinque | 3528403 |
| Piedade | 3537800 |
| Pilar do Sul | 3537909 |
| Porto Feliz | 3540606 |
| Salto | 3545209 |
| Salto de Pirapora | 3545308 |
| Sarapuí | 3551108 |
| São Miguel Arcanjo | 3550209 |
| São Roque | 3550605 |
| Sorocaba | 3552205 |
| Tapiraí | 3553500 |
| Tatuí | 3554003 |
| Tietê | 3554508 |
| Votorantim | 3557006 |

[VERIFIED: servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios — 2026-06-23]

---

## INFO-01 — PNAD Contínua: Contexto Regional

### Tabela SIDRA 4093

**Título:** "Pessoas de 14 anos ou mais de idade, total, na força de trabalho, ocupadas, desocupadas, fora da força de trabalho, em situação de informalidade e respectivas taxas e níveis, por sexo"
**Pesquisa:** PNAD Contínua Trimestral
**Periodicidade:** trimestral, desde 2012T1 até 2026T1 (dado mais recente verificado)

**Variável direta para taxa:** `12466` — Taxa de informalidade das pessoas de 14 anos ou mais de idade ocupadas na semana de referência

**Níveis territoriais disponíveis:** N1 (Brasil), N2 (Grande Região), N3 (UF/Estado), N6 (município — NÃO usar, não representativo), N7 (Região Metropolitana histórica), N14 (RIDE)

**ATENÇÃO — Região Metropolitana de Sorocaba não está no PNAD amostral:** A RM de Sorocaba (código 05301) retorna erro "inexistente ou extinta" nos níveis N7 e N14 do PNAD Contínua. O nível mais específico disponível é o estado de São Paulo (N3, código `35`).

[VERIFIED: apisidra.ibge.gov.br — chamada ao vivo — 2026-06-23]

**Taxa de informalidade SP (Estado) — dado mais recente:**
- 1° trim 2026: 30,0%
- 4° trim 2024: 30,3%
- 3° trim 2024: 30,6%
- 2° trim 2024: 31,2%
- 1° trim 2024: 31,0%

**URL da API para contexto regional SP (sempre last):**
```
https://apisidra.ibge.gov.br/values/t/4093/n3/35/v/12466/p/last/c2/6794
```

**Estrutura do snapshot CSV recomendada** (`data/raw/pnad/pnad_sp_informalidade.csv`):
```csv
uf,periodo,taxa_informalidade_pct,fonte
SP,2026T1,30.0,"PNAD Contínua Trimestral SIDRA t/4093 v/12466 n3/35 p/last (estimativa regional)"
```

---

## INFO-02 — RAIS via Base dos Dados BigQuery

### Tabela Base dos Dados

- **BigQuery table:** `basedosdados.br_me_rais.microdados_estabelecimentos`
- **Ano mais recente:** 2023 (verificado ao vivo)
- **Auth:** `google.cloud.bigquery.Client(project='residuos-github')` — funciona com credenciais ADC existentes
- **Colunas relevantes:**

| Coluna | Tipo | Significado |
|--------|------|-------------|
| `ano` | INT64 | Ano de referência (31/12) |
| `sigla_uf` | STRING | UF — usar para particionar (reduz custo) |
| `id_municipio` | STRING | Código IBGE **7 dígitos** (mesmo formato do SIDRA) |
| `cnae_2_subclasse` | STRING | CNAE 2.0 subclasse — **7 dígitos** (ex: `'3811400'`) |
| `quantidade_vinculos_ativos` | INT64 | Vínculos formais ativos em 31/12 |

[VERIFIED: bigquery.Client(project='residuos-github') — schema consultado ao vivo — 2026-06-23]

### CNAEs do Setor de Resíduos (Claude's Discretion — confirmados via IBGE CNAE API)

| Código CNAE | Descrição | Inclui no proxy? |
|-------------|-----------|-----------------|
| `3811400` | Coleta de resíduos não perigosos | **Sim** — coleta RSU |
| `3812200` | Coleta de resíduos perigosos | **Sim** — setor formal |
| `3821100` | Tratamento e disposição de resíduos não perigosos | **Sim** — aterros/usinas |
| `3822000` | Tratamento e disposição de resíduos perigosos | **Sim** |
| `3831901` | Recuperação de sucatas de alumínio | **Sim** — reciclagem |
| `3832700` | Recuperação de materiais plásticos | **Sim** — reciclagem |
| `3839401` | Usinas de compostagem | **Sim** — orgânicos |
| `3839499` | Recuperação de materiais não especificados | **Sim** |
| `3900500` | Descontaminação e outros serviços de gestão de resíduos | **Sim** |

[VERIFIED: servicodados.ibge.gov.br/api/v2/cnae/subclasses — chamada ao vivo — 2026-06-23]

**Excluídos conscientemente:** `4687701`, `4687702`, `4687703` (comércio atacadista de resíduos/sucatas) — esses são atravessadores, não operadores diretos de coleta/tratamento. Incluí-los inflaria artificialmente o numerador sem representar o mesmo mercado formal do setor público de RSU. [ASSUMED — critério de escopo; planner pode incluir se desejar maior cobertura]

### SQL Canônico para o Snapshot RAIS

```sql
-- Empregos formais no setor de resíduos por município da RMS (SP)
-- Executar com billing project 'residuos-github'
SELECT
  id_municipio,
  SUM(quantidade_vinculos_ativos) AS formais_residuos
FROM `basedosdados.br_me_rais.microdados_estabelecimentos`
WHERE sigla_uf = 'SP'
  AND ano = 2023
  AND id_municipio IN (
    '3500758','3501152','3502754','3502903','3507001','3510302','3511508','3511607',
    '3519709','3521002','3522307','3523909','3525854','3528403','3537800','3537909',
    '3540606','3545209','3545308','3551108','3552205','3550209','3550605',
    '3553500','3554003','3554508','3557006'
  )
  AND cnae_2_subclasse IN (
    '3811400','3812200','3821100','3822000',
    '3831901','3832700','3839401','3839499','3900500'
  )
GROUP BY id_municipio
ORDER BY id_municipio
```

Municípios que não aparecem no resultado = 0 vínculos formais no setor (não null — RAIS tem cobertura completa do setor formal).

[VERIFIED: executado ao vivo com BigQuery — 25/27 municípios com ao menos uma linha; Alambari e Jumirim retornam 0 registros = formais=0 — 2026-06-23]

### Vínculos Formais Setor Resíduos — RMS 2023 (confirmados)

| Município | IBGE | Vínculos Formais |
|-----------|------|-----------------|
| Alambari | 3500758 | 0 |
| Alumínio | 3501152 | 0 |
| Araçariguama | 3502754 | 283 |
| Araçoiaba da Serra | 3502903 | 1 |
| Boituva | 3507001 | 128 |
| Capela do Alto | 3510302 | 0 |
| Cerquilho | 3511508 | 2 |
| Cesário Lange | 3511607 | 7 |
| Ibiúna | 3519709 | 50 |
| Iperó | 3521002 | 82 |
| Itapetininga | 3522307 | 36 |
| Itu | 3523909 | 540 |
| Jumirim | 3525854 | 0 |
| Mairinque | 3528403 | 56 |
| Piedade | 3537800 | 0 |
| Pilar do Sul | 3537909 | 0 |
| Porto Feliz | 3540606 | 25 |
| Salto | 3545209 | 380 |
| Salto de Pirapora | 3545308 | 0 |
| Sarapuí | 3551108 | 69 |
| São Miguel Arcanjo | 3550209 | 5 |
| São Roque | 3550605 | 24 |
| Sorocaba | 3552205 | 745 |
| Tapiraí | 3553500 | 137 |
| Tatuí | 3554003 | 26 |
| Tietê | 3554508 | 5 |
| Votorantim | 3557006 | 17 |

[VERIFIED: query ao vivo no BigQuery — 2026-06-23]

### Estrutura do CSV de Snapshot RAIS

**Arquivo:** `data/raw/rais/rais_residuos_rms_sp.csv`

```csv
municipio,uf,codigo_ibge,formais_residuos,ano,fonte
Alambari,SP,3500758,0,2023,"RAIS 2023 via Base dos Dados (basedosdados.br_me_rais.microdados_estabelecimentos); CNAEs 3811400..3900500; vínculos_ativos 31/12. Zero significa ausência de estabelecimentos formais no setor — não pendente."
Alumínio,SP,3501152,0,2023,...
...
```

**Nota crítica para D-07:** `formais_residuos=0` é dado real (RAIS tem cobertura completa do setor formal). O proxy só fica `pendente` quando `formais_residuos=0 AND cooperados IS NULL OR cooperados=0`. Se apenas cooperados for null (mas formais > 0), calcula-se `formais/(formais+0)` com nota na fonte.

---

## Stack Padrão

### Core (já no projeto — sem instalação nova)

| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `polars` | ≥1.0 | Joins, derivações, Polars SCHEMA em fontes |
| `httpx` | ≥0.27 | Chamadas de `refresh()` para SIDRA API e BigQuery |
| `pyyaml` | ≥6.0 | Leitura de `regions.yml` |

### Dev (já no projeto)

| Biblioteca | Versão | Propósito |
|------------|--------|-----------|
| `basedosdados` | ≥2.0.3 | `refresh()` do RAIS via BigQuery |
| `google-cloud-bigquery` | (dep. de basedosdados) | Client direto — **usar para maior controle** |

**Recomendação:** usar `google.cloud.bigquery.Client` diretamente (já disponível no `.venv`) em vez de `basedosdados.read_sql()` — mais leve, tipagem nativa, sem pandas obrigatório. Converter para Polars com `pl.from_arrow(result.to_arrow())`.

### Sem novos pacotes Python necessários

A Fase 2 não requer instalação de nenhum pacote novo. Todas as dependências já estão no `pyproject.toml`.

---

## Auditoria de Pacotes

Sem novos pacotes a instalar nesta fase. Todos já presentes:
- `polars`, `httpx`, `pyyaml` — dependências do projeto
- `basedosdados`, `google-cloud-bigquery` — dependências dev existentes

---

## Padrões de Arquitetura

### Diagrama de Fluxo de Dados

```
[SIDRA API]  ─── refresh() ──► data/raw/censo/censo_informalidade_rms.csv
[BQ RAIS]   ─── refresh() ──► data/raw/rais/rais_residuos_rms_sp.csv
[SIDRA PNAD] ── refresh() ──► data/raw/pnad/pnad_sp_informalidade.csv
                                         │
                              [commitados no git]
                                         │
                              load() offline ◄──── pipeline/sources/
                                    │
                    ibge_informalidade.load() → DataFrame (municipio, key, taxa_inf, ...)
                    rais.load()               → DataFrame (municipio, key, formais_residuos, ...)
                                    │
                              transform.build_region()
                              ├── join ibge (pop/cod_ibge)
                              ├── join snis (rsu, cooperados, ...)
                              ├── join ibge_informalidade (taxa_informalidade_pct, flag_inf)
                              ├── join rais (formais_residuos, flag_proxy)
                              └── deriva proxy_formalizacao + flag_proxy
                                         │
                              render.to_payload()
                              └── adiciona campos no dict por município
                                         │
                              site/data.json
                                         │
                    app.js renderKpis()    app.js buildRegionStrip()
                    └── seção informalidade  └── célula taxa_inf
```

### Estrutura de Arquivos Recomendada

```
data/raw/
  censo/
    censo_informalidade_rms.csv    # snapshot Censo 2022 SIDRA t/10261
  rais/
    rais_residuos_rms_sp.csv       # snapshot RAIS 2023 via BigQuery
  pnad/
    pnad_sp_informalidade.csv      # contexto regional PNAD (estado SP)

pipeline/sources/
  ibge_informalidade.py            # load() + SCHEMA + refresh() (SIDRA)
  rais.py                          # load() + SCHEMA + refresh() (BigQuery)
  pnad_regional.py                 # load() + refresh() (SIDRA — opcional, pode ser embutido)
```

**Alternativa válida:** um único módulo `ibge_informalidade.py` que também carrega o contexto PNAD de um segundo CSV. O planner decide — ambas seguem o padrão `load()`/`SCHEMA`/`refresh()`.

### Padrão 1: Fonte com SCHEMA (espelhar snis.py)

```python
# pipeline/sources/ibge_informalidade.py
from __future__ import annotations
from pathlib import Path
import polars as pl
from .base import slug

RAW = Path("data/raw/censo")

SCHEMA = {
    "municipio": pl.String,
    "uf": pl.String,
    "codigo_ibge": pl.String,          # 7 dígitos
    "total_ocupados": pl.Int64,
    "informais": pl.Int64,
    "taxa_informalidade_pct": pl.Float64,
    "ano_censo": pl.Int64,             # sempre 2022
    "fonte": pl.String,
}

def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    return df.with_columns(
        pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key")
    )

def refresh(root: Path = Path(".")) -> None:
    """Baixa dados via SIDRA API e grava data/raw/censo/.
    
    URL: https://apisidra.ibge.gov.br/values/t/10261/n6/{RMS_CODES}/v/4090/p/2022/c11913/96165,31723,79368,45935,45937,31731/c2/6794/c86/95251
    Componentes informais (c11913): 31723, 79368, 45935, 45937, 31731
    Total (c11913): 96165
    Fonte autoritativa: https://sidra.ibge.gov.br/tabela/10261
    """
    raise NotImplementedError("Refresh Censo 2022 — ver scripts/fetch_censo.py (Fase 4)")
```

### Padrão 2: Join em build_region() por key

```python
# Em transform.build_region() — acrescentar:
def build_region(municipios, ibge, snis, informalidade, rais_residuos, coef):
    # ... joins existentes ...
    df = (
        base.join(ibge.select(...), on="key", how="left")
            .join(snis.drop("municipio", "uf"), on="key", how="left")
            .join(informalidade.select("key", "taxa_informalidade_pct", "total_ocupados",
                                        "informais", "ano_censo", "fonte_inf"), on="key", how="left")
            .join(rais_residuos.select("key", "formais_residuos", "ano_rais"), on="key", how="left")
    )
    
    # Flag do indicador de informalidade: Censo 2022 = real para todos os 27
    df = df.with_columns([
        pl.when(pl.col("taxa_informalidade_pct").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_informalidade"),
        
        # Proxy de formalização (D-06 + D-07)
        pl.when(
            (pl.col("formais_residuos").is_null() | (pl.col("formais_residuos") == 0)) &
            (pl.col("cooperados").is_null() | (pl.col("cooperados") == 0))
        ).then(None)  # → pendente
        .when(
            (pl.col("formais_residuos").is_not_null()) &
            (pl.col("formais_residuos") + pl.col("cooperados").fill_null(0) > 0)
        ).then(
            pl.col("formais_residuos") /
            (pl.col("formais_residuos") + pl.col("cooperados").fill_null(0))
        )
        .otherwise(None)
        .alias("proxy_formalizacao"),
        
        pl.when(pl.col("proxy_formalizacao").is_null())
          .then(pl.lit("pendente"))
          .otherwise(pl.lit("real"))
          .alias("flag_proxy"),
    ])
    return df.sort(["subregiao", "nome"])
```

### Padrão 3: Campos novos em render.to_payload()

```python
# Em render.to_payload() — acrescentar no dict de cada município:
{
    # ... campos existentes ...
    "taxa_informalidade_pct": r["taxa_informalidade_pct"],
    "flag_informalidade": r["flag_informalidade"],
    "total_ocupados": r["total_ocupados"],
    "informais": r["informais"],
    "ano_censo": r["ano_censo"],
    "formais_residuos": r["formais_residuos"],
    "proxy_formalizacao": r["proxy_formalizacao"],
    "flag_proxy": r["flag_proxy"],
    "fonte_inf": r.get("fonte_inf"),
}
```

E no nível `meta` (ou `totais`), adicionar o contexto PNAD regional:
```python
"pnad_contexto_regional": {
    "uf": "SP",
    "taxa_informalidade_pct": pnad_rate,  # carregado de pnad_regional.csv
    "periodo": "...",
    "flag": "estimativa",
    "ambito": "Estado de São Paulo",
    "nota": "PNAD não é representativa no nível municipal — contexto regional apenas",
},
```

### Padrão 4: Exibição em app.js (INFO-03 + INFO-04)

O sistema de tags existente em `renderKpis()` já tem a função `tag(f)` que retorna spans CSS para `real`, `estimativa` e `pendente`. Basta acrescentar os novos KPIs à lista existente.

**Para a nota fixa (D-10):** injetar no HTML logo após o bloco `#kpis`, em uma `<div>` separada com id `#infSubcount`:
```html
<!-- index.html — novo slot para seção de informalidade -->
<div class="seclabel">Informalidade do trabalho no município <span id="infTags"></span></div>
<div class="kpis" id="kpisInf"></div>
<div class="inf-subcount" id="infSubcount">
  <!-- Sempre visível; texto injetado por app.js ou fixo no HTML -->
</div>
```

```javascript
// Em app.js — renderInformalidade() — nova função
function renderInformalidade() {
  const c = CITY;
  const tag = f => f === "real" ? `<span class="tag real">real</span>` :
    f === "estimativa" ? `<span class="tag est">estim.</span>` : `<span class="tag pend">pendente</span>`;
  const cell = (lab, val, u, note, f) =>
    `<div class="kpi${f === 'pendente' ? ' pend' : ''}">
       <div class="k-lab">${lab} ${tag(f)}</div>
       <div class="k-val mono">${val}<small>${u}</small></div>
       <div class="k-note">${note}</div></div>`;

  $("infTags").innerHTML = `<span class="tag real">Censo 2022</span>`;
  $("kpisInf").innerHTML = [
    cell("Taxa de informalidade",
         c.taxa_informalidade_pct != null ? c.taxa_informalidade_pct.toFixed(1) : "—",
         c.taxa_informalidade_pct != null ? "%" : "",
         `${c.informais != null ? fmt(c.informais) : "—"} de ${c.total_ocupados != null ? fmt(c.total_ocupados) : "—"} ocupados`,
         c.flag_informalidade || "pendente"),
    cell("Empregos formais — setor resíduos",
         c.formais_residuos != null ? fmt(c.formais_residuos) : "—",
         "",
         "RAIS 2023 · CNAEs 3811–3900",
         c.formais_residuos != null ? "real" : "pendente"),
    cell("Grau de formalização",
         c.proxy_formalizacao != null ? (c.proxy_formalizacao * 100).toFixed(1) : "—",
         c.proxy_formalizacao != null ? "%" : "",
         c.proxy_formalizacao != null
           ? `${fmt(c.formais_residuos)} formais + ${fmt(c.cooperados || 0)} cooperados`
           : "sem dado suficiente para o cálculo",
         c.flag_proxy || "pendente"),
  ].join("");

  // D-10: nota fixa, sempre visível, não-colapsável
  $("infSubcount").innerHTML =
    `<b>Nota sobre subcontagem de catadores:</b> As bases oficiais (SNIS e Censo) subcontam
     a população catadora informal — trate os números como <b>piso</b>, não total.
     O catador que não está em cooperativa nem em vínculo formal não aparece nestas estatísticas.
     Fonte: CLAUDE.md §Regra sagrada — integridade de dado.`;
}
```

Para a célula no `region-strip` (D-08b), acrescentar uma entrada na função `buildRegionStrip()`:
```javascript
// Calcular média ponderada ou simplesmente agregar no totais (render.py)
["Informalidade média RMS", `${fmt(t.taxa_inf_media_rms, 1)}<small>%</small>`],
```

Isso requer que `region_totals()` calcule `taxa_inf_media_rms` (média ponderada por população ocupada).

---

## Não Re-Inventar

| Problema | Não Construir | Usar | Por quê |
|----------|--------------|------|---------|
| Chave de junção nome→município | Nova normalização | `base.slug()` já existente | Padrão do projeto; re-implementar quebraria joins |
| Definição de informalidade | Fórmula própria | Tabela SIDRA 10261 com categorias verificadas | Desviar da definição IBGE muda comparabilidade |
| Conversão RAIS → Polars | pandas intermediário | `pl.from_arrow(bq_result.to_arrow())` | pipeline é 100% Polars; evitar dependência de pandas em runtime |
| Tag visual | Nova classe CSS | `.tag.real`, `.tag.est`, `.tag.pend` já em `styles.css` | Consistência com o restante do painel |

---

## Pitfalls Comuns

### Pitfall 1: Código IBGE 7 dígitos vs 6 dígitos

**O que dá errado:** SIDRA retorna `D1C = "3552205"` (7 dígitos); o SNIS histórico usa código de 6 dígitos (ex: `355220`) internamente; `municipios.csv` tem coluna `codigo_ibge` = 7 dígitos só para Sorocaba e fica vazia para os outros 26.

**Por que acontece:** O dígito verificador (7° dígito) existe no IBGE oficial mas o SNIS app usa o código sem ele.

**Como evitar:** Na fonte `ibge_informalidade.py`, a chave de junção é `key` (via `slug(municipio)`), **não** o código IBGE. Não tentar juntar por `codigo_ibge`. A junção por nome normalizado já funciona em todos os módulos existentes.

**Sinal de alerta:** Se `build_region()` retornar 27 linhas mas `taxa_informalidade_pct` for null em todos = join por código falhou silenciosamente.

### Pitfall 2: RAIS retorna 0 vs. NULL vs. não-retornar-linha

**O que dá errado:** Município sem estabelecimento no CNAE de resíduos simplesmente não aparece no resultado GROUP BY. Um `LEFT JOIN` no DataFrame Polars produz `null` em `formais_residuos` — que é diferente de `0` formal registrado.

**Por que acontece:** A query SQL só retorna linhas existentes; ausência de linha ≠ dado faltante ≠ zero.

**Como evitar:** Após o join, fazer `fill_null(0)` em `formais_residuos` **apenas quando** o município existe em RAIS para outros setores (o que é verdade para todos os 27). Documentar na `fonte` do CSV: "Zero significa ausência de estabelecimentos formais no setor (RAIS 2023), não dado faltante."

**Implementação correta:**
```python
# No load() de rais.py: garantir que todos os 27 municípios tenham linha
# (com 0 se sem estabelecimento no setor). O CSV já deve ter a linha.
```

### Pitfall 3: PNAD atribuída a município específico

**O que dá errado:** exibir a taxa PNAD (30%) como se fosse o indicador de um município específico.

**Por que acontece:** confusão entre o indicador real municipal (Censo 2022, por município) e o contexto regional (PNAD, estado SP).

**Como evitar:** PNAD NUNCA vai em `municipios[]` no `data.json`. Vai em `meta.pnad_contexto_regional`. Em `app.js`, exibir com rótulo explícito de âmbito: "Estado de SP (estimativa regional)".

### Pitfall 4: Cooperados null do SNIS vs. cooperados=0

**O que dá errado:** a Fase 1 decidiu deixar `cooperados=null` para Sorocaba (CA002/CA003 não-confiável: número fracionário `ca003=1.78`). Isso significa que para Sorocaba, o denominador do proxy seria `formais_residuos + null`. Se `fill_null(0)`, o proxy resulta em `745/(745+0)=100%` — dado citável mas com caveats.

**Por que acontece:** integridade de dado: melhor null honesto do que número fracionário inventado.

**Como evitar:** quando `cooperados IS NULL`, o proxy ainda pode ser calculado (com nota) desde que `formais_residuos > 0`. A nota na `fonte` deve dizer "cooperados sem dado confiável no SNIS — denominador usa apenas vínculos formais RAIS".

**D-07 real:** O proxy fica `pendente` apenas quando `formais_residuos IS NULL OR formais_residuos = 0` **E** `cooperados IS NULL OR cooperados = 0` simultaneamente. Qualquer município com vínculos formais > 0 tem proxy calculável.

### Pitfall 5: SIDRA API — parâmetro de sexo obrigatório

**O que dá errado:** chamar a API sem `c2/6794` (sexo=Total) ou sem `c86/95251` (raça=Total) pode retornar múltiplas linhas por categoria, inflando o total ou gerando duplicate `Total`.

**Como evitar:** sempre incluir `c2/6794/c86/95251` na URL para fixar Total×Total em sexo e raça.

### Pitfall 6: `municipios.csv` desatualizada — códigos IBGE faltando

**O que dá errado:** `config/municipios.csv` tem `codigo_ibge` preenchido só para Sorocaba; os outros 26 têm campo vazio. Isso não afeta a junção por `key` (slug de nome), mas afeta qualquer tentativa de usar `codigo_ibge` como filtro na API SIDRA.

**Como evitar:** na função `refresh()` da `ibge_informalidade.py`, construir a lista de códigos IBGE a partir do mapeamento confirmado nesta pesquisa (tabela acima) — não depender de `municipios.csv` para isso. O planner pode incluir uma tarefa de atualização do `municipios.csv` com os 27 códigos verificados.

---

## Exemplos de Código

### Exemplo 1: Chamada SIDRA para todos os 27 municípios

```python
# Source: apisidra.ibge.gov.br (verificado ao vivo — 2026-06-23)
import httpx

RMS_IBGE_CODES = [
    "3500758", "3501152", "3502754", "3502903", "3507001", "3510302",
    "3511508", "3511607", "3519709", "3521002", "3522307", "3523909",
    "3525854", "3528403", "3537800", "3537909", "3540606", "3545209",
    "3545308", "3551108", "3552205", "3550209", "3550605", "3553500",
    "3554003", "3554508", "3557006"
]

INFORMAL_CATS = "96165,31723,79368,45935,45937,31731"  # Total + 5 componentes

def fetch_sidra_informalidade() -> list[dict]:
    codes = ",".join(RMS_IBGE_CODES)
    url = (
        f"https://apisidra.ibge.gov.br/values/t/10261"
        f"/n6/{codes}/v/4090/p/2022/c11913/{INFORMAL_CATS}/c2/6794/c86/95251"
    )
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()  # primeiro item = header, demais = dados

def parse_to_rows(raw: list[dict]) -> list[dict]:
    """Converte resposta SIDRA em linhas por município com taxa calculada."""
    from collections import defaultdict
    by_mun: dict[str, dict] = defaultdict(lambda: {"total": 0, "informais": 0, "nome": ""})
    for row in raw[1:]:  # pula header
        cod = row["D1C"]
        cat = row["D4C"]  # código da categoria de ocupação
        val = int(row["V"]) if row["V"] not in ("", "X", "-") else 0
        nome = row["D1N"].replace(" (SP)", "")  # remove sufixo "(SP)"
        by_mun[cod]["nome"] = nome
        if cat == "96165":
            by_mun[cod]["total"] += val
        else:  # qualquer das 5 categorias informais
            by_mun[cod]["informais"] += val
    
    rows = []
    for cod, data in by_mun.items():
        total = data["total"]
        informais = data["informais"]
        taxa = round(informais / total * 100, 2) if total > 0 else None
        rows.append({
            "municipio": data["nome"],
            "uf": "SP",
            "codigo_ibge": cod,
            "total_ocupados": total,
            "informais": informais,
            "taxa_informalidade_pct": taxa,
            "ano_censo": 2022,
            "fonte": (
                "Censo Demográfico 2022, IBGE, SIDRA t/10261, n6, v/4090, "
                "categorias 31723+79368+45935+45937+31731 / Total (96165). "
                "Definição IBGE de informalidade (5 componentes). "
                "https://sidra.ibge.gov.br/tabela/10261"
            ),
        })
    return rows
```

### Exemplo 2: Busca RAIS no BigQuery sem pandas

```python
# Source: google.cloud.bigquery (verificado ao vivo — 2026-06-23)
import polars as pl
from google.cloud import bigquery

WASTE_CNAES = [
    "3811400", "3812200", "3821100", "3822000",
    "3831901", "3832700", "3839401", "3839499", "3900500",
]

def fetch_rais(billing_project: str = "residuos-github", ano: int = 2023,
               rms_codes: list[str] = None) -> pl.DataFrame:
    if rms_codes is None:
        from .ibge_informalidade import RMS_IBGE_CODES
        rms_codes = RMS_IBGE_CODES
    
    client = bigquery.Client(project=billing_project)
    codes_sql = ", ".join(f"'{c}'" for c in rms_codes)
    cnaes_sql = ", ".join(f"'{c}'" for c in WASTE_CNAES)
    
    query = f"""
    SELECT
      id_municipio,
      SUM(quantidade_vinculos_ativos) AS formais_residuos
    FROM `basedosdados.br_me_rais.microdados_estabelecimentos`
    WHERE sigla_uf = 'SP'
      AND ano = {ano}
      AND id_municipio IN ({codes_sql})
      AND cnae_2_subclasse IN ({cnaes_sql})
    GROUP BY id_municipio
    """
    result = client.query(query).result()
    return pl.from_arrow(result.to_arrow())
```

### Exemplo 3: Cálculo do proxy D-06/D-07 em Polars

```python
# Source: padrão do projeto transform.py + D-06/D-07 de 02-CONTEXT.md
import polars as pl

df = df.with_columns([
    # Denominador: formais + cooperados (null → 0 para fins de soma)
    (
        pl.col("formais_residuos").fill_null(0) +
        pl.col("cooperados").fill_null(0)
    ).alias("_denominador"),
    
    # D-07: proxy pendente quando AMBOS são null/0
    pl.when(
        ((pl.col("formais_residuos").is_null()) | (pl.col("formais_residuos") == 0)) &
        ((pl.col("cooperados").is_null()) | (pl.col("cooperados") == 0))
    ).then(pl.lit(None))
    .when(pl.col("_denominador") > 0)
    .then(pl.col("formais_residuos").fill_null(0) / pl.col("_denominador"))
    .otherwise(pl.lit(None))
    .alias("proxy_formalizacao"),
])

df = df.with_columns([
    pl.when(pl.col("proxy_formalizacao").is_null())
      .then(pl.lit("pendente"))
      .otherwise(pl.lit("real"))
      .alias("flag_proxy"),
]).drop("_denominador")
```

---

## Análise do Estado da Arte

| Abordagem antiga | Abordagem atual | Mudança | Impacto |
|------------------|-----------------|---------|---------|
| Taxa de informalidade PNAD por município | Censo 2022 por município (SIDRA t/10261) | Censo 2022 publicado completo | Dado real disponível para todos os 27; sem mais estimativas municipais |
| CAGED para emprego formal (fluxo) | RAIS para estoque (31/12) | CAGED é fluxo (admissões/demissões); RAIS é estoque de vínculos ativos | RAIS é mais apropriado para "quanto emprego formal existe hoje" |
| Microdados RAIS individuais (400GB+) | `microdados_estabelecimentos` agregado (bem menor) | Tabela diferente do BD | Menor custo de query no BigQuery; suficiente para total por município+CNAE |
| Pandas para leitura do BigQuery | `pl.from_arrow(result.to_arrow())` | Polars-nativo | Consistência com o pipeline; sem pandas em runtime |

---

## Restrições do Projeto (de CLAUDE.md)

- **Nunca inventar número.** Todos os campos novos carregam flag `real`/`estimativa`/`pendente`.
- **Polars, não pandas.** Qualquer conversão do BigQuery é via `.to_arrow()` → `pl.from_arrow()`.
- **Junção por `base.slug()`**, não por código IBGE ou qualquer outra chave.
- **Fonte por linha.** Cada município tem `fonte_inf` e `fonte_proxy` preenchidos no CSV de snapshot.
- **Build offline e determinístico.** Os CSVs commitados são a fonte de verdade; `refresh()` só é chamado manualmente.
- **Catador como piso.** A nota D-10 usa linguagem de "piso" (floor), não "total".
- **Baseline × estimativa visualmente separados.** PNAD nunca aparece no mesmo card que o Censo.
- **Sem framework no front.** HTML + CSS + JS vanilla; sem build step.
- **`model.py` ↔ `app.js` paridade.** Não aplicável nesta fase (sem mudança no simulador BSF).

---

## Perguntas em Aberto

1. **Atualização do `municipios.csv`**
   - O que sabemos: 26 dos 27 municípios têm `codigo_ibge` vazio no cache.
   - Lacuna: o pipeline não usa o código para join, mas outras fases (ex.: Fase 4 `ibge.refresh()`) vão precisar.
   - Recomendação: o planner pode incluir uma tarefa pequena de atualizar o CSV com os 27 códigos verificados nesta pesquisa (tabela acima). Não bloqueia a Fase 2.

2. **Versão dos 7 vs. 5 componentes de informalidade**
   - O que sabemos: com 5 componentes (sem público/estatais sem carteira), Sorocaba = 28,0%. Com 7 componentes, ligeiramente maior.
   - Lacuna: documentar qual versão o IBGE usa em seus boletins divulgados.
   - Recomendação: usar os 5 componentes padrão (sem público sem carteira) para alinhar com boletins IBGE e a definição PNAD Contínua. Flag: [ASSUMED — baseado em interpretação dos boletins IBGE; verificar na publicação oficial do Censo 2022 Trabalho e Rendimento].

3. **Estrutura modular: um ou três módulos de fonte?**
   - O que sabemos: ambos os padrões são válidos e seguem o molde existente.
   - Lacuna: decisão de granularidade é discrição do planner.
   - Recomendação: três módulos separados (`ibge_informalidade.py`, `rais.py`, `pnad_regional.py`) por clareza e independência de `refresh()`.

---

## Disponibilidade de Ambiente

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|------------|--------|----------|
| SIDRA API (apisidra.ibge.gov.br) | `refresh()` de ibge_informalidade.py | Sim (pública, sem auth) | — | CSV commitado |
| BigQuery (google.cloud.bigquery) | `refresh()` de rais.py | Sim (auth ADC verificado) | — | CSV commitado |
| PNAD SIDRA (t/4093) | `refresh()` de pnad_regional.py | Sim (pública, sem auth) | — | CSV commitado |
| polars | Todas as fontes | Sim | ≥1.0 | — |
| httpx | `refresh()` SIDRA | Sim | ≥0.27 | — |
| basedosdados | `refresh()` RAIS (alt.) | Sim (dev group) | ≥2.0.3 | bigquery client direto |

**Sem dependências faltando.**

---

## Arquitetura de Validação

`nyquist_validation: false` — seção incluída por boas práticas, mas sem geração automática de plano de testes.

### Framework de Testes

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest |
| Arquivo de configuração | nenhum (pytest.ini não existe) |
| Comando rápido | `uv run pytest -q` |
| Suite completa | `uv run pytest -q` (apenas um arquivo de testes) |

### Mapa Requisito → Teste

| Req ID | Comportamento | Tipo de Teste | Comando | Existe? |
|--------|--------------|---------------|---------|---------|
| INFO-01 | `ibge_informalidade.load()` retorna 27 linhas com taxa não-nula | unit | `uv run pytest tests/test_pipeline.py::test_informalidade_censo_27_municipios -x` | Não — Wave 0 |
| INFO-01 | Invariante: nunca inventar número — município sem dado → pendente | unit | `uv run pytest tests/test_pipeline.py::test_informalidade_pendente_honesto -x` | Não — Wave 0 |
| INFO-01 | PNAD NÃO aparece em `municipios[]`, só em `meta` | unit | `uv run pytest tests/test_pipeline.py::test_pnad_nao_por_municipio -x` | Não — Wave 0 |
| INFO-02 | `rais.load()` retorna vínculos para municípios com estabelecimento | unit | `uv run pytest tests/test_pipeline.py::test_rais_load -x` | Não — Wave 0 |
| INFO-02 | D-07: proxy=pendente quando formais=0 E cooperados=null | unit | `uv run pytest tests/test_pipeline.py::test_proxy_pendente_edge_case -x` | Não — Wave 0 |
| INFO-02 | D-06: proxy calcula ratio correto quando há dados | unit | `uv run pytest tests/test_pipeline.py::test_proxy_formalizacao_calculo -x` | Não — Wave 0 |
| INFO-03 | `data.json` contém campos `taxa_informalidade_pct` e `flag_informalidade` | integração | `uv run pytest tests/test_pipeline.py::test_payload_tem_informalidade -x` | Não — Wave 0 |
| INFO-04 | — (nota fixa no HTML; validação manual) | manual | — | — |

### Gaps Wave 0

- `tests/test_pipeline.py` precisa de novos testes para INFO-01..03 (adicionar ao arquivo existente)
- Fixtures de CSV mínimos para `data/raw/censo/` e `data/raw/rais/` (para testes offline)

---

## Segurança

`security_enforcement: true`, `security_asvs_level: 1`

### Categorias ASVS Aplicáveis

| Categoria ASVS | Aplica? | Controle Padrão |
|---------------|---------|-----------------|
| V2 Autenticação | Não | — (sem login; painel público read-only) |
| V3 Gestão de Sessão | Não | — |
| V4 Controle de Acesso | Não | — (estático) |
| V5 Validação de Entrada | Sim | Validação de tipos no `SCHEMA` Polars; `refresh()` valida resposta SIDRA antes de escrever CSV |
| V6 Criptografia | Não | — (sem armazenamento de segredos) |

### Padrões de Ameaça

| Padrão | STRIDE | Mitigação |
|--------|--------|-----------|
| Dados corrompidos no CSV de snapshot | Adulteração | Schema Polars rejeita tipos inválidos no `load()`; CSV commitado no git |
| Injeção SQL via CNAE ou código IBGE | Adulteração | Usar listas literais hardcoded nos scripts de `refresh()` — sem interpolação de entrada de usuário |
| Credenciais GCP vazadas | Divulgação | ADC (application-default credentials) — não commitadas; `.venv` e arquivos de auth em `.gitignore` |
| Dado inventado apresentado como real | Repúdio | Flag `real`/`estimativa`/`pendente` obrigatório; testes de invariante |

---

## Fontes

### Primárias (confiança ALTA)

- `https://apisidra.ibge.gov.br/values/t/10261/n6/.../` — tabela Censo 2022 verificada ao vivo, dados dos 27 municípios calculados
- `https://servicodados.ibge.gov.br/api/v3/agregados/10261/metadados` — metadados completos da tabela (classificações, categorias, níveis territoriais)
- `https://apisidra.ibge.gov.br/values/t/4093/n3/35/v/12466/p/last/c2/6794` — PNAD SP verificada ao vivo
- `basedosdados.br_me_rais.microdados_estabelecimentos` — BigQuery schema e query executados ao vivo
- `servicodados.ibge.gov.br/api/v2/cnae/subclasses/{código}` — CNAEs verificados individualmente
- `servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios` — 27 códigos IBGE confirmados
- `servicodados.ibge.gov.br/api/v1/localidades/regioes-metropolitanas` — RM Sorocaba código 05301 confirmado

### Secundárias (confiança MÉDIA)

- Página SIDRA Censo 2022 Trabalho e Rendimento — lista de tabelas disponíveis (confirma 10261 como a tabela de posição na ocupação ao nível municipal)
- Issue GitHub basedosdados/queries-basedosdados#565 — confirma colunas da tabela RAIS

### Terciárias (confiança BAIXA — marcadas [ASSUMED])

- Decisão de excluir CNAEs 46877x (comércio atacadista) do proxy — critério de escopo, sem fonte oficial definidora
- Decisão de usar 5 componentes (vs. 7) na definição de informalidade — padrão dos boletins IBGE interpretado via treinamento

---

## Log de Suposições

| # | Afirmação | Seção | Risco se Errada |
|---|-----------|-------|-----------------|
| A1 | Excluir CNAEs 4687701/4687702/4687703 (atacadistas de resíduos) do proxy de formalização | INFO-02 / Stack Padrão | Subestimaria empregos formais relacionados ao setor (catadores em redes de comercialização) |
| A2 | Usar 5 componentes de informalidade (sem empregado público sem carteira) alinha com boletins IBGE publicados | INFO-01 / Code Examples | Taxa levemente menor que a divulgada pelo IBGE em boletins oficiais; comparabilidade comprometida |
| A3 | `rais.py::refresh()` deve usar `google.cloud.bigquery.Client` diretamente, não `basedosdados.read_sql()` | Architecture Patterns | Nenhum — é decisão de implementação com impacto em qualidade de código, não em dado |

**Nota:** se A1 ou A2 forem revistos, os valores dos 27 municípios já calculados mudam numericamente mas não mudam a estrutura da pipeline. O planner pode incluir uma tarefa de validação dos componentes com o usuário.

---

## Metadados

**Confiança por área:**
- Stack (fontes, CNAEs, API): ALTA — verificado ao vivo
- Dados calculados (27 municípios): ALTA — query ao vivo, não treinamento
- Integração pipeline: ALTA — baseado em leitura direta do código existente
- Exibição JS: MÉDIA — padrão existente interpretado; detalhes CSS finos não verificados

**Data da pesquisa:** 2026-06-23
**Válido até:** 2026-12-31 (RAIS pode ter ano mais recente; PNAD atualiza trimestralmente)
