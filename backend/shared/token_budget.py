"""Token budget manager — wraps LLM providers with budget enforcement.

Services call budget_manager.complete() instead of llm_provider.complete().
Tracks usage per feature, enforces daily limits, priority queue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider
    from agents.job.repositories.token_repo import TokenRepository

# Rough token-to-cost estimates (per 1K tokens)
COST_PER_1K = {
    "claude": 0.003,
    "openai": 0.002,
    "ollama": 0.0,
    "huggingface": 0.0,
}


class BudgetExceededError(Exception):
    def __init__(self, remaining: float, estimated: float):
        self.remaining = remaining
        self.estimated = estimated
        super().__init__(
            f"Token budget exceeded. Remaining: ${remaining:.4f}, "
            f"Estimated cost: ${estimated:.4f}"
        )


class BudgetManager:
    """Wraps an LLM provider with budget tracking and enforcement."""

    def __init__(self, llm_provider: LLMProvider | None, token_repo: TokenRepository):
        self._llm = llm_provider
        self._repo = token_repo

    @property
    def has_llm(self) -> bool:
        return self._llm is not None

    @property
    def provider_name(self) -> str:
        return self._llm.provider_name() if self._llm else "none"

    def complete(self, prompt: str, feature: str, system: str | None = None) -> str:
        """LLM call with budget enforcement."""
        if not self._llm:
            raise RuntimeError("No LLM provider configured")

        # Check budget
        remaining = self._repo.get_remaining_today()
        estimated_cost = self._estimate_cost(prompt)

        if remaining.get("remaining_cost") is not None and estimated_cost > remaining["remaining_cost"]:
            raise BudgetExceededError(remaining["remaining_cost"], estimated_cost)

        # Call LLM
        result = await self._llm.complete(prompt, system=system)

        # Track usage
        estimated_tokens = len(prompt.split()) + len(result.split())  # rough estimate
        provider = self._llm.provider_name()
        cost = estimated_tokens / 1000 * COST_PER_1K.get(provider, 0.003)
        self._repo.log_usage(feature, provider, estimated_tokens, cost)

        return result

    def check_budget(self, feature: str) -> dict:
        """Check if budget allows an LLM call for this feature."""
        remaining = self._repo.get_remaining_today()
        budget = self._repo.get_budget()
        has_budget = remaining.get("remaining_cost") is None or remaining["remaining_cost"] > 0
        return {"has_budget": has_budget, "remaining": remaining, "budget": budget}

    def get_usage_summary(self) -> dict:
        return self._repo.get_remaining_today()

    def _estimate_cost(self, prompt: str) -> float:
        if not self._llm:
            return 0.0
        tokens = len(prompt.split()) * 1.3  # rough word-to-token ratio
        provider = self._llm.provider_name()
        return tokens / 1000 * COST_PER_1K.get(provider, 0.003)
