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

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None
    ) -> str:
        """Send prompt with images to OpenAI Vision (GPT-4o, GPT-4.1).

        images: list of {"data": base64_string, "media_type": "image/jpeg"}
                or {"url": "https://..."}
        """
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Build content array: images + text
        content_parts = []
        for image in images:
            if "data" in image:
                media_type = image.get("media_type", "image/jpeg")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image['data']}",
                    },
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
        """Stream a completion from OpenAI, yielding text chunks."""
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
