"""Executa os três cenários reais sequencialmente, preservando resultados parciais."""
import argparse
from pathlib import Path
import pandas as pd
from src.data.prepare_dataset import save_json
from src.ml.experiment import run_experiments, export_selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model-output", default="models/production")
    args = parser.parse_args()
    runs = []
    for count in (4, 7, 10):
        run = run_experiments(f"configs/categories_{count}.yaml", args.dataset)
        runs.append(run)
        save_json(Path("reports/research_runs.json"), {"demo": False, "runs": [str(p) for p in runs], "status": "running"})
        pd.concat([pd.read_csv(p / "experiments.csv") for p in runs]).to_csv("reports/experiments.csv", index=False)
    export_selected(str(runs[-1]), args.model_output)
    save_json(Path("reports/research_runs.json"), {"demo": False, "runs": [str(p) for p in runs], "status": "complete", "model_dir": args.model_output})
    print("Pesquisa e exportação concluídas.", flush=True)


if __name__ == "__main__":
    main()
