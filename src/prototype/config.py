"""Konfiguracja prototypu systemu fact-checkingowego."""

import os

# ── Ścieżki ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_store")
CHROMA_COLLECTION_NAME = "wikipedia_facts"

# ── Modele ────────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2:1b"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_REQUEST_TIMEOUT = 600.0

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ── Wikipedia ─────────────────────────────────────────────────────────────────
WIKIPEDIA_LANGUAGE = "pl"

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# ── RAG ───────────────────────────────────────────────────────────────────────
SIMILARITY_TOP_K = 3

# ── Prompt systemowy ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
Jesteś profesjonalnym fact-checkerem. Twoim zadaniem jest ocena prawdziwości
podanego twierdzenia na podstawie dostarczonych fragmentów źródłowych
z Wikipedii.

Dla każdego twierdzenia:
1. Przeanalizuj dostarczone fragmenty źródłowe.
2. Oceń twierdzenie i przypisz jeden z werdyktów:
   - **Prawda** – twierdzenie jest zgodne z dostępnymi źródłami.
   - **Fałsz** – twierdzenie jest niezgodne z dostępnymi źródłami.
   - **Manipulacja** – twierdzenie zawiera elementy prawdziwe, ale jest
     zmanipulowane, wyrwane z kontekstu lub wprowadzające w błąd.
3. Podaj krótkie uzasadnienie werdyktu, odwołując się do konkretnych
   fragmentów źródłowych.
4. Wymień tytuły artykułów Wikipedii, które posłużyły jako źródła.

Odpowiedz w formacie:
WERDYKT: <Prawda|Fałsz|Manipulacja>
UZASADNIENIE: <tekst uzasadnienia>
ŹRÓDŁA: <lista tytułów artykułów>
"""
