import argparse
from src.ml.experiment import export_selected

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta vencedor da validação e avalia teste isolado.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", default="models/production")
    args = parser.parse_args()
    try:
        result = export_selected(args.run, args.output)
        print(f"Modelo exportado: {result['version']}")
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
