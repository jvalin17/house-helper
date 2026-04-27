"""HuggingFace Inference API provider.

Requires: HUGGINGFACE_TOKEN env var (free tier available).
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
DEFAULT_BASE_URL = "https://api-inference.huggingface.co/models"


class HuggingFaceProvider:
    """HuggingFace Inference API provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.environ.get("HUGGINGFACE_TOKEN")
        if not self._api_key:
            raise ValueError(
                "HuggingFace token required. Set HUGGINGFACE_TOKEN env var "
                "or pass api_key parameter."
            )

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send prompt to HuggingFace Inference API."""
        import httpx

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        response = httpx.post(
            f"{self._base_url}/{self._model}",
            json={"inputs": full_prompt, "parameters": {"max_new_tokens": 4096}},
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "")
            return str(data)

    def provider_name(self) -> str:
        return "huggingface"

    def model_name(self) -> str:
        return self._model
