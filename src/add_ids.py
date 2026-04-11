"""Skrypt dodający unikalne id do każdego obiektu w demagog-data.json."""

import json
from pathlib import Path

INPUT_FILE = Path(__file__).parent / "data" / "demagog-data.json"
OUTPUT_FILE = Path(__file__).parent / "data" / "demagog-data.json"


def add_ids(input_path: Path, output_path: Path) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for i, item in enumerate(data, start=1):
        item = {"id": i, **item}
        data[i - 1] = item

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Dodano id do {len(data)} obiektów → {output_path}")


if __name__ == "__main__":
    add_ids(INPUT_FILE, OUTPUT_FILE)

