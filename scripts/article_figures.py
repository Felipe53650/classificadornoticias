"""Figuras do artigo: módulo independente, também incorporado ao notebook Colab."""
import argparse
import io
import json
import os
from pathlib import Path
import platform
import tempfile
import zipfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "pauta-matplotlib"))
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

MODEL_NAMES = {"naive_bayes": "Naive Bayes", "logistic_regression": "Regressão logística",
               "linear_svm": "SVM linear", "random_forest": "Random Forest"}
COLORS = {"naive_bayes": "#0072B2", "logistic_regression": "#E69F00", "linear_svm": "#009E73", "random_forest": "#CC79A7"}


def load_results(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Lê entradas conhecidas do ZIP em memória, sem extrair arquivos ou código."""
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != {"experiments.csv", "research_summary.json"} or len(archive.infolist()) != 2:
            raise ValueError("Use o dados_artigo.zip produzido pelo empacotador do projeto.")
        if any(item.file_size > 10_000_000 for item in archive.infolist()):
            raise ValueError("Pacote de métricas excede o tamanho esperado.")
        table = pd.read_csv(io.BytesIO(archive.read("experiments.csv")), keep_default_na=False)
        summary = json.loads(archive.read("research_summary.json"))
    if summary.get("schema_version") != 1 or set(table.evaluation_split) != {"validation"}:
        raise ValueError("Formato incompatível ou mistura de partições na comparação.")
    if table.demo.astype(str).str.lower().ne("false").any():
        raise ValueError("O pacote contém dados de demonstração.")
    if table.duplicated(["scenario", "experiment_id"]).any():
        raise ValueError("Experimentos duplicados no pacote.")
    return table, summary


def configure_style(font_size: int = 11) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": font_size,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
                         "figure.facecolor": "white", "axes.facecolor": "white"})


def final_scenario(summary: dict) -> dict:
    return next(s for s in summary["scenarios"] if s["n_classes"] == 10 and "final" in s)


def model_label(model: str, weight: str) -> str:
    return MODEL_NAMES[model] + (" · balanceado" if weight == "balanced" else " · sem pesos")


def save_figure(fig, output: Path, name: str, show: bool = False, dpi: int = 300) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(output / f"{name}.{suffix}", dpi=dpi, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    plt.close(fig)


def write_table(table: pd.DataFrame, output: Path, name: str) -> None:
    """CSV para planilha, Markdown para revisão e LaTeX sem dependência extra."""
    output.mkdir(parents=True, exist_ok=True)
    table.to_csv(output / f"{name}.csv", index=False, encoding="utf-8-sig")
    def formatted(value):
        return f"{value:.4f}" if isinstance(value, (float, np.floating)) else str(value)
    rows = [[formatted(v) for v in row] for row in table.itertuples(index=False, name=None)]
    header = list(table.columns)
    markdown = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    markdown += ["| " + " | ".join(row) + " |" for row in rows]
    (output / f"{name}.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    def escaped(value):
        return "".join(replacements.get(char, char) for char in value)
    latex = [r"\begin{tabular}{" + "l" * len(header) + "}", r"\hline"]
    latex += [" & ".join(escaped(v) for v in header) + r" \\", r"\hline"]
    latex += [" & ".join(escaped(v) for v in row) + r" \\" for row in rows]
    latex += [r"\hline", r"\end{tabular}"]
    (output / f"{name}.tex").write_text("\n".join(latex) + "\n", encoding="utf-8")


def build_tables(table: pd.DataFrame, summary: dict, output: Path) -> dict[str, pd.DataFrame]:
    validation = table[["scenario", "model", "class_weight", "accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted"]].copy()
    comparison = table.pivot(index=["model", "class_weight"], columns="n_classes", values="f1_macro").reset_index()
    comparison.columns = [str(c) if isinstance(c, str) else f"F1 macro / {c} classes" for c in comparison.columns]
    sizes, distributions, weight_effects = [], [], []
    for scenario in summary["scenarios"]:
        counts = scenario["provenance"]["split_counts"]
        sizes.append({"Classes": scenario["n_classes"], "Após preparação": scenario["preparation"]["output_rows"],
                      **{name: sum(values.values()) for name, values in counts.items()}})
        for category, count in scenario["preparation"]["class_counts"].items():
            distributions.append({"Classes": scenario["n_classes"], "Categoria": category, "Notícias": count,
                                  **{part: values[category] for part, values in counts.items()}})
        for model in ("logistic_regression", "linear_svm", "random_forest"):
            reports = scenario["validation_reports"]
            for category in scenario["config"]["categories"]:
                normal, balanced = reports[f"{model}_none"][category], reports[f"{model}_balanced"][category]
                weight_effects.append({"Classes": scenario["n_classes"], "Modelo": MODEL_NAMES[model], "Categoria": category,
                                       "F1 sem pesos": normal["f1-score"], "F1 balanceado": balanced["f1-score"],
                                       "Diferença (p.p.)": 100 * (balanced["f1-score"] - normal["f1-score"])})
    final = final_scenario(summary)["final"]
    metadata = final["metadata"]
    by_class = pd.DataFrame([{ "Categoria": c, **final["classification_report"][c]} for c in final["confusion_absolute"]["labels"]])
    by_class["support"] = by_class.support.astype(int)
    metrics = pd.DataFrame([{"Métrica": key, "Valor": value} for key, value in metadata["test_metrics"].items()])
    times = table[["scenario", "model", "class_weight", "train_seconds", "inference_ms_mean", "batch_inference_ms_per_sample"]].copy()
    times["Ressalva"] = "Treino usa cache de TF-IDF; custo integral não comparável"
    tables = {"01_comparacao_validacao": comparison, "02_metricas_validacao": validation,
              "03_tamanhos_particoes": pd.DataFrame(sizes), "04_distribuicao_classes": pd.DataFrame(distributions),
              "05_efeito_pesos_por_classe": pd.DataFrame(weight_effects), "06_metricas_teste_final": metrics,
              "07_por_classe_teste_final": by_class, "08_tempos_observados": times}
    for name, frame in tables.items():
        write_table(frame, output / "tabelas", name)
    return tables


def plot_distribution(summary: dict, output: Path, show: bool = False, dpi: int = 300) -> None:
    counts = pd.Series(final_scenario(summary)["preparation"]["class_counts"]).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5.5), layout="constrained")
    bars = ax.barh(counts.index, counts.values, color="#0072B2")
    ax.bar_label(bars, labels=[f"{v:,}".replace(",", ".") for v in counts.values], padding=4, fontsize=9)
    ax.set(xlim=(0, counts.max()*1.2), xlabel="Notícias após preparação", title="Distribuição das dez categorias")
    save_figure(fig, output, "01_distribuicao_classes", show, dpi)


def plot_comparison(table: pd.DataFrame, output: Path, show: bool = False, dpi: int = 300) -> None:
    fig, ax = plt.subplots(figsize=(9, 6.5), layout="constrained")
    for (model, weight), group in table.groupby(["model", "class_weight"]):
        group = group.sort_values("n_classes")
        ax.plot(group.n_classes, group.f1_macro, color=COLORS[model], marker="s" if weight == "balanced" else "o",
                linestyle="--" if weight == "balanced" else "-", label=model_label(model, weight), linewidth=1.7)
    ax.set(xticks=[4, 7, 10], ylim=(0, 1.02), xlabel="Categorias no cenário", ylabel="F1 macro de validação", title="Comparação dos 21 experimentos na validação")
    ax.grid(alpha=.2)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.15), ncol=2, fontsize=9)
    save_figure(fig, output, "02_comparacao_validacao", show, dpi)


def plot_weight_effect(table: pd.DataFrame, output: Path, show: bool = False, dpi: int = 300) -> None:
    models = ["logistic_regression", "linear_svm", "random_forest"]
    values = []
    for model in models:
        group = table[table.model.eq(model)].pivot(index="n_classes", columns="class_weight", values="f1_macro")
        values.append(100 * (group.loc[[4, 7, 10], "balanced"] - group.loc[[4, 7, 10], "none"]).to_numpy())
    matrix = np.array(values)
    limit = max(abs(matrix).max(), .01)
    fig, ax = plt.subplots(figsize=(8, 3.7), layout="constrained")
    plot = ax.imshow(matrix, cmap="RdBu", vmin=-limit, vmax=limit)
    ax.set(xticks=range(3), xticklabels=[4, 7, 10], yticks=range(3), yticklabels=[MODEL_NAMES[m] for m in models],
           xlabel="Categorias no cenário", title="Efeito dos pesos de classe no F1 macro de validação")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{matrix[i,j]:+.2f}", ha="center", va="center", color="white" if abs(matrix[i,j]) > limit*.55 else "black")
    fig.colorbar(plot, ax=ax, label="Diferença em pontos percentuais")
    save_figure(fig, output, "03_efeito_balanceamento", show, dpi)


def plot_final_confusion(summary: dict, output: Path, normalized: bool = True, show: bool = False, dpi: int = 300) -> None:
    final = final_scenario(summary)["final"]
    data = final["confusion_normalized" if normalized else "confusion_absolute"]
    matrix = np.array(data["matrix"]) * (100 if normalized else 1)
    fig, ax = plt.subplots(figsize=(10, 8), layout="constrained")
    plot = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=100 if normalized else None)
    ax.set(xticks=range(len(data["labels"])), yticks=range(len(data["labels"])), xticklabels=data["labels"], yticklabels=data["labels"],
           xlabel="Categoria prevista", ylabel="Categoria real", title="SVM balanceada e calibrada · teste final de dez classes")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            value = f"{matrix[i,j]:.1f}" if normalized else f"{matrix[i,j]:.0f}"
            ax.text(j, i, value, ha="center", va="center", fontsize=8, color="white" if matrix[i,j] > matrix.max()*.55 else "black")
    fig.colorbar(plot, ax=ax, label="Percentual por categoria real (%)" if normalized else "Notícias")
    save_figure(fig, output, "04_confusao_normalizada_teste" if normalized else "05_confusao_absoluta_teste", show, dpi)


def plot_final_classes(summary: dict, output: Path, show: bool = False, dpi: int = 300) -> None:
    final = final_scenario(summary)["final"]
    labels = sorted(final["confusion_absolute"]["labels"], key=lambda c: final["classification_report"][c]["f1-score"])
    fig, ax = plt.subplots(figsize=(9, 6.5), layout="constrained")
    y = np.arange(len(labels))
    for offset, metric, label, color in [(-.24, "precision", "Precisão", "#0072B2"), (0, "recall", "Recall", "#E69F00"), (.24, "f1-score", "F1", "#009E73")]:
        ax.barh(y+offset, [final["classification_report"][c][metric] for c in labels], height=.23, label=label, color=color)
    ax.set(yticks=y, yticklabels=labels, xlim=(0, 1), xlabel="Valor da métrica", title="Desempenho por categoria · teste final")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.1), ncol=3)
    save_figure(fig, output, "06_metricas_por_classe_teste", show, dpi)


def plot_latency(table: pd.DataFrame, output: Path, show: bool = False, dpi: int = 300) -> None:
    data = table[table.n_classes.eq(10)].sort_values("inference_ms_mean")
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    bars = ax.barh([model_label(m, w) for m, w in zip(data.model, data.class_weight)], data.inference_ms_mean, color=[COLORS[m] for m in data.model])
    ax.bar_label(bars, fmt="%.2f", padding=4, fontsize=9)
    ax.set(xlim=(0, data.inference_ms_mean.max()*1.2), xlabel="Tempo médio por notícia (ms)", title="Inferência no benchmark de dez classes · validação")
    save_figure(fig, output, "07_latencia_validacao", show, dpi)


def diagram_canvas(title: str):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set(xlim=(0, 1), ylim=(0, 1), title=title)
    ax.axis("off")
    return fig, ax


def diagram_box(ax, x, y, text, width=.27, height=.09, color="#E5F2EE"):
    ax.add_patch(FancyBboxPatch((x-width/2, y-height/2), width, height, boxstyle="round,pad=0.012", edgecolor="#325B50", facecolor=color))
    ax.text(x, y, text, ha="center", va="center", fontsize=10)


def diagram_arrow(ax, start, end, **kwargs):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, color="#45635B", linewidth=1.4, **kwargs))


def plot_experiment_flow(output: Path, show: bool = False, dpi: int = 300) -> None:
    fig, ax = diagram_canvas("Fluxo experimental e isolamento do teste")
    diagram_box(ax, .5, .93, "Inspecionar, mapear categorias\nlimpar e deduplicar", .44)
    diagram_box(ax, .5, .77, "Cenários 4 / 7 / 10\nDivisão por classe · semente 42", .44)
    diagram_arrow(ax, (.5,.875), (.5,.825))
    for x, title in [(.16, "Treino ≈ 70%"), (.5, "Validação ≈ 15%"), (.84, "Teste ≈ 15%")]:
        diagram_box(ax, x, .60, title)
        diagram_arrow(ax, (.5,.715), (x,.655))
    diagram_box(ax, .16, .42, "Ajustar TF-IDF\ne classificadores")
    diagram_arrow(ax, (.16,.545), (.16,.475))
    diagram_box(ax, .5, .42, "Comparar na validação\nSelecionar pelo F1 macro")
    diagram_arrow(ax, (.5,.545), (.5,.475))
    diagram_arrow(ax, (.307,.42), (.353,.42))
    diagram_box(ax, .5, .23, "Calibrar o pipeline SVM e validar;\nreajustar em treino + validação", .48, .10)
    diagram_arrow(ax, (.5,.365), (.5,.292))
    diagram_box(ax, .5, .065, "Avaliar no teste reservado\nExportar modelo e metadados", .48)
    diagram_arrow(ax, (.5,.168), (.5,.122))
    ax.plot([.84,.84,.80], [.545,.065,.065], color="#45635B", linewidth=1.4)
    diagram_arrow(ax, (.80,.065), (.752,.065))
    ax.text(.84,.33,"Reservado até\na avaliação final", fontsize=9, ha="center", bbox={"facecolor": "white", "edgecolor": "none", "pad": 4})
    save_figure(fig, output, "08_fluxo_experimental", show, dpi)


def plot_editorial_flow(output: Path, show: bool = False, dpi: int = 300) -> None:
    fig, ax = diagram_canvas("Fluxo editorial com confirmação humana")
    entries = [("Editor informa título e conteúdo", "#E5F2EE"),
               ("API aplica o modelo calibrado\ne registra a previsão", "#E5F2EE"),
               ("Portal exibe sugestão, confiança e top 3", "#E5F2EE"),
               ("Editor revisa, aceita ou corrige\ne confirma a categoria final", "#FFF1CF"),
               ("API salva notícia e decisão no SQLite", "#E5F2EE"),
               ("Histórico permite analisar correções", "#E5F2EE")]
    for i, (label, color) in enumerate(entries):
        y = .92 - .16*i
        diagram_box(ax, .5, y, label, .70, .09, color)
        if i:
            diagram_arrow(ax, (.5,y+.105), (.5,y+.057))
    save_figure(fig, output, "09_fluxo_editorial", show, dpi)


def write_captions(output: Path, summary: dict) -> None:
    captions = """# Figuras e tabelas para o artigo

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
"""
    (output / "LEGENDAS_E_USO.md").write_text(captions, encoding="utf-8")
    provenance = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "matplotlib": matplotlib.__version__,
                  "source_created_at": summary["created_at"],
                  "runs": [{"id": s["run_id"], "dataset_sha256": s["provenance"]["dataset_sha256"]} for s in summary["scenarios"]]}
    (output / "proveniencia_figuras.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")


def archive_outputs(output: Path) -> Path:
    path = output.parent / f"{output.name}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(output).as_posix())
    return path


def generate_all(bundle: Path, output: Path, show: bool = False, dpi: int = 300) -> Path:
    table, summary = load_results(bundle)
    configure_style()
    build_tables(table, summary, output)
    figures = output / "figuras"
    plot_distribution(summary, figures, show, dpi)
    plot_comparison(table, figures, show, dpi)
    plot_weight_effect(table, figures, show, dpi)
    plot_final_confusion(summary, figures, True, show, dpi)
    plot_final_confusion(summary, figures, False, show, dpi)
    plot_final_classes(summary, figures, show, dpi)
    plot_latency(table, figures, show, dpi)
    plot_experiment_flow(figures, show, dpi)
    plot_editorial_flow(figures, show, dpi)
    write_captions(output, summary)
    return archive_outputs(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default="reports/artigo/dados_artigo.zip")
    parser.add_argument("--output", default="reports/artigo/figuras_e_tabelas")
    args = parser.parse_args()
    print(generate_all(Path(args.bundle), Path(args.output)))
