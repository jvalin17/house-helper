"""Repository for apartment search preferences and custom sources."""

import json
import sqlite3
import uuid


class ApartmentPreferencesRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    # ── Preferences ──────────────────────────────

    def get_preferences(self) -> dict:
        """Get saved apartment search preferences."""
        row = self._connection.execute(
            "SELECT * FROM apartment_preferences ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return {
                "location": None, "max_price": None, "min_bedrooms": None,
                "must_haves": [], "layout_requirements": [], "auto_search_active": False,
            }
        result = dict(row)
        for json_field in ("must_haves", "layout_requirements"):
            if isinstance(result.get(json_field), str):
                result[json_field] = json.loads(result[json_field])
        result["auto_search_active"] = bool(result.get("auto_search_active"))
        return result

    def save_preferences(self, **fields) -> int:
        """Save or update apartment search preferences."""
        existing = self._connection.execute(
            "SELECT id FROM apartment_preferences ORDER BY id DESC LIMIT 1"
        ).fetchone()

        must_haves_json = json.dumps(fields.get("must_haves") or [])
        layout_requirements_json = json.dumps(fields.get("layout_requirements") or [])

        if existing:
            preference_id = existing["id"]
            self._connection.execute(
                """UPDATE apartment_preferences SET
                   location = ?, max_price = ?, min_bedrooms = ?,
                   must_haves = ?, layout_requirements = ?, auto_search_active = ?
                   WHERE id = ?""",
                (
                    fields.get("location"),
                    fields.get("max_price"),
                    fields.get("min_bedrooms"),
                    must_haves_json,
                    layout_requirements_json,
                    1 if fields.get("auto_search_active") else 0,
                    preference_id,
                ),
            )
        else:
            cursor = self._connection.execute(
                """INSERT INTO apartment_preferences
                   (profile_id, location, max_price, min_bedrooms, must_haves, layout_requirements, auto_search_active)
                   VALUES (1, ?, ?, ?, ?, ?, ?)""",
                (
                    fields.get("location"),
                    fields.get("max_price"),
                    fields.get("min_bedrooms"),
                    must_haves_json,
                    layout_requirements_json,
                    1 if fields.get("auto_search_active") else 0,
                ),
            )
            preference_id = cursor.lastrowid

        self._connection.commit()
        return preference_id

    # ── Custom Apartment Sources (max 5) ─────────

    def list_custom_sources(self) -> list[dict]:
        """List custom apartment API sources from settings."""
        row = self._connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_custom_sources'"
        ).fetchone()
        if not row:
            return []
        try:
            sources = json.loads(row["value"])
            return [{**source, "api_key": "***" if source.get("has_api_key") else ""} for source in sources]
        except (json.JSONDecodeError, TypeError):
            return []

    def add_custom_source(self, name: str, api_url: str, api_key: str | None = None) -> dict:
        """Add a custom apartment source. Max 5."""
        if not name or not name.strip():
            raise ValueError("Source name is required")
        if not api_url or not api_url.strip():
            raise ValueError("API url is required")

        sources = self._load_raw_sources()
        if len(sources) >= 5:
            raise ValueError("Cannot add more than 5 custom sources (maximum reached)")

        new_source = {
            "id": f"apt_custom_{uuid.uuid4().hex[:8]}",
            "name": name.strip(),
            "api_url": api_url.strip(),
            "has_api_key": api_key is not None and len(api_key) > 0,
            "api_key": api_key or "",
            "enabled": True,
        }
        sources.append(new_source)
        self._save_raw_sources(sources)
        return {**new_source, "api_key": "***" if new_source["has_api_key"] else ""}

    def delete_custom_source(self, source_id: str) -> None:
        """Remove a custom source."""
        sources = self._load_raw_sources()
        sources = [source for source in sources if source["id"] != source_id]
        self._save_raw_sources(sources)

    def toggle_custom_source(self, source_id: str, enabled: bool) -> None:
        """Enable or disable a custom source."""
        sources = self._load_raw_sources()
        for source in sources:
            if source["id"] == source_id:
                source["enabled"] = enabled
                break
        self._save_raw_sources(sources)

    def _load_raw_sources(self) -> list[dict]:
        row = self._connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_custom_sources'"
        ).fetchone()
        if not row:
            return []
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return []

    def _save_raw_sources(self, sources: list[dict]) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('apartment_custom_sources', ?, datetime('now'))",
            [json.dumps(sources)],
        )
        self._connection.commit()
