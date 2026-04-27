"""SQLite database connection and auto-migration.

Manages the local SQLite database at ~/.house-helper/house-helper.db.
Uses PRAGMA user_version for schema versioning.

17 tables, normalized:
  - profiles (1)        — user profiles / focus areas
  - knowledge bank (5)  — experiences, skills, achievements, education, projects
  - jobs (1)            — parsed job postings
  - documents (2)       — resumes, cover_letters
  - applications (2)    — applications, status_history
  - automation (3)      — search_filters, auto_apply_queue, evidence_log
  - config (1)          — settings (key-value, replaces 3 old tables)
  - tracking (2)        — token_usage, calibration_judgements
"""

import sqlite3
from pathlib import Path

DEFAULT_DB_DIR = Path.home() / ".house-helper"
DEFAULT_DB_NAME = "house-helper.db"

MIGRATIONS: list[tuple[int, str]] = [
    (1, """
        -- Profiles
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'focus',
            description TEXT,
            search_title TEXT,
            search_keywords TEXT,
            search_location TEXT,
            search_remote INTEGER DEFAULT 0,
            resume_preferences JSON,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO profiles (id, name, type, description, is_active)
        VALUES (1, 'Default', 'focus', 'Default profile', 1);

        -- Knowledge Bank
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
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
            profile_id INTEGER REFERENCES profiles(id),
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            proficiency TEXT,
            source_experience_id INTEGER REFERENCES experiences(id),
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(name, profile_id)
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

        -- Jobs
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
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

        -- Generated Documents
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
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
            profile_id INTEGER REFERENCES profiles(id),
            job_id INTEGER REFERENCES jobs(id),
            content TEXT NOT NULL,
            preferences JSON,
            export_path TEXT,
            export_format TEXT,
            feedback INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Applications
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
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

        -- Search & Automation
        CREATE TABLE IF NOT EXISTS search_filters (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
            name TEXT NOT NULL,
            filters JSON NOT NULL,
            frequency_hours INTEGER,
            last_run TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS auto_apply_queue (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
            job_id INTEGER REFERENCES jobs(id) NOT NULL,
            resume_id INTEGER REFERENCES resumes(id),
            cover_letter_id INTEGER REFERENCES cover_letters(id),
            apply_method TEXT,
            status TEXT DEFAULT 'pending',
            confirmed_at TEXT,
            applied_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evidence_log (
            id INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            original_text TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Settings (replaces preferences + llm_config + token_budget)
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value JSON NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO settings (key, value) VALUES
        ('preferences', '{"tone": "professional", "length": "1 page", "sections": ["summary", "experience", "skills", "education", "projects"]}'),
        ('llm', '{"provider": null, "model": null, "base_url": null}'),
        ('token_budget', '{"daily_limit_cost": null, "daily_limit_tokens": null, "ask_threshold": "over_budget", "priority_order": ["resume_gen", "job_search", "cover_letter", "extraction"]}');

        -- Tracking
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            feature TEXT NOT NULL,
            provider TEXT NOT NULL,
            tokens_used INTEGER NOT NULL,
            estimated_cost REAL,
            created_at TEXT DEFAULT (datetime('now'))
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
    """),
]


def get_db_path(override: Path | None = None) -> Path:
    if override is not None:
        return override
    return DEFAULT_DB_DIR / DEFAULT_DB_NAME


def get_schema_version(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("PRAGMA user_version")
    return cursor.fetchone()[0]


def migrate(conn: sqlite3.Connection) -> None:
    current_version = get_schema_version(conn)
    for version, sql in MIGRATIONS:
        if version > current_version:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()


def connect_sync(db_path: Path | None = None) -> sqlite3.Connection:
    path = get_db_path(override=db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn
