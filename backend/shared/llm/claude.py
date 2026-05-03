"""Claude (Anthropic) LLM provider.

Supports: text completion, vision (images), streaming.
Requires: pip install anthropic
API key stored in OS keychain via keyring, or ANTHROPIC_API_KEY env var.
"""

from __future__ import annotations

import os

from shared.llm.base import LLMProviderBase

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeProvider(LLMProviderBase):
    """Anthropic Claude API provider — full capabilities."""

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

    def complete(self, prompt: str, system: str | None = None) -> str:
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

    @property
    def supports_vision(self) -> bool:
        return True

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None,
    ) -> str:
        """Send prompt with images to Claude Vision."""
        client = self._get_client()

        content_blocks = []
        for image in images:
            if "data" in image:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image.get("media_type", "image/jpeg"),
                        "data": image["data"],
                    },
                })
            elif "url" in image:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": image["url"],
                    },
                })
        content_blocks.append({"type": "text", "text": prompt})

        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": content_blocks}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text

    def complete_stream(self, prompt: str, system: str | None = None):
        """Stream a completion from Claude, yielding text chunks."""
        client = self._get_client()
        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text_chunk in stream.text_stream:
                yield text_chunk

    def provider_name(self) -> str:
        return "claude"

    def model_name(self) -> str:
        return self._model
