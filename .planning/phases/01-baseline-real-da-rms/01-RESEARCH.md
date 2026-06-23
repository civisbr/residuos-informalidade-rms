# Phase 1: Baseline real da RMS — Research

**Researched:** 2026-06-21
**Domain:** Dado público brasileiro de resíduos sólidos — SNIS-RS / SINISA, PMGIRS, Polars pipeline
**Confidence:** MEDIUM-HIGH (fontes primárias verificadas para Sorocaba e SNIS; Porto Feliz bloqueado por tamanho de PDF)

---

## Summary

A Phase 1 transforma o esqueleto M0 num observatório honesto: os 27 municípios da RMS saem de 2/27 com dado para 27/27 com linha — real onde o SNIS tiver, `pendente` onde não tiver. O trabalho tem três partes distintas:

**Parte A — SNIS para os 25 restantes (BASE-01, BASE-04, BASE-05).** O SNIS-RS disponibiliza série histórica (2002–2022+) pelo portal `app4.mdr.gov.br/serieHistorica/` e via Portal de Dados Abertos; o export é manual (UI web, não há API de download direto confirmada), e produz XLSX/CSV com os campos que o `SCHEMA` de `sources/snis.py` já espera. O processo: filtrar por estado SP, selecionar os 25 municípios da RMS, exportar, ajustar colunas, adicionar coluna `fonte` e soltar em `data/raw/snis/`. A pipeline mantém o ano mais recente por município automaticamente.

**Parte B — Gravimetria real de Sorocaba (BASE-02).** O PMGIRS de Sorocaba (SHS Consultoria, setembro/2014, publicado na SMA-SP) registra explicitamente: **"48% em massa dos resíduos domiciliares é matéria orgânica, gerando uma quantidade de 260 t/dia"** (Tomo 2, p. 27). O `coefficients.yml` atual usa 0,51 (média Brasil). A substituição exige tornar a `composicao` por-município, não mais global — o que impacta `transform.py` e provavelmente não exige mudança em `app.js` (já que o percentual orgânico entra via `data.json`).

**Parte C — RSU/reciclado/cooperados de Porto Feliz (BASE-03).** O PMGIRS de Porto Feliz está hospedado na SMA-SP (`smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf`) mas o arquivo excedeu 10 MB no WebFetch — não foi possível ler o conteúdo nesta sessão. A extração do dado real de Porto Feliz está marcada `[ASSUMED]` e requer que o pesquisador faça download e leia o PDF localmente. O dado atualmente no CSV (`17160 t/ano, qualidade=estimativa`) é explicitamente marcado como estimativa baseada em população.

**Restrição arquitetural central (regra sagrada):** Nenhuma das três partes pode inventar número. Municípios sem resposta do SNIS ficam `pendente` com `rsu_t_ano = null`. A coluna `fonte` é obrigatória em toda linha com dado.

**Primary recommendation:** Executar as três partes em sequência: (1) download manual do SNIS para os 25 municípios e ingestão via CSV; (2) substituição da composição global por dado por-município em `transform.py`; (3) extração manual do PMGIRS de Porto Feliz e elevação de `estimativa` para `real`.

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte desta pesquisa |
|----|-----------|------------------------|
| BASE-01 | Série histórica do SNIS-RS baixada e processada para a RMS | Portal SNIS + mapeamento de campos documentado abaixo |
| BASE-02 | Gravimetria real do PMGIRS de Sorocaba substitui `composicao` global | PMGIRS Sorocaba verificado: 48% orgânico (p. 27 do Tomo 2) |
| BASE-03 | RSU/reciclado/cooperados de Porto Feliz do PMGIRS 2017 (SMA-SP) | URL localizada; conteúdo não lido (PDF grande) — tarefa requer download local |
| BASE-04 | Os 27 municípios têm linha (real com o que o SNIS tiver; sem dado → `pendente`) | Pipeline já suporta; faltam os CSVs |
| BASE-05 | Cada linha cita sua `fonte` | Coluna `fonte` já existe no SCHEMA; precisa ser preenchida nos novos CSVs |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **Regra sagrada:** Nunca inventar número. Município sem fonte pública fica `pendente`. Flag obrigatório em todo indicador.
- **Stack obrigatório:** Python 3.11+, Polars (nunca pandas), type hints, funções puras quando possível.
- **Paridade model.py ↔ app.js:** Qualquer mudança na lógica de cálculo que afete projeção BSF exige atualizar os dois lados e ajustar o teste de paridade.
- **Junção por slug:** `base.slug()` é a chave de junção — nome no CSV precisa bater com `regions.yml`.
- **Fonte por linha:** Coluna `fonte` obrigatória em toda linha com dado real.
- **Sem framework no front:** HTML + CSS + JS vanilla lendo `data.json`. Sem build step.
- **Build offline e determinístico:** `uv run obs build` deve funcionar sem rede após download dos dados.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Download do SNIS | Operador humano (manual) | — | Não há API de download confirmada; é export manual do portal |
| Ingestão CSV → DataFrame | Pipeline Python (sources/snis.py) | — | Adaptador já existe; load() lê todos os CSVs em data/raw/snis/ |
| Composição por-município | Pipeline Python (transform.py) | config/coefficients.yml | Hoje é global; precisa virar coluna por linha |
| Flag de qualidade | Pipeline Python (transform.py) | — | Derivado na junção: sem RSU → pendente |
| Coluna `fonte` | CSV de entrada (dado) | Pipeline (passthrough) | Preenchida pelo humano ao montar o CSV; pipeline só passa adiante |
| Gravimetria Sorocaba | config/coefficients.yml ou dado por-município | transform.py | Se virar dado por-município, vai para o CSV ou estrutura separada |
| Exibição de `fonte` no painel | Frontend (site/app.js) | render.py | render.py já inclui `fonte` no payload; app.js precisa exibir |

---

## Standard Stack

### Core (sem mudança — stack existente)

| Biblioteca | Versão | Propósito | Por que é o padrão |
|------------|--------|-----------|-------------------|
| Polars | 1.41.2 | Todas as operações DataFrame na pipeline | CLAUDE.md proíbe pandas; Polars já em uso |
| PyYAML | >=6.0 | Carrega coefficients.yml e regions.yml | Já em uso |
| Python | 3.13.5 (runtime) | Linguagem da pipeline | Já em uso |

### Sem novas dependências previstas

Esta fase é 100% manipulação de dados em arquivos locais — CSV in, CSV transformado, JSON out. Não adiciona nenhum pacote novo.

**Instalação:** `uv sync` (sem mudança — nenhum pacote novo).

---

## Package Legitimacy Audit

> Não aplicável. Esta fase não instala nenhum pacote externo novo.

---

## Architecture Patterns

### System Architecture Diagram (existente, sem mudança de fluxo)

```
HUMANO: download manual do SNIS (app4.mdr.gov.br) → CSVs ajustados
                                                       ↓
data/raw/snis/*.csv  ─────────────► snis.load()  ─────┐
config/municipios.csv ────────────► ibge.load()  ─────┤
config/regions.yml   ─────────────► cli.cmd_build     ┤
config/coefficients.yml  ──────────────────────────────┤
                                                        ▼
                                    transform.build_region()
                                    (join por slug + indicadores + flag)
                                         ↓
                                    flag = real/estimativa/pendente
                                    fonte = passthrough do CSV
                                    organico_t_ano = rsu × composicao[municipio]  ← MUDANÇA
                                         ↓
                                    render.to_payload() → site/data.json
                                         ↓
                           site/app.js: exibe `fonte` por município
```

### Mudança arquitetural central desta fase: composição por-município

Hoje `transform.py` lê `coef["composicao"]["organico"]` — um escalar global para todos os municípios. BASE-02 exige que Sorocaba use 0,48 (gravimetria PMGIRS) e os demais usem o default global 0,51.

**Padrão recomendado:** Adicionar coluna `composicao_organico` ao CSV do SNIS (ou em arquivo de dados separado por município). Se a coluna estiver presente e não-nula, `transform.py` usa ela; caso contrário, usa o default de `coefficients.yml`. Isso respeita a estrutura existente e não força mudança em `app.js` (o percentual orgânico derivado chega via `organico_t_ano` no `data.json`).

```python
# Padrão de substituição em transform.py (Pattern: coluna por-município com fallback global)
# Fonte: design inferido da estrutura atual — [ASSUMED]
df = df.with_columns([
    pl.when(pl.col("composicao_organico").is_not_null())
      .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
      .otherwise(pl.col("rsu_t_ano") * org_pct)
      .alias("organico_t_ano"),
    ...
])
```

**Alternativa mais simples:** Dado que hoje só Sorocaba tem gravimetria real, adicionar a coluna `composicao_organico` diretamente no CSV do SNIS de Sorocaba (valor `0.48`) e deixar os demais com null (usa global). Mais simples e mais honesto com a fonte.

### Recommended Project Structure (sem mudança)

```
data/raw/snis/
├── snis_rs_sample.csv        # existente (Sorocaba + Porto Feliz)
└── snis_rms_2022.csv         # NOVO — os demais 25 municípios (ou múltiplos arquivos por ano)
config/
└── coefficients.yml          # sem mudança no valor; composição por-município vai no CSV
pipeline/
├── sources/snis.py           # sem mudança de interface; SCHEMA pode precisar de campo extra
└── transform.py              # MUDANÇA: composição por-município com fallback global
```

### Anti-Patterns a Evitar

- **Inventar número para município sem dado SNIS:** Proibido pela regra sagrada. Município sem dado fica `pendente` com `rsu_t_ano = null`.
- **Usar média regional para preencher pendente:** Também proibido. Piso honesto > estimativa desonesta.
- **Misturar gravimetria estimada com flag `real`:** Se a composição orgânica for estimativa, o flag do indicador derivado (`organico_t_ano`) precisa refletir isso ou ser documentado.
- **Nome de município no CSV divergindo do `regions.yml`:** A junção é por `slug()`. "São Roque" vs "Sao Roque" — a função slug resolve, mas "S. Roque" quebraria.
- **Adicionar dados de municípios de outros estados:** O SNIS tem municípios de todo o Brasil com nomes iguais (ex.: "Salto" existe em SP e em outros estados). Filtrar por UF = SP na extração.

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez | Por quê |
|----------|---------------|-------------|---------|
| Normalização de nome de município | Parser próprio | `base.slug()` (já existe) | Já lida com NFKD, acentos, caixa |
| Deduplicação por ano | Loop manual | `.sort("ano", descending=True).unique(subset=["key"], keep="first")` | Já implementado em `snis.load()` |
| Junção município ↔ SNIS | Merge manual | `.join(..., on="key", how="left")` em `transform.py` | Já implementado |
| Flag de qualidade | Lógica if/else dispersa | `pl.when(...).then(...).otherwise(...)` no `transform.py` | Padrão Polars; já implementado |
| Múltiplos CSVs SNIS | Concatenação manual | `pl.concat(frames, how="vertical_relaxed")` em `snis.load()` | Já implementado — solte vários CSVs em `data/raw/snis/` |

**Key insight:** A pipeline já suporta múltiplos arquivos CSV — basta soltar os novos CSVs do SNIS em `data/raw/snis/` e rodar o build. Não há necessidade de modificar `snis.load()` para ingerir dados adicionais.

---

## Fontes de Dado: Detalhamento por Requisito

### BASE-01 e BASE-04: SNIS-RS — Como baixar e quais campos usar

**Portal:** `https://app4.mdr.gov.br/serieHistorica/residuosSolidos/index`
**Dados abertos (alternativa):** `https://dadosabertos.cidades.gov.br/pt_PT/dataset/snis-serie-historica`
**Base dos Dados (alternativa SQL):** `https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697`
[CITED: app4.mdr.gov.br/serieHistorica/residuosSolidos/index]

**Anos disponíveis:** 2002–2022 (SNIS). A partir de 2024, o sistema migrou para SINISA (`indicadores-sinisa-2025.cidades.gov.br`). [CITED: diagnóstico CNMP/SNIS 2021]

**Defasagem:** O SNIS publica o diagnóstico anual com ~12-18 meses de atraso (dados de 2022 publicados em 2023/2024). [ASSUMED — defasagem típica baseada em padrão histórico do SNIS]

**Processo de download:** A extração do portal é via UI web — seleciona UF, municípios, ano, indicadores, e exporta para XLSX ou CSV. Não há URL de download direto de arquivo confirmada nesta pesquisa. O runbook `scripts/refresh_snis.md` documenta esse fluxo. [VERIFIED: arquivo scripts/refresh_snis.md no repositório]

**Mapeamento de campos SNIS → schema do projeto:**

| Campo schema (`snis.py`) | Campo SNIS | Descrição SNIS | Unidade |
|--------------------------|-----------|----------------|---------|
| `rsu_t_ano` | `CO116` + `CO117` + `CO142` + `CS048` | RDO+RPU coletado (público + privado + outros + cooperativas) | t/ano |
| `reciclado_t_ano` | `CS026` | Qtd total recolhida em coleta seletiva (4 agentes) | t/ano |
| `reciclado_pct` | `IN031` | Taxa de recuperação de recicláveis / total coletado | % |
| `coleta_seletiva_pop_pct` | `IN030` | Cobertura da coleta seletiva porta-a-porta / pop. urbana | % |
| `cooperados` | `CS048` implica presença; qtd. de associados não é IN — ver nota | ver nota abaixo | unidades |
| `custo_mensal_rs` | `FN220` / 12 | Despesa total anual com manejo de RSU ÷ 12 | R$/mês |
| `qualidade` | (derivado) | `real` se dado SNIS direto | — |
| `fonte` | (preenchido pelo operador) | ex.: "SNIS-RS 2022" | — |

[CITED: Glossário de Indicadores RS 2022, gov.br/cidades — Ministério das Cidades, emitido 30/03/2023]

**Nota sobre `cooperados`:** O SNIS não coleta diretamente "número de catadores associados" como campo individual por município de forma simples. O campo `CS048` é a *quantidade coletada em toneladas* por cooperativas/associações com parceria da prefeitura, não o número de pessoas. O número de associados é declarado pelas prefeituras na amostra SNIS, mas não como indicador padrão no glossário de indicadores RS 2022. Para municípios onde este dado não existir no SNIS, `cooperados` deve ficar `null` (não inventar). [CITED: Glossário de Indicadores RS 2022]

**Aviso de subcontagem:** O SNIS-RS "não realiza censo dos catadores. O valor corresponde ao declarado pelas prefeituras participantes da amostra." [CITED: Diagnóstico Temático SNIS-RS 2020/2021, CNMP, p. 49] — O campo `cooperados` em toda base deve ser tratado como piso, não como contagem real.

**Conversão de unidades:** O SNIS exporta algumas quantidades em toneladas/ano; `custo_mensal_rs` precisa ser calculado como `FN220 / 12` (ou preenchido com o valor anual se a coluna aceitar). Verificar unidade do export antes de inserir.

**Municípios sem dado SNIS:** Em 2020, apenas 4.589 de 5.570 municípios participaram do SNIS-RS. É esperado que alguns dos 25 municípios menores da RMS não tenham dado — eles ficam `pendente` com `rsu_t_ano = null`. [CITED: Diagnóstico Temático SNIS-RS 2020/2021]

---

### BASE-02: Gravimetria real de Sorocaba (PMGIRS)

**Fonte verificada:** PMGIRS de Sorocaba, Tomo 2 — Planejamento Integrado, SHS Consultoria e Projetos de Engenharia Ltda., setembro/2014, publicado pela SMA-SP.

**URL:** `https://smastr16.blob.core.windows.net/cpla/2017/05/sorocaba-vol.-2.pdf`
**URL alternativa (prefeitura):** `http://www.sorocaba.sp.gov.br/anexos/SEAD/Outros/Plano-Municipal-Residuos-solidos/`

**Dado verificado:** `"De acordo com a gravimetria dos resíduos de Sorocaba, 48% em massa dos resíduos domiciliares é matéria orgânica, gerando uma quantidade de 260 t/dia."` — Tomo 2, p. 27.
[VERIFIED: PDF lido diretamente via pdftotext nesta sessão]

**Contexto adicional verificado no mesmo documento:**
- Ano base do PMGIRS: 2014 (dado de diagnóstico referente a 2013/2014)
- RSU total implícito: 260 t/dia ÷ 0,48 ≈ **541 t/dia ≈ 197.500 t/ano** (para população de ~629 mil hab. em 2013)
- O CSV atual do projeto tem Sorocaba com 228.000 t/ano (ano 2024), o que é coerente — população cresceu e o dado é mais recente.
- Cooperativas identificadas no documento: REVIVER, CORENT, UNIÃO, CORESO, CATARES (Sorocaba)
- O dado atual de 140 cooperados para Sorocaba no CSV vem de fonte diferente (SNIS 2024 / Prefeitura). A gravimetria PMGIRS é independente e complementar.

**Como citar na coluna `fonte`:** `"PMGIRS Sorocaba — SHS Consultoria/Prefeitura de Sorocaba, 2014. Gravimetria: 48% orgânico (Tomo 2, p. 27)"`

**Impacto em `coefficients.yml` vs. dado por-município:**
A composição 48% é específica para Sorocaba (domiciliar). O coeficiente global 51% (média Brasil) continua válido para os demais municípios sem gravimetria própria. A mudança necessária é tornar a composição orgânica por-município — não alterar o coeficiente global.

---

### BASE-03: Porto Feliz — PMGIRS 2017 (SMA-SP)

**URL localizada:** `https://smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf`
**URL arquivo (SMA):** `http://arquivo.ambiente.sp.gov.br/cpla/2017/05/porto-feliz.pdf`
[CITED: resultado de busca — smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf]

**Status de leitura:** O PDF excedeu o limite de tamanho do WebFetch durante esta pesquisa. O conteúdo não foi lido. [ASSUMED que contém RSU, reciclado, cooperados — é o tipo de dado que um PMGIRS sempre inclui, mas os números específicos precisam ser extraídos manualmente.]

**Ação necessária no plano:** Uma tarefa deve incluir download local e extração dos dados de RSU total, reciclado/coleta seletiva, e cooperados de Porto Feliz. Usar `pdftotext` ou similar. A data de referência do PMGIRS é 2017 (dados do diagnóstico provavelmente 2015-2016).

**Dado atual no projeto:** Porto Feliz está no CSV com `rsu_t_ano = 17160, qualidade = "estimativa"` e nota "Estimativa: pop x 0,9 kg/hab/dia". A extração do PMGIRS deve substituir esta estimativa por dado real citado.

**Como citar na coluna `fonte` (após extração):** `"PMGIRS Porto Feliz — SMA-SP, 2017, p. XX"` (número de página a preencher após leitura).

---

## Common Pitfalls

### Pitfall 1: Nome de município divergente entre SNIS e regions.yml

**O que falha:** A junção no `transform.py` usa `key = slug(nome)`. Se o SNIS exporta "São Roque" e o `regions.yml` tem "São Roque", `slug()` normaliza ambos para "sao roque" — OK. Mas se o SNIS exportar "S. Roque" ou "Sao Roque (SP)", a junção quebra e o município aparece como `pendente` mesmo com dado.

**Por que ocorre:** O SNIS usa sua própria nomenclatura; nomes com abreviações, sufixos "(SP)" ou variações ortográficas são comuns.

**Como evitar:** Após baixar o CSV do SNIS, rodar `uv run obs build --region rms` e verificar quais municípios continuam `pendente`. Se algum com dado esperado ficar `pendente`, investigar o slug. Pode-se adicionar um mapeamento explícito ou ajustar o nome no CSV para casar com `regions.yml`.

**Warning signs:** Build mostra menos municípios com dado do que o número de linhas no CSV.

---

### Pitfall 2: Filtrar apenas por UF sem verificar municípios homônimos

**O que falha:** O SNIS tem municípios com o mesmo nome em UFs diferentes. Se o export não filtrar por UF = SP antes de inserir no CSV, pode-se incluir "Salto" do RS em vez do "Salto" de SP.

**Por que ocorre:** Descuido no filtro de export do portal SNIS.

**Como evitar:** Sempre adicionar a coluna `uf` no CSV com o valor correto (SP para todos os municípios da RMS). O SCHEMA de `snis.py` inclui `uf: pl.String` por essa razão, mas a junção atual usa apenas `key` (slug do nome). Para municípios homônimos em UFs diferentes, a junção por slug quebraria — verificar se há homônimos entre os 25 municípios da RMS e outros estados.

---

### Pitfall 3: Usar `composicao` global como se fosse dado real de Sorocaba

**O que falha:** Depois de BASE-02, Sorocaba terá `composicao_organico = 0.48`. Se um bug de implementação fizer `organico_t_ano` de Sorocaba usar o global 0.51, o número no painel diverge da fonte citada — violação sutil da regra sagrada.

**Por que ocorre:** Lógica de fallback implementada erroneamente (ex.: verificar `null` em vez de `is_not_null()`).

**Como evitar:** Adicionar asserção no teste: `soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)`. O teste atual craca `rsu_t_ano == 228000` mas não verifica `organico_t_ano`.

---

### Pitfall 4: Apresentar Porto Feliz com flag `real` antes de ter o PMGIRS extraído

**O que falha:** Se o plano elevar o flag de `estimativa` para `real` para Porto Feliz antes de extrair o dado do PMGIRS, a regra sagrada é violada.

**Por que ocorre:** Confusão entre "encontramos a URL do PMGIRS" e "extraímos o dado do PMGIRS".

**Como evitar:** O upgrade de flag de Porto Feliz de `estimativa` → `real` só acontece **depois** que os números do PMGIRS estiverem no CSV com a fonte citada. Até lá, se os números mudarem, atualizar os números mantendo o flag adequado.

---

### Pitfall 5: Subcontagem de catadores — tratar como piso, não como total

**O que falha:** O número de `cooperados` no SNIS é autodeclarado pelas prefeituras e reconhecidamente subcontado. Apresentar sem nota de subcontagem no painel viola a regra sagrada (ver BASE-05 e INFO-04).

**Por que ocorre:** O dado parece uma contagem objetiva quando na verdade é uma estimativa com viés de subregistro.

**Como evitar:** A coluna `fonte` do campo `cooperados` deve incluir nota de subcontagem, ou o painel deve exibir aviso explícito (preparar terreno para INFO-04 na Fase 2). Na Fase 1, garantir que a fonte no CSV mencione "SNIS autodeclarado — tratar como piso".

---

### Pitfall 6: `custo_mensal_rs` — unidade e período de referência

**O que falha:** O SNIS reporta `FN220` como despesa anual total. Se inserido diretamente como `custo_mensal_rs`, o número fica 12x maior do que o esperado.

**Por que ocorre:** Confusão na conversão de unidade no momento de montar o CSV.

**Como evitar:** `custo_mensal_rs = FN220 / 12`. Documentar a conversão na coluna `fonte` do CSV.

---

## Code Examples

### Padrão atual: carga de múltiplos CSVs (snis.load — sem mudança necessária)

```python
# Source: pipeline/sources/snis.py (verificado nesta sessão)
def load(_root: Path = Path(".")) -> pl.DataFrame:
    files = sorted((_root / RAW).glob("*.csv"))
    if not files:
        return pl.DataFrame(schema=SCHEMA)
    frames = [pl.read_csv(f, schema_overrides=SCHEMA, infer_schema_length=0) for f in files]
    df = pl.concat(frames, how="vertical_relaxed")
    # mantém o ano mais recente por município
    df = (
        df.with_columns(pl.col("municipio").map_elements(slug, return_dtype=pl.String).alias("key"))
          .sort("ano", descending=True)
          .unique(subset=["key"], keep="first")
    )
    return df
```

### Padrão para composição por-município em transform.py

```python
# Source: design desta pesquisa — [ASSUMED] — a adaptar conforme implementação
# Pressupõe que o CSV do SNIS inclui coluna opcional "composicao_organico"
# (presente para Sorocaba = 0.48; null para os demais)
def build_region(municipios: list[dict], ibge: pl.DataFrame, snis: pl.DataFrame,
                 coef: dict) -> pl.DataFrame:
    org_pct_global = coef["composicao"]["organico"]  # 0.51 — default Brasil
    ...
    df = df.with_columns([
        # composição por-município com fallback global
        pl.when(pl.col("composicao_organico").is_not_null())
          .then(pl.col("rsu_t_ano") * pl.col("composicao_organico"))
          .otherwise(pl.col("rsu_t_ano") * org_pct_global)
          .alias("organico_t_ano"),
        ...
    ])
```

### Schema CSV para novos dados do SNIS (colunas obrigatórias)

```csv
municipio,uf,ano,rsu_t_ano,reciclado_t_ano,reciclado_pct,coleta_seletiva_pop_pct,cooperados,custo_mensal_rs,qualidade,fonte
Salto,SP,2022,XXXXX,XXX,X.X,X.X,XXX,XXXXXXX,real,"SNIS-RS 2022 — download em YYYY-MM-DD"
Itu,SP,2022,XXXXX,,,,,,real,"SNIS-RS 2022 — campos reciclado/cooperados não disponíveis"
Jumirim,SP,2022,,,,,,,,pendente,"SNIS-RS 2022 — município não participou"
```

Nota: Para municípios que não participaram do SNIS, incluir a linha com `rsu_t_ano` em branco (null), `qualidade = pendente`, e `fonte` explicando o motivo. [VERIFIED: snis.py SCHEMA e transform.py lógica de flag]

---

## State of the Art

| Abordagem antiga | Abordagem atual | Quando mudou | Impacto |
|-----------------|-----------------|--------------|---------|
| SNIS (gov autônomo) | SINISA — Sistema Nacional de Informações em Saneamento Básico (Lei 14.026/2020) | 2024 | Para dados pré-2024, continuar usando o portal SNIS histórico; dados 2024+ estarão no SINISA |
| `composicao.organico = 0.51` (global) | Por-município com fallback global | Esta fase (BASE-02) | Sorocaba passa a 0.48; outros municípios mantêm o global |
| 2/27 municípios com dado | 27/27 com linha (real ou pendente honesto) | Esta fase (BASE-04) | Painel passa a ser utilizável como referência regional |

**Deprecated/outdated:**
- Portal antigo `snis.gov.br` — redirecionado para o novo sistema. Usar `app4.mdr.gov.br` ou `dadosabertos.cidades.gov.br`.

---

## Runtime State Inventory

> Fase de ingestão/transformação de dado — não é rename/refactor. Mas há estado em arquivo que muda.

| Categoria | Itens encontrados | Ação necessária |
|-----------|------------------|-----------------|
| Stored data (arquivos) | `data/raw/snis/snis_rs_sample.csv` — 2 linhas (Sorocaba + Porto Feliz estimado) | Adicionar novos CSVs com dados dos 25 municípios; não apagar o arquivo existente |
| `config/municipios.csv` | 10 municípios com população, 18 com nome mas sem código/pop | Não muda nesta fase (M4 trata ibge.refresh) |
| `config/coefficients.yml` | `composicao.organico = 0.51` (global) | Não alterar valor global; composição por-município vai no CSV |
| `site/data.json` | Gerado — 2/27 municípios com dado | Regerado automaticamente pelo `obs build` após novos CSVs |
| Testes (`test_pipeline.py`) | `assert pend.height >= 20` — vai falhar quando municípios saírem de `pendente` | **Atualizar asserção** para refletir novo número de `pendentes` após dados do SNIS |
| Testes | `assert soro["rsu_t_ano"] == 228000` | Permanece válido — Sorocaba não muda |
| Testes — lacuna | Sem verificação de `organico_t_ano` para Sorocaba | **Adicionar teste:** `soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)` |

**Nada encontrado em:** Banco de dados, serviços ao vivo, OS-registered state, secrets/env vars. Projeto é 100% arquivo plano + build offline.

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|------------|--------|---------|
| Python 3.11+ (via uv) | Pipeline | ✓ | 3.13.5 | — |
| Polars | transform.py | ✓ | 1.41.2 | — |
| pytest | Testes | ✓ | 8.3.4 | — |
| uv | Build/test runner | ✓ | 0.9.8 | — |
| pdftotext | Extração Porto Feliz PMGIRS | ✓ | instalado em /usr/bin | — |
| Browser / acesso a app4.mdr.gov.br | Download SNIS | ✗ (operador humano) | — | basedosdados.org como alternativa |
| acesso a smastr16.blob.core.windows.net | Porto Feliz PMGIRS | ✗ (requer HTTPS no curl direto) | — | arquivo.ambiente.sp.gov.br |

**Missing dependencies with no fallback:** Nenhuma — o download SNIS é passo manual pelo operador, não requer automação nesta fase.

**Missing dependencies with fallback:**
- Download Porto Feliz PMGIRS: `curl -L "https://smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf" -o /tmp/porto-feliz.pdf` e `pdftotext /tmp/porto-feliz.pdf -` — requer HTTPS (curl resolve, o teste de request anterior usou http incorreto).

---

## Open Questions

1. **Número exato de municípios da RMS que têm dado no SNIS-RS**
   - O que sabemos: O SNIS não cobre todos os 5.570 municípios. Municípios pequenos (como Jumirim, Alambari, Tapiraí — população < 10 mil) frequentemente não participam.
   - O que está incerto: Quantos dos 25 municípios restantes terão algum dado vs. zero dado.
   - Recomendação: Ao fazer o download, registrar quais ficaram `pendente` e documentar no CSV (linha com `rsu_t_ano` null, `fonte = "SNIS-RS 2022 — município não participou"`).

2. **Dados de Porto Feliz no PMGIRS 2017**
   - O que sabemos: URL localizada, PMGIRS existe, ano de referência 2017.
   - O que está incerto: Valores exatos de RSU total, reciclado, cooperados.
   - Recomendação: Tarefa de extração manual — download do PDF + pdftotext + busca por "RSU", "tonelada", "coleta seletiva", "catador". O dado atual de 17.160 t/ano é estimativa (pop. 53k × 0,9 kg/hab/dia × 365).

3. **Composição orgânica como coluna no CSV vs. tabela separada**
   - O que sabemos: O SCHEMA de `snis.py` não tem `composicao_organico` hoje; adicionar exige mudança em duas ou três linhas.
   - O que está incerto: Se a abordagem "coluna no CSV" é preferida pelo mantenedor vs. "arquivo de configuração por-município separado".
   - Recomendação: Coluna no CSV é mais simples e mais rastreável (a fonte da composição fica na mesma linha do dado). Mas se o mantenedor preferir separar, uma tabela `config/gravimetria.csv` com `municipio, composicao_organico, fonte_gravimetria` também funciona.

4. **Ano de referência do SNIS a usar**
   - O que sabemos: SNIS 2022 é o mais recente completo disponível no sistema histórico. SINISA 2024+ substituiu o SNIS.
   - O que está incerto: Se os dados de 2022 já estão publicados no portal histórico ou se o mais recente é 2021.
   - Recomendação: Verificar no portal `app4.mdr.gov.br/serieHistorica/residuosSolidos/index` qual é o ano mais recente disponível ao fazer o download.

---

## Assumptions Log

| # | Afirmação | Seção | Risco se errada |
|---|-----------|-------|-----------------|
| A1 | Defasagem típica do SNIS é 12-18 meses (dados 2022 disponíveis em 2023/2024) | Fontes de Dado | Pode ser que só 2021 esteja disponível; impacta apenas o ano de referência |
| A2 | PMGIRS Porto Feliz contém RSU total, reciclado, cooperados | BASE-03 | Se o plano for muito agregado e não desagregar por município, os dados não estarão lá |
| A3 | Melhor abordagem para composição por-município é coluna no CSV | Architecture Patterns | Se o mantenedor preferir configuração externa, o padrão muda |
| A4 | `custo_mensal_rs` = `FN220 / 12` (SNIS exporta anual) | Mapeamento de campos | Se o SNIS exportar mensal, a divisão por 12 geraria erro |
| A5 | `cooperados` no SNIS não é campo padrão por município como contagem de pessoas | Mapeamento de campos | Se o portal de export tiver campo específico de qtd. de catadores associados, usar diretamente |

---

## Sources

### Primary (HIGH confidence)
- `pipeline/sources/snis.py` — SCHEMA de colunas verificado (municipio, uf, ano, rsu_t_ano, reciclado_t_ano, reciclado_pct, coleta_seletiva_pop_pct, cooperados, custo_mensal_rs, qualidade, fonte)
- `pipeline/transform.py` — lógica de flag e composição global verificada
- `data/raw/snis/snis_rs_sample.csv` — estrutura atual e dados de Sorocaba e Porto Feliz
- `config/coefficients.yml` — `composicao.organico = 0.51` verificado
- PMGIRS Sorocaba, Tomo 2, SHS Consultoria, set/2014 — gravimetria 48% orgânico, p. 27 (PDF lido via pdftotext)
- Glossário de Indicadores RS 2022, Ministério das Cidades/SNIS, emitido 30/03/2023 — mapeamento de campos CO116, CO117, CS048, CS026, CS009, FN220, IN031, IN030 (PDF lido via pdftotext)

### Secondary (MEDIUM confidence)
- Portal SNIS `app4.mdr.gov.br/serieHistorica/residuosSolidos/index` — confirmado via WebSearch como ponto de acesso à série histórica de resíduos sólidos [CITED: dados.gov.br/dados/conjuntos-dados/snis---srie-histrica]
- Diagnóstico Temático SNIS-RS 2020/2021 (CNMP) — estatísticas de cobertura e nota de subcontagem de catadores (PDF lido via pdftotext)
- URL do PMGIRS Porto Feliz: `smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf` — confirmada via WebSearch [CITED: resultado de busca]
- Transição SNIS → SINISA em 2024 [CITED: diagnóstico SNIS 2021, parágrafo introdutório]

### Tertiary (LOW confidence)
- Defasagem de publicação do SNIS (12-18 meses) — [ASSUMED] baseado em padrão histórico
- Conteúdo específico do PMGIRS Porto Feliz (RSU, reciclado, cooperados) — [ASSUMED] não lido nesta sessão
- Campo para número de catadores associados no export do SNIS — [ASSUMED] não verificado no portal diretamente

---

## Metadata

**Confidence breakdown:**
- Schema de dados (SNIS): HIGH — verificado no código e no glossário oficial
- Gravimetria Sorocaba (48%): HIGH — verificado no PDF do PMGIRS Tomo 2, p. 27
- URL e portal SNIS: MEDIUM — verificado via WebSearch e confirmado como portal oficial
- Conteúdo Porto Feliz: LOW — URL encontrada, PDF não lido
- Mapeamento CO116→rsu_t_ano: HIGH — derivado do Glossário de Indicadores RS 2022 oficial
- Campo `cooperados` vs. SNIS: MEDIUM — SNIS não tem campo simples para "nº de catadores" no glossário de indicadores

**Research date:** 2026-06-21
**Valid until:** 2026-09-21 (90 dias — SNIS histórico é estável; SINISA mudanças podem afetar novos downloads)
