"""SQLite database connection and auto-migration.

Manages the local SQLite database at ~/.house-helper/house-helper.db.
Uses PRAGMA user_version for schema versioning — migrations run
automatically on every app startup. Silent, no user interaction.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB_DIR = Path.home() / ".house-helper"
DEFAULT_DB_NAME = "house-helper.db"

# Each migration is (version_number, sql_statements).
# App checks current version on startup and applies pending migrations.
MIGRATIONS: list[tuple[int, str]] = [
    (1, """
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            start_date TEXT,
            end_date TEXT,
            description TEXT,
            metadata JSON,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            proficiency TEXT,
            source_experience_id INTEGER REFERENCES experiences(id),
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY,
            experience_id INTEGER REFERENCES experiences(id),
            description TEXT NOT NULL,
            metric TEXT,
            impact TEXT,
            metadata JSON,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY,
            institution TEXT NOT NULL,
            degree TEXT,
            field TEXT,
            start_date TEXT,
            end_date TEXT,
            metadata JSON,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            tech_stack JSON,
            url TEXT,
            metadata JSON,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT,
            source_url TEXT,
            source_text TEXT,
            parsed_data JSON NOT NULL,
            match_score REAL,
            match_breakdown JSON,
            status TEXT DEFAULT 'saved',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            content TEXT NOT NULL,
            preferences JSON NOT NULL,
            export_path TEXT,
            export_format TEXT,
            feedback INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cover_letters (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            content TEXT NOT NULL,
            preferences JSON,
            export_path TEXT,
            export_format TEXT,
            feedback INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id) NOT NULL,
            resume_id INTEGER REFERENCES resumes(id),
            cover_letter_id INTEGER REFERENCES cover_letters(id),
            status TEXT NOT NULL DEFAULT 'applied',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS application_status_history (
            id INTEGER PRIMARY KEY,
            application_id INTEGER REFERENCES applications(id) NOT NULL,
            status TEXT NOT NULL,
            changed_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            defaults JSON NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calibration_judgements (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            match_score REAL NOT NULL,
            match_features JSON NOT NULL,
            user_rating TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS calibration_weights (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            weights JSON NOT NULL DEFAULT '{"skills_overlap": 0.3, "semantic_sim": 0.3, "tfidf": 0.2, "experience_years": 0.2}',
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS llm_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            provider TEXT,
            model TEXT,
            base_url TEXT,
            config JSON
        );
    """),
]


def get_db_path(override: Path | None = None) -> Path:
    """Return the path to the SQLite database file."""
    if override is not None:
        return override
    return DEFAULT_DB_DIR / DEFAULT_DB_NAME


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version from PRAGMA user_version."""
    cursor = conn.execute("PRAGMA user_version")
    return cursor.fetchone()[0]


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending migrations based on PRAGMA user_version."""
    current_version = get_schema_version(conn)

    for version, sql in MIGRATIONS:
        if version > current_version:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()


def connect_sync(db_path: Path | None = None) -> sqlite3.Connection:
    """Create a synchronous SQLite connection with WAL mode."""
    path = get_db_path(override=db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    migrate(conn)
    return conn
