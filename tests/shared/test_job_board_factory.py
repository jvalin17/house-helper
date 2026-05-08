"""Job board factory — tests for board discovery, fallback, and toggle logic.

Covers: premium board fallback to free boards, source toggling,
disabled sources excluded, Adzuna two-field credential reading.
"""

import sqlite3

import pytest

from shared.db import migrate
from shared.credentials import CredentialStore
from shared.job_boards.factory import (
    get_available_boards,
    get_all_boards,
    set_db_connection,
    toggle_source,
)


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    set_db_connection(connection)
    yield connection
    set_db_connection(None)
    connection.close()


def test_premium_board_excludes_free_boards(database_connection):
    """When JSearch (premium) is available, RemoteOK (free) is excluded."""
    CredentialStore(database_connection).set_key("rapidapi", "rk-test-key-12345")

    available = get_available_boards()
    board_names = [board.board_name() for board in available]

    assert "jsearch" in board_names
    assert "remoteok" not in board_names  # excluded when premium exists


def test_free_boards_used_when_no_premium(database_connection):
    """When no premium boards configured, free boards are available."""
    # No API keys set — only RemoteOK should be available
    available = get_available_boards()
    board_names = [board.board_name() for board in available]

    assert "remoteok" in board_names
    assert "jsearch" not in board_names  # no key


def test_disabled_source_excluded(database_connection):
    """User-disabled sources are not returned."""
    CredentialStore(database_connection).set_key("rapidapi", "rk-test-key-12345")
    toggle_source("jsearch", False)

    available = get_available_boards()
    board_names = [board.board_name() for board in available]

    assert "jsearch" not in board_names


def test_adzuna_requires_both_fields(database_connection):
    """Adzuna needs both app_id and app_key to be available."""
    # Only one field set — should not be available
    CredentialStore(database_connection).set_key("adzuna_app_id", "test-app-id")

    all_boards = get_all_boards()
    adzuna = [board for board in all_boards if board.board_name() == "adzuna"][0]
    assert not adzuna.is_available()

    # Both fields set — now available
    CredentialStore(database_connection).set_key("adzuna_app_key", "test-app-key-67890")
    all_boards = get_all_boards()
    adzuna = [board for board in all_boards if board.board_name() == "adzuna"][0]
    assert adzuna.is_available()
