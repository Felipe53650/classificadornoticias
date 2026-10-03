"""Métricas e gráficos persistidos sem estado de interface gráfica."""
from pathlib import Path
from time import perf_counter
import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "pauta-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, log_loss, precision_recall_fscore_support
from src.data.prepare_dataset import save_json


def evaluate(model, data, categories: list[str], output: Path) -> dict:
    texts = data.combined_text.tolist()
    start = perf_counter()
    predictions = model.predict(texts)
    batch_ms = (perf_counter() - start) * 1000 / len(texts)
    timings = []
    for text in texts[:min(100, len(texts))]:
        start = perf_counter()
        model.predict([text])
        timings.append((perf_counter() - start) * 1000)
    metrics = {"accuracy": accuracy_score(data.category, predictions), "inference_ms_mean": float(np.mean(timings)), "batch_inference_ms_per_sample": batch_ms}
    for average in ("macro", "weighted"):
        p, r, f, _ = precision_recall_fscore_support(data.category, predictions, average=average, zero_division=0)
        metrics.update({f"precision_{average}": p, f"recall_{average}": r, f"f1_{average}": f})
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(texts)
        truth = np.array([[int(label == c) for c in model.classes_] for label in data.category])
        metrics["log_loss"] = log_loss(data.category, probabilities, labels=model.classes_)
        metrics["brier_multiclass"] = float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))
    output.mkdir(parents=True, exist_ok=True)
    report = classification_report(data.category, predictions, labels=categories, output_dict=True, zero_division=0)
    save_json(output / "classification_report.json", report)
    save_json(output / "metrics.json", metrics)
    errors = data[["text_id", "title", "category"]].copy()
    errors["prediction"] = predictions
    errors.loc[errors.category != errors.prediction].to_csv(output / "errors.csv", index=False)
    for normalized in (False, True):
        matrix = confusion_matrix(data.category, predictions, labels=categories, normalize="true" if normalized else None)
        suffix = "normalized" if normalized else "absolute"
        save_json(output / f"confusion_{suffix}.json", {"labels": categories, "matrix": matrix.tolist()})
        fig, ax = plt.subplots(figsize=(10, 8))
        plot = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1 if normalized else None)
        ax.set(xticks=range(len(categories)), yticks=range(len(categories)), xticklabels=categories, yticklabels=categories, xlabel="Prevista", ylabel="Real")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        for i in range(len(categories)):
            for j in range(len(categories)):
                ax.text(j, i, f"{matrix[i,j]:.2f}" if normalized else str(matrix[i,j]), ha="center", va="center", fontsize=7)
        fig.colorbar(plot, ax=ax)
        fig.tight_layout()
        fig.savefig(output / f"confusion_{suffix}.png", dpi=130)
        plt.close(fig)
    return metrics
