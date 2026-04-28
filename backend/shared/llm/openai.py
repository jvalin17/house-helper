"""OpenAI LLM provider.

Requires: pip install openai
API key via OPENAI_API_KEY env var.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    """OpenAI-compatible API provider. Works with OpenAI, DeepSeek, Grok, Gemini."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, base_url: str | None = None):
        self._model = model
        self._base_url = base_url
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "API key required. Set the appropriate env var "
                "or pass api_key parameter."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            kwargs = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send prompt to OpenAI and return the response text."""
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content

    def provider_name(self) -> str:
        return "openai"

    def model_name(self) -> str:
        return self._model
