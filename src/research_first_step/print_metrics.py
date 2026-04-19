"""Skrypt wyświetlający macierz pomyłek i metryki na podstawie pliku wyników."""

import json
import sys
from evaluator import compute_metrics, print_metrics


def main():
    if len(sys.argv) != 2:
        print(f"Użycie: python {sys.argv[0]} <plik_wyników.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    y_true = [r["true_label"] for r in results]
    y_pred = [r["predicted_label"] for r in results]

    # Determine labels from dataset type
    dataset_type = data.get("dataset_type", "liar")
    if dataset_type == "demagog":
        labels = ["Prawda", "Manipulacja", "Fałsz"]
    else:
        labels = ["True", "Manipulation", "False"]

    metrics = compute_metrics(y_true, y_pred, labels)

    print(f"Model: {data.get('model', 'N/A')}")
    print(f"Dataset: {data.get('dataset_type', 'N/A')}")
    print(f"Plik danych: {data.get('data_file', 'N/A')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print(f"Sklasyfikowanych: {data.get('classified', 'N/A')}")
    print(f"Błędy/nieznane: {data.get('errors_and_unknowns', 'N/A')}")

    print_metrics(metrics, labels)


if __name__ == "__main__":
    main()

