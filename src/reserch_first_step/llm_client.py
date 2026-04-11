"""Klienty LLM – abstrakcja dla Gemini, Groq i Ollama."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv

# Załaduj .env z katalogu pakietu
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH)

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstrakcyjny klient LLM."""

    @abstractmethod
    def classify(self, system_prompt: str, user_message: str) -> str:
        """Wysyła zapytanie klasyfikacyjne i zwraca surową odpowiedź modelu."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nazwa modelu."""


class GeminiClient(LLMClient):
    """Klient Google Gemini API (google-genai)."""

    def __init__(self, model: str):
        from google import genai  # type: ignore

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "placeholder":
            raise ValueError(
                "Brak klucza API Gemini. Ustaw GEMINI_API_KEY w pliku "
                f"{_ENV_PATH}"
            )

        self._model = model if model.startswith("models/") else f"models/{model}"
        self._client = genai.Client(api_key=api_key)
        logger.info(f"Zainicjalizowano klienta Gemini: {self._model}")

    @property
    def model_name(self) -> str:
        return self._model

    def classify(self, system_prompt: str, user_message: str) -> str:
        from google.genai import types  # type: ignore

        response = self._client.models.generate_content(
            model=self._model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
            contents=user_message,
        )
        return response.text or ""


class GroqClient(LLMClient):
    """Klient Groq Cloud API."""

    def __init__(self, model: str):
        from groq import Groq  # type: ignore

        # Obsługuje obie nazwy zmiennej środowiskowej
        api_key = (
            os.environ.get("GROQ_API_KEY")
            or os.environ.get("GROK_CLOUD_API_KEY")
        )
        if not api_key or api_key == "placeholder":
            raise ValueError(
                "Brak klucza API Groq. Ustaw GROQ_API_KEY (lub GROK_CLOUD_API_KEY) "
                f"w pliku {_ENV_PATH}"
            )

        self._model = model
        self._client = Groq(api_key=api_key)
        logger.info(f"Zainicjalizowano klienta Groq: {self._model}")

    @property
    def model_name(self) -> str:
        return self._model

    def classify(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content or ""


class OllamaClient(LLMClient):
    """Klient Ollama (REST API)."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url.rstrip("/")
        logger.info(f"Zainicjalizowano klienta Ollama: {self._model} @ {self._base_url}")

    @property
    def model_name(self) -> str:
        return self._model

    def classify(self, system_prompt: str, user_message: str) -> str:
        import requests

        response = requests.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
            },
            timeout=600,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


PROVIDERS = ("google", "groq", "ollama")


def create_client(
    model_name: str,
    provider: str | None = None,
    ollama_base_url: str = "http://localhost:11434",
) -> LLMClient:
    """Tworzy klienta LLM na podstawie nazwy dostawcy.

    provider:
      - 'google'  → Google Gemini API
      - 'groq'    → Groq Cloud API
      - 'ollama'  → lokalny serwer Ollama
      - None      → auto-detekcja na podstawie nazwy modelu
                    ('gemini' → google, 'groq' w nazwie → groq, inne → ollama)
    """
    resolved = provider.lower().strip() if provider else _detect_provider(model_name)

    if resolved == "google":
        return GeminiClient(model_name)
    elif resolved == "groq":
        return GroqClient(model_name)
    elif resolved == "ollama":
        return OllamaClient(model_name, base_url=ollama_base_url)
    else:
        raise ValueError(
            f"Nieznany dostawca: '{resolved}'. "
            f"Dostępne: {', '.join(PROVIDERS)}"
        )


def _detect_provider(model_name: str) -> str:
    """Auto-detekcja dostawcy na podstawie nazwy modelu."""
    name = model_name.lower()
    if "gemini" in name:
        return "google"
    if "groq" in name:
        return "groq"
    return "ollama"
