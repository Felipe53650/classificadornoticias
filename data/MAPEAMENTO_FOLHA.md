# Mapeamento do arquivo recebido

Arquivo: `brazilian-news.parquet`, 311.705.743 bytes, 167.053 registros. Colunas observadas: `title`, `text`, `date`, `category`, `subcategory`, `link`. A inspeção está em `reports/folha_inspection.json`. O hash completo é registrado no manifesto de cada execução.

| Original | Categoria adotada | Registros brutos | Cenários |
|---|---|---:|---|
| poder | Política | 22.022 | 4, 7, 10 |
| mercado | Economia | 20.970 | 4, 7, 10 |
| esporte | Esportes | 19.730 | 4, 7, 10 |
| mundo | Mundo | 17.130 | 4, 7, 10 |
| tec | Tecnologia | 2.260 | 7, 10 |
| ciencia | Ciência | 1.335 | 7, 10 |
| equilibrioesaude | Saúde | 1.312 | 7, 10 |
| educacao | Educação | 2.118 | 10 |
| ilustrada | Entretenimento | 16.345 | 10 |
| turismo | Turismo | 1.903 | 10 |

Existem 48 rótulos originais. Os demais são explicitamente mapeados para `null` nas configurações. Foram excluídas editorias transversais ou fora do escopo, como `colunas`, `opiniao`, `cotidiano`, `paineldoleitor`, `bbc` e `tv`; não se inferem categorias temáticas pelo texto. Uma notícia de `tv`, por exemplo, não é automaticamente anexada à classe Entretenimento.

`ilustrada` é uma aproximação operacional para cultura/entretenimento; `equilibrioesaude` abrange saúde e bem-estar. São agregações conceituais documentadas, não rótulos ontológicos perfeitos. Essas diferenças devem ser discutidas no TCC.

A inspeção encontrou 765 corpos vazios, nenhum título vazio e nenhum registro com ambos vazios. Notícias somente com título são preservadas. Não há linhas inteiras duplicadas; a auditoria posterior faz deduplicação pelo texto normalizado e remove conflitos entre rótulos mapeados.

As categorias são fortemente desbalanceadas; não foi feito subamostragem para igualar volumes. O limite TF-IDF de 50.000 atributos, representação `float32` e a floresta com 50 árvores/profundidade 30 controlam memória e custo. Os classificadores lineares e o Naive Bayes mantêm a mesma representação. Essa é uma configuração inicial registrada, não um ótimo obtido por busca de hiperparâmetros.

O arquivo recebido não é copiado para o repositório nem redistribuído. Sua estrutura é compatível com a base citada no plano; a origem exata da conversão para Parquet não foi fornecida. As colunas `date`, `subcategory` e `link` não entram no modelo, evitando aprendizado direto de URL/editoria. Datas não foram reinterpretadas nem usadas em split temporal.
