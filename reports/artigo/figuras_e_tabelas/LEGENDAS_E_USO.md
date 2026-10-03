# Figuras e tabelas para o artigo

Fonte sugerida: elaboração própria a partir dos experimentos deste trabalho.

- 01: Distribuição de notícias após a preparação, cenário de dez categorias.
- 02: F1 macro de validação nos cenários de 4, 7 e 10 categorias. Cada ponto é uma execução com semente 42; linhas apenas conectam cenários observados. Volume e composição também mudam entre cenários.
- 03: Diferença de F1 macro (balanceado menos sem pesos), em pontos percentuais, na validação. Não representa significância estatística.
- 04: Matriz de confusão do modelo final no teste, normalizada por categoria real. Linhas somam aproximadamente 100% devido ao arredondamento.
- 05: Mesma matriz em contagens absolutas; categorias têm suportes diferentes.
- 06: Precision, recall e F1 por categoria no teste final da SVM balanceada e calibrada.
- 07: Latência individual observada em até 100 exemplos de validação por modelo no cenário de dez classes. A SVM desse benchmark não é calibrada. A latência do artefato final calibrado está na tabela de teste; medidas dependem do hardware e não são teste de carga.
- 08: Fluxo experimental implementado; ajuste de TF-IDF somente nos dados de treinamento, incluindo dentro dos folds da calibração. O teste não participa da seleção.
- 09: Fluxo editorial implementado. Confirmação humana precede o salvamento da decisão; não há publicação externa nem retreinamento automático.

Use no corpo do artigo prioritariamente 01, 02, 04 e 08; acrescente 03 ou 06 conforme o espaço. O fluxo editorial pode acompanhar a seção de aplicação. Tabelas completas e matriz absoluta podem ir em apêndice/material suplementar.

CSV preserva números para cálculos. Markdown permite revisão. LaTeX contém tabular, para inserir dentro de table; ajuste largura e cabeçalhos ao template. PNG tem 300 dpi por padrão; PDF/SVG são vetoriais. Títulos, fontes e cores podem ser ajustados nas funções do notebook.

Não misture validação com teste em uma classificação geral de modelos. Os modelos experimentais de SVM usam LinearSVC; o teste corresponde à versão calibrada após reajuste. Valores de treino incluem cache e não permitem comparação uniforme de custo integral. Uma única semente não fornece intervalos de confiança; eles não foram inventados. Calibrar não demonstra por si só calibração perfeita. Notícias quase duplicadas e generalização temporal continuam como limitações.
