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

## Caminho programático (M4)
- `basedosdados` espelha o SNIS em tabela consultável (requer projeto GCP).
- Alternativa: scraping/download direto da série histórica do SNIS.
- Implementar em `pipeline/sources/snis.py::refresh()` e documentar aqui.

## Gravimetria (composição do RSU)
A fração orgânica padrão (51%) é média nacional. Para Sorocaba, o PMGIRS traz
gravimetria real — substitua em `config/coefficients.yml::composicao` por município
quando for refinar (idealmente a composição vira coluna por município, não global).
