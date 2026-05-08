"""Service registry — tests for built-in service sync on startup.

Covers: sync adds missing services, updates categories, doesn't overwrite keys,
cleans up obsolete entries.
"""

import sqlite3

import pytest

from shared.db import migrate
from shared.service_registry import sync_built_in_services, BUILT_IN_SERVICES


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def test_sync_adds_all_built_in_services(database_connection):
    """First sync populates all built-in services with empty keys."""
    # Migration already seeds some — sync should add any missing
    added_count = sync_built_in_services(database_connection)

    rows = database_connection.execute("SELECT service_name FROM api_credentials").fetchall()
    service_names = {row["service_name"] for row in rows}

    for built_in_service in BUILT_IN_SERVICES:
        assert built_in_service["service_name"] in service_names, f"Missing: {built_in_service['service_name']}"


def test_sync_does_not_overwrite_existing_keys(database_connection):
    """Sync preserves user-entered API keys."""
    # Set a key for realtyapi
    database_connection.execute(
        "UPDATE api_credentials SET api_key = 'user-secret-key-12345' WHERE service_name = 'realtyapi'"
    )
    database_connection.commit()

    sync_built_in_services(database_connection)

    row = database_connection.execute(
        "SELECT api_key FROM api_credentials WHERE service_name = 'realtyapi'"
    ).fetchone()
    assert row["api_key"] == "user-secret-key-12345"


def test_sync_updates_category_if_changed(database_connection):
    """If a service's category changes in BUILT_IN_SERVICES, sync updates it."""
    # Manually change category
    database_connection.execute(
        "UPDATE api_credentials SET category = 'old_category' WHERE service_name = 'walkscore'"
    )
    database_connection.commit()

    sync_built_in_services(database_connection)

    row = database_connection.execute(
        "SELECT category FROM api_credentials WHERE service_name = 'walkscore'"
    ).fetchone()
    assert row["category"] == "shared_source"  # restored to correct value


def test_sync_cleans_up_obsolete_entries(database_connection):
    """Obsolete services with empty keys are deleted."""
    # Insert an obsolete service
    database_connection.execute(
        "INSERT INTO api_credentials (service_name, category, display_name, api_key) VALUES ('jooble', 'data_source', 'Jooble', '')"
    )
    database_connection.commit()

    sync_built_in_services(database_connection)

    row = database_connection.execute(
        "SELECT id FROM api_credentials WHERE service_name = 'jooble'"
    ).fetchone()
    assert row is None  # cleaned up


def test_sync_idempotent(database_connection):
    """Running sync twice produces same result."""
    sync_built_in_services(database_connection)
    count_after_first = database_connection.execute("SELECT COUNT(*) as count FROM api_credentials").fetchone()["count"]

    sync_built_in_services(database_connection)
    count_after_second = database_connection.execute("SELECT COUNT(*) as count FROM api_credentials").fetchone()["count"]

    assert count_after_first == count_after_second
