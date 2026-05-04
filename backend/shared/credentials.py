"""Unified credential store — one place for all API keys across all agents.

Replaces scattered JSON blobs (apartment_api_keys, api_keys, llm).
Services call credential_store.get_key("google_maps") — works for any agent.
Auto-discovery: agents check is_configured() to know what's available.
"""

import sqlite3


class CredentialStore:
    """Manages API keys for all services (LLM providers + data sources)."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_key(self, service_name: str) -> str | None:
        """Get API key for a service. Returns None if not configured."""
        row = self._connection.execute(
            "SELECT api_key FROM api_credentials WHERE service_name = ? AND is_enabled = 1",
            (service_name,),
        ).fetchone()
        if not row or not row["api_key"]:
            return None
        return row["api_key"]

    def set_key(self, service_name: str, api_key: str) -> None:
        """Save API key for a service. Creates row if it doesn't exist."""
        existing = self._connection.execute(
            "SELECT id FROM api_credentials WHERE service_name = ?",
            (service_name,),
        ).fetchone()
        if existing:
            self._connection.execute(
                "UPDATE api_credentials SET api_key = ?, updated_at = datetime('now') WHERE service_name = ?",
                (api_key, service_name),
            )
        else:
            self._connection.execute(
                "INSERT INTO api_credentials (service_name, category, display_name, api_key) VALUES (?, 'custom', ?, ?)",
                (service_name, service_name, api_key),
            )
        self._connection.commit()

    def delete_key(self, service_name: str) -> None:
        """Remove API key (set to empty, keep the row for UI display)."""
        self._connection.execute(
            "UPDATE api_credentials SET api_key = '', updated_at = datetime('now') WHERE service_name = ?",
            (service_name,),
        )
        self._connection.commit()

    def is_configured(self, service_name: str) -> bool:
        """Check if a service has a non-empty API key."""
        row = self._connection.execute(
            "SELECT api_key FROM api_credentials WHERE service_name = ? AND is_enabled = 1",
            (service_name,),
        ).fetchone()
        return bool(row and row["api_key"])

    def get_all_services(self) -> list[dict]:
        """Get all services with their status — for the settings UI."""
        rows = self._connection.execute(
            "SELECT service_name, category, display_name, signup_url, description, "
            "is_enabled, (api_key != '' AND api_key IS NOT NULL) as is_configured "
            "FROM api_credentials ORDER BY category, display_name"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_configured_services(self, category: str | None = None) -> list[str]:
        """Get service names that have keys configured — for auto-discovery."""
        if category:
            rows = self._connection.execute(
                "SELECT service_name FROM api_credentials "
                "WHERE api_key != '' AND api_key IS NOT NULL AND is_enabled = 1 AND category = ?",
                (category,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT service_name FROM api_credentials "
                "WHERE api_key != '' AND api_key IS NOT NULL AND is_enabled = 1",
            ).fetchall()
        return [row["service_name"] for row in rows]

    def get_status_map(self) -> dict[str, bool]:
        """Return {service_name: is_configured} for all services."""
        rows = self._connection.execute(
            "SELECT service_name, (api_key != '' AND api_key IS NOT NULL) as is_configured "
            "FROM api_credentials WHERE is_enabled = 1"
        ).fetchall()
        return {row["service_name"]: bool(row["is_configured"]) for row in rows}
