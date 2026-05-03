"""OpenAI-compatible LLM provider.

Supports: text completion, vision (GPT-4o+), streaming.
Works with: OpenAI, DeepSeek, Grok, Gemini, OpenRouter, any OpenAI-compatible API.
Requires: pip install openai
"""

from __future__ import annotations

import os

from shared.llm.base import LLMProviderBase

DEFAULT_MODEL = "gpt-4o"

# Models known to support vision (image inputs)
VISION_CAPABLE_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4-turbo"}


class OpenAIProvider(LLMProviderBase):
    """OpenAI-compatible API provider — full capabilities."""

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
        """Send prompt and return the response text."""
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

    @property
    def supports_vision(self) -> bool:
        """Vision supported on GPT-4o and similar models."""
        return self._model in VISION_CAPABLE_MODELS

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None,
    ) -> str:
        """Send prompt with images to OpenAI Vision."""
        if not self.supports_vision:
            from shared.llm.base import NotSupportedError
            raise NotSupportedError(
                f"{self.provider_name()}/{self._model}", "vision/image analysis"
            )

        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        content_parts = []
        for image in images:
            if "data" in image:
                media_type = image.get("media_type", "image/jpeg")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image['data']}"},
                })
            elif "url" in image:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": image["url"]},
                })
        content_parts.append({"type": "text", "text": prompt})

        messages.append({"role": "user", "content": content_parts})

        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return response.choices[0].message.content

    def complete_stream(self, prompt: str, system: str | None = None):
        """Stream a completion, yielding text chunks."""
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        stream_response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )
        for chunk in stream_response:
            delta_content = chunk.choices[0].delta.content if chunk.choices else None
            if delta_content:
                yield delta_content

    def provider_name(self) -> str:
        return "openai"

    def model_name(self) -> str:
        return self._model
