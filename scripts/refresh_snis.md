# Atualizar os dados do SNIS

O SNIS-RS (Resíduos Sólidos) publica uma série histórica anual por município.
A pipeline é determinística: ela reprocessa o que estiver em `data/raw/snis/`.

## Caminho manual (recomendado para começar)
1. Acesse a série histórica do SNIS (Ministério das Cidades) e exporte o conjunto
   de Manejo de Resíduos Sólidos Urbanos para os municípios/ano desejados.
   - Portal de Resíduos Sólidos: <https://app4.cidades.gov.br/serieHistorica/residuosSolidos/index>
   - Consulta geral por município: <https://app4.cidades.gov.br/serieHistorica/municipio/index>
   - (O domínio antigo `app4.mdr.gov.br` saiu do ar — o MDR virou Ministério das Cidades.)
   - Alternativa (mesmos dados, via SQL): Base dos Dados
     <https://basedosdados.org/dataset/2a543ad8-3cdb-4047-9498-efe7fb8ed697>
2. Ajuste as colunas para o esquema esperado (ver `pipeline/sources/snis.py`):
   `municipio, uf, ano, rsu_t_ano, reciclado_t_ano, reciclado_pct,
    coleta_seletiva_pop_pct, cooperados, custo_mensal_rs, qualidade, fonte`
3. Salve como CSV em `data/raw/snis/` (pode ter vários arquivos/anos).
4. `uv run obs build --region rms` — a pipeline mantém o ano mais recente por município.

## Caminho programático (recomendado) — `scripts/scrape_snis.py`
O SNIS-RS (resíduos sólidos) **não** está na Base dos Dados (que só espelha
água/esgoto). O caminho que funciona é o backend jqGrid da Série Histórica:

```bash
uv run python scripts/scrape_snis.py --build --region rms \
    --exclude sorocaba "porto feliz"   # já têm dado citável no sample
# -> data/raw/snis/snis_rms_sp.csv (ano mais recente; 1 município por linha)
uv run obs build --region rms && uv run pytest -q
```

O script faz engenharia reversa do controlador `consolidadoMunicipio` (tipo_info=3),
resolve códigos de 6 dígitos por município, monta a busca (getGridConfig assíncrono
+ polling), lê o grid (getGridData) e mapeia cada coluna pelo `colModel`. Cada linha
cita a `fonte` com os campos SNIS usados (CO116/CO117/CO142/CS048, CS026, IN031_RS,
IN030_RS, FN220) e a data de download. É a semente de `snis.py::refresh()` (M4/GEN-02).

> `scripts/fetch_snis.py` (via Base dos Dados/BigQuery) é um **beco sem saída**
> para resíduos sólidos — a BD não publica a tabela de RSU. Mantido só como
> referência; use `scrape_snis.py`.

## Gravimetria (composição do RSU)
A fração orgânica padrão (51%) é média nacional. Para Sorocaba, o PMGIRS traz
gravimetria real — substitua em `config/coefficients.yml::composicao` por município
quando for refinar (idealmente a composição vira coluna por município, não global).
