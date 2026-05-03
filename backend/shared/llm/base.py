"""LLM provider protocol — the interface all providers implement.

Services call provider.complete(prompt) without knowing
if it's Claude, OpenAI, Ollama, or anything else.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must implement."""

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt and return the completion text."""
        ...

    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'claude', 'openai')."""
        ...

    def model_name(self) -> str:
        """Return the model identifier (e.g., 'claude-sonnet-4-20250514')."""
        ...


class VisionCapable(Protocol):
    """Protocol for providers that support image inputs.

    Not all providers support vision. Check with:
        if isinstance(provider, VisionCapable): ...
    """

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None
    ) -> str:
        """Send a prompt with images and return the completion text.

        images: list of {"data": base64_string, "media_type": "image/jpeg"}
                or {"url": "https://..."}
        """
        ...


class StreamCapable(Protocol):
    """Protocol for providers that support streaming responses.

    Not all providers support streaming. Check with:
        hasattr(provider, 'complete_stream')

    Yields text chunks as they arrive from the LLM.
    """

    def complete_stream(
        self, prompt: str, system: str | None = None
    ):
        """Stream a completion, yielding text chunks.

        Returns an iterator/generator of string chunks.
        """
        ...
