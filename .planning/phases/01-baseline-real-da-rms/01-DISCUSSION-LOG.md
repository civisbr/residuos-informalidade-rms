# Phase 1: Baseline real da RMS - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-21
**Phase:** 01-baseline-real-da-rms
**Areas discussed:** Gravimetria por-município, Honestidade da composição, Ano-base do SNIS, Porto Feliz / dado bloqueado, Fallback Porto Feliz, Catadores como piso

---

## Onde mora a gravimetria por-município

| Option | Description | Selected |
|--------|-------------|----------|
| Coluna no CSV do SNIS | `composicao_organico` no schema do CSV; fonte na mesma linha; fallback global 0,51 | ✓ |
| config/gravimetria.csv separado | Tabela própria municipio,composicao_organico,fonte_gravimetria | |
| Você decide | Seguir recomendação da pesquisa | |

**User's choice:** Coluna no CSV do SNIS
**Notes:** Mais simples e mais rastreável — fonte da gravimetria na mesma linha do dado.

---

## Honestidade da composição (organico derivado de estimativa global)

| Option | Description | Selected |
|--------|-------------|----------|
| Campo de procedência da composição | `composicao_fonte`: 'PMGIRS local' vs 'média Brasil (estimativa)'; separado do flag do RSU | ✓ |
| Reusar o flag existente | Orgânico herda flag do RSU; sem campo novo | |
| Você decide | Seguir procedência (mais honesta) | |

**User's choice:** Campo de procedência da composição
**Notes:** Permite ao painel distinguir orgânico medido (gravimetria) de estimado (média Brasil) sem violar a regra sagrada.

---

## Ano-base do SNIS

| Option | Description | Selected |
|--------|-------------|----------|
| Ano mais recente por município | Comportamento atual de snis.load(); maximiza cobertura | ✓ |
| Fixar um ano único (ex.: 2022) | Comparabilidade estrita; mais pendentes | |
| Você decide | Manter comportamento atual | |

**User's choice:** Ano mais recente por município
**Notes:** Colunas `ano` + `fonte` deixam o ano de cada linha explícito.

---

## Porto Feliz / dado bloqueado (PMGIRS 2017)

| Option | Description | Selected |
|--------|-------------|----------|
| Eu tento extrair na execução | curl HTTPS + pdftotext; sobe a real com página citada se conseguir | ✓ |
| Você extrai manualmente | Usuário passa números; útil se PDF for imagem | |
| Você decide | Tentar; fallback estimativa | |

**User's choice:** Eu tento extrair na execução

---

## Fallback Porto Feliz (se extração falhar)

| Option | Description | Selected |
|--------|-------------|----------|
| Mantém estimativa, não sobe pra real | Flag estimativa + fonte honesta; não bloqueia a fase | ✓ |
| Bloqueia a fase até ter o dado real | Fase 1 não fecha sem Porto Feliz real | |
| Você decide | Estimativa honesta + pendência carregada | |

**User's choice:** Mantém estimativa, não sobe pra real
**Notes:** Regra sagrada — nunca `real` sem fonte citável. Não trava o baseline por um município.

---

## Catadores / cooperados como piso

| Option | Description | Selected |
|--------|-------------|----------|
| Nota de piso na fonte + null honesto | Preenche onde SNIS tem (fonte: 'autodeclarado — piso'); null onde não tem | ✓ |
| Deixar tudo null nesta fase | Joga 100% para a Fase 2 | |
| Você decide | Preencher com nota; null onde não houver | |

**User's choice:** Nota de piso na fonte + null honesto
**Notes:** Prepara terreno para o aviso de subcontagem da Fase 2 (INFO-04) sem implementá-lo agora.

---

## Claude's Discretion

- Estrutura/nomes exatos dos novos CSVs em `data/raw/snis/` (não apagar `snis_rs_sample.csv`).
- Extensão do `SCHEMA` em `sources/snis.py` e passthrough em `transform.py`/`render.py` para os novos campos.
- Mapeamento campo-a-campo SNIS→schema ao montar os CSVs (documentado no RESEARCH.md).
- Ajuste de testes: atualizar `pend.height >= 20` e adicionar teste de `organico_t_ano` de Sorocaba (228000×0,48).

## Deferred Ideas

- Aviso de subcontagem da população catadora no painel → Fase 2 (INFO-04).
- Exibição rica de informalidade e proxy RAIS/CAGED → Fase 2.
- `snis.refresh()` / automação do download → Fase 4 (GEN-02).
- Composição orgânica por-município além de Sorocaba (outras gravimetrias PMGIRS) → incremento futuro.
