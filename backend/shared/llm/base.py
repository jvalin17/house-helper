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
