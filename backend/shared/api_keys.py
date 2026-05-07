"""DEPRECATED — use shared.credentials.CredentialStore instead.

This module exists only for backward compatibility with tests that import it.
"""

from shared.credentials import CredentialStore


def get_api_key(connection, key_name: str) -> str | None:
    """Deprecated: use CredentialStore(connection).get_key(key_name)."""
    return CredentialStore(connection).get_key(key_name)
