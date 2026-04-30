"""Lazy LLM provider — reads config from DB on every call.

Allows switching models in Settings without restarting.
Services hold a reference to this wrapper, not a concrete provider.
Budget enforcement: checks daily spend limit before each LLM call.
"""

import json
import os
import sqlite3

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


class LazyLLMProvider:
    """Wraps LLM provider lookup. Reads from settings table on each call."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._cached_provider = None
        self._cached_config_hash = None

    def _get_provider(self):
        """Get or refresh the LLM provider from DB settings."""
        row = self._conn.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
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
            from agents.job.repositories.token_repo import TokenRepository
            repo = TokenRepository(self._conn)
            budget = repo.get_budget()
            limit = budget.get("daily_limit_cost")
            if limit is None:
                return  # No limit set
            usage = repo.get_today_usage()
            spent = usage.get("total_cost", 0)
            if spent >= limit:
                raise BudgetExceededError(spent=spent, limit=limit)
        except BudgetExceededError:
            raise
        except Exception:
            pass  # Don't block LLM calls if budget check itself fails

    def complete(self, prompt: str, system: str | None = None, feature: str = "unknown",
                 force_override: bool = False) -> str:
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")

        # Budget enforcement — check before calling LLM
        if not force_override:
            self._check_budget()

        response = provider.complete(prompt, system=system)
        self._log_usage(provider, prompt, system or "", response, feature)
        return response

    def _log_usage(self, provider, prompt: str, system: str, response: str, feature: str) -> None:
        """Log token usage and estimated cost."""
        try:
            from shared.llm.pricing import estimate_cost

            input_tokens = int(len(f"{system} {prompt}".split()) * 1.3)
            output_tokens = int(len(response.split()) * 1.3)
            cost = estimate_cost(provider.provider_name(), provider.model_name(), input_tokens, output_tokens)

            self._conn.execute(
                "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost) VALUES (?, ?, ?, ?)",
                (feature, provider.provider_name(), input_tokens + output_tokens, cost),
            )
            self._conn.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Usage logging failed: %s", e)

    def provider_name(self) -> str:
        provider = self._get_provider()
        return provider.provider_name() if provider else "none"

    def model_name(self) -> str:
        provider = self._get_provider()
        return provider.model_name() if provider else "none"

    def is_configured(self) -> bool:
        return self._get_provider() is not None

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
            }
        return {"active": False, "provider": None, "model": None}
