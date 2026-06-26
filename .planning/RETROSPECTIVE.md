# Retrospective — Observatório de Resíduos & Informalidade

## Milestone: v1.0 — MVP — Observatório RMS

**Shipped:** 2026-06-26
**Phases:** 5 | **Plans:** 13 | **Tasks:** ~25 | **LOC:** ~3185 | **Janela:** 21→25/06/2026

### What Was Built
- **Fase 1 — Baseline real da RMS:** 27 municípios com SNIS-RS 2022 real (scraper decifrado do portal Série Histórica), Sorocaba com gravimetria PMGIRS (0.48) e Porto Feliz do PMGIRS 2017; cada linha cita `fonte`.
- **Fase 2 — Camada de informalidade:** informalidade por município (Censo 2022) + proxy de formalização (RAIS 2023), contexto PNAD regional, nota fixa de subcontagem (D-10); tudo com flag real/pendente.
- **Fase 3 — Deploy contínuo:** workflow GitHub Actions (v5, concurrency, BUILD_DATE) reconstrói e publica; render determinístico; badge + link no README.
- **Fase 4 — Generalizar para qualquer cidade BR:** `ibge.refresh()`/`snis.refresh()` por `--region`, erro amigável com sugestão (difflib), guia "5 minutos" no README; desacoplamento mínimo da RMS.
- **Fase 5 — Camada viva (operacional):** "esqueleto vivo" — fonte `operacao.py`, série temporal SVG real×projetado (calibração reusando `model.project()`), 4 cards de impacto acumulado, estado vazio honesto.

### What Worked
- **Regra sagrada como bússola:** "nunca inventar número" guiou decisões de design em todas as fases (pendente honesto, estado vazio, `null` nunca zero). O produto manteve credibilidade.
- **Separação `load()`/`refresh()`** preservou o build offline/determinístico mesmo ao adicionar rede (Fase 4) e telemetria (Fase 5).
- **Discuss → research → pattern-map → plan → check** antes de executar produziu planos com analogs concretos; a Fase 5 saiu em 2 fatias verticais limpas.
- **Fatiamento MVP vertical** na Fase 5 (esqueleto vivo primeiro, profundidade depois) provou o cano end-to-end com zero dado antes de construir a calibração.

### What Was Inefficient
- **Paridade `model.py`↔`app.js` sem teste** arrastou-se como dívida desde M0 (CONCERNS #7, `carros_equivalente`/`carros` divergiram) e só foi fechada na Fase 5, quando a calibração passou a depender dela. Deveria ter sido travada cedo.
- **Verificação humana acumulada:** Fases 3 e 4 ficaram `human_needed` (Pages ao vivo + UAT de rede) e a Fase 1 nunca recebeu `VERIFICATION.md` formal — empurrou o v1.0 para um override closeout em vez de fechamento limpo.
- **Beco BigQuery na Fase 1:** tempo gasto no caminho Base dos Dados antes de descobrir que não havia resíduos sólidos lá; o scraping foi a semente real.

### Patterns Established
- Toda fonte = módulo em `pipeline/sources/` com `load()` (offline) e `refresh()` (rede) opcional; junção por `base.slug`.
- Toda classe de dado no painel carrega flag/cor distinta (real/estimativa/pendente/projeção/medição) — separação visual é parte da regra sagrada.
- `data.json` commitado e determinístico (sentinel `local` para `gerado_em`).
- Estado vazio honesto > placeholder vazio mudo: a seção "acende" quando há dado.

### Key Lessons
- Travar invariantes cross-arquivo (paridade Py↔JS) com teste **antes** de construir em cima — não deixar como dívida.
- UAT humano/de rede precisa ser agendado durante a fase, não empurrado para o fim; senão o milestone fecha com ressalvas.
- "Painel majoritariamente pendente, com estrutura e flags corretos, é um painel válido" — escopo honesto destrava entrega.

### Cost Observations
- Model mix: predominantemente Opus (orquestração + subagentes GSD).
- Notável: a sessão bateu o limite durante o code-review advisory da Fase 5; o pipeline foi retomado via `/gsd-resume-work` sem perda de estado (artefatos no disco + git).

## Cross-Milestone Trends

| Milestone | Fases | Planos | LOC | Janela | Closeout |
|-----------|-------|--------|-----|--------|----------|
| v1.0 | 5 | 13 | ~3185 | 5 dias | override (3 itens human_needed) |
