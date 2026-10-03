import pandas as pd
import pytest
from src.data.prepare_dataset import combine_text, prepare, split_dataset
from src.data.inspect_dataset import inspect_dataset
from src.data.prepare_dataset import read_dataset


def test_missing_label_fails(frame, config):
    with pytest.raises(ValueError, match="Colunas ausentes"):
        prepare(frame.drop(columns="category"), config)


def test_unknown_category_fails(frame, config):
    frame.loc[0, "category"] = "desconhecida"
    with pytest.raises(ValueError, match="sem mapeamento"):
        prepare(frame, config)


def test_empty_duplicates_and_conflicts(frame, config):
    extras = pd.DataFrame([{"title": "", "text": " <p> </p>", "category": "Economia"}, frame.iloc[0].to_dict(),
                           {**frame.iloc[1].to_dict(), "category": "Economia"}])
    data, audit = prepare(pd.concat([frame, extras]), config)
    assert audit["empty_text_removed"] == 1
    assert audit["duplicates_removed"] == 1
    assert audit["conflicting_rows_removed"] == 2
    assert data.text_id.is_unique


def test_split_disjoint_reproducible_and_shared_across_scenarios(frame, config):
    data, _ = prepare(frame, config)
    first, second = split_dataset(data, config), split_dataset(data, config)
    ids = []
    for key in first:
        assert set(first[key].category) == set(config["categories"])
        assert first[key].equals(second[key])
        ids.append(set(first[key].text_id))
    assert not ids[0] & ids[1] and not ids[1] & ids[2] and not ids[0] & ids[2]
    expanded = {**config, "categories": list(frame.category.unique())}
    big, _ = prepare(frame, expanded)
    for key, value in split_dataset(big, expanded).items():
        assert set(first[key].text_id) <= set(value.text_id)


def test_cleaning_and_inspection(tmp_path, frame):
    assert combine_text("<b>Olá</b>", "mundo &amp; notícia") == "[TITULO] Olá\n[TEXTO] mundo & notícia"
    with pytest.raises(ValueError):
        combine_text(" ", "<p></p>")
    path = tmp_path / "sample.csv"
    frame.to_csv(path, index=False)
    result = inspect_dataset(str(path), "title", "text", "category")
    assert result["total_rows"] == 450
    assert len(result["category_counts"]) == 10


def test_insufficient_classes(frame, config):
    with pytest.raises(ValueError, match="volume insuficiente"):
        prepare(frame.iloc[:10], config)


def test_parquet_input_matches_csv(tmp_path, frame):
    parquet, csv = tmp_path / "input.parquet", tmp_path / "input.csv"
    frame.to_parquet(parquet, index=False)
    frame.to_csv(csv, index=False)
    assert read_dataset(parquet).equals(read_dataset(csv))
    assert inspect_dataset(str(parquet), "title", "text", "category")["total_rows"] == len(frame)
