"""Ollama LLM provider — local models, no API key needed.

Supports: text completion, streaming, vision (llava/bakllava models).
Requires: Ollama installed and running (brew install ollama && ollama serve).
Communicates via HTTP to localhost:11434.
"""

from __future__ import annotations

import json

from shared.llm.base import LLMProviderBase

DEFAULT_MODEL = "llama3.1"
DEFAULT_BASE_URL = "http://localhost:11434"

# Ollama models known to support vision
VISION_CAPABLE_MODELS = {"llava", "llava:13b", "llava:34b", "bakllava", "moondream"}


class OllamaProvider(LLMProviderBase):
    """Ollama local model provider — streaming and optional vision."""

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

    @property
    def supports_vision(self) -> bool:
        """Vision supported on llava/bakllava/moondream models."""
        model_base = self._model.split(":")[0].lower()
        return model_base in VISION_CAPABLE_MODELS

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None,
    ) -> str:
        """Send prompt with images to Ollama vision model (llava/bakllava)."""
        if not self.supports_vision:
            from shared.llm.base import NotSupportedError
            raise NotSupportedError(
                f"ollama/{self._model}", "vision/image analysis"
            )

        import httpx

        # Ollama expects images as base64 strings in an "images" array
        image_data_list = []
        for image in images:
            if "data" in image:
                image_data_list.append(image["data"])

        payload = {
            "model": self._model,
            "prompt": prompt,
            "images": image_data_list,
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

    def complete_stream(self, prompt: str, system: str | None = None):
        """Stream a completion from Ollama, yielding text chunks."""
        import httpx

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        with httpx.stream(
            "POST",
            f"{self._base_url}/api/generate",
            json=payload,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk_data = json.loads(line)
                    text_chunk = chunk_data.get("response", "")
                    if text_chunk:
                        yield text_chunk

    def provider_name(self) -> str:
        return "ollama"

    def model_name(self) -> str:
        return self._model
