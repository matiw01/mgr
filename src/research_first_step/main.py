#!/usr/bin/env python3
"""Główny moduł – CLI pierwszego etapu badań.

Użycie:
    python -m research_first_step --model <nazwa_modelu> --data <ścieżka_do_pliku>

Przykłady:
    python -m research_first_step --model gemini-2.5-flash-lite --data src/data/demagog-data.json
    python -m research_first_step --model gemini-2.5-flash-lite --data src/data/train.tsv
    python -m research_first_step --model llama3.2:1b --data src/data/demagog-data.json --limit 20
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Upewnij się, że moduły z tego katalogu są importowalne
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_data
from prompts import get_prompts, get_verdict_field, get_valid_labels
from llm_client import create_client, PROVIDERS
from evaluator import compute_metrics, print_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Ekstrakcja werdyktu z odpowiedzi modelu ──────────────────────────────────

def extract_verdict(response: str, verdict_field: str, valid_labels: list[str]) -> str:
    """Wyciąga werdykt z odpowiedzi LLM.

    Szuka linii zaczynającej się od np. 'WERDYKT:' lub 'VERDICT:'
    i dopasowuje wartość do jednej z dozwolonych etykiet.
    """
    for line in response.split("\n"):
        stripped = line.strip()
        # Usuń ewentualne formatowanie Markdown (np. **WERDYKT:**)
        cleaned = stripped.replace("*", "").replace("#", "").strip()

        if cleaned.upper().startswith(verdict_field.upper() + ":"):
            value = cleaned[len(verdict_field) + 1:].strip()
            # Usuń otaczające cudzysłowy / nawiasy
            value = value.strip("\"'<>").strip()

            # Dokładne dopasowanie (case-insensitive)
            for label in valid_labels:
                if value.lower() == label.lower():
                    return label

            # Dopasowanie częściowe – etykieta zawarta w wartości
            for label in valid_labels:
                if label.lower() in value.lower():
                    return label

            # Nie udało się dopasować – zwróć surową wartość
            return value

    return "UNKNOWN"


# ── Główna pętla klasyfikacji ─────────────────────────────────────────────────

def run_classification(
    model_name: str,
    data_file: str,
    output_dir: str | None = None,
    limit: int | None = None,
    provider: str | None = None,
) -> None:
    """Przeprowadza klasyfikację wszystkich wypowiedzi ze zbioru danych."""

    # 1. Ładowanie danych
    logger.info(f"Ładowanie danych z: {data_file}")
    dataset_type, records = load_data(data_file)
    logger.info(f"Typ zbioru: {dataset_type}, liczba rekordów: {len(records)}")

    if limit:
        records = records[:limit]
        logger.info(f"Ograniczono do {limit} rekordów")

    # 2. Przygotowanie promptów
    system_prompt, user_template = get_prompts(dataset_type)
    verdict_field = get_verdict_field(dataset_type)
    valid_labels = get_valid_labels(dataset_type)

    # 3. Inicjalizacja klienta LLM
    logger.info(f"Inicjalizacja modelu: {model_name}" + (f" (provider: {provider})" if provider else ""))
    client = create_client(model_name, provider=provider)

    # 4. Klasyfikacja
    results: list[dict] = []
    y_true: list[str] = []
    y_pred: list[str] = []

    total = len(records)
    logger.info(f"Rozpoczynam klasyfikację {total} wypowiedzi...")

    for i, record in enumerate(records):
        statement = record["statement"]
        true_label = record["label"]

        user_message = user_template.format(statement=statement)

        truncated = statement[:100] + ("..." if len(statement) > 100 else "")
        logger.info(f"[{i + 1}/{total}] {truncated}")

        max_retries = 3
        raw_response = f"ERROR: no attempts made"
        predicted_label = "ERROR"
        for attempt in range(1, max_retries + 1):
            try:
                raw_response = client.classify(system_prompt, user_message)
                predicted_label = extract_verdict(raw_response, verdict_field, valid_labels)
            except Exception as e:
                logger.error(f"  Błąd przy klasyfikacji (próba {attempt}/{max_retries}): {e}")
                raw_response = f"ERROR: {e}"
                predicted_label = "ERROR"
            if predicted_label not in ("ERROR", "UNKNOWN"):
                break
            if attempt < max_retries:
                logger.warning(f"  Wynik '{predicted_label}' – ponawiam zapytanie (próba {attempt + 1}/{max_retries})...")
                time.sleep(1.0 * pow(2, attempt))

        result_entry = {
            "index": i,
            "statement": statement,
            "true_label": true_label,
            "predicted_label": predicted_label,
            "raw_response": raw_response,
        }
        # Dodaj dodatkowe metadane z rekordu
        for key in record:
            if key not in ("statement", "label"):
                result_entry[key] = record[key]

        results.append(result_entry)

        if predicted_label not in ("ERROR", "UNKNOWN"):
            y_true.append(true_label)
            y_pred.append(predicted_label)

        # Status
        status = "✅" if predicted_label == true_label else "❌"
        logger.info(f"  {status}  Prawdziwa: {true_label} | Predykcja: {predicted_label}")

        # Opóźnienie między zapytaniami (rate limiting)
        time.sleep(0.5)

    # 5. Obliczanie metryk
    if y_true:
        # Uwzględnij wszystkie etykiety (z definicji + ewentualnie nowe z predykcji)
        all_labels = list(valid_labels)
        for label in set(y_true + y_pred):
            if label not in all_labels:
                all_labels.append(label)

        metrics = compute_metrics(y_true, y_pred, all_labels)
        print_metrics(metrics, all_labels)
    else:
        metrics = {}
        logger.warning("Brak wyników do obliczenia metryk.")

    # 6. Zapis wyników
    resolved_output_dir: str = output_dir if output_dir is not None else os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
    )
    os.makedirs(resolved_output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model_name.replace("/", "_").replace(":", "_")

    output_file = os.path.join(
        resolved_output_dir,
        f"results_{dataset_type}_{safe_model}_{timestamp}.json",
    )

    output_data = {
        "model": model_name,
        "provider": client.model_name and provider or "auto",
        "dataset_type": dataset_type,
        "data_file": os.path.abspath(data_file),
        "timestamp": timestamp,
        "total_records": total,
        "classified": len(y_true),
        "errors_and_unknowns": total - len(y_true),
        "metrics": metrics,
        "results": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Wyniki zapisano do: {output_file}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pierwszy etap badań – klasyfikacja wypowiedzi przez LLM (sekcja 3.3.1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Przykłady użycia:
  python -m research_first_step -m gemini-2.5-flash-lite -d data/demagog-data.json
  python -m research_first_step -m gemini-2.5-flash-lite -d data/train.tsv
  python -m research_first_step -m llama-3.3-70b-versatile -p groq -d data/demagog-data.json
  python -m research_first_step -m llama3.2:1b -p ollama -d data/demagog-data.json
  python -m research_first_step -m gemini-2.5-flash-lite -d data/train.tsv --limit 50
        """,
    )

    parser.add_argument(
        "--model", "-m",
        required=True,
        help=(
            "Nazwa modelu LLM. "
            "Np.: 'gemini-2.5-flash-lite', 'llama-3.3-70b-versatile', 'llama3.2:1b'"
        ),
    )
    parser.add_argument(
        "--provider", "-p",
        choices=list(PROVIDERS),
        default=None,
        help=(
            "Dostawca LLM: 'google' (Gemini API), 'groq' (Groq Cloud), 'ollama' (lokalny). "
            "Domyślnie: auto-detekcja na podstawie nazwy modelu "
            "('gemini'→google, 'groq'→groq, inne→ollama)."
        ),
    )
    parser.add_argument(
        "--data", "-d",
        required=True,
        help="Ścieżka do pliku z danymi (.json → Demagog, .tsv → LIAR)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Katalog na wyniki (domyślnie: research_first_step/results/)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Ogranicz liczbę przetwarzanych rekordów (przydatne do testów)",
    )

    args = parser.parse_args()

    run_classification(
        model_name=args.model,
        data_file=args.data,
        output_dir=args.output,
        limit=args.limit,
        provider=args.provider,
    )


if __name__ == "__main__":
    main()



