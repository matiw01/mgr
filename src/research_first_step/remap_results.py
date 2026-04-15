#!/usr/bin/env python3
"""Skrypt do przebudowy plików wyników w folderze results/.

Zmienia klasy klasyfikacji:
  LIAR:
    "Mostly True"   → "True"
    "Half True"     → "Manipulation"
    "Mostly False"  → "Manipulation"
    "Pants on Fire" → "False"

  Demagog:
    "Częściowa prawda" → "Prawda"

Po zmapowaniu etykiet przelicza od nowa metryki klasyfikacji.

Użycie:
    python remap_results.py
    python remap_results.py --results-dir ścieżka/do/results
    python remap_results.py --dry-run          # podgląd bez zapisu
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from typing import Dict, List

# ── Mapowania etykiet ─────────────────────────────────────────────────────────

LIAR_REMAP = {
    "Mostly True": "True",
    "Half True": "Manipulation",
    "Mostly False": "Manipulation",
    "Pants on Fire": "False",
}

DEMAGOG_REMAP = {
    "Częściowa prawda": "Prawda",
}

NEW_LIAR_LABELS = ["True", "Manipulation", "False"]
NEW_DEMAGOG_LABELS = ["Prawda", "Fałsz", "Manipulacja"]


# ── Obliczanie metryk (kopia logiki z evaluator.py) ──────────────────────────

def compute_metrics(y_true: List[str], y_pred: List[str], labels: List[str]) -> Dict:
    """Oblicza metryki klasyfikacji."""
    confusion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for true, pred in zip(y_true, y_pred):
        confusion[true][pred] += 1

    per_class: Dict[str, Dict] = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in labels if other != label)
        fn = sum(confusion[label][other] for other in labels if other != label)
        support = tp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    classes_with_support = [l for l in labels if per_class[l]["support"] > 0]
    n = len(classes_with_support)
    macro_precision = (
        sum(per_class[l]["precision"] for l in classes_with_support) / n if n > 0 else 0.0
    )
    macro_recall = (
        sum(per_class[l]["recall"] for l in classes_with_support) / n if n > 0 else 0.0
    )
    macro_f1 = (
        sum(per_class[l]["f1"] for l in classes_with_support) / n if n > 0 else 0.0
    )

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0.0

    cm: Dict[str, Dict[str, int]] = {}
    for true_label in labels:
        cm[true_label] = {}
        for pred_label in labels:
            cm[true_label][pred_label] = confusion[true_label][pred_label]

    return {
        "per_class": per_class,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "confusion_matrix": cm,
        "total_samples": len(y_true),
    }


# ── Główna logika ────────────────────────────────────────────────────────────

def remap_label(label: str, remap: Dict[str, str]) -> str:
    """Mapuje etykietę na nową klasę (lub zwraca oryginalną jeśli brak mapowania)."""
    return remap.get(label, label)


def process_result_file(filepath: str, dry_run: bool = False) -> None:
    """Przetwarza jeden plik wyników – przemapowuje etykiety i przelicza metryki."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    dataset_type = data.get("dataset_type", "")
    if dataset_type == "liar":
        remap = LIAR_REMAP
        new_labels = NEW_LIAR_LABELS
    elif dataset_type == "demagog":
        remap = DEMAGOG_REMAP
        new_labels = NEW_DEMAGOG_LABELS
    else:
        print(f"  ⚠️  Nieznany dataset_type '{dataset_type}' – pomijam: {filepath}")
        return

    # Przemapuj etykiety w wynikach
    y_true: List[str] = []
    y_pred: List[str] = []

    for entry in data.get("results", []):
        old_true = entry["true_label"]
        old_pred = entry["predicted_label"]

        new_true = remap_label(old_true, remap)
        new_pred = remap_label(old_pred, remap)

        entry["true_label"] = new_true
        entry["predicted_label"] = new_pred

        # Zachowaj oryginalne etykiety
        if "original_true_label" not in entry:
            entry["original_true_label"] = old_true
        if "original_predicted_label" not in entry:
            entry["original_predicted_label"] = old_pred

        if new_pred not in ("ERROR", "UNKNOWN"):
            y_true.append(new_true)
            y_pred.append(new_pred)

    # Przelicz metryki
    all_labels = list(new_labels)
    for label in set(y_true + y_pred):
        if label not in all_labels:
            all_labels.append(label)

    if y_true:
        new_metrics = compute_metrics(y_true, y_pred, all_labels)
    else:
        new_metrics = {}

    # Zachowaj stare metryki
    if "original_metrics" not in data:
        data["original_metrics"] = data.get("metrics", {})

    data["metrics"] = new_metrics
    data["classified"] = len(y_true)

    filename = os.path.basename(filepath)
    old_acc = data.get("original_metrics", {}).get("accuracy", "?")
    new_acc = new_metrics.get("accuracy", "?")
    old_f1 = data.get("original_metrics", {}).get("macro_f1", "?")
    new_f1 = new_metrics.get("macro_f1", "?")

    print(f"  📄 {filename}")
    print(f"     Accuracy: {old_acc} → {new_acc}")
    print(f"     Macro F1: {old_f1} → {new_f1}")

    if not dry_run:
        # Utwórz backup
        backup_path = filepath + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"     ✅ Zapisano (backup: {os.path.basename(backup_path)})")
    else:
        print(f"     🔍 Tryb podglądu – brak zapisu")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Przemapowanie klas i przeliczenie metryk w plikach wyników"
    )
    parser.add_argument(
        "--results-dir",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"),
        help="Ścieżka do folderu z wynikami (domyślnie: results/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko podgląd zmian, bez zapisywania",
    )
    args = parser.parse_args()

    results_dir = args.results_dir
    if not os.path.isdir(results_dir):
        print(f"❌ Folder nie istnieje: {results_dir}")
        sys.exit(1)

    json_files = sorted(
        f for f in os.listdir(results_dir)
        if f.endswith(".json") and not f.endswith(".bak.json")
    )

    if not json_files:
        print(f"❌ Brak plików .json w: {results_dir}")
        sys.exit(1)

    print(f"📂 Przetwarzanie {len(json_files)} plików z: {results_dir}")
    print(f"   Tryb: {'PODGLĄD (dry-run)' if args.dry_run else 'ZAPIS'}")
    print()

    for filename in json_files:
        filepath = os.path.join(results_dir, filename)
        try:
            process_result_file(filepath, dry_run=args.dry_run)
        except Exception as e:
            print(f"  ❌ Błąd przy {filename}: {e}")
        print()

    print("✅ Gotowe!")


if __name__ == "__main__":
    main()


