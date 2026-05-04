"""Shared API key retrieval — reads from unified api_credentials table.

Falls back to legacy apartment_api_keys JSON blob for backward compatibility.
"""

import json
import sqlite3


def get_api_key(connection: sqlite3.Connection, key_name: str) -> str | None:
    """Retrieve an API key by name.

    First checks api_credentials table (new unified store).
    Falls back to apartment_api_keys JSON blob (legacy).
    """
    # Try unified credential store first
    try:
        row = connection.execute(
            "SELECT api_key FROM api_credentials WHERE service_name = ? AND is_enabled = 1",
            (key_name,),
        ).fetchone()
        if row and row["api_key"]:
            return row["api_key"]
    except Exception:
        pass  # Table might not exist yet (pre-migration)

    # Fallback: legacy apartment_api_keys JSON blob
    try:
        legacy_row = connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
        ).fetchone()
        if legacy_row:
            keys = json.loads(legacy_row["value"])
            return keys.get(key_name)
    except (json.JSONDecodeError, TypeError, Exception):
        pass

    return None
