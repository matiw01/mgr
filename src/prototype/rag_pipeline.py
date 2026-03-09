"""Moduł RAG pipeline – budowa query engine i fact-checking."""

from __future__ import annotations

import chromadb

from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL_NAME,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_REQUEST_TIMEOUT,
    SIMILARITY_TOP_K,
    SYSTEM_PROMPT,
)

# ── Szablon promptu QA ───────────────────────────────────────────────────────
QA_PROMPT_TEMPLATE = """\
Poniżej znajdują się fragmenty źródłowe z Wikipedii:
---------------------
{context_str}
---------------------

Na podstawie powyższych fragmentów źródłowych oceń prawdziwość następującego
twierdzenia. Jeśli fragmenty nie zawierają wystarczających informacji,
zaznacz to w uzasadnieniu.

Twierdzenie do oceny:
{query_str}

Odpowiedz w formacie:
WERDYKT: <Prawda|Fałsz|Manipulacja>
UZASADNIENIE: <tekst uzasadnienia>
ŹRÓDŁA: <lista tytułów artykułów>
"""


def build_query_engine():
    """Buduje query engine LlamaIndex z ChromaDB i Ollama."""
    # Embedding model
    embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL_NAME)

    # LLM – Llama 3 via Ollama
    llm = Ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        request_timeout=OLLAMA_REQUEST_TIMEOUT,
        system_prompt=SYSTEM_PROMPT,
    )

    # Globalne ustawienia LlamaIndex
    Settings.llm = llm
    Settings.embed_model = embed_model

    # ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # Indeks
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model,
    )

    # Query engine
    qa_prompt = PromptTemplate(QA_PROMPT_TEMPLATE)
    query_engine = index.as_query_engine(
        similarity_top_k=SIMILARITY_TOP_K,
        text_qa_template=qa_prompt,
    )

    return query_engine


def fact_check(claim: str, query_engine=None) -> dict:
    """Weryfikuje twierdzenie i zwraca wynik fact-checkingu.

    Returns:
        dict z kluczami: verdict, explanation, sources, raw_response
    """
    if query_engine is None:
        query_engine = build_query_engine()

    response = query_engine.query(claim)

    # Wyciągnij źródła z metadanych pobranych chunków
    source_titles: list[str] = []
    for node in response.source_nodes:
        title = node.metadata.get("title", "Nieznane źródło")
        if title not in source_titles:
            source_titles.append(title)

    # Parsowanie odpowiedzi
    raw = str(response)
    result = {
        "verdict": _extract_field(raw, "WERDYKT"),
        "explanation": _extract_field(raw, "UZASADNIENIE"),
        "sources": source_titles,
        "raw_response": raw,
    }

    return result


def _extract_field(text: str, field_name: str) -> str:
    """Wyciąga wartość pola z odpowiedzi LLM."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith(field_name.upper() + ":"):
            return stripped[len(field_name) + 1:].strip()
    return ""

