"""Gera tabelas e gráficos acadêmicos a partir de execuções concluídas."""
import json
from pathlib import Path
import pandas as pd
from src.ml.evaluate import plt
from src.data.prepare_dataset import save_json


def main() -> None:
    root = Path("reports")
    manifest = json.loads((root / "research_runs.json").read_text(encoding="utf-8"))
    runs = [Path(p) for p in manifest["runs"]]
    previous = None
    split_audit = []
    for run in runs:
        parts = {name: pd.read_csv(run / f"{name}.csv", usecols=["text_id", "category"])
                 for name in ("train", "validation", "test")}
        ids = {name: set(part.text_id) for name, part in parts.items()}
        if any(len(ids[name]) != len(part) for name, part in parts.items()):
            raise ValueError(f"Duplicação dentro de partição: {run}")
        if ids["train"] & ids["validation"] or ids["train"] & ids["test"] or ids["validation"] & ids["test"]:
            raise ValueError(f"Sobreposição entre partições: {run}")
        current = {name: {label: set(group.text_id) for label, group in part.groupby("category")}
                   for name, part in parts.items()}
        if previous:
            for name in parts:
                for label in set(previous[name]) & set(current[name]):
                    if previous[name][label] != current[name][label]:
                        raise ValueError(f"Partição inconsistente entre cenários: {label} / {name}")
        split_audit.append({"run": str(run), "disjoint": True, "shared_classes_consistent": True,
                            "counts": {name: len(part) for name, part in parts.items()}})
        previous = current
    save_json(root / "split_audit.json", split_audit)
    table = pd.concat([pd.read_csv(p / "experiments.csv") for p in runs])
    table.to_csv(root / "experiments.csv", index=False)
    winners = table.sort_values(["f1_macro", "experiment_id"], ascending=[False, True]).groupby("n_classes", sort=True).head(1).sort_values("n_classes")
    selected = winners[["scenario", "model", "class_weight", "f1_macro", "accuracy", "train_samples", "validation_samples", "test_samples"]]
    selected.to_csv(root / "selected_models.csv", index=False)
    weight_effects = []
    for run in runs:
        config = json.loads((run / "config.json").read_text(encoding="utf-8"))
        for model in ("logistic_regression", "linear_svm", "random_forest"):
            baseline_path = run / f"{model}_none/classification_report.json"
            balanced_path = run / f"{model}_balanced/classification_report.json"
            if not baseline_path.exists() or not balanced_path.exists():
                continue
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            balanced = json.loads(balanced_path.read_text(encoding="utf-8"))
            for category in config["categories"]:
                weight_effects.append({"scenario": config["scenario"], "model": model, "category": category,
                                       "support": baseline[category]["support"],
                                       "f1_none": baseline[category]["f1-score"], "f1_balanced": balanced[category]["f1-score"],
                                       "f1_delta": balanced[category]["f1-score"] - baseline[category]["f1-score"],
                                       "recall_none": baseline[category]["recall"], "recall_balanced": balanced[category]["recall"]})
    pd.DataFrame(weight_effects).to_csv(root / "weight_effects.csv", index=False)
    figures = root / "figures"
    figures.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6))
    for experiment_id, group in table.groupby("experiment_id"):
        group = group.sort_values("n_classes")
        ax.plot(group.n_classes, group.f1_macro, marker="o", label=experiment_id)
    ax.set(xlabel="Quantidade de categorias", ylabel="F1 macro de validação", xticks=[4, 7, 10], ylim=(0, 1), title="Comparação de modelos · validação")
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(figures / "validation_comparison.png", dpi=150)
    plt.close(fig)
    audit = json.loads((runs[-1] / "preparation.json").read_text(encoding="utf-8"))
    counts = pd.Series(audit["class_counts"]).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    counts.plot.barh(ax=ax, color="#17624d")
    ax.set(xlabel="Notícias após preparação", title="Distribuição das dez categorias")
    fig.tight_layout()
    fig.savefig(figures / "class_distribution.png", dpi=150)
    plt.close(fig)
    metadata = json.loads((runs[-1] / "final_evaluation.json").read_text(encoding="utf-8"))
    confusion = json.loads((runs[-1] / "final_test/confusion_absolute.json").read_text(encoding="utf-8"))
    pairs = [{"actual": a, "predicted": b, "count": confusion["matrix"][i][j]}
             for i, a in enumerate(confusion["labels"]) for j, b in enumerate(confusion["labels"]) if i != j]
    pairs.sort(key=lambda p: p["count"], reverse=True)
    save_json(root / "top_confusions.json", pairs[:15])
    lines = ["# Resultados no dataset recebido", "", "Uma execução com semente 42. Seleção feita exclusivamente na validação de cada cenário.", "",
             "| Classes | Modelo | Pesos | F1 macro validação | Accuracy validação | Treino / validação / teste |",
             "|---:|---|---|---:|---:|---|"]
    for _, row in selected.iterrows():
        lines.append(f"| {row.scenario} | {row.model} | {row.class_weight} | {row.f1_macro:.4f} | {row.accuracy:.4f} | {row.train_samples} / {row.validation_samples} / {row.test_samples} |")
    metrics = metadata["test_metrics"]
    lines += ["", "## Avaliação final do cenário de dez classes", "", f"Modelo: **{metadata['model_name']}**; versão `{metadata['version']}`.", "",
              f"- F1 macro: **{metrics['f1_macro']:.4f}**.", f"- F1 weighted: **{metrics['f1_weighted']:.4f}**.",
              f"- Accuracy: **{metrics['accuracy']:.4f}**.", f"- Inferência individual média: **{metrics['inference_ms_mean']:.2f} ms** (até 100 exemplos).",
              f"- Artefato: **{metadata['artifact_bytes'] / 1024**2:.2f} MiB**.", "",
              "O teste foi consultado apenas após seleção. Não houve ajuste em função das métricas finais. As métricas não estimam qualidade de notícias futuras nem de categorias ausentes.",
              "", "## Maiores confusões no teste", "", "| Real | Prevista | Quantidade |", "|---|---|---:|"]
    lines += [f"| {p['actual']} | {p['predicted']} | {p['count']} |" for p in pairs[:10]]
    lines += ["", "## Limites de interpretação", "", "Adicionar categorias altera volume e composição além da dificuldade. Uma única semente não fornece intervalo de confiança. Duplicados exatos foram tratados; notícias quase duplicadas e dependência temporal ainda exigem auditoria. Resultados não confirmam automaticamente causalidade, H1–H4 ou calibração perfeita.", "",
              "Os gráficos estão em `figures/`, a tabela completa em `experiments.csv`, a comparação de pesos por categoria em `weight_effects.csv`, e os relatórios por classe e matrizes nas pastas listadas em `research_runs.json`."]
    (root / "RESULTADOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(selected.to_string(index=False))
    print("Final test:", metrics)


if __name__ == "__main__":
    main()
