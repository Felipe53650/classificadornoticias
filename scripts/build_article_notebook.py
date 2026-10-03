"""Monta notebook autossuficiente a partir da fonte única das figuras."""
import json
from pathlib import Path


def build_notebook(root: Path) -> Path:
    cells = []
    def cell(kind: str, source: str):
        item = {"cell_type": kind, "id": f"artigo-{len(cells):02}", "metadata": {}, "source": source.strip().splitlines(keepends=True)}
        if kind == "code":
            item.update(execution_count=None, outputs=[])
        cells.append(item)

    cell("markdown", """
# Figuras e tabelas do artigo — Classificador de notícias

Este notebook apresenta os **resultados reais já calculados**. Não treina modelos,
não reavalia o teste e não exige GPU, dataset, banco de dados ou arquivo joblib.

**Como usar no Google Colab:**
1. Abra este `.ipynb` em **Arquivo → Fazer upload de notebook**.
2. Use **Ambiente de execução → Executar tudo** (os nomes variam conforme o idioma).
3. Quando solicitado, envie **`dados_artigo.zip`**, localizado em `reports/artigo/` no projeto.
4. Veja as figuras e baixe **`saida_artigo.zip`** na última célula.

O pacote contém somente métricas, contagens, parâmetros e proveniência dos experimentos.
As funções estão incluídas neste notebook: não é preciso copiar o código do projeto.
Dependências: NumPy, pandas e Matplotlib. Se executar fora do Colab e faltarem bibliotecas,
instale-as com `%pip install numpy pandas matplotlib` em uma célula separada.

**Leitura científica:** a comparação dos algoritmos usa validação; o teste final é
apresentado separadamente e corresponde à SVM calibrada. Não há intervalos de confiança
porque foi usada uma única semente. Adicionar categorias também mudou volume e composição.
""")
    cell("markdown", "## 1. Funções de geração\nExecute esta célula. Ela concentra as funções usadas nas demais seções; você pode ajustar estilos e textos aqui.")
    module = (root / "scripts/article_figures.py").read_text(encoding="utf-8")
    cell("code", module.rsplit('\nif __name__ == "__main__":', 1)[0])
    cell("markdown", "## 2. Carregar o pacote de resultados\nNo Colab, será exibido um seletor de arquivo. A leitura verifica o formato do pacote e não extrai seu conteúdo no sistema.")
    cell("code", """
try:
    from google.colab import files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

BUNDLE = Path("dados_artigo.zip")
if IN_COLAB and not BUNDLE.is_file():
    uploaded = files.upload()
    candidates = [name for name in uploaded if name.lower().endswith(".zip")]
    if len(candidates) != 1:
        raise ValueError("Selecione apenas o arquivo dados_artigo.zip.")
    BUNDLE = Path(candidates[0])
elif not IN_COLAB and not BUNDLE.is_file():
    candidates = [Path("reports/artigo/dados_artigo.zip"), Path("../reports/artigo/dados_artigo.zip")]
    BUNDLE = next((p for p in candidates if p.is_file()), BUNDLE)

experiments, research = load_results(BUNDLE)
OUTPUT = Path("saida_artigo")
FIGURES = OUTPUT / "figuras"
DPI = 300  # resolução apenas dos arquivos PNG; PDF e SVG são vetoriais
SHOW = True
configure_style(font_size=11)
print(f"Pacote: {BUNDLE}; criado em {research['created_at']}")
print(f"{len(experiments)} experimentos; cenários: {sorted(experiments.n_classes.unique())}")
print("Modelo final:", final_scenario(research)["final"]["metadata"]["version"])
""")
    cell("markdown", "## 3. Tabelas comparativas e resultados numéricos\nSerão exportadas oito tabelas em CSV, Markdown e LaTeX. A tabela de tempos contém uma ressalva: o cache de TF-IDF impede interpretar os tempos de treino como custos integrais uniformemente comparáveis.")
    cell("code", """
from IPython.display import display
tables = build_tables(experiments, research, OUTPUT)
display(tables["01_comparacao_validacao"])
display(tables["03_tamanhos_particoes"])
display(tables["06_metricas_teste_final"])
display(tables["07_por_classe_teste_final"])
""")
    sections = [
        ("4. Distribuição das classes", "Contagens após preparação no cenário de dez categorias. Este gráfico evidencia o desbalanceamento.", "plot_distribution(research, FIGURES, SHOW, DPI)"),
        ("5. Comparação dos modelos", "Cada curva mantém modelo e estratégia de pesos. Todos os valores são de validação; as linhas conectam somente os três cenários observados.", "plot_comparison(experiments, FIGURES, SHOW, DPI)"),
        ("6. Efeito do balanceamento", "Diferença em pontos percentuais: F1 macro balanceado menos F1 macro sem pesos. Valores positivos indicam melhora nesta execução; não representam significância estatística.", "plot_weight_effect(experiments, FIGURES, SHOW, DPI)\ndisplay(tables['05_efeito_pesos_por_classe'])"),
        ("7. Matriz de confusão no teste reservado", "Modelo final de dez classes, balanceado e calibrado. Prefira a matriz normalizada no texto do artigo para comparar classes com suportes diferentes. A matriz absoluta também será exportada.", "plot_final_confusion(research, FIGURES, True, SHOW, DPI)\nplot_final_confusion(research, FIGURES, False, SHOW, DPI)"),
        ("8. Desempenho por categoria", "Precision, recall e F1 calculados no teste final. A tabela correspondente inclui o suporte de cada categoria.", "plot_final_classes(research, FIGURES, SHOW, DPI)"),
        ("9. Latência observada", "Até 100 previsões individuais por configuração, na validação de dez classes. A SVM do benchmark ainda não é calibrada. O tempo da SVM calibrada está separado na tabela do teste final. Não é teste de carga nem comparação entre hardwares.", "plot_latency(experiments, FIGURES, SHOW, DPI)"),
        ("10. Diagramas para metodologia e aplicação", "Fluxos baseados no código implementado. A calibração envolve o pipeline completo em folds internos. A decisão editorial exige confirmação humana.", "plot_experiment_flow(FIGURES, SHOW, DPI)\nplot_editorial_flow(FIGURES, SHOW, DPI)"),
    ]
    for title, explanation, code in sections:
        cell("markdown", f"## {title}\n{explanation}")
        cell("code", code)
    cell("markdown", """
## 11. Exportar e baixar tudo

O ZIP inclui **9 figuras × 3 formatos** (PNG de alta resolução, PDF e SVG),
**8 tabelas × 3 formatos** (CSV, Markdown, LaTeX), sugestões de legendas e proveniência.
Para Word, use PNG ou SVG; para LaTeX, prefira PDF e os arquivos `.tex` das tabelas.
As tabelas LaTeX contêm `tabular`; acrescente legenda e ajuste a largura ao template do artigo.

Sugestão de seleção para o corpo do artigo: distribuição, comparação de F1 macro,
matriz normalizada e fluxo experimental. Acrescente balanceamento ou métricas por classe
conforme a discussão. A tabela completa e figuras adicionais podem ir em apêndice.

Fonte sugerida nas legendas: **Elaboração própria a partir dos experimentos deste trabalho.**
""")
    cell("code", """
write_captions(OUTPUT, research)
archive = archive_outputs(OUTPUT)
print(f"Saídas: {OUTPUT.resolve()}")
print(f"Pacote completo: {archive.resolve()}")
if IN_COLAB:
    files.download(str(archive))
""")
    cell("markdown", """
## Atualizar com novas execuções

No computador do projeto, gere novamente `dados_artigo.zip` com:

```powershell
python -m scripts.package_article_results
```

Envie o novo ZIP a uma sessão nova do Colab ou ajuste `BUNDLE` para o nome enviado.
O notebook não precisa do arquivo Parquet e não altera os resultados experimentais.

Documentação: [upload de notebooks no Colab](https://research.google.com/colaboratory/intl/en-GB/faq.html)
e [exportação de figuras no Matplotlib](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html).
""")
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"colab": {"name": "Figuras_Artigo_Classificador_Noticias.ipynb", "provenance": []},
                             "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                             "language_info": {"name": "python"}}, "cells": cells}
    target = root / "notebooks/Figuras_Artigo_Classificador_Noticias.ipynb"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    print(build_notebook(Path.cwd()))
