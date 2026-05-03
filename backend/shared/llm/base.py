"""LLM provider base class — the single interface all providers implement.

Every provider (Claude, OpenAI, Ollama, HuggingFace, custom) extends
LLMProviderBase. Capabilities are declared via properties:

    provider.supports_vision    → can it analyze images?
    provider.supports_streaming → can it yield chunks?

Default implementations:
    complete_stream()       → falls back to complete() as one chunk
    complete_with_images()  → raises NotSupportedError

Providers override only what they add. No hasattr() checks needed.
"""

from abc import ABC, abstractmethod


class NotSupportedError(Exception):
    """Raised when a provider doesn't support a requested capability."""

    def __init__(self, provider_name: str, capability: str):
        self.provider_name = provider_name
        self.capability = capability
        super().__init__(
            f"{provider_name} does not support {capability}. "
            f"Use a provider that supports it (e.g., Claude or OpenAI GPT-4o)."
        )


class LLMProviderBase(ABC):
    """Base class for all LLM providers.

    Required (must override):
        complete()       — send prompt, get response
        provider_name()  — e.g., 'claude', 'openai'
        model_name()     — e.g., 'claude-sonnet-4-20250514'

    Optional (override to enable):
        complete_stream()        — streaming text chunks
        complete_with_images()   — vision/image analysis
        supports_vision          — property, default False
        supports_streaming       — property, default True (fallback exists)
    """

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt and return the completion text."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'claude', 'openai')."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g., 'claude-sonnet-4-20250514')."""
        ...

    @property
    def supports_vision(self) -> bool:
        """Whether this provider can analyze images. Override to return True."""
        return False

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider has native streaming. Always True via fallback."""
        return True

    def complete_stream(self, prompt: str, system: str | None = None):
        """Stream a completion, yielding text chunks.

        Default: calls complete() and yields the full response as one chunk.
        Providers with native streaming override this.
        """
        yield self.complete(prompt, system=system)

    def complete_with_images(
        self, prompt: str, images: list[dict], system: str | None = None,
    ) -> str:
        """Send a prompt with images and return the completion text.

        images: list of {"data": base64_string, "media_type": "image/jpeg"}
                or {"url": "https://..."}

        Default: raises NotSupportedError. Providers with vision override this.
        """
        raise NotSupportedError(self.provider_name(), "vision/image analysis")
