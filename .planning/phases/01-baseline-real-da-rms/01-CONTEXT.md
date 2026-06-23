# Phase 1: Baseline real da RMS - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Levar os 27 municípios da RMS de 2/27 para 27/27 com linha de dado: `real` onde
o SNIS-RS / PMGIRS tiver, `pendente` honesto onde não tiver, com a coluna
`fonte` preenchida em toda linha com dado. Sorocaba e Porto Feliz completos a
partir de fonte citável (gravimetria PMGIRS Sorocaba 48%; RSU/reciclado/
cooperados de Porto Feliz do PMGIRS 2017). Cobre BASE-01..05.

**Fora de escopo (outras fases):** indicador de informalidade e aviso de
subcontagem no painel (Fase 2 / INFO-*), deploy contínuo no Pages (Fase 3),
generalização para outras cidades e `refresh()` automatizado (Fase 4).
Discussão clarifica COMO implementar o que já está escopado — não adiciona
capacidade nova.

</domain>

<decisions>
## Implementation Decisions

### Gravimetria / composição orgânica por-município
- **D-01:** A composição orgânica por-município mora numa **coluna `composicao_organico` no CSV do SNIS** (não em arquivo separado). A fonte da gravimetria fica na mesma linha do dado — rastreável. Sorocaba = `0.48`; demais municípios = `null`.
- **D-02:** `transform.py` usa a coluna quando não-nula, senão cai no global `coef["composicao"]["organico"]` (0,51). NÃO alterar o valor global em `coefficients.yml`. Padrão Polars: `pl.when(col.is_not_null()).then(rsu*col).otherwise(rsu*org_pct_global)`.
- **D-03:** Adicionar campo de **procedência da composição** por município (`composicao_fonte`) distinguindo gravimetria local de estimativa: `"PMGIRS local"` (Sorocaba) vs `"média Brasil (estimativa)"`. Objetivo: o `organico_t_ano` de municípios sem gravimetria local é estimativa derivada — isso precisa ser sinalizável no painel sem se confundir com o flag do RSU. Não misturar com o flag `real/estimativa/pendente` da linha.

### Ano-base do SNIS
- **D-04:** Manter o comportamento atual de `snis.load()` — **ano mais recente por município** (`sort("ano", descending=True).unique(subset=["key"], keep="first")`). Maximiza cobertura; cada município mostra seu dado mais fresco. NÃO fixar um ano único. As colunas `ano` + `fonte` deixam explícito o ano de cada linha.

### Porto Feliz (BASE-03) — dado bloqueado na pesquisa
- **D-05:** Durante a execução, **tentar extrair** o PMGIRS 2017 de Porto Feliz autonomamente: `curl -L` (HTTPS) do PDF + `pdftotext` (disponível em `/usr/bin/pdftotext`), buscando RSU total, reciclado/coleta seletiva, cooperados, com número de página para citar.
- **D-06 (regra sagrada):** Se a extração falhar (PDF escaneado/imagem, números não desagregados), Porto Feliz **mantém flag `estimativa`** e `fonte` explicando "estimativa por população; PMGIRS pendente de extração". **Nunca subir para `real` sem fonte citável.** Isso NÃO bloqueia o fechamento da Fase 1 — registrar como pendência carregada.

### Catadores / `cooperados`
- **D-07:** Onde o SNIS tiver o número: preencher `cooperados` e incluir na `fonte` a nota **"SNIS autodeclarado — tratar como piso"** (subcontagem reconhecida). Onde não tiver: `cooperados = null` (não inventar). Prepara o terreno para o aviso de subcontagem da Fase 2 (INFO-04), sem implementar o aviso no painel agora.

### Integridade de dado (regra sagrada — transversal)
- **D-08:** Município sem resposta do SNIS entra com linha de `rsu_t_ano` null, `qualidade = pendente`, e `fonte` explicando o motivo (ex.: "SNIS-RS {ano} — município não participou"). Jamais preencher com chute ou média regional.
- **D-09:** Filtrar export do SNIS por **UF = SP** e verificar homônimos de município entre estados antes de inserir (junção é por `slug(nome)`); conferir que nomes no CSV batem com `config/regions.yml`. Após o build, qualquer município com dado esperado que fique `pendente` indica divergência de slug — investigar.
- **D-10:** `custo_mensal_rs = FN220 / 12` (SNIS reporta despesa anual). Documentar a conversão na `fonte`.

### Testes (decisão de implementação, derivada da pesquisa)
- **D-11:** Atualizar a asserção `assert pend.height >= 20` em `tests/test_pipeline.py` para refletir o novo número de pendentes após ingestão do SNIS (menos pendentes).
- **D-12:** Adicionar teste travando BASE-02: `soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)` — garante que Sorocaba usa a gravimetria local 0,48 e não o global 0,51. Manter `assert soro["rsu_t_ano"] == 228000`. Build deve continuar offline e determinístico.

### Claude's Discretion
- Estrutura/nomes exatos dos novos CSVs em `data/raw/snis/` (ex.: `snis_rms_2022.csv` ou múltiplos por ano) — não apagar `snis_rs_sample.csv` existente.
- Se `composicao_organico`/`composicao_fonte` exigem extensão do `SCHEMA` em `sources/snis.py` e do passthrough em `transform.py`/`render.py` — decisão de implementação do planner/executor, respeitando o padrão existente.
- Mapeamento exato campo-a-campo SNIS→schema ao montar os CSVs (documentado no RESEARCH.md).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pesquisa e regra do projeto
- `.planning/phases/01-baseline-real-da-rms/01-RESEARCH.md` — mapeamento de campos SNIS→schema, gravimetria Sorocaba (48%, p.27), URLs de fonte, pitfalls, padrão de composição por-município. **Leitura obrigatória.**
- `CLAUDE.md` — regra sagrada de integridade de dado, Polars (não pandas), paridade `model.py`↔`app.js`, junção por `base.slug`, fonte por linha.
- `GSD.md` §M1 — checklist autoral da milestone.

### Código e dado a modificar
- `pipeline/sources/snis.py` — `SCHEMA` das colunas e `load()` (concatena múltiplos CSVs, mantém ano mais recente por slug). Pode precisar de `composicao_organico`/`composicao_fonte` no SCHEMA.
- `pipeline/transform.py` — lógica de flag e composição global; ponto da mudança D-02/D-03.
- `pipeline/render.py` — passthrough de campos para `site/data.json` (já inclui `fonte`).
- `pipeline/sources/base.py` — `slug()` (chave de junção; não reimplementar).
- `config/regions.yml` — 27 municípios da RMS (nomes-âncora para a junção).
- `config/coefficients.yml` — `composicao.organico = 0.51` (NÃO alterar; é o fallback global).
- `data/raw/snis/snis_rs_sample.csv` — estrutura atual (Sorocaba real + Porto Feliz estimativa); não apagar.
- `tests/test_pipeline.py` — asserções a atualizar (D-11, D-12).
- `scripts/refresh_snis.md` — runbook do download manual do SNIS.

### Fontes externas (download na execução)
- SNIS série histórica: `https://app4.mdr.gov.br/serieHistorica/residuosSolidos/index` (export manual, UF=SP). Alternativa: `https://dadosabertos.cidades.gov.br/.../snis-serie-historica`.
- PMGIRS Sorocaba (gravimetria 48%, Tomo 2 p.27): `https://smastr16.blob.core.windows.net/cpla/2017/05/sorocaba-vol.-2.pdf`.
- PMGIRS Porto Feliz 2017: `https://smastr16.blob.core.windows.net/cpla/2017/05/porto-feliz.pdf` (extrair via pdftotext).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `snis.load()` já concatena todos os `data/raw/snis/*.csv` (`pl.concat(how="vertical_relaxed")`) e deduplica por ano — basta soltar novos CSVs, sem mudar a interface da fonte.
- `base.slug()` (NFKD, sem acento, lower) resolve a junção nome→município; reusar, não reimplementar.
- Padrão de flag `pl.when(...).then(...).otherwise(...)` em `transform.py` é onde a composição por-município se encaixa.

### Established Patterns
- Pipeline batch offline → `data.json` estático → painel vanilla. Sem framework, sem build step. Build precisa permanecer offline e determinístico.
- Coluna `fonte` é passthrough do CSV até o `data.json`; o dado de proveniência mora no arquivo de entrada (humano preenche).

### Integration Points
- `transform.build_region()` é o ponto único da mudança de cálculo (composição por-município).
- `render.to_payload()` precisa carregar os novos campos (`composicao_fonte`) para o `data.json` se forem exibidos.
- Exibir `fonte`/procedência no painel (`site/app.js`) é leitura do `data.json` — o backend já entrega; o front é incremento leve (parte de BASE-05, mas o aviso de subcontagem detalhado é Fase 2).

</code_context>

<specifics>
## Specific Ideas

- Gravimetria de Sorocaba: usar exatamente **0,48** (48% em massa, PMGIRS Tomo 2, p.27), citando `"PMGIRS Sorocaba — SHS Consultoria/Prefeitura, 2014. Gravimetria: 48% orgânico (Tomo 2, p.27)"`.
- Para municípios que não participaram do SNIS, a `fonte` da linha pendente deve dizer o motivo, não ficar vazia.
- Reusar a estrutura de CSV documentada no RESEARCH.md (colunas obrigatórias + exemplos de linha real/parcial/pendente).

</specifics>

<deferred>
## Deferred Ideas

- Aviso explícito de subcontagem da população catadora **no painel** → Fase 2 (INFO-04). Na Fase 1 só preparamos o terreno (nota de piso na `fonte`).
- Exibição rica de informalidade e proxy RAIS/CAGED → Fase 2.
- `snis.refresh()` / automação do download → Fase 4 (GEN-02). Nesta fase o download é passo manual do operador / extração pontual.
- Composição orgânica por-município para municípios além de Sorocaba (quando houver outras gravimetrias PMGIRS) → incremento futuro; nesta fase só Sorocaba tem gravimetria local.

</deferred>

---

*Phase: 01-baseline-real-da-rms*
*Context gathered: 2026-06-21*
