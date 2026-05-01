"""Custom job sources — TDD tests for user-added job board sources.

Users can add up to 5 custom job sources with name, API URL, and optional API key.
Sources are stored in the settings table as JSON.

Covers:
- Add a custom source (name + URL)
- List returns built-in + custom sources
- Max 5 custom sources enforced
- Delete a custom source
- Toggle custom source on/off
- Update a custom source
"""

import json
import sqlite3
import pytest

from shared.db import migrate


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


def _get_custom_sources(connection: sqlite3.Connection) -> list:
    row = connection.execute("SELECT value FROM settings WHERE key = 'custom_sources'").fetchone()
    if not row:
        return []
    return json.loads(row["value"])


def _save_custom_sources(connection: sqlite3.Connection, sources: list) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('custom_sources', ?, datetime('now'))",
        [json.dumps(sources)],
    )
    connection.commit()


class TestAddCustomSource:
    def test_add_source_stores_in_settings(self, database_connection):
        """Adding a custom source should store it in the settings table."""
        from shared.job_boards.custom_sources import add_custom_source

        result = add_custom_source(database_connection, name="Greenhouse", api_url="https://api.greenhouse.io/jobs")
        assert result["name"] == "Greenhouse"
        assert result["api_url"] == "https://api.greenhouse.io/jobs"
        assert "id" in result

        stored = _get_custom_sources(database_connection)
        assert len(stored) == 1
        assert stored[0]["name"] == "Greenhouse"

    def test_add_source_with_api_key(self, database_connection):
        """Adding a source with an API key should store the key."""
        from shared.job_boards.custom_sources import add_custom_source

        result = add_custom_source(
            database_connection,
            name="MyBoard",
            api_url="https://myboard.com/api/jobs",
            api_key="sk-test-123",
        )
        assert result["has_api_key"] is True

    def test_max_5_sources_enforced(self, database_connection):
        """Cannot add more than 5 custom sources."""
        from shared.job_boards.custom_sources import add_custom_source

        for i in range(5):
            add_custom_source(database_connection, name=f"Source {i+1}", api_url=f"https://source{i+1}.com/jobs")

        with pytest.raises(ValueError, match="maximum"):
            add_custom_source(database_connection, name="Source 6", api_url="https://source6.com/jobs")

    def test_add_requires_name_and_url(self, database_connection):
        """Name and URL are required."""
        from shared.job_boards.custom_sources import add_custom_source

        with pytest.raises(ValueError, match="name"):
            add_custom_source(database_connection, name="", api_url="https://example.com")

        with pytest.raises(ValueError, match="url"):
            add_custom_source(database_connection, name="Board", api_url="")


class TestDeleteCustomSource:
    def test_delete_removes_source(self, database_connection):
        """Deleting a source removes it from settings."""
        from shared.job_boards.custom_sources import add_custom_source, delete_custom_source

        source = add_custom_source(database_connection, name="TempBoard", api_url="https://temp.com/jobs")
        delete_custom_source(database_connection, source["id"])

        stored = _get_custom_sources(database_connection)
        assert len(stored) == 0

    def test_delete_nonexistent_does_not_crash(self, database_connection):
        """Deleting a nonexistent source ID should not raise."""
        from shared.job_boards.custom_sources import delete_custom_source

        delete_custom_source(database_connection, "nonexistent-id")


class TestListCustomSources:
    def test_list_returns_custom_sources(self, database_connection):
        """Listing sources should include custom ones."""
        from shared.job_boards.custom_sources import add_custom_source, list_custom_sources

        add_custom_source(database_connection, name="Board A", api_url="https://a.com/jobs")
        add_custom_source(database_connection, name="Board B", api_url="https://b.com/jobs")

        sources = list_custom_sources(database_connection)
        assert len(sources) == 2
        names = [source["name"] for source in sources]
        assert "Board A" in names
        assert "Board B" in names

    def test_list_empty_returns_empty(self, database_connection):
        """No custom sources returns empty list."""
        from shared.job_boards.custom_sources import list_custom_sources

        sources = list_custom_sources(database_connection)
        assert sources == []


class TestUpdateCustomSource:
    def test_update_name(self, database_connection):
        """Updating a source's name should persist."""
        from shared.job_boards.custom_sources import add_custom_source, update_custom_source, list_custom_sources

        source = add_custom_source(database_connection, name="Old Name", api_url="https://old.com/jobs")
        update_custom_source(database_connection, source["id"], name="New Name")

        sources = list_custom_sources(database_connection)
        assert sources[0]["name"] == "New Name"
        assert sources[0]["api_url"] == "https://old.com/jobs"
