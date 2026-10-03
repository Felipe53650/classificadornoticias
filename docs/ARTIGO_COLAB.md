# Diagramas, tabelas e gráficos para o artigo

Os arquivos desta entrega usam as métricas reais dos 21 experimentos já concluídos. Não treinam novamente, não consultam o teste com outros modelos e não precisam do dataset Parquet.

## Arquivos prontos

- `notebooks/Figuras_Artigo_Classificador_Noticias.ipynb`: notebook autossuficiente para o Colab.
- `reports/artigo/dados_artigo.zip`: pacote pequeno de métricas, contagens, parâmetros e proveniência para enviar ao notebook.
- `reports/artigo/figuras_e_tabelas.zip`: todas as saídas já geradas localmente, prontas para baixar/extrair.
- `reports/artigo/figuras_e_tabelas/`: mesmas saídas em pastas, com sugestões de legendas.
- `reports/artigo/notebook_executado.ipynb`: registro da execução local das células e suas saídas. Para usar no Colab, prefira o notebook limpo da pasta `notebooks/`.

## Como executar no Google Colab

1. Acesse [Google Colab](https://colab.research.google.com/).
2. Use **Arquivo → Fazer upload de notebook** e escolha `Figuras_Artigo_Classificador_Noticias.ipynb`. Os nomes dos menus podem variar com o idioma.
3. Use **Ambiente de execução → Executar tudo**. CPU é suficiente; não precisa selecionar GPU.
4. Quando o seletor de arquivos aparecer, envie somente `dados_artigo.zip`.
5. Confira as figuras exibidas. A última célula oferece o download de `saida_artigo.zip`.

Se o navegador bloquear o download automático, baixe `saida_artigo.zip` pelo painel de arquivos do Colab. Para trocar os resultados, use uma sessão nova ou ajuste `BUNDLE` para o nome do novo ZIP enviado. O notebook usa NumPy, pandas e Matplotlib; as funções de geração estão incorporadas nele.

O [FAQ oficial do Colab](https://research.google.com/colaboratory/intl/en-GB/faq.html) documenta o upload de notebooks existentes. O [exemplo oficial de entrada e saída de arquivos](https://colab.research.google.com/notebooks/io.ipynb) explica `files.upload()` e `files.download()`.

## O que incluir no artigo

| Material | Finalidade | Local sugerido |
|---|---|---|
| Diagrama experimental | Explicar preparação, partições, seleção e teste isolado | Metodologia |
| Tabela de tamanhos e distribuição | Mostrar quais dados foram usados e o desbalanceamento | Metodologia |
| Tabela comparativa de F1 macro | Mostrar os sete modelos/variantes nos três cenários | Resultados |
| Gráfico de F1 macro | Facilitar a leitura das diferenças entre cenários | Resultados |
| Gráfico de efeito dos pesos | Sustentar a discussão do balanceamento | Resultados/discussão |
| Matriz de confusão normalizada | Identificar confusões levando em conta o suporte de cada classe | Discussão |
| Tabela/gráfico por categoria | Mostrar precision, recall, F1 e quantidade de exemplos | Resultados/discussão |
| Diagrama editorial | Explicar sugestão, revisão humana e persistência | Aplicação |
| Tabela detalhada de todos os experimentos | Permitir consulta dos valores completos | Apêndice/material suplementar |

Evite repetir os mesmos números em muitas figuras. Em um artigo curto, priorize o fluxo experimental, a distribuição, a comparação de F1 macro e a matriz normalizada; use a tabela para valores exatos e o gráfico para tendências.

## Formatos e personalização

São **nove figuras** em PNG a 300 dpi, PDF e SVG. As **oito tabelas** são exportadas em CSV (UTF-8 com BOM), Markdown e LaTeX. CSV mantém a precisão numérica; a apresentação em Markdown/LaTeX arredonda números decimais a quatro casas. As matrizes são mostradas em porcentagem ou em contagens, conforme o nome do arquivo.

Para Word, use PNG ou SVG. Para LaTeX, prefira figuras PDF e inclua o `.tex` da tabela dentro de um ambiente `table`, acrescentando legenda e ajustando largura/cabeçalhos ao template. As tabelas `.tex` usam `tabular` sem exigir `booktabs`. O [Matplotlib documenta a exportação para formatos raster e vetoriais](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html).

No notebook, altere `DPI`, `configure_style(font_size=...)` e as cores em `COLORS`. Os títulos e dimensões estão nas funções da primeira célula. O arquivo `LEGENDAS_E_USO.md` acompanha as saídas e sugere legendas. Fonte sugerida: **Elaboração própria a partir dos experimentos deste trabalho.**

## Cuidados na interpretação

- A comparação dos 21 experimentos é de **validação**; as métricas e matrizes do modelo final são de **teste**. As figuras identificam essa distinção.
- A SVM do benchmark é `LinearSVC`; o artefato final inclui calibração e reajuste em treino + validação. Não atribua as métricas de teste diretamente à versão não calibrada.
- O gráfico de latência compara modelos do benchmark no cenário de dez classes. O tempo do modelo calibrado fica separado na tabela final. São medidas locais em até 100 previsões individuais.
- Os tempos de treinamento incluem uso de cache de TF-IDF. Foram disponibilizados em tabela com ressalva, sem apresentar um ranking de custo integral de treinamento.
- Não há barras de erro ou testes de significância: houve uma única semente. Quantidade de classes, composição e tamanho do corpus mudam simultaneamente.
- O pacote enviado ao Colab contém dados agregados; não contém notícias, títulos, partições com textos, banco editorial, código executável ou modelos joblib.

## Regerar no computador do projeto

```powershell
.\.venv\Scripts\python -m scripts.package_article_results
.\.venv\Scripts\python -m scripts.article_figures
```

Esses comandos geram o pacote de entrada e o ZIP final, sem carregar modelos ou dados brutos. Se alterar `scripts/article_figures.py`, sincronize o notebook:

```powershell
.\.venv\Scripts\python -m scripts.build_article_notebook
```

Validação opcional em um kernel Jupyter local:

```powershell
.\.venv\Scripts\python -m pip install nbformat nbclient ipykernel
.\.venv\Scripts\python -m scripts.check_article_notebook
```

O notebook foi executado localmente em kernel Jupyter, em diretório isolado contendo apenas o ZIP de métricas. As 11 células de código foram concluídas e produziram 27 arquivos de figuras e 24 arquivos de tabelas. A autenticação, o seletor de upload e o download da interface hospedada do Colab não foram testados em uma conta Google nesta entrega.
