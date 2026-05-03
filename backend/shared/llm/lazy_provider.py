"""Backward-compatible re-export. LazyLLMProvider renamed to LLMProviderManager."""

from shared.llm.provider_manager import LLMProviderManager, BudgetExceededError

# Keep old name working for existing imports
LazyLLMProvider = LLMProviderManager

__all__ = ["LazyLLMProvider", "LLMProviderManager", "BudgetExceededError"]
