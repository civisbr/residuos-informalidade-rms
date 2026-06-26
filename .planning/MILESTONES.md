# Milestones

## v1.0 MVP — Observatório RMS (Shipped: 2026-06-26)

**Phases completed:** 5 phases, 13 plans, 25 tasks

**Key accomplishments:**

- Gravimetria Sorocaba 0.48 por-município via pl.when com fallback global 0.51; Porto Feliz extraído de PMGIRS 2017 (pdftotext): rsu=14213 t/ano, reciclado_pct=23.4%, cooperados=17 — ambos com flag real e fonte citada.
- Os 27 municípios da RMS têm dado SNIS-RS real (2022): os 25 restantes
- data/raw/censo/censo_informalidade_rms.csv
- Joins de Censo 2022 + RAIS 2023 em build_region() com proxy D-06/D-07 em Polars; to_payload() expõe taxa_informalidade_pct e pnad_contexto_regional; data.json regenerado com informalidade completa para os 27 municípios da RMS
- Seção de informalidade adicionada ao painel vanilla JS: 3 KPIs (taxa Censo 2022, empregos formais RAIS, grau de formalização proxy) com tags real/pendente, nota D-10 fixa, contexto PNAD rotulado como estimativa regional e célula de informalidade média no region-strip
- Workflow GitHub Actions atualizado para actions v5 com concurrency group e BUILD_DATE injetado; gerado_em em render.py passa a usar sentinel 'local' eliminando diffs espurios em rebuilds locais
- README ganha badge de status do workflow build-and-deploy e link 'Ver painel ao vivo' para a URL pública do Pages; ativação manual do Pages (D-04) ADIADA por decisão do usuário — site ainda não está ao vivo
- 1. [Rule 1 - Bug] Tipo de codigo_ibge em test_ibge_load_permanece_intacto
- Rename atômico de taxa_inf_media_rms para taxa_inf_media em transform.py e app.js com sort Polars nulls_last=True e buildCitySelect dinâmico suportando qualquer conjunto de sub-regiões
- snis.refresh() exposto como `obs refresh-snis --region <chave>`, com UF_NOMES para 27 estados e validação de path traversal via yaml.safe_load
- Telemetria operacional flui da fonte ao painel COM ZERO dado: nova fonte operacao.py (só load), CSV-template documentado, chave operacao no payload e seção "Operação ao vivo" com estado vazio honesto — pronto para "ligar" sem inventar número.
- Confronto real×projetado calibrado reusando model.project() em base mensal (÷12) com paridade model.py↔app.js travada por teste (CONCERNS #7 fechado), série temporal SVG inline à mão (real sólido × projetado tracejado) e 4 cards de impacto acumulado — sem nunca apresentar projeção como medição nem preencher mês sem dado com zero.

---
