"""Moduł ewaluacji – obliczanie metryk klasyfikacji."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List


def compute_metrics(y_true: List[str], y_pred: List[str], labels: List[str]) -> Dict:
    """Oblicza metryki klasyfikacji.

    Metryki (zgodnie z sekcją 3.3.1 pracy):
    - Dokładność (Accuracy)
    - Precyzja (Precision) per klasa
    - Czułość (Recall) per klasa
    - F1-score per klasa
    - Macro F1-score

    Returns:
        Słownik z kluczami: per_class, accuracy, macro_precision,
        macro_recall, macro_f1, confusion_matrix, total_samples
    """
    # Macierz pomyłek
    confusion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for true, pred in zip(y_true, y_pred):
        confusion[true][pred] += 1

    # Metryki per klasa
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

    # Macro uśrednienie (tylko klasy z support > 0)
    classes_with_support = [l for l in labels if per_class[l]["support"] > 0]
    n = len(classes_with_support)
    macro_precision = (
        sum(per_class[l]["precision"] for l in classes_with_support) / n
        if n > 0
        else 0.0
    )
    macro_recall = (
        sum(per_class[l]["recall"] for l in classes_with_support) / n
        if n > 0
        else 0.0
    )
    macro_f1 = (
        sum(per_class[l]["f1"] for l in classes_with_support) / n if n > 0 else 0.0
    )

    # Dokładność
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0.0

    # Macierz pomyłek jako zagnieżdżony słownik
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


def print_metrics(metrics: Dict, labels: List[str]) -> None:
    """Wyświetla metryki w sformatowanej tabeli."""
    print()
    print("=" * 80)
    print("  WYNIKI KLASYFIKACJI")
    print("=" * 80)

    print(f"\n  Liczba próbek:          {metrics['total_samples']}")
    print(f"  Dokładność (Accuracy):  {metrics['accuracy']:.4f}")
    print(f"  Macro Precision:        {metrics['macro_precision']:.4f}")
    print(f"  Macro Recall:           {metrics['macro_recall']:.4f}")
    print(f"  Macro F1-score:         {metrics['macro_f1']:.4f}")

    print()
    print("-" * 80)
    print(f"  {'Klasa':<20} {'Precision':>10} {'Recall':>10} {'F1-score':>10} {'Support':>10}")
    print("-" * 80)

    for label in labels:
        m = metrics["per_class"].get(label, {})
        print(
            f"  {label:<20} "
            f"{m.get('precision', 0):>10.4f} "
            f"{m.get('recall', 0):>10.4f} "
            f"{m.get('f1', 0):>10.4f} "
            f"{m.get('support', 0):>10}"
        )

    print("-" * 80)

    # Macierz pomyłek
    print("\n  Macierz pomyłek (wiersze: prawdziwe, kolumny: predykcje):")
    print()

    # Nagłówek
    max_len = max(len(l) for l in labels)
    col_width = max(max_len + 2, 8)

    header = " " * (col_width + 2)
    for label in labels:
        header += f"{label:>{col_width}}"
    print(f"  {header}")

    cm = metrics["confusion_matrix"]
    for true_label in labels:
        row = f"  {true_label:<{col_width + 2}}"
        for pred_label in labels:
            val = cm.get(true_label, {}).get(pred_label, 0)
            row += f"{val:>{col_width}}"
        print(row)

    print()

