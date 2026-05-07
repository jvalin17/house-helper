"""Repository for apartment feature preferences — 3-state tags.

Features cycle through: neutral → must_have → deal_breaker → neutral.
Preferences are GLOBAL (not per-listing) — "I need in-unit W/D" applies everywhere.
"""

import sqlite3

VALID_PREFERENCES = {"neutral", "must_have", "deal_breaker"}


class FeaturePreferencesRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_all_preferences(self) -> list[dict]:
        """Get all feature preferences (non-neutral only)."""
        rows = self._connection.execute(
            "SELECT feature_name, category, preference, updated_at "
            "FROM apartment_feature_preferences "
            "WHERE preference != 'neutral' "
            "ORDER BY category, feature_name"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_preference(self, feature_name: str) -> dict | None:
        """Get preference for a specific feature."""
        row = self._connection.execute(
            "SELECT feature_name, category, preference, updated_at "
            "FROM apartment_feature_preferences WHERE feature_name = ?",
            (feature_name,),
        ).fetchone()
        return dict(row) if row else None

    def set_preference(self, feature_name: str, category: str, preference: str) -> None:
        """Set a feature preference (upsert). Validates preference value."""
        if preference not in VALID_PREFERENCES:
            raise ValueError(
                f"Invalid preference '{preference}'. Must be one of: {', '.join(sorted(VALID_PREFERENCES))}"
            )
        self._connection.execute(
            """INSERT INTO apartment_feature_preferences (feature_name, category, preference, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(feature_name) DO UPDATE SET
                 category = excluded.category,
                 preference = excluded.preference,
                 updated_at = datetime('now')""",
            (feature_name, category, preference),
        )
        self._connection.commit()

    def reset_preference(self, feature_name: str) -> None:
        """Remove a feature preference (back to neutral)."""
        self._connection.execute(
            "DELETE FROM apartment_feature_preferences WHERE feature_name = ?",
            (feature_name,),
        )
        self._connection.commit()

    def get_must_haves(self) -> list[str]:
        """Get all feature names marked as must_have."""
        rows = self._connection.execute(
            "SELECT feature_name FROM apartment_feature_preferences WHERE preference = 'must_have'"
        ).fetchall()
        return [row["feature_name"] for row in rows]

    def get_deal_breakers(self) -> list[str]:
        """Get all feature names marked as deal_breaker."""
        rows = self._connection.execute(
            "SELECT feature_name FROM apartment_feature_preferences WHERE preference = 'deal_breaker'"
        ).fetchall()
        return [row["feature_name"] for row in rows]
