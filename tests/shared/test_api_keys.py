"""Shared API key retrieval — tests for backward-compatible wrapper.

api_keys.get_api_key() delegates to CredentialStore.get_key().
"""

import sqlite3

import pytest

from shared.db import migrate
from shared.api_keys import get_api_key
from shared.credentials import CredentialStore


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class TestGetApiKey:
    def test_returns_key_when_stored(self, database_connection):
        credential_store = CredentialStore(database_connection)
        credential_store.set_key("realtyapi", "rt_test_key_123")
        credential_store.set_key("rentcast", "rc_test_key_456")
        assert get_api_key(database_connection, "realtyapi") == "rt_test_key_123"
        assert get_api_key(database_connection, "rentcast") == "rc_test_key_456"

    def test_returns_none_when_no_key_set(self, database_connection):
        assert get_api_key(database_connection, "realtyapi") is None

    def test_returns_none_for_unknown_service(self, database_connection):
        assert get_api_key(database_connection, "nonexistent_service") is None

    def test_delegates_to_credential_store(self, database_connection):
        """get_api_key is a thin wrapper around CredentialStore.get_key."""
        credential_store = CredentialStore(database_connection)
        credential_store.set_key("walkscore", "ws_test_key")
        assert get_api_key(database_connection, "walkscore") == "ws_test_key"
