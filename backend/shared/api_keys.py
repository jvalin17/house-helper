"""Shared API key retrieval — single function used by all services.

Reads from the apartment_api_keys JSON blob in the settings table.
Replaces duplicate get_realtyapi_key / get_rentcast_api_key / _get_api_key functions.
"""

import json
import sqlite3


def get_api_key(connection: sqlite3.Connection, key_name: str) -> str | None:
    """Retrieve an API key by name from settings.

    Keys stored as JSON: {"realtyapi": "rt_...", "rentcast": "rc_...", "walkscore": "ws_..."}
    """
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
    ).fetchone()
    if not row:
        return None
    try:
        keys = json.loads(row["value"])
        return keys.get(key_name)
    except (json.JSONDecodeError, TypeError):
        return None
