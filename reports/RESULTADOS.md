# Resultados no dataset recebido

Uma execução com semente 42. Seleção feita exclusivamente na validação de cada cenário.

| Classes | Modelo | Pesos | F1 macro validação | Accuracy validação | Treino / validação / teste |
|---:|---|---|---:|---:|---|
| categories_4 | linear_svm | none | 0.9662 | 0.9656 | 55860 / 11971 / 11972 |
| categories_7 | linear_svm | balanced | 0.8975 | 0.9496 | 59289 / 12707 / 12708 |
| categories_10 | linear_svm | balanced | 0.8906 | 0.9419 | 73027 / 15650 / 15654 |

## Avaliação final do cenário de dez classes

Modelo: **linear_svm**; versão `0ed06db95acf`.

- F1 macro: **0.8955**.
- F1 weighted: **0.9430**.
- Accuracy: **0.9432**.
- Inferência individual média: **7.61 ms** (até 100 exemplos).
- Artefato: **16.58 MiB**.

O teste foi consultado apenas após seleção. Não houve ajuste em função das métricas finais. As métricas não estimam qualidade de notícias futuras nem de categorias ausentes.

## Maiores confusões no teste

| Real | Prevista | Quantidade |
|---|---|---:|
| Política | Economia | 112 |
| Economia | Política | 89 |
| Tecnologia | Economia | 62 |
| Economia | Tecnologia | 57 |
| Mundo | Economia | 42 |
| Economia | Mundo | 39 |
| Política | Mundo | 33 |
| Entretenimento | Mundo | 30 |
| Mundo | Entretenimento | 29 |
| Política | Entretenimento | 21 |

## Limites de interpretação

Adicionar categorias altera volume e composição além da dificuldade. Uma única semente não fornece intervalo de confiança. Duplicados exatos foram tratados; notícias quase duplicadas e dependência temporal ainda exigem auditoria. Resultados não confirmam automaticamente causalidade, H1–H4 ou calibração perfeita.

Os gráficos estão em `figures/`, a tabela completa em `experiments.csv`, a comparação de pesos por categoria em `weight_effects.csv`, e os relatórios por classe e matrizes nas pastas listadas em `research_runs.json`.
