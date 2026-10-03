# Plano técnico de implementação do TCC

## Classificação automática de notícias por assunto para apoio editorial em portal de notícias

**Ambiente principal:** Visual Studio Code  
**Linguagem:** Python 3.12  
**Foco do TCC:** Machine Learning aplicado a classificação textual multiclasse  
**Aplicação demonstrável:** portal editorial com sugestão automática de categoria  
**Abordagem operacional:** human-in-the-loop - o modelo sugere e o editor confirma ou corrige  

---

## 1. Visão geral

O projeto deverá desenvolver e avaliar modelos de Machine Learning capazes de classificar automaticamente notícias em categorias temáticas. O melhor modelo experimental será integrado a um portal de notícias simplificado, no qual um jornalista ou editor informa título e conteúdo da matéria e recebe uma sugestão de categoria, acompanhada de nível de confiança e alternativas mais prováveis.

A aplicação não deverá publicar ou classificar definitivamente uma notícia sem intervenção humana. A categoria retornada pelo modelo será uma recomendação editorial. O editor poderá aceitar ou corrigir a sugestão antes de salvar/publicar a matéria. As correções serão armazenadas para posterior análise e possível retreinamento do modelo.

O projeto deve preservar duas dimensões claramente separadas:

1. **Pesquisa experimental de Machine Learning:** comparação de algoritmos, quantidade de categorias, tratamento de desbalanceamento e análise de erros.
2. **Prova de conceito aplicada:** integração do melhor modelo a uma aplicação web simples que represente um fluxo editorial real.

---

## 2. Problema de pesquisa

Pergunta principal sugerida:

> Como o aumento da quantidade e da similaridade entre categorias afeta o desempenho de algoritmos de Machine Learning na classificação automática de notícias em língua portuguesa?

Perguntas secundárias:

- Qual algoritmo apresenta melhor desempenho global e por classe?
- Quais categorias são mais frequentemente confundidas?
- Qual é o efeito do desbalanceamento entre categorias?
- O uso de pesos de classe melhora o F1-score das categorias minoritárias?
- Qual modelo oferece a melhor relação entre qualidade de classificação, tempo de treinamento e tempo de inferência?
- O modelo selecionado mantém desempenho adequado quando integrado a uma API e utilizado de forma interativa?

---

## 3. Objetivo geral

Desenvolver, avaliar e integrar a um portal editorial um sistema de classificação automática de notícias em português, comparando técnicas de Machine Learning para identificar o impacto da quantidade de categorias e do desbalanceamento dos dados no desempenho dos classificadores.

## 4. Objetivos específicos

- Preparar e explorar um corpus de notícias em português com categorias temáticas.
- Selecionar subconjuntos com 4, 7 e 10 categorias para produzir níveis progressivos de dificuldade.
- Construir um pipeline reprodutível de preparação textual e vetorização TF-IDF.
- Treinar e comparar diferentes classificadores supervisionados.
- Avaliar os modelos utilizando accuracy, precision, recall, F1-score e matriz de confusão.
- Adotar o F1-score macro como uma das métricas principais, por ser mais informativo diante de classes desbalanceadas.
- Avaliar estratégias simples de tratamento do desbalanceamento, especialmente `class_weight="balanced"` quando suportado.
- Identificar quais classes apresentam maior confusão semântica.
- Integrar o melhor modelo a uma API REST.
- Implementar um portal editorial simples no qual o usuário possa aceitar ou corrigir a classificação sugerida.
- Registrar previsões e correções humanas para análise posterior.

---

## 5. Dataset

### 5.1 Base principal

Utilizar uma base de notícias da Folha de S.Paulo disponibilizada publicamente para pesquisa, conhecida em repositórios de datasets como **News of the Brazilian Newspaper / FolhaUOL**. O arquivo bruto deve permanecer fora do repositório Git caso sua licença ou termos de distribuição não permitam redistribuição.

O agente de implementação **não deve assumir previamente os nomes exatos de todas as categorias**. A primeira tarefa sobre dados deve ser inspecionar o arquivo real e gerar uma tabela contendo:

- nome da coluna de título;
- nome da coluna de conteúdo;
- nome da coluna de categoria;
- número total de registros;
- quantidade de registros vazios;
- quantidade de duplicados;
- distribuição de registros por categoria.

### 5.2 Categorias propostas

A pesquisa deverá tentar trabalhar com dez classes semanticamente distintas, por exemplo:

- Política;
- Economia;
- Esportes;
- Mundo/Internacional;
- Tecnologia;
- Educação;
- Ciência;
- Saúde;
- Entretenimento;
- Turismo.

Os nomes acima são **categorias semânticas desejadas**, não necessariamente os valores literais presentes no dataset. Após a análise exploratória, criar um mapeamento explícito entre os rótulos originais do arquivo e os rótulos adotados pelo projeto.

### 5.3 Cenários experimentais

Criar três configurações reproduzíveis:

**Cenário A - 4 categorias**  
Política, Economia, Esportes e Mundo.

**Cenário B - 7 categorias**  
As quatro anteriores mais Tecnologia, Ciência e Saúde.

**Cenário C - 10 categorias**  
As sete anteriores mais Educação, Entretenimento e Turismo.

Se alguma categoria escolhida tiver poucas amostras, documentar o problema e substituir por outra categoria com volume adequado. Toda alteração deve ficar registrada em arquivo de configuração, e não espalhada pelo código.

---

## 6. Hipóteses experimentais

Hipóteses a testar, sem assumir antecipadamente que serão confirmadas:

- H1: o F1-score macro tende a diminuir conforme aumenta a quantidade de categorias.
- H2: categorias semanticamente próximas apresentam maior taxa de confusão.
- H3: algoritmos lineares baseados em TF-IDF tendem a oferecer uma boa relação entre desempenho e custo computacional para textos jornalísticos.
- H4: estratégias de balanceamento por peso de classe tendem a melhorar o recall/F1 das classes minoritárias, podendo afetar a precisão global.

---

## 7. Arquitetura da solução

```text
                     TREINAMENTO / PESQUISA

Dataset bruto
    |
    v
Inspeção e limpeza
    |
    v
Seleção de categorias (4 / 7 / 10)
    |
    v
Split estratificado treino / validação / teste
    |
    v
Pipeline TF-IDF + Classificador
    |
    v
Avaliação e comparação
    |
    v
Modelo selecionado + metadados
    |
    +-------------------------------+
                                    |
                                    v
                         APLICAÇÃO EDITORIAL

Jornalista/Editor -> Portal Web -> FastAPI -> Modelo treinado
                                      |
                                      v
                       Categoria + probabilidades
                                      |
                                      v
                            Confirmação humana
                                      |
                                      v
                              SQLite/PostgreSQL
```

A parte acadêmica deve funcionar independentemente do portal. Se a interface web deixar de funcionar, ainda deve ser possível reproduzir todos os experimentos via linha de comando.

---

## 8. Stack técnica recomendada

### Machine Learning

- Python 3.12
- pandas
- numpy
- scikit-learn
- joblib
- matplotlib
- seaborn **não é necessário**; os gráficos podem ser feitos apenas com matplotlib

### Aplicação

- FastAPI
- Uvicorn
- Jinja2
- HTML5
- CSS
- JavaScript vanilla
- SQLAlchemy
- SQLite no MVP

### Testes e qualidade

- pytest
- httpx ou TestClient do FastAPI
- ruff para lint opcional
- black para formatação opcional

A escolha por FastAPI + Jinja2 + JavaScript simples reduz a complexidade do frontend e mantém o foco do TCC em Machine Learning. React não é necessário para o MVP.

---

## 9. Estrutura sugerida do repositório

```text
news-classifier-tcc/
|
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- .env.example
|-- pyproject.toml                    # opcional
|
|-- configs/
|   |-- categories_4.yaml
|   |-- categories_7.yaml
|   `-- categories_10.yaml
|
|-- data/
|   |-- raw/                          # ignorado pelo Git
|   |-- processed/                    # ignorado ou parcialmente versionado
|   `-- README.md                     # explica como obter o dataset
|
|-- notebooks/
|   `-- 01_exploratory_analysis.ipynb # opcional, nunca única fonte da lógica
|
|-- src/
|   |-- __init__.py
|   |
|   |-- data/
|   |   |-- inspect_dataset.py
|   |   |-- prepare_dataset.py
|   |   `-- schemas.py
|   |
|   |-- ml/
|   |   |-- train.py
|   |   |-- evaluate.py
|   |   |-- experiment.py
|   |   |-- inference.py
|   |   `-- metrics.py
|   |
|   |-- api/
|   |   |-- main.py
|   |   |-- dependencies.py
|   |   |-- schemas.py
|   |   `-- routes/
|   |       |-- health.py
|   |       |-- classify.py
|   |       `-- articles.py
|   |
|   |-- db/
|   |   |-- database.py
|   |   |-- models.py
|   |   `-- repository.py
|   |
|   `-- web/
|       |-- templates/
|       |   |-- base.html
|       |   |-- index.html
|       |   `-- history.html
|       `-- static/
|           |-- css/app.css
|           `-- js/app.js
|
|-- models/
|   |-- best_model.joblib
|   `-- metadata.json
|
|-- reports/
|   |-- experiments.csv
|   |-- metrics/
|   |-- confusion_matrices/
|   `-- figures/
|
|-- tests/
|   |-- test_data.py
|   |-- test_inference.py
|   |-- test_api.py
|   `-- test_database.py
|
`-- scripts/
    |-- run_experiments.py
    |-- train_best_model.py
    `-- init_db.py
```

---

## 10. Preparação dos dados

### 10.1 Validações mínimas

Antes do treinamento:

- remover registros sem título e sem conteúdo;
- remover duplicados exatos;
- padronizar os nomes das categorias;
- unir título e corpo em um campo textual controlado;
- remover apenas ruídos óbvios de HTML/whitespace;
- evitar limpeza agressiva que destrua informação linguística;
- registrar quantos registros foram removidos em cada etapa.

Formato sugerido para o texto enviado ao vetorizador:

```text
[TITULO] Banco Central mantém taxa de juros
[TEXTO] O Comitê de Política Monetária anunciou...
```

### 10.2 Split dos dados

Usar divisão estratificada para manter proporções semelhantes de classes. Sugestão inicial:

- 70% treino;
- 15% validação;
- 15% teste final.

O conjunto de teste deve permanecer isolado até a avaliação final do modelo. Ajustes de hiperparâmetros não devem usar o teste.

### 10.3 Prevenção de vazamento de dados

TF-IDF e classificador devem ser encapsulados em `sklearn.pipeline.Pipeline`. O `fit` do TF-IDF deve acontecer somente sobre o conjunto de treinamento de cada experimento.

Não vetorizar o dataset completo antes do split.

---

## 11. Representação textual

Utilizar inicialmente `TfidfVectorizer`.

Parâmetros a experimentar de forma controlada:

```python
TfidfVectorizer(
    lowercase=True,
    strip_accents=None,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    max_features=None,
    sublinear_tf=True
)
```

Não assumir que todos esses valores são ótimos. Eles constituem apenas uma configuração inicial. Registrar qualquer alteração nos experimentos.

Stopwords em português podem ser avaliadas como uma variável adicional, mas não devem ser adicionadas automaticamente sem comparação, pois certas palavras funcionais podem carregar sinal útil dependendo do corpus.

---

## 12. Modelos a comparar

### Modelo 1 - Multinomial Naive Bayes

Baseline rápido e tradicional para classificação textual.

### Modelo 2 - Logistic Regression

Modelo linear forte para vetores TF-IDF e com suporte nativo a `predict_proba`.

### Modelo 3 - Linear SVM

Usar `LinearSVC` para o benchmark principal. Caso seja escolhido para a aplicação, envolver o classificador em `CalibratedClassifierCV` para gerar probabilidades calibradas e permitir exibição de confiança.

### Modelo 4 - Random Forest

Pode ser mantido como comparação adicional, mas deve ser tratado como secundário porque matrizes TF-IDF são esparsas e de alta dimensionalidade. Se o custo for excessivo ou o desempenho claramente inferior, documentar isso como resultado experimental em vez de forçar sua adoção.

---

## 13. Experimentos obrigatórios

Para cada cenário de 4, 7 e 10 categorias:

1. Treinar os modelos definidos.
2. Registrar tempo de treinamento.
3. Registrar tempo médio de inferência.
4. Calcular accuracy.
5. Calcular precision macro e weighted.
6. Calcular recall macro e weighted.
7. Calcular F1 macro e weighted.
8. Gerar relatório por classe.
9. Gerar matriz de confusão absoluta.
10. Gerar matriz de confusão normalizada.
11. Registrar quantidade de exemplos por classe.
12. Repetir, quando aplicável, com `class_weight="balanced"`.

Todos os resultados devem ser persistidos em CSV ou JSON para posterior inclusão no TCC.

Formato mínimo de `reports/experiments.csv`:

```text
experiment_id
scenario
n_classes
model
class_weight
tfidf_config
train_samples
validation_samples
test_samples
accuracy
precision_macro
recall_macro
f1_macro
precision_weighted
recall_weighted
f1_weighted
train_seconds
inference_ms_mean
random_state
created_at
```

---

## 14. Critério para seleção do modelo de produção

Não selecionar automaticamente o modelo com maior accuracy.

Critérios de decisão:

1. F1 macro no conjunto de validação/teste;
2. estabilidade do desempenho entre classes;
3. matriz de confusão;
4. custo de inferência;
5. capacidade de produzir confiança calibrada;
6. tamanho do artefato do modelo;
7. simplicidade operacional.

O modelo escolhido deve ser salvo junto com seus metadados:

```json
{
  "model_name": "logistic_regression",
  "version": "1.0.0",
  "scenario": "10_classes",
  "categories": ["..."],
  "f1_macro": 0.0,
  "accuracy": 0.0,
  "trained_at": "ISO-8601",
  "dataset_version": "local-v1",
  "random_state": 42
}
```

---

## 15. Serviço de inferência

Criar uma classe única de inferência, por exemplo `NewsClassifier`, responsável por:

- carregar o pipeline salvo;
- validar título e texto;
- concatenar os campos no mesmo formato usado no treinamento;
- retornar categoria principal;
- retornar top 3 categorias quando houver probabilidades;
- retornar confiança;
- retornar versão do modelo;
- evitar que a API conheça detalhes internos do scikit-learn.

Interface conceitual:

```python
result = classifier.predict(
    title="Banco Central mantém taxa de juros",
    content="O Comitê de Política Monetária..."
)
```

Resposta esperada:

```python
{
    "category": "Economia",
    "confidence": 0.94,
    "top_k": [
        {"category": "Economia", "confidence": 0.94},
        {"category": "Política", "confidence": 0.04},
        {"category": "Mundo", "confidence": 0.02}
    ],
    "model_version": "1.0.0"
}
```

---

## 16. API REST

### GET `/health`

Retorna estado da aplicação e se o modelo foi carregado.

Resposta:

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "1.0.0"
}
```

### POST `/api/classify`

Entrada:

```json
{
  "title": "Banco Central mantém taxa Selic",
  "content": "O Comitê de Política Monetária..."
}
```

Saída:

```json
{
  "predicted_category": "Economia",
  "confidence": 0.94,
  "top_k": [
    {"category": "Economia", "confidence": 0.94},
    {"category": "Política", "confidence": 0.04},
    {"category": "Mundo", "confidence": 0.02}
  ],
  "model_version": "1.0.0"
}
```

### POST `/api/articles`

Salva a notícia após o editor aceitar ou corrigir a sugestão.

Entrada mínima:

```json
{
  "title": "...",
  "content": "...",
  "predicted_category": "Economia",
  "predicted_confidence": 0.94,
  "final_category": "Economia",
  "was_corrected": false,
  "model_version": "1.0.0"
}
```

### GET `/api/articles`

Permite visualizar histórico e comparar classificação automática com decisão final humana.

---

## 17. Banco de dados

### Tabela `articles`

Campos sugeridos:

```text
id                  INTEGER / UUID
created_at          DATETIME
title               TEXT
content             TEXT
predicted_category  TEXT
predicted_confidence REAL
final_category      TEXT
was_corrected       BOOLEAN
model_version       TEXT
```

### Tabela opcional `prediction_candidates`

Permite armazenar top 3 por previsão:

```text
id
article_id
category
confidence
rank
```

Para o MVP, SQLite é suficiente. A camada de acesso deve permitir futura troca por PostgreSQL sem alterar a lógica de Machine Learning.

---

## 18. Interface web do portal

### Tela principal

Campos:

- Título da notícia;
- Conteúdo da notícia;
- botão `Analisar notícia`;
- categoria sugerida;
- percentual de confiança;
- top 3 categorias;
- seletor para categoria final;
- botão `Salvar/Publicar`.

Comportamento esperado:

```text
1. Usuário preenche título e conteúdo.
2. Clica em "Analisar notícia".
3. Frontend chama POST /api/classify.
4. Resultado é exibido sem salvar automaticamente.
5. Usuário aceita ou altera a categoria.
6. Frontend chama POST /api/articles.
7. Sistema registra previsão e decisão humana.
```

### Regras de confiança da interface

A confiança não deve ser apresentada como garantia de correção. Usar apenas como sinal operacional.

Faixas iniciais para UX, configuráveis:

```text
>= 0.85       Alta confiança
0.65 - 0.849  Revisão recomendada
< 0.65        Classificação incerta
```

Essas faixas são regras de interface, não conclusões científicas, e podem ser alteradas após avaliar a calibração real do modelo.

### Tela de histórico

Exibir:

- data;
- título;
- categoria prevista;
- confiança;
- categoria final;
- indicador de correção humana.

Adicionar filtros por categoria e por `was_corrected` se isso não aumentar excessivamente o escopo.

---

## 19. Feedback humano

O sistema deve registrar quando:

```text
predicted_category != final_category
```

Isso permitirá calcular posteriormente:

- taxa de aceitação das sugestões;
- taxa de correção por categoria;
- pares de classes mais corrigidos;
- exemplos reais em que o modelo demonstrou incerteza.

O MVP **não precisa realizar retreinamento automático**. O feedback deve apenas ser armazenado. Retreinamento com feedback humano entra como trabalho futuro ou extensão opcional.

---

## 20. Reprodutibilidade

Todas as execuções de treinamento devem utilizar `random_state=42` quando o algoritmo suportar.

Criar comandos reproduzíveis, por exemplo:

```bash
python scripts/run_experiments.py --config configs/categories_4.yaml
python scripts/run_experiments.py --config configs/categories_7.yaml
python scripts/run_experiments.py --config configs/categories_10.yaml
python scripts/train_best_model.py --config configs/categories_10.yaml --model logistic_regression
```

A configuração deve registrar:

```yaml
scenario: categories_10
random_state: 42
text_column: combined_text
label_column: category
categories:
  - politica
  - economia
  - esportes
  - mundo
  - tecnologia
  - ciencia
  - saude
  - educacao
  - entretenimento
  - turismo
split:
  train: 0.70
  validation: 0.15
  test: 0.15
```

O arquivo real deverá utilizar os nomes mapeados após a inspeção do dataset.

---

## 21. Testes mínimos

### Dados

- dataset sem categoria deve falhar com mensagem clara;
- registros sem texto devem ser tratados;
- categorias desconhecidas devem ser detectadas;
- split deve preservar classes.

### Inferência

- modelo carrega com sucesso;
- título + conteúdo válidos retornam uma categoria conhecida;
- entrada vazia retorna erro de validação;
- top 3 não contém categorias duplicadas;
- confiança está entre 0 e 1 quando disponível.

### API

- `/health` retorna 200;
- `/api/classify` retorna 200 para payload válido;
- `/api/classify` retorna 422 para payload inválido;
- `/api/articles` persiste decisão final;
- histórico retorna dados persistidos.

### Banco

- inserção de artigo;
- recuperação de histórico;
- persistência correta de `was_corrected`.

---

## 22. Critérios de aceite do MVP

O MVP está concluído quando:

- o dataset pode ser preparado por script;
- os cenários de 4, 7 e 10 classes podem ser executados de forma reproduzível;
- pelo menos três classificadores são comparados;
- métricas e matrizes de confusão são salvas em `reports/`;
- um modelo final é exportado com metadados;
- a aplicação FastAPI inicia sem notebook;
- o portal recebe título e conteúdo;
- o modelo retorna uma categoria e confiança quando suportada;
- o editor pode alterar a categoria;
- a previsão e a categoria final ficam salvas no banco;
- há testes automatizados para os fluxos principais;
- o README permite executar o projeto em uma máquina limpa com VS Code e Python.

---

## 23. Etapas de implementação para o Codex

### Fase 0 - Bootstrap do projeto

Entregas:

- criar estrutura de diretórios;
- `.gitignore` adequado para Python, VS Code, dados e modelos grandes;
- `requirements.txt`;
- README inicial;
- ambiente virtual documentado;
- teste básico de importação.

Não implementar a interface ainda.

### Fase 1 - Inspeção e preparação do dataset

Entregas:

- script `inspect_dataset.py`;
- relatório de distribuição das categorias;
- script `prepare_dataset.py`;
- mapeamento configurável de categorias;
- dados processados reproduzíveis.

Bloqueio: não avançar para o treinamento sem confirmar os nomes e volumes reais das classes.

### Fase 2 - Pipeline de Machine Learning

Entregas:

- TF-IDF em `Pipeline`;
- implementações dos classificadores;
- split estratificado;
- função de treinamento comum;
- persistência de resultados.

### Fase 3 - Framework experimental

Entregas:

- execução automatizada 4/7/10 classes;
- CSV consolidado;
- classification reports;
- matrizes de confusão;
- tempos de treino e inferência;
- comparação com e sem pesos de classe quando aplicável.

### Fase 4 - Seleção e empacotamento do melhor modelo

Entregas:

- script para treinar configuração final;
- `best_model.joblib`;
- `metadata.json`;
- classe `NewsClassifier`;
- testes de inferência.

### Fase 5 - API

Entregas:

- FastAPI;
- `/health`;
- `/api/classify`;
- schemas Pydantic;
- tratamento de erros;
- testes de API.

### Fase 6 - Banco e feedback editorial

Entregas:

- SQLAlchemy;
- SQLite;
- entidade de artigo;
- endpoints de salvamento e histórico;
- registro de correções humanas.

### Fase 7 - Portal web

Entregas:

- tela editorial;
- chamada assíncrona ao classificador;
- exibição top 3;
- seletor de categoria final;
- salvamento;
- histórico básico.

### Fase 8 - Qualidade e documentação

Entregas:

- pytest completo;
- README final;
- comandos de reprodução;
- screenshots opcionais;
- descrição da arquitetura;
- documentação das limitações.

---

## 24. Comandos de ambiente no Windows / VS Code

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Executar testes:

```powershell
pytest -q
```

Executar aplicação:

```powershell
uvicorn src.api.main:app --reload
```

Acessar localmente:

```text
http://127.0.0.1:8000
```

---

## 25. Dependências iniciais sugeridas

```text
pandas
numpy
scikit-learn
joblib
matplotlib
fastapi
uvicorn[standard]
jinja2
sqlalchemy
pydantic
python-multipart
pytest
httpx
pyyaml
```

Evitar adicionar bibliotecas sem necessidade. O agente deve preferir a biblioteca padrão quando suficiente.

---

## 26. Regras de implementação para o agente Codex

1. Implementar em fases pequenas e testáveis.
2. Não criar componentes que não estejam justificados pelo escopo.
3. Não transformar notebook em dependência de produção.
4. Centralizar configurações de categorias e experimentos em YAML/JSON.
5. Evitar valores mágicos espalhados pelo código.
6. Usar type hints nas funções públicas.
7. Escrever docstrings curtas para componentes relevantes.
8. Criar tratamento explícito para ausência do arquivo do dataset e ausência do modelo treinado.
9. Não versionar dataset bruto, banco local, `.venv`, artefatos grandes ou segredos.
10. Salvar pipeline completo TF-IDF + classificador, não apenas o estimador.
11. Nunca ajustar TF-IDF usando dados de teste.
12. Não selecionar modelo apenas por accuracy.
13. Manter separação clara entre código de experimento e código da aplicação.
14. Antes de alterar arquitetura ou dependências principais, documentar a justificativa.
15. Após cada fase, executar testes e atualizar o README com o estado real do projeto.

---

## 27. O que fica fora do MVP

Para evitar expansão excessiva de escopo, não implementar inicialmente:

- autenticação de usuários;
- níveis de permissão;
- publicação em um portal real;
- web scraping contínuo;
- retreinamento automático;
- filas assíncronas;
- Kubernetes;
- microserviços separados;
- React/Next.js;
- LLMs para classificação;
- BERT/Transformers como requisito obrigatório;
- classificação multilabel;
- sistema completo de recomendação.

Esses itens podem ser tratados como trabalhos futuros.

---

## 28. Extensões opcionais após o MVP

Somente após o MVP estar funcional e testado:

### Extensão A - BERT em português

Comparar o melhor pipeline TF-IDF com um Transformer pré-treinado em português. Essa extensão deve ser considerada um experimento adicional, não requisito para concluir o projeto.

### Extensão B - Classificação multilabel

Permitir que uma notícia receba mais de uma categoria, por exemplo `Tecnologia + Ciência + Saúde`.

### Extensão C - Active learning / feedback

Priorizar para revisão humana notícias com menor confiança e utilizar correções futuras como exemplos rotulados.

### Extensão D - Monitoramento de drift

Comparar a distribuição de categorias e vocabulário de notícias novas com o corpus de treinamento.

### Extensão E - Docker

Empacotar a aplicação apenas depois que treinamento, testes, API e portal estiverem estáveis localmente.

---

## 29. Resultados esperados para apresentação acadêmica

Ao final, o projeto deve produzir material suficiente para apresentar:

- distribuição das classes do dataset;
- comparação de 4, 7 e 10 categorias;
- comparação entre algoritmos;
- impacto de classes desbalanceadas;
- F1-score macro e weighted;
- precision e recall por classe;
- matrizes de confusão;
- categorias que mais se confundem;
- tempo de treinamento;
- tempo de inferência;
- demonstração do portal;
- exemplos de classificação correta;
- exemplos de classificação ambígua;
- exemplos em que o editor corrigiu o modelo.

O valor acadêmico principal não deve ser apenas a interface. A interface comprova aplicabilidade; a contribuição experimental está na avaliação sistemática dos classificadores e das diferentes granularidades de categorias.

---

## 30. Possível título do TCC

**Desenvolvimento e Avaliação de um Sistema de Machine Learning para Classificação Automática de Notícias em Portais Digitais**

Alternativa com foco experimental:

**Análise do Impacto da Granularidade e do Desbalanceamento de Classes na Classificação Automática de Notícias em Língua Portuguesa**

---

## 31. Prompt inicial recomendado para o Codex

Copiar o texto abaixo para iniciar a implementação:

```text
Você atuará como agente de implementação deste projeto de TCC no VS Code.

Leia integralmente o documento Plano_TCC_Classificador_Noticias_Codex.md antes de modificar qualquer arquivo.

Objetivo: implementar um sistema de classificação automática de notícias em português, com pipeline experimental de Machine Learning e uma prova de conceito de portal editorial usando FastAPI.

Regras:
- siga as fases descritas no documento em ordem;
- implemente apenas uma fase por vez;
- não pule diretamente para a interface;
- mantenha o treinamento reproduzível;
- use Pipeline do scikit-learn para evitar data leakage;
- não use o conjunto de teste para ajuste de hiperparâmetros;
- não versione o dataset bruto;
- mantenha o foco do projeto em ML, não em complexidade de frontend;
- escreva testes para cada componente principal;
- ao final de cada fase, execute os testes e informe exatamente o que foi criado, o que foi validado e o que ainda falta.

Comece pela Fase 0. Antes de escrever código, apresente uma lista curta dos arquivos que serão criados nessa fase e a justificativa de cada um. Em seguida, implemente a Fase 0 e rode os testes aplicáveis.
```

---

## 32. Definição de sucesso do projeto

O projeto será considerado tecnicamente bem sucedido se conseguir demonstrar, de forma reproduzível, como diferentes algoritmos e diferentes quantidades de categorias afetam a classificação de notícias em português e, adicionalmente, integrar o modelo selecionado a um fluxo editorial funcional no qual a decisão final permanece com o usuário humano.
