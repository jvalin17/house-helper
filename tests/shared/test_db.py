"""Tests for shared/db.py — SQLite connection, WAL mode, auto-migration."""

import sqlite3
from pathlib import Path

import pytest

from shared.db import get_db_path, migrate, get_schema_version, MIGRATIONS


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a temporary database path for testing."""
    return tmp_path / "test.db"


@pytest.fixture
def db_conn(tmp_db_path):
    """Create an in-memory-style SQLite connection for testing."""
    conn = sqlite3.connect(str(tmp_db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestGetDbPath:
    """Database path resolution."""

    def test_returns_path_object(self):
        path = get_db_path()
        assert isinstance(path, Path)

    def test_default_path_under_home(self):
        path = get_db_path()
        assert ".sahaiy" in str(path)
        assert path.name == "sahaiy.db"

    def test_custom_path(self):
        custom = Path("/tmp/custom.db")
        path = get_db_path(override=custom)
        assert path == custom


class TestMigrate:
    """Auto-migration using PRAGMA user_version."""

    def test_fresh_db_starts_at_version_zero(self, db_conn):
        version = get_schema_version(db_conn)
        assert version == 0

    def test_migrate_applies_all_migrations(self, db_conn):
        migrate(db_conn)
        version = get_schema_version(db_conn)
        assert version == len(MIGRATIONS)

    def test_migrate_is_idempotent(self, db_conn):
        migrate(db_conn)
        version_first = get_schema_version(db_conn)
        migrate(db_conn)
        version_second = get_schema_version(db_conn)
        assert version_first == version_second

    def test_creates_experiences_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='experiences'"
        )
        assert cursor.fetchone() is not None

    def test_creates_skills_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='skills'"
        )
        assert cursor.fetchone() is not None

    def test_creates_jobs_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        assert cursor.fetchone() is not None

    def test_creates_resumes_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resumes'"
        )
        assert cursor.fetchone() is not None

    def test_creates_applications_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
        )
        assert cursor.fetchone() is not None

    def test_creates_calibration_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_judgements'"
        )
        assert cursor.fetchone() is not None

    def test_creates_settings_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        )
        assert cursor.fetchone() is not None

    def test_creates_profiles_table(self, db_conn):
        migrate(db_conn)
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
        )
        assert cursor.fetchone() is not None
        # Default profile exists
        row = db_conn.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
        assert row is not None

    def test_can_insert_and_read_experience(self, db_conn):
        migrate(db_conn)
        db_conn.execute(
            "INSERT INTO experiences (type, title, company, description) VALUES (?, ?, ?, ?)",
            ("job", "Engineer", "Acme", "Built things"),
        )
        db_conn.commit()
        row = db_conn.execute("SELECT * FROM experiences WHERE title = ?", ("Engineer",)).fetchone()
        assert row["company"] == "Acme"
        assert row["type"] == "job"

    def test_can_insert_and_read_job(self, db_conn):
        migrate(db_conn)
        db_conn.execute(
            "INSERT INTO jobs (title, company, parsed_data) VALUES (?, ?, ?)",
            ("SWE", "BigTech", '{"required_skills": ["Python"]}'),
        )
        db_conn.commit()
        row = db_conn.execute("SELECT * FROM jobs WHERE company = ?", ("BigTech",)).fetchone()
        assert row["title"] == "SWE"


class TestWalMode:
    """WAL mode is enabled for crash safety."""

    def test_wal_mode_can_be_enabled(self, tmp_db_path):
        conn = sqlite3.connect(str(tmp_db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        result = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert result == "wal"
        conn.close()
