"""Repository for user profiles — focus areas or different people."""

import json
import sqlite3


class ProfileRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_profile(
        self,
        name: str,
        type: str = "focus",
        description: str | None = None,
        search_title: str | None = None,
        search_keywords: str | None = None,
        search_location: str | None = None,
        search_remote: bool = False,
        resume_preferences: dict | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO profiles (name, type, description, search_title, search_keywords,
               search_location, search_remote, resume_preferences)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, type, description, search_title, search_keywords,
             search_location, 1 if search_remote else 0,
             json.dumps(resume_preferences or {})),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_active_profile(self) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM profiles WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def set_active(self, profile_id: int) -> None:
        self._conn.execute("UPDATE profiles SET is_active = 0")
        self._conn.execute("UPDATE profiles SET is_active = 1 WHERE id = ?", (profile_id,))
        self._conn.commit()

    def list_profiles(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM profiles ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row) if row else None

    def update_profile(self, profile_id: int, **fields) -> None:
        if not fields:
            return
        set_clause = ", ".join(f"{field_name} = ?" for field_name in fields)
        values = list(fields.values()) + [profile_id]
        self._conn.execute(f"UPDATE profiles SET {set_clause} WHERE id = ?", values)
        self._conn.commit()

    def delete_profile(self, profile_id: int) -> None:
        if profile_id == 1:
            return  # never delete default
        self._conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self._conn.commit()
