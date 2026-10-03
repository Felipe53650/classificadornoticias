"""Fábrica única dos pipelines experimentais."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
import numpy as np


def make_model(name: str, config: dict, balanced: bool = False, calibrated: bool = False):
    weight = "balanced" if balanced else None
    seed = config["random_state"]
    factories = {
        "naive_bayes": lambda: MultinomialNB(),
        "logistic_regression": lambda: LogisticRegression(max_iter=2000, class_weight=weight, random_state=seed),
        "linear_svm": lambda: LinearSVC(class_weight=weight, random_state=seed),
        "random_forest": lambda: RandomForestClassifier(n_estimators=config.get("forest_trees", 100), max_depth=config.get("forest_max_depth"), class_weight=weight, random_state=seed, n_jobs=config.get("n_jobs", 2)),
    }
    if name not in factories or (name == "naive_bayes" and balanced):
        raise ValueError("Modelo ou estratégia de pesos inválidos.")
    options = dict(config["tfidf"])
    options["ngram_range"] = tuple(options["ngram_range"])
    if "dtype" in options:
        options["dtype"] = getattr(np, options["dtype"])
    pipeline = Pipeline([("tfidf", TfidfVectorizer(**options)), ("classifier", factories[name]())])
    # Calibrar o pipeline inteiro evita ajustar o vocabulário nos folds de calibração.
    if calibrated and name == "linear_svm":
        return CalibratedClassifierCV(pipeline, cv=3, method="sigmoid")
    return pipeline
