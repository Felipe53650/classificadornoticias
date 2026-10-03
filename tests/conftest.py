from pathlib import Path
import joblib
import pytest
from scripts.demo import make_demo_frame, VOCABULARY
from src.artifacts import dataset_hash
from src.data.prepare_dataset import load_config, prepare, save_json
from src.ml.train import make_model


@pytest.fixture
def config():
    result = load_config("configs/categories_4.yaml")
    result.update(mapping_confirmed=True, demo=True, label_mapping={c: c for c in VOCABULARY})
    return result


@pytest.fixture
def frame():
    return make_demo_frame()


@pytest.fixture
def trained_dir(tmp_path, config, frame):
    data, _ = prepare(frame, config)
    model = make_model("logistic_regression", config)
    model.fit(data.combined_text, data.category)
    path = tmp_path / "model"
    path.mkdir()
    joblib.dump(model, path / "best_model.joblib")
    save_json(path / "metadata.json", {"version": "test-v1", "categories": list(model.classes_), "demo": True,
                                       "artifact_sha256": dataset_hash(path / "best_model.joblib")})
    return path
