import argparse
from pathlib import Path
from src.data.prepare_dataset import load_config, prepare, read_dataset, save_json, split_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpa e divide um CSV conforme a configuração.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="data/processed/prepared")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        data, audit = prepare(read_dataset(args.dataset), config)
        destination = Path(args.output)
        save_json(destination / "audit.json", audit)
        for name, part in split_dataset(data, config).items():
            part.to_csv(destination / f"{name}.csv", index=False)
        print(f"Dados preparados: {destination}")
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
