#!/usr/bin/env python3
"""CLI systemu fact-checkingowego – punkt wejściowy."""

from __future__ import annotations

import argparse
import sys
import os

# Upewnij się, że moduły z tego katalogu są importowalne
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest import run_ingest
from rag_pipeline import build_query_engine, fact_check

# ── Kolory ANSI ───────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

VERDICT_COLORS = {
    "prawda": GREEN,
    "fałsz": RED,
    "manipulacja": YELLOW,
}


def colorize_verdict(verdict: str) -> str:
    """Koloruje werdykt na podstawie jego wartości."""
    color = VERDICT_COLORS.get(verdict.lower().strip(), CYAN)
    return f"{BOLD}{color}{verdict}{RESET}"


def print_result(result: dict) -> None:
    """Wyświetla sformatowany wynik fact-checkingu."""
    print()
    print("─" * 60)
    verdict_display = colorize_verdict(result["verdict"]) if result["verdict"] else f"{YELLOW}Brak werdyktu{RESET}"
    print(f"  {BOLD}WERDYKT:{RESET}       {verdict_display}")
    print()
    if result["explanation"]:
        print(f"  {BOLD}UZASADNIENIE:{RESET}  {result['explanation']}")
        print()
    if result["sources"]:
        print(f"  {BOLD}ŹRÓDŁA:{RESET}")
        for src in result["sources"]:
            print(f"    • {src}")
    print("─" * 60)
    print()


def cmd_ingest(args: argparse.Namespace) -> None:
    """Obsługuje komendę ingestion."""
    run_ingest(args.topics)


def cmd_check(args: argparse.Namespace) -> None:
    """Obsługuje komendę sprawdzania twierdzenia."""
    if args.claim:
        claim = " ".join(args.claim)
        print(f"\n🔍  Weryfikuję twierdzenie: \"{claim}\" ...")
        query_engine = build_query_engine()
        result = fact_check(claim, query_engine=query_engine)
        print_result(result)
    else:
        # Tryb interaktywny
        interactive_mode()


def interactive_mode() -> None:
    """Tryb interaktywny – pętla sprawdzania twierdzeń."""
    print()
    print("=" * 60)
    print(f"  {BOLD}🔍  FACT-CHECKER – Tryb interaktywny{RESET}")
    print("=" * 60)
    print("  Wpisz twierdzenie do weryfikacji lub 'quit' aby zakończyć.")
    print()

    print("⏳  Ładowanie modelu i indeksu...")
    query_engine = build_query_engine()
    print("✅  Gotowe! Możesz zacząć weryfikować twierdzenia.\n")

    while True:
        try:
            claim = input(f"{CYAN}Twierdzenie > {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋  Do widzenia!")
            break

        if not claim:
            continue
        if claim.lower() in ("quit", "exit", "q", "wyjdź"):
            print("👋  Do widzenia!")
            break

        print(f"⏳  Weryfikuję...")
        result = fact_check(claim, query_engine=query_engine)
        print_result(result)


def cmd_interactive(args: argparse.Namespace) -> None:
    """Obsługuje komendę trybu interaktywnego."""
    interactive_mode()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prototyp systemu fact-checkingowego z RAG (LlamaIndex + ChromaDB + Llama 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Przykłady użycia:
  python main.py ingest "Zmiana klimatu" "Szczepionki" "Polska"
  python main.py check "Polska jest największym krajem w UE"
  python main.py interactive
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Dostępne komendy")

    # ── ingest ────────────────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Pobierz artykuły z Wikipedii i zaindeksuj w ChromaDB",
    )
    ingest_parser.add_argument(
        "topics",
        nargs="+",
        help="Lista tematów artykułów Wikipedii do pobrania",
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # ── check ─────────────────────────────────────────────────────────────────
    check_parser = subparsers.add_parser(
        "check",
        help="Sprawdź prawdziwość twierdzenia",
    )
    check_parser.add_argument(
        "claim",
        nargs="*",
        help="Twierdzenie do weryfikacji (jeśli puste – tryb interaktywny)",
    )
    check_parser.set_defaults(func=cmd_check)

    # ── interactive ───────────────────────────────────────────────────────────
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Tryb interaktywny – weryfikacja wielu twierdzeń",
    )
    interactive_parser.set_defaults(func=cmd_interactive)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()

