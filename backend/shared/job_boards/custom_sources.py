"""Custom job sources — user-added job board API endpoints.

Stored in settings table as JSON under key 'custom_sources'.
Max 5 sources. Each has: id, name, api_url, api_key (optional), enabled.
"""

import json
import sqlite3
import uuid


MAX_CUSTOM_SOURCES = 5


def _load_sources(connection: sqlite3.Connection) -> list[dict]:
    """Load custom sources from settings table."""
    row = connection.execute("SELECT value FROM settings WHERE key = 'custom_sources'").fetchone()
    if not row:
        return []
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return []


def _save_sources(connection: sqlite3.Connection, sources: list[dict]) -> None:
    """Persist custom sources to settings table."""
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('custom_sources', ?, datetime('now'))",
        [json.dumps(sources)],
    )
    connection.commit()


def add_custom_source(
    connection: sqlite3.Connection,
    name: str,
    api_url: str,
    api_key: str | None = None,
) -> dict:
    """Add a custom job source. Max 5 allowed."""
    if not name or not name.strip():
        raise ValueError("Source name is required")
    if not api_url or not api_url.strip():
        raise ValueError("API url is required")

    sources = _load_sources(connection)
    if len(sources) >= MAX_CUSTOM_SOURCES:
        raise ValueError(f"Cannot add more than {MAX_CUSTOM_SOURCES} custom sources (maximum reached)")

    new_source = {
        "id": f"custom_{uuid.uuid4().hex[:8]}",
        "name": name.strip(),
        "api_url": api_url.strip(),
        "has_api_key": api_key is not None and len(api_key) > 0,
        "api_key": api_key or "",
        "enabled": True,
    }

    sources.append(new_source)
    _save_sources(connection, sources)

    # Return without exposing the full API key
    return {**new_source, "api_key": "***" if new_source["has_api_key"] else ""}


def delete_custom_source(connection: sqlite3.Connection, source_id: str) -> None:
    """Remove a custom source by ID."""
    sources = _load_sources(connection)
    sources = [source for source in sources if source["id"] != source_id]
    _save_sources(connection, sources)


def list_custom_sources(connection: sqlite3.Connection) -> list[dict]:
    """List all custom sources (API keys masked)."""
    sources = _load_sources(connection)
    return [
        {**source, "api_key": "***" if source.get("has_api_key") else ""}
        for source in sources
    ]


def update_custom_source(connection: sqlite3.Connection, source_id: str, **fields: str) -> None:
    """Update a custom source's fields (name, api_url, api_key)."""
    allowed_fields = {"name", "api_url", "api_key"}
    sources = _load_sources(connection)

    for source in sources:
        if source["id"] == source_id:
            for field_name, field_value in fields.items():
                if field_name in allowed_fields and field_value is not None:
                    source[field_name] = field_value
            if "api_key" in fields:
                source["has_api_key"] = bool(fields["api_key"])
            break

    _save_sources(connection, sources)


def toggle_custom_source(connection: sqlite3.Connection, source_id: str, enabled: bool) -> None:
    """Enable or disable a custom source."""
    sources = _load_sources(connection)
    for source in sources:
        if source["id"] == source_id:
            source["enabled"] = enabled
            break
    _save_sources(connection, sources)
