"""LLM provider factory — creates the right provider from config.

Config is read from the llm_config table or passed directly.
"""

from __future__ import annotations

from shared.llm.base import LLMProvider

SUPPORTED_PROVIDERS = ["claude", "openai", "ollama", "huggingface"]


def create_provider(config: dict) -> LLMProvider | None:
    """Create an LLM provider from a config dict.

    Config keys: provider, model, base_url, api_key.
    Returns None if provider is None or not configured.
    """
    provider_name = config.get("provider")

    if provider_name is None:
        return None

    if provider_name == "claude":
        from shared.llm.claude import ClaudeProvider

        return ClaudeProvider(
            api_key=config.get("api_key"),
            model=config.get("model", "claude-sonnet-4-20250514"),
        )

    if provider_name == "openai":
        from shared.llm.openai import OpenAIProvider

        return OpenAIProvider(
            api_key=config.get("api_key"),
            model=config.get("model", "gpt-4o"),
        )

    if provider_name == "ollama":
        from shared.llm.ollama import OllamaProvider

        return OllamaProvider(
            model=config.get("model", "llama3.1"),
            base_url=config.get("base_url", "http://localhost:11434"),
        )

    if provider_name == "huggingface":
        from shared.llm.huggingface import HuggingFaceProvider

        return HuggingFaceProvider(
            api_key=config.get("api_key"),
            model=config.get("model", "mistralai/Mistral-7B-Instruct-v0.3"),
            base_url=config.get("base_url", "https://api-inference.huggingface.co/models"),
        )

    raise ValueError(f"Unknown LLM provider: '{provider_name}'")


def list_available_providers() -> list[str]:
    """List all supported provider names."""
    return list(SUPPORTED_PROVIDERS)
