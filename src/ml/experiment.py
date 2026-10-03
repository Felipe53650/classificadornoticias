"""Experimentos selecionam por validação; exportação avalia o teste uma vez."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
from time import perf_counter
from uuid import uuid4
import joblib
import pandas as pd
from src.data.prepare_dataset import load_config, prepare, read_dataset, save_json, split_dataset
from src.ml.evaluate import evaluate
from src.ml.train import make_model
from src.artifacts import dataset_hash


def run_experiments(config_path: str, dataset: str, output: str = "reports/runs") -> Path:
    config = load_config(config_path)
    if not config.get("mapping_confirmed"):
        raise ValueError("Inspecione o dataset e confirme label_mapping antes de treinar.")
    data, audit = prepare(read_dataset(dataset), config)
    splits = split_dataset(data, config)
    run = Path(output) / f"{config['scenario']}_{uuid4().hex[:10]}"
    run.mkdir(parents=True)
    save_json(run / "config.json", config)
    save_json(run / "preparation.json", audit)
    for name, part in splits.items():
        part.to_csv(run / f"{name}.csv", index=False)
    manifest = {"dataset_sha256": dataset_hash(Path(dataset)), "dataset_version": config["dataset_version"],
                "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
                "packages": {p: version(p) for p in ("scikit-learn", "numpy", "pandas", "joblib")},
                "split_counts": {k: v.category.value_counts().to_dict() for k, v in splits.items()},
                "demo": config.get("demo", False)}
    rows = []
    for name in config.get("models", ["naive_bayes", "logistic_regression", "linear_svm", "random_forest"]):
        for balanced in ([False] if name == "naive_bayes" else [False, True]):
            experiment_id = f"{name}_{'balanced' if balanced else 'none'}"
            model = make_model(name, config, balanced)
            model.memory = str(run / "pipeline_cache")
            print(f"{config['scenario']} / {experiment_id}: treinamento iniciado", flush=True)
            start = perf_counter()
            model.fit(splits["train"].combined_text, splits["train"].category)
            seconds = perf_counter() - start
            metrics = evaluate(model, splits["validation"], config["categories"], run / experiment_id)
            print(f"{experiment_id}: F1 macro={metrics['f1_macro']:.4f}; treino={seconds:.1f}s", flush=True)
            rows.append({"experiment_id": experiment_id, "scenario": config["scenario"], "n_classes": len(config["categories"]),
                         "model": name, "class_weight": "balanced" if balanced else "none", "tfidf_config": json.dumps(config["tfidf"]),
                         **{f"{k}_samples": len(v) for k, v in splits.items()}, **metrics,
                         "train_seconds": seconds, "random_state": config["random_state"],
                         "created_at": manifest["created_at"], "evaluation_split": "validation", "demo": manifest["demo"]})
            pd.DataFrame(rows).to_csv(run / "experiments.csv", index=False)
    table = pd.DataFrame(rows)
    table.to_csv(run / "experiments.csv", index=False)
    # Não comparar cenários de dificuldades diferentes para escolher o modelo.
    winner = table.sort_values(["f1_macro", "experiment_id"], ascending=[False, True]).iloc[0]
    selection = {"model": winner.model, "balanced": winner.class_weight == "balanced", "validation_f1_macro": float(winner.f1_macro),
                 "criterion": "Maior F1 macro de validação dentro do cenário; desempate por identificador estável."}
    # SVM calibrada muda a predição: registrar sua validação antes de abrir o teste.
    if winner.model == "linear_svm":
        calibrated = make_model("linear_svm", config, selection["balanced"], calibrated=True)
        calibrated.fit(splits["train"].combined_text, splits["train"].category)
        selection["calibrated_validation"] = evaluate(calibrated, splits["validation"], config["categories"], run / "selected_calibrated_validation")
    save_json(run / "selection.json", selection)
    save_json(run / "manifest.json", manifest)
    print(f"Experimentos concluídos: {run}")
    return run


def export_selected(run_path: str, model_dir: str) -> dict:
    run, target = Path(run_path), Path(model_dir)
    if (run / "final_evaluation.json").exists() or (target / "best_model.joblib").exists():
        raise ValueError("Avaliação final ou destino já existe. Preserve o resultado; use uma nova execução para novo protocolo.")
    config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    selection = json.loads((run / "selection.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    training = pd.concat([pd.read_csv(run / f"{p}.csv", keep_default_na=False) for p in ("train", "validation")])
    model = make_model(selection["model"], config, selection["balanced"], calibrated=True)
    start = perf_counter()
    model.fit(training.combined_text, training.category)
    train_seconds = perf_counter() - start
    metrics = evaluate(model, pd.read_csv(run / "test.csv", keep_default_na=False), config["categories"], run / "final_test")
    target.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target / "best_model.joblib")
    metadata = {"model_name": selection["model"], "version": uuid4().hex[:12], "scenario": config["scenario"],
                "categories": list(model.classes_), "trained_at": datetime.now(timezone.utc).isoformat(),
                "random_state": config["random_state"], "dataset_version": manifest["dataset_version"],
                "dataset_sha256": manifest["dataset_sha256"], "demo": manifest["demo"], "packages": manifest["packages"],
                "selection": selection, "test_metrics": metrics, "train_seconds": train_seconds,
                "artifact_bytes": (target / "best_model.joblib").stat().st_size,
                "artifact_sha256": dataset_hash(target / "best_model.joblib"), "config": config}
    save_json(target / "metadata.json", metadata)
    save_json(run / "final_evaluation.json", metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="reports/runs")
    args = parser.parse_args()
    try:
        run_experiments(args.config, args.dataset, args.output)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    main()
