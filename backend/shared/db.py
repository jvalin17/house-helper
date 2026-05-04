"""SQLite database connection and auto-migration.

Manages the local SQLite database at ~/.panini/panini.db.
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

DEFAULT_DB_DIR = Path.home() / ".panini"
DEFAULT_DB_NAME = "panini.db"

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
        ('token_budget', '{"daily_limit_cost": 0.50, "daily_limit_tokens": null, "ask_threshold": "over_budget", "priority_order": ["resume_gen", "job_search", "cover_letter", "extraction"]}');

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
    (2, """
        ALTER TABLE resumes ADD COLUMN docx_binary BLOB;
    """),
    (3, """
        CREATE TABLE IF NOT EXISTS suggestion_feedback (
            id INTEGER PRIMARY KEY,
            suggestion_text TEXT NOT NULL,
            original_bullet TEXT,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS resume_templates (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            filename TEXT NOT NULL,
            format TEXT NOT NULL,
            raw_text TEXT,
            docx_binary BLOB,
            paragraph_map JSON,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """),
    (4, """
        ALTER TABLE resumes ADD COLUMN is_saved INTEGER DEFAULT 0;
        ALTER TABLE resumes ADD COLUMN save_name TEXT;
    """),
    (5, """
        CREATE TABLE IF NOT EXISTS apartment_listings (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
            source TEXT,
            source_url TEXT,
            title TEXT NOT NULL,
            address TEXT,
            latitude REAL,
            longitude REAL,
            price REAL,
            bedrooms INTEGER,
            bathrooms REAL,
            sqft INTEGER,
            amenities JSON,
            parsed_data JSON,
            match_score REAL,
            is_saved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartment_notes (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER REFERENCES apartment_listings(id),
            visit_date TEXT,
            notes TEXT,
            structured_data JSON,
            specials JSON,
            status TEXT DEFAULT 'interested',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartment_neighborhood (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER REFERENCES apartment_listings(id),
            crime_score REAL,
            grocery_distance_km REAL,
            indian_grocery_distance_km REAL,
            school_rating REAL,
            airport_distance_km REAL,
            airport_drive_minutes INTEGER,
            rush_hour_traffic JSON,
            google_reviews JSON,
            pros_cons JSON,
            raw_data JSON,
            fetched_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartment_cost (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER REFERENCES apartment_listings(id),
            base_rent REAL,
            lease_months INTEGER,
            special_description TEXT,
            special_discount REAL,
            effective_monthly REAL,
            parking_fee REAL DEFAULT 0,
            pet_fee REAL DEFAULT 0,
            utilities_estimate REAL DEFAULT 0,
            total_monthly REAL
        );

        CREATE TABLE IF NOT EXISTS apartment_notifications (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER REFERENCES apartment_listings(id),
            is_read INTEGER DEFAULT 0,
            search_date TEXT,
            match_score REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartment_floor_plans (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER REFERENCES apartment_listings(id),
            image_url TEXT,
            image_binary BLOB,
            unit_type TEXT,
            ai_analysis JSON,
            requirement_scores JSON,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS apartment_preferences (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id),
            location TEXT,
            max_price REAL,
            min_bedrooms INTEGER,
            must_haves JSON,
            layout_requirements JSON,
            auto_search_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """),
    (6, """
        -- Nest Lab tables
        CREATE TABLE IF NOT EXISTS apartment_feature_preferences (
            id INTEGER PRIMARY KEY,
            feature_name TEXT NOT NULL,
            category TEXT NOT NULL,
            preference TEXT NOT NULL DEFAULT 'neutral',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(feature_name)
        );

        CREATE TABLE IF NOT EXISTS apartment_lab_analysis (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
            analysis_type TEXT NOT NULL,
            result JSON NOT NULL,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            estimated_cost REAL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(listing_id, analysis_type)
        );

        CREATE TABLE IF NOT EXISTS apartment_qa_history (
            id INTEGER PRIMARY KEY,
            listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """),
    (7, """
        -- Add unique constraint on apartment_cost.listing_id (one cost breakdown per listing)
        CREATE UNIQUE INDEX IF NOT EXISTS idx_apartment_cost_listing
            ON apartment_cost(listing_id);

        -- Add unique constraint on apartment_neighborhood.listing_id
        CREATE UNIQUE INDEX IF NOT EXISTS idx_apartment_neighborhood_listing
            ON apartment_neighborhood(listing_id);
    """),
    (8, """
        -- Unified credential store for all API keys across all agents
        CREATE TABLE IF NOT EXISTS api_credentials (
            id INTEGER PRIMARY KEY,
            service_name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            api_key TEXT NOT NULL DEFAULT '',
            display_name TEXT NOT NULL,
            signup_url TEXT,
            description TEXT,
            is_enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Seed built-in services (empty keys — user fills in Settings)
        INSERT OR IGNORE INTO api_credentials (service_name, category, display_name, signup_url, description) VALUES
            ('claude', 'ai_provider', 'Claude (Anthropic)', 'https://console.anthropic.com', 'Sonnet 4, Opus 4, Haiku — vision + streaming'),
            ('openai', 'ai_provider', 'OpenAI', 'https://platform.openai.com/api-keys', 'GPT-4o, GPT-4.1 — vision + streaming'),
            ('deepseek', 'ai_provider', 'DeepSeek', 'https://platform.deepseek.com', 'V3/R1 — fast + cheap'),
            ('grok', 'ai_provider', 'Grok (xAI)', 'https://console.x.ai', 'Grok 2'),
            ('gemini', 'ai_provider', 'Gemini (Google)', 'https://aistudio.google.com/apikey', 'Gemini 2.0 Flash/2.5 Pro'),
            ('openrouter', 'ai_provider', 'OpenRouter', 'https://openrouter.ai/keys', 'Multi-provider gateway'),
            ('ollama', 'ai_provider', 'Ollama (Local)', NULL, 'Local models — no API key needed'),
            ('realtyapi', 'data_source', 'RealtyAPI', 'https://www.realtyapi.io', '250 req/mo — apartment images + listings'),
            ('rentcast', 'data_source', 'RentCast', 'https://www.rentcast.io/api', '50 req/mo — market data'),
            ('walkscore', 'data_source', 'Walk Score', 'https://www.walkscore.com/professional/api.php', '5K/day — walk/transit/bike scores'),
            ('google_maps', 'data_source', 'Google Maps', 'https://console.cloud.google.com/apis', '$200/mo credit — distance + commute'),
            ('adzuna', 'data_source', 'Adzuna', 'https://developer.adzuna.com', 'Job search API'),
            ('jooble', 'data_source', 'Jooble', 'https://jooble.org/api/about', 'Job search API');
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
    # Post-migration: move existing resume from settings to templates table
    _migrate_settings_to_template(conn)


def _migrate_settings_to_template(conn: sqlite3.Connection) -> None:
    """One-time migration: if settings has a resume but templates table is empty, create a template."""
    try:
        template_count = conn.execute("SELECT COUNT(*) FROM resume_templates").fetchone()[0]
        if template_count > 0:
            return  # already migrated

        resume_row = conn.execute("SELECT value FROM settings WHERE key = 'original_resume'").fetchone()
        if not resume_row:
            return  # no resume to migrate

        import json
        import base64

        raw_text = json.loads(resume_row["value"])
        if not raw_text or len(raw_text.strip()) < 50:
            return

        docx_binary = None
        paragraph_map = None

        docx_row = conn.execute("SELECT value FROM settings WHERE key = 'original_resume_docx'").fetchone()
        if docx_row:
            docx_binary = base64.b64decode(json.loads(docx_row["value"]))
            # Re-extract text from DOCX to ensure text matches binary
            try:
                import io
                from docx import Document
                docx_document = Document(io.BytesIO(docx_binary))
                import re
                raw_text = "\n".join(
                    re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", paragraph.text).strip()
                    for paragraph in docx_document.paragraphs if paragraph.text.strip()
                )
            except Exception:
                pass  # keep the settings text

        map_row = conn.execute("SELECT value FROM settings WHERE key = 'original_resume_map'").fetchone()
        if map_row:
            paragraph_map = map_row["value"]  # already JSON string

        conn.execute(
            """INSERT INTO resume_templates (name, filename, format, raw_text, docx_binary, paragraph_map, is_default)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            ("My Resume", "imported_resume.docx", "docx", raw_text, docx_binary, paragraph_map),
        )
        conn.commit()
    except Exception:
        pass  # migration is best-effort


def connect_sync(db_path: Path | None = None) -> sqlite3.Connection:
    path = get_db_path(override=db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn
