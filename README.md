# Pauta · Classificador de notícias

Pipeline experimental de classificação textual em português e portal editorial local. O modelo sugere uma categoria; o editor revisa e salva a decisão. Python, TF-IDF, scikit-learn, FastAPI, Jinja2 e SQLite.

**Estado:** implementação concluída, com 33 testes automatizados aprovados e fluxo verificado em navegador desktop/mobile usando o modelo real. O dataset `brazilian-news.parquet` contém 167.053 registros e 48 rótulos, dos quais dez editorias foram mapeadas para as categorias do projeto. Foram executados 21 experimentos nos cenários 4/7/10 classes. A SVM balanceada e calibrada foi exportada para `models/production`: **F1 macro 0,8955 e accuracy 94,32% em 15.654 notícias do teste reservado**. A inferência individual média observada foi 7,61 ms.

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

A página inicial (`/`) é o feed de leitura do Pauta, com matéria em destaque, cards ilustrados, busca no título/conteúdo, filtros por editoria e origem, paginação e página de leitura completa. O layout se adapta ao computador e ao celular e a navegação do feed funciona sem JavaScript.

Oito textos fictícios, identificados como **Exemplo fictício**, permitem explorar o portal mesmo com o banco vazio ou sem modelo carregado. Esses exemplos ficam em `src/web/feed.py`: não são inseridos no banco, não vêm do dataset Folha e não entram no treinamento, nas métricas ou no feedback editorial. O filtro **Da redação** mostra somente os registros confirmados no banco local; **Exemplos** mostra somente as demonstrações.

As notícias salvas pela redação aparecem antes dos exemplos, da mais recente para a mais antiga, usando a categoria **final confirmada**. Apenas analisar um texto não o inclui no feed. As ilustrações são composições decorativas em CSS, sem imagens externas. O indicador de leitura é uma estimativa de 200 palavras por minuto.

1. Abra a **Mesa editorial** (`/editor`), escreva título e/ou conteúdo e clique em **Analisar notícia**.
2. Revise a categoria sugerida, confiança e top 3.
3. Escolha a categoria final e marque a confirmação.
4. Clique em **Salvar decisão** e consulte o feed ou o histórico (`/history`).

Editar o texto invalida a sugestão. Salvar disponibiliza a matéria no feed deste protótipo local, sem publicar em site externo. O banco `editorial.db` é criado automaticamente e preserva artigos após reiniciar.

No **Histórico**, cada notícia tem as ações **Editar** e **Remover**:

- **Editar** abre a mesa editorial com o texto, a categoria final e a análise salva. Mudar título ou conteúdo exige uma nova análise e confirmação antes de **Salvar alterações**. Alterar somente a categoria reaproveita a análise existente e funciona mesmo sem o modelo carregado. **Cancelar edição** volta ao histórico sem modificar a notícia.
- **Remover** abre uma confirmação com o título da notícia. Confirmar retira o registro do histórico e do feed; cancelar ou pressionar Escape mantém a notícia. A interface não oferece desfazer.
- A edição mantém o identificador e a data de criação da notícia. O feed e o feedback editorial passam a refletir a decisão atual; as métricas dos experimentos do TCC não são alteradas. As análises persistidas permanecem no banco, mas não constituem um histórico completo de versões das decisões.
- Se outra aba modificar a notícia, a operação retorna conflito e pede para reabrir a edição ou atualizar o histórico. A exclusão da última linha de uma página retorna automaticamente à página anterior disponível.

| Endpoint | Função |
|---|---|
| `GET /` | Feed paginado; filtros `q`, `category`, `source` (`all`, `editorial`, `demo`) e página `p` |
| `GET /news/{key}` | Leitura de matéria (`local-ID` ou `demo-slug`); 404 para chave inexistente |
| `GET /editor` | Mesa de análise e confirmação editorial |
| `GET /history` | Histórico das decisões editoriais |
| `GET /health` | Disponibilidade e versão do modelo; `degraded` quando ausente |
| `GET /api/categories` | Categorias e limiares da interface |
| `POST /api/classify` | Sugestão com top 3 e identificador persistido da previsão |
| `POST /api/articles` | Confirmação humana de uma previsão |
| `GET /api/articles` | Histórico paginado; filtros `category`, `was_corrected` |
| `GET /api/articles/{id}` | Texto, decisão, análise salva, categorias válidas e `revision` para edição |
| `PUT /api/articles/{id}` | Atualiza a notícia a partir de uma análise persistida e confirmação humana |
| `DELETE /api/articles/{id}` | Remove do histórico/feed após confirmação e conferência da revisão |
| `GET /api/feedback` | Aceitação, correções e pares de categorias |

Exemplos de payload:

```json
{"title": "Banco Central anuncia decisão", "content": "O comitê discutiu a taxa de juros..."}
```

```json
{"prediction_id": "IDENTIFICADOR_RETORNADO", "final_category": "Economia", "confirmed": true}
```

A segunda requisição usa os dados da previsão armazenada no servidor; o cliente não define confiança, categoria prevista, versão ou indicador de correção. Uma previsão só pode estar vinculada a uma notícia por vez. A API retorna 422 para entradas inválidas, 503 quando o modelo está indisponível, 404 para notícia/previsão desconhecida e 409 para duplicação ou conflito de edição.

Para atualizar, envie ao `PUT` os campos de confirmação acima mais `expected_revision`, obtido no `GET` da notícia. Para remover, envie ao `DELETE` um corpo JSON com `confirmed: true` e `expected_revision`. O servidor valida a revisão antes de modificar o registro. Texto e metadados da edição são copiados da análise indicada por `prediction_id`; a API não aceita texto livre nesse endpoint.

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

Esse teste inicia e encerra seu próprio servidor, usa banco temporário e verifica feed, busca, editorias, paginação, leitura, análise, confirmação, correção, histórico, filtros, invalidação após editar texto e layout mobile. Capturas são salvas no diretório indicado. Playwright não é dependência do portal nem do pipeline de pesquisa.

Sem autenticação, publicação externa, coleta automática, retreinamento automático ou detecção de conteúdo fora das categorias. Uso previsto: demonstração local. Pesquisas com dados reais precisam avaliar quase duplicados, desbalanceamento, calibração, variabilidade e mudança temporal. Limiares da interface não são garantias de acerto.

## Figuras e tabelas do artigo no Google Colab

Abra [Figuras_Artigo_Classificador_Noticias.ipynb](notebooks/Figuras_Artigo_Classificador_Noticias.ipynb) no Colab, execute todas as células e envie `reports/artigo/dados_artigo.zip` quando solicitado. O notebook gera nove figuras (incluindo dois diagramas) e oito tabelas com as métricas reais, sem treinamento nem envio do dataset. PDF/SVG/PNG, CSV/LaTeX/Markdown são reunidos em um ZIP para download.

As saídas prontas estão em `reports/artigo/figuras_e_tabelas.zip`. Consulte o [guia de uso e seleção de figuras](docs/ARTIGO_COLAB.md) para instruções, legendas e ressalvas metodológicas.
