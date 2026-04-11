"""Klienty LLM – abstrakcja dla Gemini i Ollama."""

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


def create_client(model_name: str, ollama_base_url: str = "http://localhost:11434") -> LLMClient:
    """Tworzy klienta LLM na podstawie nazwy modelu.

    - Jeśli nazwa zawiera 'gemini' → Google Gemini API
    - W przeciwnym razie → Ollama (lokalny serwer)
    """
    if "gemini" in model_name.lower():
        return GeminiClient(model_name)
    else:
        return OllamaClient(model_name, base_url=ollama_base_url)
