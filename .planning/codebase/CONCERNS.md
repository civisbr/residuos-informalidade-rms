# Concerns

*Mapped: 2026-06-21*

Dívida técnica, fragilidades e riscos observados. Muitos já estão mapeados como
trabalho futuro no `GSD.md` (M1–M5); os referenciamos quando aplicável.

## Funcionalidade incompleta / quebrada

1. **`ibge.refresh()` lança `NotImplementedError`** (`pipeline/sources/ibge.py:34`).
   `obs refresh-ibge` quebra em toda chamada. Esperado — é tarefa M4. O build
   offline funciona sem isto.
2. **Não existe `snis.refresh()`** — atualização do SNIS é 100% manual via
   `scripts/refresh_snis.md`. Tarefa M1/M4.
3. **`refresh-ibge` exposto na CLI mas não funcional** — usuário descobre o gap
   só ao rodar. Faltam mensagem amigável e validação (M4 pede "erro amigável
   quando município não resolve no IBGE").

## Cobertura de dado (esperado nesta fase, mas é risco)

4. **19/27 municípios sem código IBGE; 25/27 sem dado SNIS.** Coerente com M1
   ainda não feito (só Sorocaba completo; Porto Feliz pendente). É honesto
   (aparecem como `pendente`), mas o painel ainda é majoritariamente lacuna.
5. **`composicao.organico` global aplicada a todos os municípios**
   (`transform.py`) — não há gravimetria por município ligada. M1 pede
   substituir pela gravimetria real do PMGIRS de Sorocaba. Risco de apresentar
   estimativa uniforme como se fosse específica; mitigado pelo flag, mas a
   composição não tem flag própria.

## Determinismo / reprodutibilidade

6. **`date.today()` em `render.py:36`** injeta `gerado_em` no `data.json` →
   diffs espúrios a cada build, atrapalhando a regra "data.json commitado".
   Considerar data fixa/injetável ou tirar do diff.

## Paridade e contratos

7. **Divergência model.py ↔ app.js**: `model.project()` retorna
   `carros_equivalente`; `app.js` usa `carros`. Os nomes de campo já divergiram e
   **não há teste de paridade cross-language**, apesar de o contrato (CLAUDE.md)
   exigir o mesmo número dos dois lados. Risco real de o simulador do painel e o
   build divergirem silenciosamente.

## Generalização (acoplamento à RMS)

8. **`subregiao` e laços assumindo a RMS** — código enviesado para a região
   piloto. Generalizar para qualquer cidade BR (M4) exige remover suposições de
   sub-região hardcoded.

## Testes

9. **`os.chdir(ROOT)` em `tests/test_pipeline.py:18`** quebra isolamento: muda o
   CWD do processo para os demais testes. Sintoma do acoplamento a `Path(".")` na
   `cli.py`. Idealmente passar `root` explicitamente em vez de depender do CWD.

## Front / performance

10. **`cache: "no-store"` no fetch do painel** (`site/app.js`) força re-download
    completo do `data.json` a cada visita. Aceitável para um JSON pequeno, mas
    revisar quando o payload crescer (multi-região, série temporal de M5).

## Segurança

- Sem segredos no repo (fontes públicas, sem auth). APIs IBGE/SNIS são abertas.
  Baixo risco. Nenhum dado pessoal processado.

## Observação transversal

A maior parte dos itens acima é **dívida intencional e mapeada** no GSD.md, não
bug surpresa. Os riscos de maior atenção para credibilidade (a "regra sagrada")
são: (5) composição uniforme sem flag próprio e (7) paridade do modelo sem teste.
