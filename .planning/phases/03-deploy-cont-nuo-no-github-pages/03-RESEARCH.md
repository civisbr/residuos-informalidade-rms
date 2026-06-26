# Phase 3: Deploy contínuo no GitHub Pages — Research

**Pesquisada:** 2026-06-23
**Domínio:** GitHub Actions (Pages deploy), determinismo de build Python, badge de workflow
**Confiança geral:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Manter o modelo "GitHub Actions (artifact fresco)": cada push na `main` roda
  `pytest` + `obs build --region rms` e faz deploy via `upload-pages-artifact` +
  `deploy-pages`. O Pages serve o que o build acabou de gerar, não o arquivo commitado.
- **D-02:** `site/data.json` commitado é safety net + preview local (não a fonte do Pages).
  "Funciona sem rebuild" se cumpre porque o Action rebuilda a cada push.
- **D-03:** Gate mínimo sem mudar o disparo: `on: push (main)` + `workflow_dispatch`.
  `pytest` é pré-requisito do deploy (job `build` falha → `deploy` não roda).
  Não adicionar check em PR nesta fase.
- **D-04 (passo manual, não é código):** Ativar GitHub Pages nas Settings do repositório
  com Source = "GitHub Actions". Não é versionável; o plano deve documentar como
  passo de operação/verificação explícito.
- **D-05 (Claude's Discretion com meta fixa):** O planner escolhe a abordagem para
  `gerado_em`, mas com duas metas obrigatórias:
  1. Deploy mostra data útil de publicação.
  2. Rebuild local NÃO gera diff espúrio no `site/data.json` commitado.
- **D-06:** URL default `https://civisbr.github.io/residuos-informalidade-rms/`. Sem
  CNAME nesta fase. Caminhos relativos no front funcionam sem `<base href>`.
- **D-07:** Badge do workflow `build-and-deploy` + link "painel ao vivo" no topo do README.

### Claude's Discretion

- Abordagem técnica para D-05 (determinismo do `gerado_em`).
- Detalhes de robustez do workflow: `concurrency`, pin de versões de actions.
- Texto/posição exata do bloco badge + link no README (ambos no topo).

### Deferred Ideas (OUT OF SCOPE)

- Check de CI em pull requests (build sem deploy).
- Domínio custom / CNAME.
- Automação de `ibge.refresh()` / `snis.refresh()` (Fase 4).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte da pesquisa |
|----|-----------|---------------------|
| DEPLOY-01 | Workflow `.github/workflows/build.yml` revisado e reconstrói `data.json` no push à `main` | Seções "Robustez do workflow" e "Versões das Actions" |
| DEPLOY-02 | GitHub Pages ativado (Source = GitHub Actions) e servindo o site | Seção "Ativação manual do Pages (D-04)" |
| DEPLOY-03 | README com badge de build e URL pública | Seção "Badge e URL no README (D-07)" |
| DEPLOY-04 | `site/data.json` commitado para o Pages funcionar mesmo sem rebuild | Seção "Determinismo de `gerado_em` (D-05)" — arquivo já commitado; D-05 resolve o diff espúrio |
</phase_requirements>

---

## Sumário

Esta fase é majoritariamente **revisão e finalização** de um workflow já funcional
(`.github/workflows/build.yml`). Os três pontos de trabalho real são: (1) atualizar
versões das actions (v3/v4 → v5 para pages; setup-uv v3 → v8.x); (2) aplicar a
solução de determinismo do `gerado_em` em `pipeline/render.py`; (3) adicionar badge
e link no README.

O ponto tecnicamente mais delicado é **D-05**: `date.today().isoformat()` em
`render.py:61` gera diff espúrio a cada build local. A solução recomendada é
injetar `BUILD_DATE` como variável de ambiente no CI com fallback a um sentinel
fixo local (`"local"`). Isso satisfaz simultaneamente as duas metas obrigatórias:
o deploy exibe a data real; rebuild local sempre produz o mesmo valor.

A ativação do Pages (D-04) é um passo manual único no GitHub, não código. Deve
aparecer no plano como tarefa de verificação com instruções precisas.

**Recomendação primária:** atualizar as quatro actions para versões atuais,
adicionar `concurrency` group, aplicar o padrão `BUILD_DATE` env var, e documentar
D-04 como passo manual obrigatório antes do primeiro push pós-workflow.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Tier primário | Tier secundário | Rationale |
|------------|--------------|-----------------|-----------|
| Rebuild de `data.json` | CI / GitHub Actions | — | Pipeline Python offline; o CI é o único "servidor" |
| Deploy do site estático | GitHub Pages (CDN) | — | Artifact empacotado pelo CI, servido pelo Pages |
| Determinismo do build | Pipeline Python (`render.py`) | CI (injeta `BUILD_DATE`) | A lógica fica no Python; o CI apenas fornece o valor |
| Badge de status | GitHub (endpoint nativo) | README (referência) | GitHub gera a SVG; README só linka |
| Ativação do Pages | GitHub Settings (manual) | — | Não é código, não é versionável |
| Caminhos relativos do front | Browser | — | `./data.json`, `app.js`, `styles.css` — já relativos, sem ajuste |

---

## Stack Padrão

### Actions do CI (versões atuais verificadas)

| Action | Versão atual | Versão no build.yml | Status |
|--------|-------------|---------------------|--------|
| `actions/checkout` | v4 (tag móvel; patch mais recente v4.x) | v4 | OK — manter v4 |
| `astral-sh/setup-uv` | v8.2.0 (imutável — sem tag v8 móvel) | v3 | **ATUALIZAR** |
| `actions/upload-pages-artifact` | v5.0.0 | v3 | **ATUALIZAR** |
| `actions/deploy-pages` | v5.0.0 | v4 | **ATUALIZAR** |

[VERIFIED: github.com/astral-sh/setup-uv/releases — v8.2.0 em junho 2026]
[VERIFIED: github.com/actions/upload-pages-artifact/releases — v5.0.0 em abril 2026]
[VERIFIED: github.com/actions/deploy-pages/releases — v5.0.0 em março 2026]
[CITED: docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages]

**Nota sobre setup-uv:** A partir de v8.0.0, o projeto parou de publicar tags
móveis (`v8`, `v8.0`). O uso correto é `astral-sh/setup-uv@v8.2.0` (tag imutável
de versão completa). [VERIFIED: github.com/astral-sh/setup-uv/releases]

**Nota sobre configure-pages:** A documentação oficial menciona `actions/configure-pages`
para fluxos com gerador de site estático (Jekyll, Hugo, etc.). Para este projeto
(pipeline Python que gera `data.json` diretamente), o `configure-pages` **não é
necessário**. O fluxo mínimo funcional é: checkout → setup-uv → uv sync → pytest
→ obs build → upload-pages-artifact → deploy-pages. [CITED: github.com/actions/upload-pages-artifact]

### Permissões do workflow (já corretas no build.yml)

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

[CITED: docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages]

---

## Robustez do Workflow (Claude's Discretion)

### Concurrency group para evitar deploys concorrentes

**Problema:** Sem `concurrency`, dois pushes rápidos em sequência disparam dois
workflows. O segundo pode fazer deploy de artifact mais antigo (race condition)
ou deixar o Pages em estado inconsistente enquanto o primeiro ainda está rodando.

**Solução recomendada:**

```yaml
concurrency:
  group: pages
  cancel-in-progress: true
```

`cancel-in-progress: true` cancela o workflow anterior quando chega um mais novo.
Para Pages (conteúdo substitutivo, não cumulativo), isso é o comportamento correto:
o push mais recente é sempre o que deve estar no ar.
[CITED: docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency]

**Alternativa — `cancel-in-progress: false`:** mantém o anterior na fila mas não
cancela; adequado para deploys com efeitos cumulativos. Não se aplica aqui.

### Environment no job deploy (já correto)

O job `deploy` já tem:
```yaml
environment:
  name: github-pages
  url: ${{ steps.deployment.outputs.page_url }}
```

Isso é **obrigatório**: o environment `github-pages` é o que o Pages usa como
contexto de proteção (só a branch `main` pode fazer deploy). [CITED: docs.github.com/en/pages/...]

### Workflow completo revisado (referência para o planner)

```yaml
name: build-and-deploy

on:
  push: { branches: [main] }
  workflow_dispatch:

concurrency:
  group: pages
  cancel-in-progress: true

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v8.2.0
      - run: uv sync
      - run: uv run pytest -q
      - run: uv run obs build --region rms
        env:
          BUILD_DATE: ${{ github.event.repository.pushed_at || github.event.head_commit.timestamp }}
      - uses: actions/upload-pages-artifact@v5
        with: { path: site }

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```

[ASSUMED — a expressão `github.event.repository.pushed_at || github.event.head_commit.timestamp`
precisa ser validada contra os contextos disponíveis no GitHub Actions; ver seção
"Determinismo" abaixo para abordagem mais simples]

---

## Determinismo do `gerado_em` (D-05)

### Problema raiz

`pipeline/render.py:61`:
```python
"gerado_em": date.today().isoformat(),
```

Cada chamada local a `uv run obs build` gera uma data diferente → diff espúrio em
`site/data.json` → `git status` sempre mostra arquivo modificado → commits de
"atualização" acidentais.

### Abordagem recomendada: `BUILD_DATE` env var com sentinel local

**Lógica em `render.py`:**

```python
import os
from datetime import date

_BUILD_DATE = os.environ.get("BUILD_DATE", "")
gerado_em = _BUILD_DATE if _BUILD_DATE else date.today().isoformat()
```

Porém isso **não resolve** o diff local, porque localmente `BUILD_DATE` não está
definida e continua usando `date.today()`.

**Solução correta para satisfazer as DUAS metas de D-05:**

```python
import os
from datetime import date

# CI injeta BUILD_DATE=<data-ISO>. Local: fallback para "local" (fixo, sem diff).
_BUILD_DATE = os.environ.get("BUILD_DATE", "local")
gerado_em = _BUILD_DATE if _BUILD_DATE != "local" else "local"
```

Simplificado:
```python
gerado_em = os.environ.get("BUILD_DATE", "local")
```

- **No CI:** `BUILD_DATE` é injetada com a data ISO do push → `gerado_em = "2026-06-23"`.
- **Local:** `BUILD_DATE` não existe → `gerado_em = "local"` (string fixa, sem diff).

**No workflow**, o step `obs build` recebe:
```yaml
- run: uv run obs build --region rms
  env:
    BUILD_DATE: ${{ github.event.head_commit.timestamp }}
```

`github.event.head_commit.timestamp` retorna o ISO 8601 do commit mais recente
(ex.: `"2026-06-23T17:30:00+00:00"`). Basta tomar os 10 primeiros caracteres em
Python para extrair a data: `os.environ.get("BUILD_DATE", "local")[:10]`.

**Alternativa mais simples no workflow** (sem depender de contexto de evento):
```yaml
env:
  BUILD_DATE: ${{ github.run_id && 'ci' || 'local' }}
```
Não, isso não gera data útil. A abordagem com `head_commit.timestamp` é melhor.

**Alternativa alternativa:** usar `$(date -I)` no shell:
```yaml
- run: |
    BUILD_DATE=$(date -I) uv run obs build --region rms
```
Isso funciona mas é menos explícito. A forma com `env:` é mais idiomática.

**Impacto nos testes:** `pytest` não deve definir `BUILD_DATE`. O teste
`test_payload_tem_informalidade` lê `site/data.json` do disco (já commitado).
Não há nenhum teste que valide o valor de `gerado_em` — portanto, nenhum ajuste
nos testes é necessário. O `uv run pytest -q` continua determinístico.
[VERIFIED: leitura de tests/test_pipeline.py — nenhum teste valida `gerado_em`]

### Padrão SOURCE_DATE_EPOCH (alternativa considerada)

`SOURCE_DATE_EPOCH` é o padrão da comunidade reproducible-builds para timestamps
em segundos desde o epoch Unix. Aplicável quando o objetivo é reprodutibilidade
bit-a-bit. Para este projeto (JSON com data ISO legível), o padrão `BUILD_DATE`
com string ISO é mais simples e igualmente correto. [CITED: reproducible-builds.org/docs/source-date-epoch/]

---

## Ativação Manual do Pages (D-04)

### O que precisa acontecer (não é código)

1. Abrir o repositório no GitHub → Settings → Pages
2. Em "Build and deployment" → "Source": selecionar **"GitHub Actions"**
3. Salvar

Após este passo, o GitHub cria automaticamente o environment `github-pages` no
repositório. Este environment é o que o job `deploy` referencia com
`environment: github-pages`. Sem a ativação manual, o workflow falha com erro
de environment não encontrado.

**Quando fazer:** Antes do primeiro push com o workflow finalizado. A ordem
importa: Pages ativo primeiro, depois push com workflow atualizado.

**Verificação:** Após o primeiro deploy bem-sucedido, acessar
`https://civisbr.github.io/residuos-informalidade-rms/` deve exibir o painel.
O badge no README vai mostrar status verde. [CITED: docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site]

---

## Badge e URL no README (D-07)

### Sintaxe correta do badge

```markdown
[![Build](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg)](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml)
```

- Formato: `https://github.com/OWNER/REPO/actions/workflows/WORKFLOW-FILE/badge.svg`
- O link do badge aponta para a página de execuções do workflow (padrão open-source).
- `?branch=main` pode ser adicionado para exibir só o status da branch main, mas
  é opcional (GitHub usa a branch padrão por default). [CITED: docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge]

### Bloco completo recomendado para o topo do README

```markdown
[![Build](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg)](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml)
[Ver painel ao vivo →](https://civisbr.github.io/residuos-informalidade-rms/)
```

Ou em uma linha de destaque maior:

```markdown
[![Build](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml/badge.svg)](https://github.com/civisbr/residuos-informalidade-rms/actions/workflows/build.yml)
&nbsp;**[Ver painel ao vivo →](https://civisbr.github.io/residuos-informalidade-rms/)**
```

Posição: **imediatamente abaixo do título `# Observatório de Resíduos & Informalidade`**
e antes do blockquote descritivo (linha 3 do README atual). Isso garante
visibilidade máxima para contribuidores (padrão open-source). [ASSUMED — posição
exata é Claude's Discretion per D-07; sugestão acima é a convenção mais comum]

### Compatibilidade de subpath (D-06)

`site/index.html` usa:
- `<link rel="stylesheet" href="styles.css">` (relativo)
- `<script src="app.js"></script>` (relativo)

`site/app.js` usa:
- `fetch("./data.json", ...)` (relativo com `./`)

Todos os caminhos são relativos ao documento atual. No Pages, o documento vive em
`/residuos-informalidade-rms/index.html`, então `styles.css` resolve para
`/residuos-informalidade-rms/styles.css` e `./data.json` para
`/residuos-informalidade-rms/data.json` — correto, sem `<base href>` necessário.
[VERIFIED: leitura de site/index.html e site/app.js]

---

## Anti-Padrões a Evitar

- **Não adicionar `actions/configure-pages`**: Desnecessário para pipeline Python
  sem SSG. Adiciona um step sem benefício para este projeto.
- **Não usar `cancel-in-progress: false` para Pages**: Deixaria o Pages potencialmente
  servir conteúdo de push mais antigo enquanto o novo está na fila.
- **Não hardcodar a URL do Pages no front-end** (`app.js` ou `index.html`): Os
  caminhos relativos já funcionam corretamente no subpath do Pages.
- **Não remover `site/data.json` do git**: O arquivo commitado é o safety net (D-02).
  O CI o sobrescreve com um rebuild fresco a cada push; localmente ele está disponível
  para preview sem rebuild.
- **Não usar `date.today()` sem env var**: Continua gerando diff espúrio a cada `obs build` local.
- **Não definir `BUILD_DATE` no ambiente de desenvolvimento local** (`.env`, etc.):
  Isso derrotaria o propósito do sentinel "local".

---

## Pitfalls Comuns

### Pitfall 1: Pages não ativa sem o passo manual

**O que vai errado:** Workflow existe no repo, push acontece, o job `deploy` falha
com `Error: HttpError: Not Found` ou `environment 'github-pages' not found`.
**Por quê:** O environment `github-pages` só é criado após a ativação manual em
Settings → Pages → Source = "GitHub Actions".
**Como evitar:** Documentar D-04 como passo de operação obrigatório **antes** do
primeiro push com o workflow finalizado.
**Sinal de aviso:** Badge mostrando `failing` na primeira execução pós-workflow.

### Pitfall 2: upload-pages-artifact@v3 com deploy-pages@v5 (incompatibilidade)

**O que vai errado:** Versões misturadas do artifact/deploy podem causar falha no
handshake entre jobs.
**Por quê:** O formato do artifact mudou entre versões. O par deve ser compatível
(v3+v4, ou v5+v5).
**Como evitar:** Atualizar ambas simultaneamente para a mesma geração (v5+v5).

### Pitfall 3: `gerado_em` poluindo git após build local

**O que vai errado:** Desenvolvedor roda `uv run obs build` para preview → `git status`
mostra `site/data.json` modificado → commit acidental ou confusão.
**Por quê:** `date.today()` é determinístico por execução, não por commit.
**Como evitar:** Aplicar o padrão `os.environ.get("BUILD_DATE", "local")`.

### Pitfall 4: `astral-sh/setup-uv@v3` ainda funciona mas é antiga

**O que vai errado:** Pode falhar silenciosamente em novas versões do uv ou exibir
warnings de deprecação.
**Por quê:** v3 é de 2023/2024; a versão atual (v8.2.0) tem mudanças de comportamento
na resolução de dependências e no cache.
**Como evitar:** Atualizar para `astral-sh/setup-uv@v8.2.0`.

### Pitfall 5: Race condition sem concurrency group

**O que vai errado:** Dois pushes rápidos → dois workflows concorrentes → o Pages
serve uma versão inconsistente durante a sobreposição de deploys.
**Como evitar:** Adicionar `concurrency: group: pages, cancel-in-progress: true`.

---

## Exemplos de Código

### render.py — ajuste de determinismo (D-05)

```python
# pipeline/render.py
# Antes (linha 61):
"gerado_em": date.today().isoformat(),

# Depois:
"gerado_em": os.environ.get("BUILD_DATE", "local")[:10],
```

Adicionar `import os` ao topo se ainda não existir (já tem `from datetime import date`).

O `[:10]` garante que se `BUILD_DATE` vier como ISO 8601 completo
(`"2026-06-23T17:30:00+00:00"`), só a parte da data (`"2026-06-23"`) seja usada.

### build.yml — step obs build com BUILD_DATE

```yaml
- run: uv run obs build --region rms
  env:
    BUILD_DATE: ${{ github.event.head_commit.timestamp }}
```

`github.event.head_commit.timestamp` está disponível em eventos `push`. Para
`workflow_dispatch` (disparo manual), o valor pode ser `null` — nesse caso o
fallback `"local"` entra em ação e o painel exibe `"local"` como data. Para
garantir data real também no `workflow_dispatch`, usar:

```yaml
- run: uv run obs build --region rms
  env:
    BUILD_DATE: ${{ github.event.head_commit.timestamp || github.event.created_at || '' }}
```

[ASSUMED — `github.event.created_at` disponível em `workflow_dispatch`; verificar
nos contextos do GitHub Actions antes de usar]

Alternativa robusta (sem depender de contexto de evento):
```yaml
- run: BUILD_DATE=$(date -I) uv run obs build --region rms
```

Esta forma usa o relógio do runner Ubuntu, que está em UTC e sempre disponível
independente do tipo de evento. É a mais simples e segura. [VERIFIED: padrão Unix]

---

## Verificação Local (sem push)

`act` não está instalado e não é necessário instalar para esta fase. A validação
local completa pode ser feita com:

```bash
# 1. Testar o build com BUILD_DATE setada (simula CI):
BUILD_DATE=2026-06-23 uv run obs build --region rms
git diff site/data.json  # deve mostrar só mudança de gerado_em (de "local" p/ data real)

# 2. Testar o build SEM BUILD_DATE (simula rebuild local):
uv run obs build --region rms
git diff site/data.json  # deve ser VAZIO (gerado_em="local" igual ao commitado)

# 3. Rodar os testes:
uv run pytest -q

# 4. Preview do site:
cd site && python -m http.server
```

Para validar o workflow YAML sintaticamente sem push:
```bash
# Não há ferramenta local disponível (act não instalado).
# Validar visualmente o YAML e confiar no lint do GitHub ao abrir o PR/push.
```

---

## Audit de Legitimidade de Pacotes

Esta fase não instala novos pacotes Python nem npm. Atualiza apenas versões de
GitHub Actions (configuração YAML). Nenhum package legitimacy audit é necessário.

---

## Estado da Arte

| Abordagem antiga | Abordagem atual | Quando mudou | Impacto |
|-----------------|----------------|-------------|---------|
| `upload-pages-artifact@v3` | `upload-pages-artifact@v5` | Abril 2026 | v3 funcional mas desatualizado; v5 usa upload-artifact@v7 |
| `deploy-pages@v4` | `deploy-pages@v5` | Março 2026 | v5 usa Node.js 24 |
| `astral-sh/setup-uv@v3` | `astral-sh/setup-uv@v8.2.0` | 2025 | Tags móveis abandonadas (v8+); usar versão imutável completa |
| sem concurrency | `concurrency: group: pages` | Padrão recomendado | Evita race condition de deploy |

---

## Disponibilidade de Ambiente

| Dependência | Requerida por | Disponível | Versão | Fallback |
|------------|--------------|-----------|--------|----------|
| Python 3.11+ | pipeline | ✓ | 3.12.3 | — |
| uv | CI e local | ✓ | 0.9.8 local; CI instala via setup-uv | — |
| GitHub Actions runner | CI | ✓ (ubuntu-latest) | — | — |
| GitHub Pages (ativado) | DEPLOY-02 | ✗ (passo manual pendente) | — | Sem fallback — é o objetivo da fase |
| `act` (validação local) | Opcional | ✗ | — | Usar `BUILD_DATE=... uv run obs build` + `git diff` |

**Dependências sem fallback que bloqueiam execução:**
- GitHub Pages não ativado (D-04): bloqueante para DEPLOY-02, mas é passo manual da fase.

---

## Domínio de Segurança

`security_enforcement: true` está ativo na config.

| Categoria ASVS | Aplica | Controle padrão |
|----------------|--------|----------------|
| V2 Autenticação | não | Site público sem login |
| V3 Sessão | não | Sem sessão |
| V4 Controle de acesso | parcial | Pages protection rule (só `main` faz deploy) via environment `github-pages` |
| V5 Validação de entrada | não | Sem input do usuário; JSON gerado offline |
| V6 Criptografia | não | HTTPS do GitHub Pages (automático, gerenciado pelo GitHub) |

**Padrões de ameaça relevantes:**

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| Supply chain via action comprometida | Tampering | Pinning de versão por tag imutável (setup-uv@v8.2.0); para hardening adicional, usar SHA — fora de escopo desta fase |
| Deploy de branch não-main | Elevation of privilege | Environment `github-pages` com protection rule na main |
| Secrets expostos no log | Information Disclosure | Sem secrets neste workflow (build offline, APIs públicas) |

Nenhum bloco de segurança (`security_block_on: high`) identificado para esta fase.

---

## Log de Suposições

| # | Afirmação | Seção | Risco se errado |
|---|-----------|-------|----------------|
| A1 | `github.event.head_commit.timestamp` disponível no evento `push` e retorna ISO 8601 | Exemplos de código (BUILD_DATE) | BUILD_DATE seria vazio → `gerado_em` ficaria `""` em vez de `"local"` — bug silencioso. Usar `[:10]` com fallback `"local"` já mitiga |
| A2 | `github.event.created_at` disponível no evento `workflow_dispatch` | Exemplos de código (BUILD_DATE alternativa) | Fallback para string vazia; mitigado pelo `or ''` e pelo `[:10]` |
| A3 | Posição do badge imediatamente abaixo do título (linha 2 do README) | Badge e URL no README | Só afeta estética; planner tem liberdade per D-07 |

---

## Perguntas em Aberto (RESOLVED)

1. **`BUILD_DATE` em `workflow_dispatch`**
   - O que sabemos: `github.event.head_commit.timestamp` não existe em `workflow_dispatch` (só em `push`).
   - O que está incerto: `github.event.created_at` ou `github.run_attempt` disponíveis?
   - Recomendação: usar a alternativa shell `BUILD_DATE=$(date -I) uv run obs build --region rms` — disponível em qualquer tipo de evento, sem depender de contexto.
   - **RESOLVED:** plano 03-01 adota `BUILD_DATE=$(date -I)` (forma shell) no step `obs build` — independe do tipo de evento (push ou workflow_dispatch).

2. **Exibição de `"local"` no painel publicado**
   - O que sabemos: se o deploys usar `workflow_dispatch` sem BUILD_DATE, o painel exibira `"local"` como `gerado_em`.
   - O que está incerto: é aceitável para o usuário ver `"local"` no site ao vivo?
   - Recomendação: usar `BUILD_DATE=$(date -I)` no workflow (shell direto) → sempre retorna data real no CI, sem depender do tipo de evento.
   - **RESOLVED:** como o CI sempre injeta `BUILD_DATE=$(date -I)`, `"local"` nunca aparece no site publicado — só em rebuilds locais (comportamento desejado por D-05).

---

## Fontes

### Primárias (HIGH)
- [docs.github.com — Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — permissões, environment, jobs
- [docs.github.com — Adding a workflow status badge](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge) — sintaxe do badge
- [docs.github.com — Configuring publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) — ativação manual (D-04)
- [docs.github.com — Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) — concurrency group
- [github.com/actions/upload-pages-artifact/releases](https://github.com/actions/upload-pages-artifact/releases) — v5.0.0 atual
- [github.com/actions/deploy-pages/releases](https://github.com/actions/deploy-pages/releases) — v5.0.0 atual
- [github.com/astral-sh/setup-uv/releases](https://github.com/astral-sh/setup-uv/releases) — v8.2.0 atual
- [reproducible-builds.org/docs/source-date-epoch](https://reproducible-builds.org/docs/source-date-epoch/) — padrão SOURCE_DATE_EPOCH

### Secundárias (MEDIUM)
- [github.blog — Deprecation notice: GitHub Pages actions to require artifacts v4](https://github.blog/changelog/2024-12-05-deprecation-notice-github-pages-actions-to-require-artifacts-actions-v4-on-github-com/) — histórico de versões
- Verificação direta do código: `site/index.html`, `site/app.js`, `pipeline/render.py`, `.github/workflows/build.yml`, `tests/test_pipeline.py`

---

## Metadados

**Quebra de confiança:**
- Versões das actions: HIGH — verificadas diretamente nas páginas de releases
- Workflow (concurrency, environment, permissions): HIGH — citado de docs oficiais
- Determinismo BUILD_DATE: HIGH — padrão bem estabelecido; ASSUMED apenas nas expressões de contexto do GH Actions para `workflow_dispatch`
- Badge sintaxe: HIGH — citado de docs oficiais
- Subpath Pages compatibilidade: HIGH — verificado lendo o código fonte

**Data da pesquisa:** 2026-06-23
**Válida até:** 2026-07-23 (GitHub Actions versions podem mudar; re-verificar antes de usar)
