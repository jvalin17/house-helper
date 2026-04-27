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

    def complete(self, prompt: str, system: str | None = None) -> str:
        provider = self._get_provider()
        if not provider:
            raise RuntimeError("No LLM provider configured. Set one in Settings.")
        return provider.complete(prompt, system=system)

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
