"""OpenAI LLM provider.

Requires: pip install openai
API key via OPENAI_API_KEY env var.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    """OpenAI API provider."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var "
                "or pass api_key parameter."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    async def complete(self, prompt: str, system: str | None = None) -> str:
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
