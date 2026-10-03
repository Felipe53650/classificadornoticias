# Dados

O projeto aceita CSV e Parquet. O arquivo recebido, `brazilian-news.parquet`, foi inspecionado diretamente em Downloads: 167.053 registros, 48 categorias originais. O [mapeamento auditado](MAPEAMENTO_FOLHA.md) documenta as dez classes adotadas. Não é necessário copiar o arquivo para o repositório. O projeto não baixa nem redistribui notícias automaticamente. Fonte sugerida no plano: [News of the Brazilian Newspaper](https://www.kaggle.com/datasets/marlesson/news-of-the-site-folhauol).

Primeiro inspecione as colunas, sem presumir a taxonomia:

```powershell
python -m src.data.inspect_dataset data/raw/folha.csv
```

Depois informe os nomes encontrados para obter distribuição de categorias e vazios:

```powershell
python -m src.data.inspect_dataset data/raw/folha.csv --title-column title --content-column text --category-column category --output reports/folha_inspection.json
```

`title`, `text` e `category` são os nomes confirmados no arquivo recebido. Para outros arquivos, substitua pelos nomes reais. O leitor aceita Parquet (via PyArrow) e CSV UTF-8 separado por vírgulas, com cabeçalho.

As três configurações em `configs/` já estão confirmadas para o arquivo recebido. Para outra base, ajuste `columns`, `categories`, `dataset_version` e `label_mapping`. O mapeamento deve incluir **todos** os rótulos observados, mesmo os externos ao cenário; use `null` para excluir um rótulo. Só então altere `mapping_confirmed` para `true`. Não agrupe categorias semanticamente diferentes apenas para atingir dez classes. Documente substituições neste diretório.

Exemplo puramente ilustrativo, sem afirmar rótulos do corpus:

```yaml
label_mapping:
  rotulo_original_de_economia: Economia
  rotulo_excluido: null
```

`scripts.demo` cria 450 exemplos sintéticos artificiais em dez classes, com vocabulários deliberadamente separáveis. Resultados nessa base não são evidência de qualidade em notícias reais. Os CSVs brutos, processados e partições experimentais não entram no Git.
