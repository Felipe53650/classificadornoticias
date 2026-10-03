# Pauta · Classificador de notícias

Pipeline experimental de classificação textual em português e portal editorial local. O modelo sugere uma categoria; o editor revisa e salva a decisão. Python, TF-IDF, scikit-learn, FastAPI, Jinja2 e SQLite.

**Estado:** implementação concluída, com 21 testes automatizados aprovados e fluxo verificado em navegador desktop/mobile usando o modelo real. O dataset `brazilian-news.parquet` contém 167.053 registros e 48 rótulos, dos quais dez editorias foram mapeadas para as categorias do projeto. Foram executados 21 experimentos nos cenários 4/7/10 classes. A SVM balanceada e calibrada foi exportada para `models/production`: **F1 macro 0,8955 e accuracy 94,32% em 15.654 notícias do teste reservado**. A inferência individual média observada foi 7,61 ms.

Consulte os [resultados e limites de interpretação](reports/RESULTADOS.md), o [registro de validação](docs/VALIDACAO.md) e a [captura do portal com o modelo real](docs/screenshots/production/analysis-desktop.png). As execuções são rastreadas em `reports/research_runs.json`; a demonstração sintética permanece separada.

Consulte a [revisão do plano](docs/REVISAO_PLANO.md) para as correções metodológicas, decisões de implementação e limitações. O original foi preservado em `docs/PLANO_ORIGINAL.md`.

## Iniciar no Windows / VS Code

Abra esta pasta no VS Code e execute no terminal PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
$env:MODEL_DIR = "models/production"
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Acesse **http://127.0.0.1:8000**. Documentação interativa: **http://127.0.0.1:8000/docs**. Se a política do PowerShell impedir ativação, substitua `python` por `.\.venv\Scripts\python.exe` nos comandos. Não é necessário alterar a política de execução.

O ambiente desta entrega foi validado em **Python 3.14.3 no Windows**. `requirements.txt` define faixas; `requirements-lock.txt` fixa todas as versões do ambiente testado e pode ser instalado com `python -m pip install -r requirements-lock.txt`. Python 3.12 era a proposta original e não foi testado nesta máquina.

O comando acima usa o modelo real exportado em `models/production`. Em uma cópia limpa do repositório, os artefatos não estarão presentes: execute primeiro o treinamento descrito abaixo ou use a demonstração sintética:

```powershell
python -m scripts.demo
$env:MODEL_DIR = "models/demo"
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

`scripts.demo` executa os cenários 4/7/10, compara quatro algoritmos e suas variantes de pesos (sete experimentos por cenário), exporta o vencedor do cenário de dez classes em `models/demo` e gera `reports/demo_experiments.csv`. Se o modelo demo já existe, use-o diretamente ou escolha `--output models/demo-v2` para outra execução. A interface indica permanentemente que se trata de demonstração. Não use essas métricas no TCC como resultados reais.

## Dataset e pesquisa

Siga [data/README.md](data/README.md) para inspecionar CSV ou Parquet. Os três YAMLs já contêm o [mapeamento verificado do arquivo recebido](data/MAPEAMENTO_FOLHA.md). Para outra base, refaça a inspeção antes de confirmar o mapeamento.

Para repetir a pesquisa completa usando o arquivo enviado (o diretório de saída do modelo deve estar livre):

```powershell
python -m scripts.run_research --dataset "C:\Users\felipe\Downloads\brazilian-news.parquet" --model-output models/production-v2
python -m scripts.summarize_research
```

Os exemplos abaixo mostram execução individual por cenário; aceitam `.parquet` no lugar de `.csv`.

```powershell
python -m src.data.inspect_dataset data/raw/folha.csv
# Ajuste os nomes de colunas conforme a inspeção:
python -m src.data.inspect_dataset data/raw/folha.csv --title-column title --content-column text --category-column category --output reports/folha_inspection.json
# Após revisar os YAMLs e confirmar o mapeamento:
python -m scripts.prepare_data --dataset data/raw/folha.csv --config configs/categories_10.yaml
python -m scripts.run_experiments --dataset data/raw/folha.csv --config configs/categories_4.yaml
python -m scripts.run_experiments --dataset data/raw/folha.csv --config configs/categories_7.yaml
python -m scripts.run_experiments --dataset data/raw/folha.csv --config configs/categories_10.yaml
```

Cada execução imprime seu diretório `reports/runs/categories_N_<id>`, contendo:

- `config.json`, `manifest.json` e `preparation.json`: configuração, proveniência e auditoria;
- `train.csv`, `validation.csv`, `test.csv`: partições rastreáveis por hash textual;
- `experiments.csv`: accuracy, precision/recall/F1 macro e weighted, tempos e volumes;
- pastas por experimento: relatórios por classe, erros, matrizes absolutas e normalizadas em JSON e PNG;
- `selection.json`: vencedor por F1 macro de **validação**, dentro do cenário.

Os experimentos não calculam métricas no teste. Para exportar o vencedor do cenário escolhido e fazer a avaliação final:

```powershell
python -m scripts.train_best_model --run reports/runs/categories_10_ID_DA_EXECUCAO --output models/production
$env:MODEL_DIR = "models/production"
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Substitua `ID_DA_EXECUCAO` pelo caminho impresso. O modelo é reajustado em treino + validação. Se SVM vencer, o pipeline inteiro é calibrado por validação cruzada. O teste final gera `final_test/` e `final_evaluation.json`. A exportação recusa sobrescrever uma avaliação final ou um modelo existente. Não ajuste configurações após consultar esse teste.

`models/production` recebe `best_model.joblib` e `metadata.json` com versão única, classes, hash do corpus/artefato, versões de dependências, decisão de seleção, tamanho, tempo e métricas finais. Carregue somente artefatos joblib locais confiáveis.

Os cenários reais usam no máximo 50.000 atributos TF-IDF `float32`. A floresta secundária tem 50 árvores com profundidade máxima 30. O cache de TF-IDF é compartilhado entre modelos **somente dentro da mesma execução e partição de treino**. Por isso, `train_seconds` após o primeiro modelo pode incluir reaproveitamento da vetorização; não o interprete como custo total comparável de treinamento sem cache. Configurações e limitações constam da revisão metodológica.

## Portal e API

1. Escreva título e/ou conteúdo e clique em **Analisar notícia**.
2. Revise a categoria sugerida, confiança e top 3.
3. Escolha a categoria final e marque a confirmação.
4. Clique em **Salvar decisão** e consulte o histórico.

Editar o texto invalida a sugestão. Salvar não publica em site externo. O banco `editorial.db` é criado automaticamente e preserva artigos após reiniciar.

| Endpoint | Função |
|---|---|
| `GET /health` | Disponibilidade e versão do modelo; `degraded` quando ausente |
| `GET /api/categories` | Categorias e limiares da interface |
| `POST /api/classify` | Sugestão com top 3 e identificador persistido da previsão |
| `POST /api/articles` | Confirmação humana de uma previsão |
| `GET /api/articles` | Histórico paginado; filtros `category`, `was_corrected` |
| `GET /api/feedback` | Aceitação, correções e pares de categorias |

Exemplos de payload:

```json
{"title": "Banco Central anuncia decisão", "content": "O comitê discutiu a taxa de juros..."}
```

```json
{"prediction_id": "IDENTIFICADOR_RETORNADO", "final_category": "Economia", "confirmed": true}
```

A segunda requisição usa os dados da previsão armazenada no servidor; o cliente não define confiança, categoria prevista, versão ou indicador de correção. Uma previsão só pode ser salva uma vez. A API retorna 422 para entradas inválidas, 503 quando o modelo está indisponível, 404 para previsão desconhecida e 409 para duplicação.

## Configuração e arquitetura

Variáveis de ambiente documentadas em `.env.example` (não carregado automaticamente):

```powershell
$env:MODEL_DIR = "models/production"
$env:DATABASE_URL = "sqlite:///./editorial.db"
$env:CONFIDENCE_HIGH = "0.85"
$env:CONFIDENCE_MEDIUM = "0.65"
```

`src/data` concentra limpeza/inspeção; `src/ml` contém treino, avaliação e inferência; `src/api` fornece rotas e validação; `src/db` usa SQLAlchemy; `src/web` contém templates, CSS e JavaScript sem build. `scripts` oferece comandos reproduzíveis. O pipeline acadêmico funciona sem o portal. A camada SQLAlchemy permite migração futura de banco, mas PostgreSQL não foi validado e requer driver próprio.

## Validação e limites

Execute `python -m pytest -q`. A suíte verifica dados inválidos, deduplicação, conflitos, partições disjuntas/reproduzíveis, calibração, integridade do artefato, inferência, API, confirmação editorial e persistência após reinício. A demonstração completa também exercita relatórios dos três cenários e exportação final.

Teste opcional de navegador, com Microsoft Edge instalado:

```powershell
python -m pip install playwright
python -m scripts.check_ui --model-dir models/production --screenshots docs/screenshots/production
```

Esse teste inicia e encerra seu próprio servidor, usa banco temporário e verifica análise, confirmação, correção, histórico, filtros, invalidação após editar texto e layout mobile. Capturas são salvas no diretório indicado. Playwright não é dependência do portal nem do pipeline de pesquisa.

Sem autenticação, publicação externa, coleta automática, retreinamento automático ou detecção de conteúdo fora das categorias. Uso previsto: demonstração local. Pesquisas com dados reais precisam avaliar quase duplicados, desbalanceamento, calibração, variabilidade e mudança temporal. Limiares da interface não são garantias de acerto.

## Figuras e tabelas do artigo no Google Colab

Abra [Figuras_Artigo_Classificador_Noticias.ipynb](notebooks/Figuras_Artigo_Classificador_Noticias.ipynb) no Colab, execute todas as células e envie `reports/artigo/dados_artigo.zip` quando solicitado. O notebook gera nove figuras (incluindo dois diagramas) e oito tabelas com as métricas reais, sem treinamento nem envio do dataset. PDF/SVG/PNG, CSV/LaTeX/Markdown são reunidos em um ZIP para download.

As saídas prontas estão em `reports/artigo/figuras_e_tabelas.zip`. Consulte o [guia de uso e seleção de figuras](docs/ARTIGO_COLAB.md) para instruções, legendas e ressalvas metodológicas.
