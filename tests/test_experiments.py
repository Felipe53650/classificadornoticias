import json
import pandas as pd
import pytest
import yaml
from src.ml.experiment import run_experiments, export_selected
from src.ml.inference import NewsClassifier


def test_experiment_selection_export_and_final_test_guard(tmp_path, config, frame):
    config["models"] = ["naive_bayes", "logistic_regression"]
    configuration, dataset = tmp_path / "config.yaml", tmp_path / "data.csv"
    configuration.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    frame.to_csv(dataset, index=False)
    run = run_experiments(str(configuration), str(dataset), str(tmp_path / "runs"))
    results = pd.read_csv(run / "experiments.csv")
    assert len(results) == 3
    assert set(results.evaluation_split) == {"validation"}
    assert not (run / "final_test").exists()
    selection = json.loads((run / "selection.json").read_text(encoding="utf-8"))
    assert selection["validation_f1_macro"] == results.f1_macro.max()
    destination = tmp_path / "model"
    metadata = export_selected(str(run), str(destination))
    assert "test_metrics" in metadata
    assert (run / "final_test/confusion_normalized.png").is_file()
    assert NewsClassifier(destination).predict("Banco e juros", "Inflação")["model_version"] == metadata["version"]
    with pytest.raises(ValueError, match="já existe"):
        export_selected(str(run), str(tmp_path / "second_model"))


def test_unconfirmed_mapping_blocks_training(tmp_path, config):
    config["mapping_confirmed"] = False
    configuration = tmp_path / "config.yaml"
    configuration.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="confirme"):
        run_experiments(str(configuration), "missing.csv")
