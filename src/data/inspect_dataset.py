"""Inspeção do arquivo real, sem presumir os nomes de colunas."""
import argparse
from pathlib import Path
from src.data.prepare_dataset import read_dataset, save_json


def inspect_dataset(path: str, title: str | None = None, content: str | None = None, category: str | None = None) -> dict:
    frame = read_dataset(path)
    result = {"file": str(path), "columns": list(frame.columns), "total_rows": len(frame),
              "exact_duplicate_rows": int(frame.duplicated().sum()),
              "empty_by_column": {c: int(frame[c].astype(str).str.strip().eq("").sum()) for c in frame}}
    specified = {"title": title, "content": content, "category": category}
    for name in specified.values():
        if name and name not in frame:
            raise ValueError(f"Coluna não encontrada: {name}")
    result["selected_columns"] = specified
    if category:
        result["category_counts"] = frame[category].value_counts(dropna=False).to_dict()
    if title and content:
        result["empty_text_rows"] = int((frame[title].str.strip().eq("") & frame[content].str.strip().eq("")).sum())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    for column in ("title", "content", "category"):
        parser.add_argument(f"--{column}-column")
    parser.add_argument("--output", default="reports/inspection.json")
    args = parser.parse_args()
    result = inspect_dataset(args.dataset, args.title_column, args.content_column, args.category_column)
    save_json(Path(args.output), result)
    print(result)


if __name__ == "__main__":
    main()
