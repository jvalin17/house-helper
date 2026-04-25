"""Claude (Anthropic) LLM provider.

Requires: pip install anthropic
API key stored in OS keychain via keyring, or ANTHROPIC_API_KEY env var.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeProvider:
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Claude API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key parameter."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    async def complete(self, prompt: str, system: str | None = None) -> str:
        """Send prompt to Claude and return the response text."""
        client = self._get_client()
        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text

    def provider_name(self) -> str:
        return "claude"

    def model_name(self) -> str:
        return self._model
