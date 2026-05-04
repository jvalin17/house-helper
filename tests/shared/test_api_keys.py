"""Shared API key retrieval — tests."""

import json
import sqlite3

import pytest

from shared.db import migrate
from shared.api_keys import get_api_key


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class TestGetApiKey:
    def test_returns_key_when_stored(self, database_connection):
        database_connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
            [json.dumps({"realtyapi": "rt_test_key_123", "rentcast": "rc_test_key_456"})],
        )
        database_connection.commit()
        assert get_api_key(database_connection, "realtyapi") == "rt_test_key_123"
        assert get_api_key(database_connection, "rentcast") == "rc_test_key_456"

    def test_returns_none_when_no_settings(self, database_connection):
        assert get_api_key(database_connection, "realtyapi") is None

    def test_returns_none_for_missing_key_name(self, database_connection):
        database_connection.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
            [json.dumps({"realtyapi": "rt_key"})],
        )
        database_connection.commit()
        assert get_api_key(database_connection, "walkscore") is None

    def test_handles_malformed_json(self, database_connection):
        database_connection.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', 'not-json', datetime('now'))",
        )
        database_connection.commit()
        assert get_api_key(database_connection, "realtyapi") is None

    def test_handles_empty_key_value(self, database_connection):
        database_connection.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
            [json.dumps({"realtyapi": ""})],
        )
        database_connection.commit()
        assert get_api_key(database_connection, "realtyapi") == ""
