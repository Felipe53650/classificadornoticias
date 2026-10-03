"""Demonstração sintética, sem valor de avaliação acadêmica."""
import argparse
from pathlib import Path
import random
import pandas as pd
import yaml
from src.data.inspect_dataset import inspect_dataset
from src.data.prepare_dataset import load_config, save_json
from src.ml.experiment import export_selected, run_experiments

VOCABULARY = {
    "Política": ["eleição", "congresso", "deputado", "governo", "partido", "votação", "senado", "ministro"],
    "Economia": ["juros", "banco", "inflação", "mercado", "investimento", "renda", "moeda", "emprego"],
    "Esportes": ["futebol", "campeonato", "atleta", "jogo", "gol", "treinador", "equipe", "torcida"],
    "Mundo": ["diplomacia", "países", "embaixada", "fronteira", "internacional", "tratado", "guerra", "aliança"],
    "Tecnologia": ["software", "computador", "aplicativo", "internet", "digital", "dispositivo", "rede", "programação"],
    "Ciência": ["pesquisa", "laboratório", "experimento", "astronomia", "descoberta", "espécie", "cientista", "molécula"],
    "Saúde": ["hospital", "médico", "vacina", "tratamento", "paciente", "doença", "prevenção", "consulta"],
    "Educação": ["escola", "aluno", "professor", "ensino", "universidade", "aula", "vestibular", "aprendizagem"],
    "Entretenimento": ["cinema", "filme", "cantor", "música", "festival", "ator", "teatro", "estreia"],
    "Turismo": ["viagem", "hotel", "roteiro", "praia", "visitante", "passeio", "hospedagem", "destino"],
}


def make_demo_frame() -> pd.DataFrame:
    rng = random.Random(42)
    rows = []
    for category, words in VOCABULARY.items():
        for number in range(45):
            sample = rng.sample(words, 6)
            rows.append({"title": f"Boletim {number}: {sample[0]} e {sample[1]}",
                         "text": f"Reportagem demonstrativa: {' '.join(sample)}. Novidades locais na edição {number}.", "category": category})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/demo")
    args = parser.parse_args()
    if (Path(args.output) / "best_model.joblib").exists():
        parser.exit(2, "Modelo de demonstração já existe. Use --output com um novo diretório.\n")
    path = Path("data/raw/demo.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    make_demo_frame().to_csv(path, index=False)
    save_json(Path("reports/demo_inspection.json"), inspect_dataset(str(path), "title", "text", "category"))
    runs = []
    for count in (4, 7, 10):
        config = load_config(f"configs/categories_{count}.yaml")
        config.update(mapping_confirmed=True, demo=True, dataset_version="synthetic-demo-v1",
                      label_mapping={c: c for c in VOCABULARY}, forest_trees=30)
        config_path = Path(f"data/processed/demo_{count}.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
        run = run_experiments(str(config_path), str(path))
        runs.append(run)
    export_selected(str(runs[-1]), args.output)
    pd.concat([pd.read_csv(run / "experiments.csv") for run in runs]).to_csv("reports/demo_experiments.csv", index=False)
    save_json(Path("reports/demo_runs.json"), {"demo": True, "runs": [str(p) for p in runs], "model_dir": args.output})
    print("Demonstração concluída. Estes resultados NÃO medem desempenho em notícias reais.")


if __name__ == "__main__":
    main()
