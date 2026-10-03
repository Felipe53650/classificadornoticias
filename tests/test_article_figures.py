import json
from zipfile import ZipFile
import pandas as pd
import pytest
from scripts.article_figures import load_results, write_table


def bundle(tmp_path, **changes):
    row = {"scenario": "categories_10", "experiment_id": "linear_svm_balanced", "evaluation_split": "validation", "demo": False, "f1_macro": .89}
    row.update(changes)
    path = tmp_path / "metrics.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("experiments.csv", pd.DataFrame([row]).to_csv(index=False))
        archive.writestr("research_summary.json", json.dumps({"schema_version": 1}))
    return path


@pytest.mark.parametrize("change", [{"evaluation_split": "test"}, {"demo": True}])
def test_article_comparison_rejects_mixed_provenance(tmp_path, change):
    with pytest.raises(ValueError):
        load_results(bundle(tmp_path, **change))


def test_article_zip_does_not_accept_additional_payloads(tmp_path):
    path = bundle(tmp_path)
    with ZipFile(path, "a") as archive:
        archive.writestr("articles.csv", "title,content\nExample,Text")
    with pytest.raises(ValueError, match="empacotador"):
        load_results(path)


def test_tables_keep_numeric_precision_and_escape_latex(tmp_path):
    frame = pd.DataFrame({"Categoria": ["Ciência & Saúde"], "F1_macro": [.8954823714242863]})
    write_table(frame, tmp_path, "test")
    restored = pd.read_csv(tmp_path / "test.csv")
    assert restored.F1_macro.iloc[0] == pytest.approx(frame.F1_macro.iloc[0], abs=1e-15)
    latex = (tmp_path / "test.tex").read_text(encoding="utf-8")
    assert r"Ciência \& Saúde" in latex
    assert r"F1\_macro" in latex
