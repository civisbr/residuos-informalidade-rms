# Phase 4: Generalizar para qualquer cidade BR - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Tornar o painel **gerável para qualquer cidade do Brasil só editando
`config/regions.yml`**, sem tocar em código. Cobre GEN-01..04:

- `ibge.refresh()` resolve código IBGE + população via API e regrava o cache
  (não mais `NotImplementedError`).
- `snis.refresh()` documentado **e automatizado** (promovendo o scraper já
  decifrado), por região.
- Erro amigável quando um município não resolve no IBGE (sem stack trace).
- Guia "Crie o painel da sua cidade em 5 minutos" no README; um terceiro segue
  o passo-a-passo só editando `regions.yml`.

**Regra sagrada vale aqui:** para uma região nova, o que não tem fonte pública
fica `pendente` honesto — nunca chute. Um painel majoritariamente `pendente`,
com estrutura e flags corretos, é um painel **válido**.

**Fora de escopo (outras fases / Out of Scope v1):** generalizar
`ibge_informalidade.py`/`rais.py` para resolver os códigos da região ativa
(seguem RMS-only nesta fase — ver D-02); telemetria viva (Fase 5); mapa
coroplético, comparação de pares e export PDF (Out of Scope, PROJECT.md).
Discussão clarifica COMO generalizar o que já está escopado — não adiciona
capacidade nova.

</domain>

<decisions>
## Implementation Decisions

### Fronteira "sem código" — o que é automático vs `pendente` (GEN-01, GEN-04)
- **D-01:** Para uma região NOVA, "painel gerado com sucesso" =
  **identidade automática + resto `pendente` honesto**. `ibge.refresh()`
  resolve código+população de cada município; SNIS/informalidade/RAIS ficam
  `pendente` até o usuário rodar os refreshes correspondentes. Painel válido =
  estrutura correta + flags honestos, mesmo majoritariamente `pendente`.
  **Não** buscar tudo online no build (quebraria o build offline/determinístico
  — Constraint do PROJECT.md).

### Desacoplamento da RMS (robustez mínima)
- **D-02:** Entregar **robustez mínima**, não desacoplamento total:
  1. Tolerar `subregiao` ausente/`null` sem quebrar — o `sort(["subregiao",
     "nome"])` em `transform.py:97` e a emissão de `subregiao` em `render.py:20`
     devem funcionar para região sem sub-regiões (resultado: lista plana, sem
     agrupamento).
  2. Renomear `taxa_inf_media_rms` (em `transform.py` ~L115/128 e consumido em
     `cli.py:48-50`) para um nome genérico (ex.: `taxa_inf_media`), removendo o
     rótulo "RMS" de saída usada por outras regiões.
  - **Não** reescrever `ibge_informalidade.py`/`rais.py` (que têm
    `RMS_IBGE_CODES` hardcoded). Para uma região nova, o join é por slug
    (`base.slug`) → os códigos RMS simplesmente **não casam** → informalidade
    cai em `pendente` honesto, sem crash. Informalidade-para-todos fica para
    fase futura (ver Deferred).

### Contrato de `regions.yml` (GEN-04)
- **D-03:** Contrato **mínimo** para o terceiro:
  - Por município: **só `nome` e `uf` obrigatórios**. `subregiao` opcional
    (sem ele = lista plana).
  - Na região: **`nome` obrigatório**; `destaque` opcional (default = 1º
    município, ou nenhum); `fonte` opcional.
  - Objetivo: máxima simplicidade para o guia de 5 min. O planner deve conferir
    o que `transform`/`render` realmente consomem e tornar opcional o que não
    for essencial, sem quebrar a RMS existente.

### `ibge.refresh()` — disparo, escopo e determinismo (GEN-01)
- **D-04:** Disparo **explícito, região-alvo**:
  `obs refresh-ibge --region <chave>` resolve só os municípios daquela região e
  faz **upsert** no cache (`config/municipios.csv`), mantendo as demais linhas.
  O **build continua 100% offline** lendo o cache — refresh é passo de rede
  consciente, alinhado à separação `load()`/`refresh()` já existente em
  `pipeline/sources/`.
- **D-05:** **Fonte de população = Censo 2022** (número oficial, citável,
  consistente com a informalidade que já usa Censo 2022). Gravar
  `fonte_pop = "IBGE Censo 2022"`. Evita a instabilidade da estimativa anual
  (agregado 6579) num dado commitado/determinístico.
- **D-06:** Upsert **só preenche vazios**: `refresh` resolve `codigo_ibge` e
  `populacao` apenas onde estão faltando/vazios; **não sobrescreve** linhas já
  preenchidas. Preserva curadoria manual (ex.: Sorocaba com pop. urbana
  SINISA, `populacao=709000`, código já preenchido) e é **idempotente**.
  Matching na API por `nome` normalizado dentro da `uf`.

### `snis.refresh()` — automação (GEN-02)
- **D-07:** **Automatizar via scraper**: promover `scripts/scrape_snis.py` a
  `snis.refresh(region)`, exposto por `obs refresh-snis --region <chave>`,
  scraping qualquer município BR pelo `cod_mun`. O recipe do portal SNIS
  Série Histórica está **100% decifrado e validado** (ver STATE.md / 01-02) —
  automação é viável. `scripts/refresh_snis.md` vira o doc de uso/fallback.
- **D-08:** `snis.refresh()` grava **um CSV por região**:
  `data/raw/snis/snis_<chave-regiao>.csv` (ex.: `snis_campinas.csv`).
  `snis.load()` já concatena todos os CSVs da pasta de forma determinística.
  Município sem dado no SNIS → linha `pendente` honesta (consistente com a
  decisão de integridade de 01-02: cooperados `null` em vez de chute).

### Erro amigável (GEN-03)
- **D-09:** **Fail-soft + sugestão** quando um município não resolve no IBGE:
  - No `refresh`: **não aborta**; reporta `Município X (UF) não encontrado no
    IBGE — você quis dizer Y?` (nome mais próximo por similaridade), continua
    com os demais e **lista os não resolvidos no fim**.
  - No `build`: município sem código vira `pendente`, sem travar.
  - **Nunca** stack trace.

### Guia "5 minutos" (GEN-04)
- **D-10:** **Seção dedicada no README** (padrão open-source; o README já tem
  badge + link do painel ao vivo da Fase 3). Fluxo honesto de 4 passos:
  1. editar `regions.yml` (`nome` + `uf`);
  2. `obs refresh-ibge --region X` (identidade);
  3. `obs refresh-snis --region X` (resíduos);
  4. `obs build --region X`.
  Deixar **explícito** que informalidade/RAIS ficam `pendente` fora da RMS
  (honestidade sobre o que é automático vs manual — D-01/D-02).

### Claude's Discretion
- Detalhes da API IBGE (qual endpoint de localidades por UF, qual agregado do
  Censo 2022 para população, formato de chamada) — planner/researcher decide,
  desde que respeite D-05 (Censo 2022, `fonte_pop` correta) e o build offline.
- Algoritmo de similaridade para a sugestão de nome (D-09) — planner escolhe
  (ex.: Levenshtein/difflib), desde que a mensagem seja amigável.
- Estrutura interna de `snis.refresh()` ao promover `scrape_snis.py`
  (assinatura, reuso vs refactor) — planner decide, mantendo D-07/D-08.
- Conjunto exato de campos opcionais em `regions.yml` (D-03) — planner valida
  contra o que `transform`/`render` consomem.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regra do projeto e fase
- `CLAUDE.md` — regra sagrada (nunca inventar número; flag `real`/`estimativa`/
  `pendente`; build offline/determinístico; junção por nome normalizado
  `base.slug`); seção "Como estender → Nova região". Convenções de commit
  (PT-BR imperativo).
- `.planning/PROJECT.md` — Constraints (build offline/determinístico; `data.json`
  commitado; junção por `base.slug`); Out of Scope (informalidade-para-todos
  não está no v1 explicitamente, mas mapa/pares/PDF estão fora).
- `.planning/REQUIREMENTS.md` — GEN-01..04 (linhas 33-38, 82-85).
- `GSD.md` §M4 — checklist autoral "Generalizar para qualquer cidade BR"
  (`ibge.refresh()`; `snis.refresh()` doc/automação; erro amigável; guia 5 min).

### Artefatos a estender/implementar
- `pipeline/sources/ibge.py` — `refresh()` é `NotImplementedError` (linhas 25-36);
  alvo de GEN-01 (D-04/D-05/D-06). `load()` lê `config/municipios.csv` (cache).
- `pipeline/sources/snis.py` — só tem `load()` (concatena `data/raw/snis/*.csv`);
  adicionar `refresh(region)` (D-07/D-08).
- `scripts/scrape_snis.py` — scraper do portal SNIS Série Histórica já decifrado
  e validado; semente de `snis.refresh()` (D-07).
- `scripts/refresh_snis.md` — doc de refresh manual existente; vira doc de
  uso/fallback do scraper (D-07).
- `pipeline/cli.py` — comandos `build`/`regions`/`refresh-ibge` (linhas 64-78);
  adicionar `--region` ao `refresh-ibge` e o comando `refresh-snis` (D-04/D-07);
  remover label "RMS" hardcoded em L48-50 (D-02).
- `pipeline/transform.py` — `sort(["subregiao","nome"])` (L97) e
  `taxa_inf_media_rms` (~L115/128) a generalizar (D-02).
- `pipeline/render.py` — emite `subregiao` por município (L20); tolerar `null` (D-02).
- `config/regions.yml` — contrato editável pelo terceiro; já traz exemplo
  comentado de outra região (linhas 45-51); formalizar campos mínimos (D-03).
- `config/municipios.csv` — cache alvo do upsert (D-06); colunas:
  `nome,uf,codigo_ibge,populacao,fonte_pop`.
- `README.md` — onde entra a seção "Crie o painel da sua cidade em 5 min" (D-10);
  já tem badge + link do Pages (Fase 3).
- `pipeline/sources/ibge_informalidade.py` / `pipeline/sources/rais.py` —
  `RMS_IBGE_CODES` hardcoded; **NÃO** generalizar nesta fase (D-02), mas
  entender que para região nova o join por slug não casa → `pendente`.

### Codebase intel
- `.planning/codebase/CONCERNS.md` — registra `ibge.refresh()` `NotImplementedError`
  e o acoplamento à RMS (`subregiao` hardcoded) como dívida atribuída a esta fase.
- `.planning/codebase/INTEGRATIONS.md` — fontes externas (APIs IBGE/SNIS sem auth).
- `.planning/STATE.md` (HISTÓRICO 01-02) — **recipe completo do scraper SNIS**
  (endpoints, nomes de campo Yii `ShMunicipios[...]`, `cod_mun` 6 dígitos, ordem
  de colunas por `colModel`, validação Sorocaba 2022). Base direta de D-07.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/scrape_snis.py` — scraper completo e validado; reaproveitar como
  núcleo de `snis.refresh()` (D-07). Evita reimplementar o protocolo do portal.
- `pipeline/sources/base.py::slug` — normalização de nome usada como chave de
  junção em todas as fontes; o matching IBGE e a não-correspondência de
  informalidade fora da RMS dependem dela.
- Padrão `load()` (offline) + `refresh()` (rede) já estabelecido em
  `pipeline/sources/` — `ibge.refresh()`/`snis.refresh()` seguem o mesmo molde.
- `config/regions.yml` já tem bloco de exemplo comentado de outra região — base
  do contrato mínimo (D-03).

### Established Patterns
- Pipeline batch **offline → `data.json` estático → painel vanilla**; refresh é
  passo de rede separado, build nunca toca a rede (Constraint preservada por D-04).
- Junção de fontes por `slug(nome)`, não por código IBGE (decisão 02-01). Por
  isso informalidade RMS-hardcoded não vaza para região nova (D-02).
- Integridade: campo sem fonte confiável → `null`/`pendente`, nunca chute
  (01-02 cooperados `null`). Aplica-se a SNIS/informalidade de região nova.

### Integration Points
- `pipeline/cli.py` — ponto de entrada dos novos comandos `refresh-ibge --region`
  e `refresh-snis --region` (D-04/D-07).
- `config/municipios.csv` — alvo do upsert do `ibge.refresh()` (D-06).
- `data/raw/snis/snis_<region>.csv` — saída do `snis.refresh()`, consumida pelo
  `snis.load()` existente (D-08).
- `README.md` — seção do guia de 5 min (D-10).

</code_context>

<specifics>
## Specific Ideas

- Comandos-alvo literais: `obs refresh-ibge --region <chave>` e
  `obs refresh-snis --region <chave>`.
- Mensagem de erro amigável (D-09): "Município X (UF) não encontrado no IBGE —
  você quis dizer Y?" + lista de não resolvidos ao final do refresh.
- Convenção de arquivo SNIS: `data/raw/snis/snis_<chave-regiao>.csv`.
- `fonte_pop = "IBGE Censo 2022"` para linhas resolvidas pelo refresh.
- Guia de 5 min = 4 passos (editar → refresh-ibge → refresh-snis → build), com
  aviso honesto de que informalidade/RAIS ficam `pendente` fora da RMS.

</specifics>

<deferred>
## Deferred Ideas

- **Informalidade/RAIS para qualquer região** — generalizar
  `ibge_informalidade.py`/`rais.py` para resolver os códigos da região ativa
  (não a lista RMS fixa). Grande o suficiente para fase própria; fora do núcleo
  GEN-01/04. Por ora, fora da RMS = `pendente` honesto (D-02).
- **Comparação de pares (município vs. mediana sub-região)** — já listado em
  Out of Scope v1; depende de cobertura ampla de dado (pós-M4).
- **Check de CI em pull requests (build sem deploy)** — herdado da Fase 3;
  faz sentido quando abrir contribuição externa, que esta fase habilita. Não é
  requisito de GEN-01..04.
- **Cache de população por estimativa anual (agregado 6579)** — descartado em
  favor de Censo 2022 (D-05) por estabilidade; revisitar só se precisar de
  número mais atual que o Censo.

</deferred>

---

*Phase: 4-generalizar-para-qualquer-cidade-br*
*Context gathered: 2026-06-24*
