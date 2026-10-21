# Registro da validação da entrega

## Ambiente

Windows, Python 3.14.3; dependências fixadas em `requirements-lock.txt`. O arquivo Parquet recebido tem SHA-256 `de4907dc2c2a45c0deea9a5890829caa90befec57f3bb8631cc6685afb4c6c3b`. O conteúdo original foi somente lido.

## Testes automatizados

`python -m pytest -q`: **21 testes aprovados**. Cobertura dos fluxos: leitura CSV/Parquet, limpeza, deduplicação, rótulos conflitantes/desconhecidos, volumes mínimos, partições reproduzíveis, isolamento do vocabulário, calibração do pipeline, integridade do artefato, inferência, seleção por validação, bloqueio de reavaliação final, API, confirmação editorial, persistência e recuperação após reinício.

A execução apresentou dois avisos de depreciação nas dependências de teste Starlette/AnyIO, sem falhas. `pip check` não encontrou incompatibilidades; `compileall` e a checagem de sintaxe JavaScript passaram.

## Experimentos reais

- 167.053 registros inspecionados; 48 rótulos originais.
- 21 experimentos: quatro algoritmos e sete combinações de modelo/pesos em cada cenário.
- 79.803, 84.704 e 104.331 notícias preparadas nos cenários de 4, 7 e 10 classes.
- Resultados por classe, matrizes absolutas/normalizadas, erros e tempos persistidos por execução.
- Auditoria dos arquivos reais: sem duplicação interna, sem sobreposição entre treino/validação/teste e com partições consistentes para classes compartilhadas entre cenários. Evidência: `reports/split_audit.json`.
- Seleção pela validação, seguida de calibração da SVM e reajuste em treino + validação. O teste final do cenário de dez classes contém 15.654 notícias e não foi usado para seleção.

## Modelo final

SVM linear balanceada, calibrada por sigmoide em três folds com o TF-IDF dentro de cada fold. Versão `0ed06db95acf`, exportada em `models/production`.

| Métrica de teste | Resultado |
|---|---:|
| F1 macro | 0,8955 |
| F1 weighted | 0,9430 |
| Accuracy | 94,32% |
| Precision macro | 0,9049 |
| Recall macro | 0,8869 |
| Log-loss | 0,1806 |
| Brier multiclasse | 0,0864 |
| Inferência individual média | 7,61 ms |
| Tamanho do artefato | 16,58 MiB |

Metadados, hash do artefato, configuração e valores completos: `models/production/metadata.json`. Resultados acadêmicos e ressalvas: `reports/RESULTADOS.md`. As medidas de latência são locais e não representam teste de carga.

## Verificação do portal

Comando executado com sucesso:

```powershell
python -m scripts.check_ui --model-dir models/production --screenshots docs/screenshots/production
```

Microsoft Edge em modo headless; resolução desktop 1440 × 1050 e mobile 390 × 844. O teste verificou: carregamento do modelo, top 3, exigência de confirmação, alteração da categoria, salvamento, histórico, filtros, invalidação após editar o texto, ausência de rolagem horizontal global no mobile e ausência de erros JavaScript. Capturas em `docs/screenshots/production/`.

O banco usado pelo teste é temporário, e o servidor de teste foi encerrado. Para abrir o portal normalmente, execute o comando do README; ele criará o banco editorial local.

## Feed de notícias — atualização de 21/10/2026

`python -m pytest -q`: **28 testes aprovados**, com dois avisos de depreciação das dependências de teste. A cobertura adicional verifica exemplos sem gravação no banco/feedback, busca, filtros, paginação entre notícias locais e exemplos, ausência de duplicação entre páginas, confirmação obrigatória antes da exibição, uso da categoria final, escape de HTML e respostas 404. O feed e a leitura também funcionam sem modelo carregado.

```powershell
python -m scripts.check_ui --model-dir models/production --screenshots docs/screenshots/feed
```

Verificação aprovada no Edge em desktop (1440 × 1050) e mobile (390 × 844): busca, filtro por editoria, paginação, leitura de exemplos, estado vazio, navegação à mesa editorial, análise, confirmação, correção, histórico, notícia confirmada no feed e invalidação após edição. Sem erros JavaScript ou rolagem horizontal global nas telas mobile verificadas. Banco temporário, sem modificar o banco do usuário ou os artefatos de pesquisa.

Capturas: [feed desktop](screenshots/feed/feed-desktop.png), [feed mobile](screenshots/feed/feed-mobile.png) e [leitura](screenshots/feed/reading-desktop.png). Os registros anteriores de treinamento e validação permanecem válidos; não houve novo treinamento para esta interface.

## Edição e remoção no histórico — 21/10/2026

`python -m pytest -q`: **33 testes aprovados**, com os mesmos dois avisos de depreciação das dependências de teste. `node --check src/web/static/js/app.js` também passou.

Verificados: atualização do texto pela nova análise, categoria final, confirmação obrigatória, rejeição de campos adulterados, análise já usada por outra notícia, conflitos de revisão, alteração de categoria sem modelo carregado, remoção sem modelo, atualização do feed e feedback, respostas 404 e persistência de edição/exclusão após reiniciar. A data de criação continua a mesma; a API serializa datas em UTC de forma consistente.

```powershell
python -m scripts.check_ui --model-dir models/production --screenshots docs/screenshots/history-management
```

Fluxo aprovado no Edge: cancelar uma edição sem alterar o registro; editar texto, analisar e confirmar; verificar a matéria atualizada no feed; cancelar a remoção por botão e Escape; confirmar a exclusão em mobile; remover a única linha da última página e retornar à anterior. Verificações feitas com banco temporário, sem editar/remover notícias do usuário. O fluxo anterior de criação e navegação também passou.

Capturas: [ações no histórico](screenshots/history-management/history-actions-desktop.png), [edição](screenshots/history-management/edit-desktop.png) e [confirmação da remoção em mobile](screenshots/history-management/delete-mobile.png).

## Limites

Uma execução com semente 42 não fornece intervalo de confiança. Quase duplicados, dependência temporal, outras fontes jornalísticas e conteúdos fora da taxonomia ainda precisam de avaliação específica. A calibração foi aplicada, mas probabilidades não são garantias de acerto. Nenhuma configuração foi ajustada com base no teste final.
