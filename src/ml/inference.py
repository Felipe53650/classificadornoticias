"""A API utiliza esta classe e desconhece os estimadores internos."""
import json
from pathlib import Path
import joblib
import numpy as np
from src.data.prepare_dataset import combine_text
from src.artifacts import dataset_hash


class NewsClassifier:
    def __init__(self, model_dir: str | Path):
        path = Path(model_dir)
        self.metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if dataset_hash(path / "best_model.joblib") != self.metadata["artifact_sha256"]:
            raise ValueError("O artefato não corresponde aos metadados.")
        # joblib executa código: carregar somente artefatos locais confiáveis.
        self.model = joblib.load(path / "best_model.joblib")
        self.categories = list(self.model.classes_)
        if self.categories != self.metadata["categories"] or not hasattr(self.model, "predict_proba"):
            raise ValueError("Modelo incompatível com o serviço de probabilidades.")

    def predict(self, title: str, content: str) -> dict:
        text = combine_text(title, content)
        probabilities = self.model.predict_proba([text])[0]
        if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any():
            raise ValueError("Probabilidades inválidas.")
        order = np.argsort(-probabilities)[:3]
        candidates = [{"category": self.categories[i], "confidence": float(probabilities[i])} for i in order]
        return {"predicted_category": candidates[0]["category"], "confidence": candidates[0]["confidence"],
                "top_k": candidates, "model_version": self.metadata["version"]}
