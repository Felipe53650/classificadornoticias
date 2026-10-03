"""Mapeamento auditado das categorias observadas no arquivo enviado."""
import json
from pathlib import Path
import yaml

MAPPING = {"poder": "Política", "mercado": "Economia", "esporte": "Esportes", "mundo": "Mundo",
           "tec": "Tecnologia", "ciencia": "Ciência", "equilibrioesaude": "Saúde", "educacao": "Educação",
           "ilustrada": "Entretenimento", "turismo": "Turismo"}


def main() -> None:
    inspection = json.loads(Path("reports/folha_inspection.json").read_text(encoding="utf-8"))
    observed = inspection["category_counts"]
    if not set(MAPPING) <= set(observed):
        raise ValueError("A inspeção não contém todas as categorias esperadas.")
    for count in (4, 7, 10):
        path = Path(f"configs/categories_{count}.yaml")
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        config.update(mapping_confirmed=True, dataset_version="brazilian-news-parquet-local-v1",
                      label_mapping={label: MAPPING.get(label) for label in observed},
                      forest_trees=50, forest_max_depth=30, n_jobs=2)
        config["tfidf"].update(max_features=50000, dtype="float32")
        path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
