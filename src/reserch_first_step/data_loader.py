"""Moduł ładowania danych – obsługa formatów Demagog (JSON) i LIAR (TSV)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

# ── Mapowanie etykiet LIAR z TSV na kanoniczne nazwy ─────────────────────────
LIAR_LABEL_MAP = {
    "true": "True",
    "mostly-true": "Mostly True",
    "half-true": "Half True",
    "barely-true": "Mostly False",
    "false": "False",
    "pants-fire": "Pants on Fire",
}


def load_demagog(filepath: str) -> Tuple[str, List[Dict[str, str]]]:
    """Wczytuje zbiór Demagog z pliku JSON.

    Returns:
        Krotka (typ_zbioru, lista rekordów z kluczami: statement, label, author, date)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: List[Dict[str, str]] = []
    for item in data:
        records.append({
            "statement": item["Statement"],
            "label": item["Class"],
            "author": item.get("Author", ""),
            "date": item.get("Date", ""),
        })

    return "demagog", records


def load_liar(filepath: str) -> Tuple[str, List[Dict[str, str]]]:
    """Wczytuje zbiór LIAR z pliku TSV.

    Kolumny TSV (wg README):
        0: ID, 1: label, 2: statement, 3: subject, 4: speaker,
        5: job title, 6: state, 7: party, 8-12: credit history, 13: context

    Returns:
        Krotka (typ_zbioru, lista rekordów z kluczami: statement, label, id, raw_label)
    """
    records: List[Dict[str, str]] = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue
            raw_label = row[1].strip()
            label = LIAR_LABEL_MAP.get(raw_label, raw_label)
            records.append({
                "statement": row[2].strip(),
                "label": label,
                "id": row[0].strip(),
                "raw_label": raw_label,
            })

    return "liar", records


def load_data(filepath: str) -> Tuple[str, List[Dict[str, str]]]:
    """Automatycznie wykrywa format pliku i ładuje dane.

    - .json → Demagog
    - .tsv  → LIAR

    Returns:
        Krotka (typ_zbioru, lista rekordów)
    """
    path = Path(filepath)
    if path.suffix == ".json":
        return load_demagog(filepath)
    elif path.suffix == ".tsv":
        return load_liar(filepath)
    else:
        raise ValueError(
            f"Nieobsługiwany format pliku: {path.suffix}. "
            "Obsługiwane: .json (Demagog), .tsv (LIAR)"
        )

