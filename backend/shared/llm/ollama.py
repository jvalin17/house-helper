"""Ollama LLM provider — local models, no API key needed.

Requires: Ollama installed and running (brew install ollama && ollama serve).
Communicates via HTTP to localhost:11434.
"""

from __future__ import annotations

import json

DEFAULT_MODEL = "llama3.1"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    """Ollama local model provider."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send prompt to local Ollama instance and return the response."""
        import httpx

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        response = httpx.post(
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    def provider_name(self) -> str:
        return "ollama"

    def model_name(self) -> str:
        return self._model
