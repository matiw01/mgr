"""Moduł ingestion – pobieranie artykułów z Wikipedii i zapis do ChromaDB."""

from __future__ import annotations

import sys
import wikipedia
import chromadb

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL_NAME,
    WIKIPEDIA_LANGUAGE,
)


def fetch_wikipedia_articles(topics: list[str]) -> list[Document]:
    """Pobiera artykuły z Wikipedii i zwraca listę Document LlamaIndex."""
    wikipedia.set_lang(WIKIPEDIA_LANGUAGE)
    documents: list[Document] = []

    for topic in topics:
        print(f"  📥  Pobieranie artykułu: '{topic}' ...")
        try:
            page = wikipedia.page(topic, auto_suggest=True)
            doc = Document(
                text=page.content,
                metadata={
                    "title": page.title,
                    "url": page.url,
                    "source": "wikipedia",
                },
            )
            documents.append(doc)
            print(f"  ✅  Pobrano: '{page.title}' ({len(page.content)} znaków)")
        except wikipedia.exceptions.DisambiguationError as e:
            print(f"  ⚠️  Niejednoznaczność dla '{topic}'. Próbuję pierwszą opcję...")
            if e.options:
                try:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                    doc = Document(
                        text=page.content,
                        metadata={
                            "title": page.title,
                            "url": page.url,
                            "source": "wikipedia",
                        },
                    )
                    documents.append(doc)
                    print(f"  ✅  Pobrano: '{page.title}' ({len(page.content)} znaków)")
                except Exception as ex:
                    print(f"  ❌  Nie udało się pobrać '{e.options[0]}': {ex}")
        except wikipedia.exceptions.PageError:
            print(f"  ❌  Nie znaleziono artykułu: '{topic}'")
        except Exception as ex:
            print(f"  ❌  Błąd przy pobieraniu '{topic}': {ex}")

    return documents


def ingest_documents(documents: list[Document]) -> None:
    """Dzieli dokumenty na chunki i zapisuje do ChromaDB."""
    if not documents:
        print("Brak dokumentów do zaindeksowania.")
        return

    print(f"\n🔧  Ładowanie modelu embeddingów: {EMBEDDING_MODEL_NAME} ...")
    embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL_NAME)

    print(f"🗄️  Inicjalizacja ChromaDB w: {CHROMA_PERSIST_DIR}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print(f"✂️  Podział na chunki (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}) ...")
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    print("📦  Indeksowanie dokumentów ...")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=[splitter],
        show_progress=True,
    )

    count = chroma_collection.count()
    print(f"\n✅  Gotowe! W kolekcji '{CHROMA_COLLECTION_NAME}' jest {count} chunków.")


def run_ingest(topics: list[str]) -> None:
    """Główna funkcja ingestion."""
    print("=" * 60)
    print("  INGESTION – Pobieranie artykułów z Wikipedii")
    print("=" * 60)
    documents = fetch_wikipedia_articles(topics)
    ingest_documents(documents)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python ingest.py <temat1> <temat2> ...")
        print('Przykład: python ingest.py "Zmiana klimatu" "Szczepionki" "Polska"')
        sys.exit(1)

    topics = sys.argv[1:]
    run_ingest(topics)

