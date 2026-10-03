# Revisão do plano e protocolo implementado

O documento original propõe uma separação adequada entre pesquisa de ML e prova de conceito editorial. Esta revisão mantém TF-IDF, classificadores tradicionais, FastAPI, Jinja2 e SQLite. Não inclui publicação externa, autenticação ou retreinamento automático.

## Ajustes metodológicos

1. **Escolha por validação, nunca pelo teste.** A seção 14 original menciona validação/teste como critério. O protocolo implementado usa somente F1 macro de validação, dentro de cada cenário. O teste fica para o vencedor, após treino em treino + validação. A exportação registra a avaliação final e recusa sobrescrever o resultado. Reexecuções não tornam o teste novo: não usar seu resultado para ajustar o protocolo.
2. **Quantidade de classes não isola similaridade semântica.** Adicionar classes muda também a composição do corpus, o tamanho do treino e a dificuldade. A pesquisa mede o efeito conjunto nos subconjuntos definidos. Uma afirmação causal exigiria controle adicional de volume por classe e definição independente de similaridade. Confusão observada, sozinha, não prova similaridade semântica.
3. **Partições consistentes entre cenários.** Cada classe é ordenada por hash textual e dividida com a mesma semente. As classes compartilhadas mantêm seus exemplos nas mesmas partições em 4/7/10 categorias. O arredondamento pode afastar os percentuais de 70/15/15 em classes pequenas; os volumes efetivos são registrados.
4. **Duplicados antes do split.** Textos idênticos após limpeza e normalização de caixa são deduplicados; todos os registros de um texto com rótulos conflitantes são removidos e contados. Notícias quase duplicadas, republicações e evolução temporal ainda podem causar otimismo. Antes de conclusões acadêmicas, auditar similaridade e considerar avaliação temporal ou agrupamento por evento.
5. **Categorias verificadas no arquivo.** As configurações só foram confirmadas após inspecionar o Parquet enviado: 167.053 registros e 48 rótulos. O mapeamento global dos três cenários está em `data/MAPEAMENTO_FOLHA.md`. Rótulos desconhecidos geram erro; exclusões precisam de mapeamento explícito para `null`.
6. **SVM com calibração sem vazamento de vocabulário.** LinearSVC participa do benchmark; caso vença, a calibração envolve o pipeline inteiro em três folds. A validação da versão calibrada também é registrada antes do teste, mas não usada para escolher novamente após observar o teste. NB, regressão logística e floresta usam probabilidades nativas, que não são presumidas calibradas. Log-loss e Brier multiclasse complementam as métricas de classificação nos modelos probabilísticos.
7. **Seleção operacional explícita.** O MVP automatiza F1 macro; empate usa identificador estável. Relatórios por classe, latência individual, tamanho de artefato e calibração permitem discussão das compensações. Não há índice arbitrário misturando essas medidas e nenhum vencedor é escolhido entre cenários com taxonomias diferentes.
8. **Reprodutibilidade.** Semente 42, hash do arquivo de dados, hash do artefato, versões das bibliotecas, configuração efetiva e partições são persistidos. Latência é medida individualmente em até 100 exemplos e por lote; são medidas locais, sem teste de carga nem intervalo de confiança. O pipeline usa cache de vetorização por execução: tempos de treino posteriores podem incluir reaproveitamento de TF-IDF, e não são comparações puras de tempo total de cada algoritmo desde o texto bruto.

9. **Ajuste de recursos documentado antes do benchmark real.** TF-IDF mantém unigramas/bigramas e `min_df=2`, mas limita o vocabulário a 50.000 atributos e usa `float32`. Random Forest, comparação secundária, usa 50 árvores e profundidade máxima 30, com dois workers. A máquina tem 16 GB de RAM compartilhados com outros aplicativos. Não houve busca de hiperparâmetros baseada no teste. PyArrow foi acrescentado porque o arquivo enviado é Parquet.

## Ajustes do fluxo editorial

- `/api/classify` registra a previsão em uma tabela própria; isso não cria uma notícia confirmada.
- `/api/articles` recebe `prediction_id`, `final_category` e `confirmed`. Os valores de previsão, confiança, texto e versão vêm do servidor. `was_corrected` é calculado pelo servidor. Isso substitui o payload do plano que permitia ao cliente informar o próprio histórico do modelo.
- Uma previsão admite uma decisão salva. Alterar o texto na interface invalida a sugestão. O histórico preserva a versão e o indicador de demonstração.
- O botão é **Salvar decisão**: não existe integração com publicação. A interface exige confirmação humana explícita.
- As faixas de confiança são configuráveis e têm função de interface; não significam precisão científica garantida.

## Situação da entrega

As fases de infraestrutura, preparação, treinamento, experimentos, empacotamento, API, persistência, portal e testes foram concluídas. A execução sintética verifica engenharia, não valida hipóteses de pesquisa. Os 21 experimentos reais e a exportação final foram concluídos, com rastreabilidade em `reports/research_runs.json` e síntese em `reports/RESULTADOS.md`. O modelo real foi validado no fluxo editorial em navegador desktop/mobile. A auditoria dos CSVs confirmou partições disjuntas e consistência dos exemplos das classes compartilhadas entre cenários.

O ambiente disponível tem Python 3.14.3. As dependências foram instaladas e os testes executados nele. O plano citava Python 3.12; não se afirma validação em 3.12. `requirements-lock.txt` registra o ambiente efetivamente utilizado.

## Limitações e próxima etapa acadêmica

- Nomes e volumes reais inspecionados; mapeamentos revisados antes do treino.
- Verificar origem e condições aplicáveis ao arquivo utilizado; o corpus não é redistribuído neste projeto.
- Definir limiar de volume cientificamente adequado. O mínimo técnico de 20 por classe serve apenas para impedir splits inviáveis, não garante estimativas confiáveis.
- Executar os três cenários e interpretar métricas por classe, erros e comparação de pesos.
- Uma única semente não estima variabilidade. Repetições ou validação cruzada externa, intervalos de confiança e análise temporal são extensões metodológicas recomendadas antes de generalizações.
- Não há detector de notícias fora da taxonomia; probabilidades altas podem ocorrer fora da distribuição de treino.
- Feedback editorial não é amostra aleatória nem verdade infalível. O endpoint de feedback agrega decisões locais, inclusive demonstrações identificadas; a análise científica deve separar essas origens.
- Aplicação destinada a uso local. Sem autenticação, não é um serviço editorial público.

## Referências verificadas

- [Dataset original no Kaggle](https://www.kaggle.com/datasets/marlesson/news-of-the-site-folhauol): fonte indicada pelo plano; a inspeção local continua obrigatória.
- [CalibratedClassifierCV — documentação oficial](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV): calibração por folds com estimadores, incluindo pipelines.
- [Pipelines — documentação oficial](https://scikit-learn.org/stable/modules/compose.html): composição de transformações e estimadores.
