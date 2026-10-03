"""Limpeza compartilhada entre pesquisa e inferência."""
import hashlib
import html
import json
import re
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value))
    return " ".join(html.unescape(value).split())


def combine_text(title: str, content: str) -> str:
    title, content = clean_text(title), clean_text(content)
    if not title and not content:
        raise ValueError("Informe título ou conteúdo com texto.")
    return f"[TITULO] {title}\n[TEXTO] {content}"


def read_dataset(path: str | Path) -> pd.DataFrame:
    if not Path(path).is_file():
        raise ValueError(f"Dataset não encontrado: {path}")
    if Path(path).suffix.lower() == ".parquet":
        return pd.read_parquet(path).fillna("")
    return pd.read_csv(path, keep_default_na=False).fillna("")


def load_config(path: str | Path) -> dict:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    categories = config["categories"]
    if len(categories) != len(set(categories)) or len(categories) < 2:
        raise ValueError("Categorias devem ser únicas e conter pelo menos duas classes.")
    split = config["split"]
    if any(split[k] <= 0 for k in ("train", "validation", "test")) or abs(sum(split.values()) - 1) > 1e-8:
        raise ValueError("Proporções de split inválidas.")
    return config


def prepare(frame: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    columns = config["columns"]
    missing = set(columns.values()) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    data = frame[[columns[k] for k in ("title", "content", "category")]].copy()
    data.columns = ["title", "content", "category"]
    for column in data:
        data[column] = data[column].fillna("").map(clean_text)
    audit = {"input_rows": len(data)}
    empty = (data.title == "") & (data.content == "")
    audit["empty_text_removed"] = int(empty.sum())
    data = data.loc[~empty].copy()
    unknown = sorted(set(data.category) - set(config["label_mapping"]))
    if unknown:
        raise ValueError(f"Categorias sem mapeamento explícito (use null para excluir): {unknown}")
    data["category"] = data.category.map(config["label_mapping"])
    data["combined_text"] = [combine_text(t, c) for t, c in zip(data.title, data.content)]
    data["text_id"] = data.combined_text.map(lambda t: hashlib.sha256(t.casefold().encode()).hexdigest())
    # Rótulos conflitantes não são resolvidos arbitrariamente.
    conflicts = data.groupby("text_id").category.nunique()
    conflict_ids = set(conflicts[conflicts > 1].index)
    audit["conflicting_rows_removed"] = int(data.text_id.isin(conflict_ids).sum())
    data = data.loc[~data.text_id.isin(conflict_ids)]
    audit["duplicates_removed"] = int(data.duplicated("text_id").sum())
    data = data.drop_duplicates("text_id")
    keep = data.category.isin(config["categories"])
    audit["outside_scenario_removed"] = int((~keep).sum())
    data = data.loc[keep].sort_values("text_id").reset_index(drop=True)
    counts = data.category.value_counts().to_dict()
    insufficient = {c: counts.get(c, 0) for c in config["categories"] if counts.get(c, 0) < config.get("min_samples_per_class", 20)}
    if insufficient:
        raise ValueError(f"Classes com volume insuficiente: {insufficient}")
    audit.update(output_rows=len(data), class_counts=counts)
    return data, audit


def split_dataset(data: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    # Split por classe: exemplos das classes compartilhadas mantêm a partição
    # mesmo quando o cenário adiciona novas categorias.
    parts = {k: [] for k in ("train", "validation", "test")}
    ratios = config["split"]
    for _, group in data.groupby("category", sort=True):
        train, remainder = train_test_split(group, train_size=ratios["train"], random_state=config["random_state"])
        validation, test = train_test_split(remainder, test_size=ratios["test"] / (ratios["validation"] + ratios["test"]), random_state=config["random_state"])
        for name, chunk in zip(parts, (train, validation, test)):
            parts[name].append(chunk)
    return {k: pd.concat(v).reset_index(drop=True) for k, v in parts.items()}


def save_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
