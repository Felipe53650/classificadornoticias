"""Empacota somente resultados agregados para o notebook do artigo."""
import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package_results(root: Path, output: Path) -> Path:
    """Lê execuções completas; nunca inclui textos, partições, bancos ou joblib."""
    manifest = read_json(root / "reports/research_runs.json")
    if manifest.get("status") != "complete" or manifest.get("demo") is not False:
        raise ValueError("É necessário concluir a pesquisa real antes de empacotar os resultados.")
    scenarios, rows = [], []
    for location in manifest["runs"]:
        run = (root / location.replace("\\", "/")).resolve()
        if not run.is_relative_to(root.resolve() / "reports/runs"):
            raise ValueError("Diretório de execução fora de reports/runs.")
        config = read_json(run / "config.json")
        if config.get("demo"):
            raise ValueError("Execução sintética não pode entrar no pacote acadêmico.")
        with (run / "experiments.csv").open(encoding="utf-8", newline="") as stream:
            run_rows = list(csv.DictReader(stream))
        if any(row["evaluation_split"] != "validation" or row["demo"].lower() != "false" for row in run_rows):
            raise ValueError("Tabela de comparação deve conter somente validação em dados reais.")
        rows.extend(run_rows)
        provenance = read_json(run / "manifest.json")
        scenario = {"run_id": run.name, "n_classes": len(config["categories"]), "config": config,
                    "preparation": read_json(run / "preparation.json"),
                    "selection": read_json(run / "selection.json"),
                    "provenance": provenance,
                    "validation_reports": {row["experiment_id"]: read_json(run / row["experiment_id"] / "classification_report.json") for row in run_rows}}
        if (run / "final_evaluation.json").exists():
            scenario["final"] = {"metadata": read_json(run / "final_evaluation.json"),
                                 "classification_report": read_json(run / "final_test/classification_report.json"),
                                 "confusion_absolute": read_json(run / "final_test/confusion_absolute.json"),
                                 "confusion_normalized": read_json(run / "final_test/confusion_normalized.json")}
        scenarios.append(scenario)
    if sorted(s["n_classes"] for s in scenarios) != [4, 7, 10]:
        raise ValueError("O pacote requer exatamente os cenários 4, 7 e 10.")
    if not any(s["n_classes"] == 10 and "final" in s for s in scenarios):
        raise ValueError("Avaliação final de dez classes ausente.")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    summary = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
               "scenarios": sorted(scenarios, key=lambda s: s["n_classes"]),
               "notes": ["Comparações entre algoritmos usam validação; teste somente para o modelo final.",
                         "Tempos de treino incluem cache de TF-IDF; não representam comparação uniforme de custo integral.",
                         "Uma semente; sem intervalos de confiança nem inferência causal sobre quantidade de classes."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("experiments.csv", buffer.getvalue().encode("utf-8"))
        archive.writestr("research_summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/artigo/dados_artigo.zip")
    args = parser.parse_args()
    print(package_results(Path.cwd(), Path(args.output)))
