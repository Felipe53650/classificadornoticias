import pytest
from src.ml.inference import NewsClassifier
from src.ml.train import make_model
from src.data.prepare_dataset import prepare, split_dataset


def test_inference(trained_dir):
    classifier = NewsClassifier(trained_dir)
    result = classifier.predict("Banco anuncia juros", "Inflação e investimento no mercado")
    assert result["predicted_category"] in classifier.categories
    assert 0 <= result["confidence"] <= 1
    assert len({x["category"] for x in result["top_k"]}) == 3
    assert result["model_version"] == "test-v1"
    with pytest.raises(ValueError):
        classifier.predict("", " ")


def test_artifact_mismatch(trained_dir):
    with (trained_dir / "best_model.joblib").open("ab") as stream:
        stream.write(b"modified")
    with pytest.raises(ValueError, match="metadados"):
        NewsClassifier(trained_dir)


def test_pipeline_never_fits_validation_vocabulary(frame, config):
    data, _ = prepare(frame, config)
    splits = split_dataset(data, config)
    model = make_model("logistic_regression", config)
    model.fit(splits["train"].combined_text, splits["train"].category)
    model.predict(["palavraexclusivadoteste"])
    assert "palavraexclusivadoteste" not in model.named_steps["tfidf"].vocabulary_


def test_calibrated_svm_wraps_complete_pipeline(frame, config):
    data, _ = prepare(frame, config)
    model = make_model("linear_svm", config, calibrated=True)
    assert "tfidf" in model.estimator.named_steps
    model.fit(data.combined_text, data.category)
    assert abs(model.predict_proba([data.combined_text.iloc[0]])[0].sum() - 1) < 1e-8
