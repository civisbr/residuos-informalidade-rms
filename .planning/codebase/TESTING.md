# Testing

*Mapped: 2026-06-21*

## Framework

**pytest** (configurado via `pyproject.toml`). Roda offline, sem rede.

```bash
uv run pytest -q
```

Também roda no CI em `.github/workflows/build.yml`.

## Structure

Um único arquivo: `tests/test_pipeline.py` (testes de sanidade). Estratégia:
garantir que o build não regrida e que a regra sagrada de integridade de dado
seja respeitada.

Testes atuais:
- `test_rms_tem_27_municipios` — a RMS tem exatamente 27 municípios em `regions.yml`.
- `test_build_offline_gera_dados` — build offline gera 27 linhas; Sorocaba tem
  `flag == "real"` e `rsu_t_ano == 228000`; existem ≥20 municípios `pendente` e
  **nenhum deles inventa número** (`rsu_t_ano` é null em todos os pendentes).
- `test_modelo_break_even_coerente` — `model.project()` com defaults devolve
  desvio > 0, `0 < pct_organico_municipal < 5` (Fase 1 é foothold, não bala de
  prata), e catadores sustentados > 0.

## Mocking & fixtures

Sem mocking. Usa **fixtures reais commitadas** (`config/*.yml`, `config/municipios.csv`,
`data/raw/snis/snis_rs_sample.csv`). Os testes leem os arquivos reais via
`ROOT = Path(__file__).resolve().parents[1]`.

## Coverage / lacunas

- **Sem teste de paridade `model.py` ↔ `app.js`** — apesar de o contrato exigir
  o mesmo número nos dois lados. Os nomes de campo já divergiram
  (`carros_equivalente` em Python vs. `carros` no JS — ver CONCERNS.md). Um teste
  de paridade cross-language está faltando e é prioritário.
- `test_build_offline_gera_dados` faz `os.chdir(ROOT)`, quebrando isolamento:
  altera o CWD do processo de teste para os demais (ver CONCERNS.md).
- Sem cobertura de `render.to_payload()`/`write()`, nem das fontes isoladas.
- Sem teste para múltiplas regiões (só RMS).

## Convenções de teste

- Nomes em português, no estilo `test_<o_que_garante>`.
- Asserts cravam valores-âncora reais (ex.: Sorocaba 228000 t/ano) para detectar
  regressão de dado.
- Todo teste deve passar **offline**.
