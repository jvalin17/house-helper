"""Lazy LLM provider — reads config from DB on every call.

Allows switching models in Settings without restarting.
Services hold a reference to this wrapper, not a concrete provider.
"""

import json
import os
import sqlite3

from shared.llm.factory import create_provider


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

    def complete(self, prompt: str, system: str | None = None, feature: str = "unknown") -> str:
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")
        # #region debug log
        try:
            from shared._dbg import dbg
            from agents.job.repositories.token_repo import TokenRepository
            tr = TokenRepository(self._conn)
            budget_info = tr.get_remaining_today()
            limit = (budget_info.get("budget") or {}).get("daily_limit_cost")
            today_cost = (budget_info.get("usage") or {}).get("total_cost") or 0.0
            over = (limit is not None) and (today_cost >= limit)
            dbg(
                "lazy_provider.py:complete",
                "LLM call about to execute (pre-call budget snapshot)",
                {
                    "feature": feature,
                    "provider": provider.provider_name(),
                    "model": provider.model_name(),
                    "daily_limit_cost": limit,
                    "today_cost": today_cost,
                    "is_over_budget": over,
                    "would_be_blocked_if_enforced": over,
                },
                hyp="H4",
            )
        except Exception:
            pass
        # #endregion
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
