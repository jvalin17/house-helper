"""LLM Provider Manager — configurable provider with budget enforcement.

Reads provider config from DB on each call (hot-swappable in Settings).
Wraps any LLMProviderBase with:
  - Budget enforcement (daily spend limits)
  - Token usage logging
  - Capability checks (vision, streaming)

Previously named LazyLLMProvider — renamed to describe what it does.
"""

import json
import os
import sqlite3

from shared.llm.base import LLMProviderBase, NotSupportedError
from shared.llm.factory import create_provider


class BudgetExceededError(Exception):
    """Raised when daily spend limit is reached."""

    def __init__(self, spent: float, limit: float):
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"Daily budget limit reached: ${spent:.4f} spent of ${limit:.2f} limit. "
            f"Adjust your limit in Settings or retry with override."
        )

    def to_dict(self) -> dict:
        return {
            "error": "budget_exceeded",
            "spent": self.spent,
            "limit": self.limit,
            "remaining": max(0, self.limit - self.spent),
        }


class LLMProviderManager:
    """Manages LLM provider lifecycle, config, budget, and usage logging.

    Reads provider config from the settings DB on each call — switching
    providers in Settings takes effect immediately without restart.
    """

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._cached_provider: LLMProviderBase | None = None
        self._cached_config_hash: str | None = None

    def _get_provider(self) -> LLMProviderBase | None:
        """Get or refresh the LLM provider from DB settings."""
        row = self._connection.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
        if not row:
            self._cached_provider = None
            return None

        config = json.loads(row["value"])
        config_hash = json.dumps(config, sort_keys=True)

        # Only recreate if config changed
        if config_hash != self._cached_config_hash:
            self._cached_config_hash = config_hash

            if not config.get("provider"):
                self._cached_provider = None
                return None

            # Inject API key from env if not in config
            if config["provider"] == "claude" and not config.get("api_key"):
                config["api_key"] = os.environ.get("ANTHROPIC_API_KEY")
            if config["provider"] == "openai" and not config.get("api_key"):
                config["api_key"] = os.environ.get("OPENAI_API_KEY")

            try:
                self._cached_provider = create_provider(config)
            except (ValueError, NotImplementedError):
                self._cached_provider = None

        return self._cached_provider

    def _check_budget(self) -> None:
        """Raise BudgetExceededError if daily spend limit is reached."""
        try:
            from shared.repositories.token_repo import TokenRepository
            token_repository = TokenRepository(self._connection)
            budget = token_repository.get_budget()
            daily_limit = budget.get("daily_limit_cost")
            if daily_limit is None:
                return
            usage = token_repository.get_today_usage()
            total_spent = usage.get("total_cost", 0)
            if total_spent >= daily_limit:
                raise BudgetExceededError(spent=total_spent, limit=daily_limit)
        except BudgetExceededError:
            raise
        except Exception as budget_check_error:
            import logging
            logging.getLogger(__name__).warning(
                "Budget check failed (allowing LLM call): %s", budget_check_error
            )

    def _log_usage(self, provider: LLMProviderBase, prompt: str, system: str, response: str, feature: str) -> None:
        """Log token usage and estimated cost."""
        try:
            from shared.llm.pricing import estimate_cost
            from shared.llm.token_counter import count_text_tokens

            input_tokens = count_text_tokens(f"{system} {prompt}")
            output_tokens = count_text_tokens(response)
            cost = estimate_cost(provider.provider_name(), provider.model_name(), input_tokens, output_tokens)

            self._connection.execute(
                "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost) VALUES (?, ?, ?, ?)",
                (feature, provider.provider_name(), input_tokens + output_tokens, cost),
            )
            self._connection.commit()
        except Exception as logging_error:
            import logging
            logging.getLogger(__name__).debug("Usage logging failed: %s", logging_error)

    # ── Core capabilities ─────────────────────────────────

    def complete(self, prompt: str, system: str | None = None, feature: str = "unknown",
                 force_override: bool = False) -> str:
        """Send prompt to LLM and return response. Budget enforced."""
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")

        if not force_override:
            self._check_budget()

        response = provider.complete(prompt, system=system)
        self._log_usage(provider, prompt, system or "", response, feature)
        return response

    def complete_stream(self, prompt: str, system: str | None = None,
                        feature: str = "unknown", force_override: bool = False):
        """Stream LLM response, yielding text chunks. Budget enforced before streaming starts.

        Works with ALL providers — those without native streaming fall back
        to yielding the complete response as one chunk.
        """
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")

        if not force_override:
            self._check_budget()

        full_response_chunks = []
        for chunk in provider.complete_stream(prompt, system=system):
            full_response_chunks.append(chunk)
            yield chunk

        full_response = "".join(full_response_chunks)
        self._log_usage(provider, prompt, system or "", full_response, feature)

    def complete_with_images(self, prompt: str, images: list[dict], system: str | None = None,
                             feature: str = "unknown", force_override: bool = False) -> str:
        """Send prompt with images to LLM. Budget enforced.

        Raises NotSupportedError if the current provider doesn't support vision.
        """
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")

        if not provider.supports_vision:
            raise NotSupportedError(provider.provider_name(), "vision/image analysis")

        if not force_override:
            self._check_budget()

        response = provider.complete_with_images(prompt, images, system=system)
        self._log_vision_usage(provider, prompt, system or "", response, images, feature)
        return response

    def _log_vision_usage(self, provider: LLMProviderBase, prompt: str, system: str,
                          response: str, images: list[dict], feature: str) -> None:
        """Log token usage for vision calls, including image token estimates."""
        try:
            from shared.llm.pricing import estimate_cost
            from shared.llm.token_counter import count_text_tokens

            text_input_tokens = count_text_tokens(f"{system} {prompt}")
            image_tokens = len(images) * 1_600  # Conservative: ~1MP per image
            input_tokens = text_input_tokens + image_tokens
            output_tokens = count_text_tokens(response)
            cost = estimate_cost(provider.provider_name(), provider.model_name(), input_tokens, output_tokens)

            self._connection.execute(
                "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost) VALUES (?, ?, ?, ?)",
                (feature, provider.provider_name(), input_tokens + output_tokens, cost),
            )
            self._connection.commit()
        except Exception as logging_error:
            import logging
            logging.getLogger(__name__).debug("Vision usage logging failed: %s", logging_error)

    # ── Status & capability checks ────────────────────────

    @property
    def supports_vision(self) -> bool:
        """Check if the current provider can analyze images."""
        provider = self._get_provider()
        return provider is not None and provider.supports_vision

    @property
    def supports_streaming(self) -> bool:
        """Check if the current provider supports streaming. Always True via fallback."""
        provider = self._get_provider()
        return provider is not None and provider.supports_streaming

    def is_configured(self) -> bool:
        """Check if any LLM provider is configured."""
        return self._get_provider() is not None

    def provider_name(self) -> str:
        provider = self._get_provider()
        return provider.provider_name() if provider else "none"

    def model_name(self) -> str:
        provider = self._get_provider()
        return provider.model_name() if provider else "none"

    def get_status(self) -> dict:
        """Return current LLM status for the UI."""
        try:
            provider = self._get_provider()
        except Exception:
            provider = None
        if provider:
            return {
                "active": True,
                "provider": provider.provider_name(),
                "model": provider.model_name(),
                "supports_vision": provider.supports_vision,
                "supports_streaming": provider.supports_streaming,
            }
        return {"active": False, "provider": None, "model": None,
                "supports_vision": False, "supports_streaming": False}
