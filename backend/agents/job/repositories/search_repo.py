"""Repository for search filters (schedule merged in — no separate table)."""

import json
import sqlite3


class SearchRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_filter(self, name: str, filters: dict, frequency_hours: int | None = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO search_filters (name, filters, frequency_hours) VALUES (?, ?, ?)",
            (name, json.dumps(filters), frequency_hours),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_filters(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM search_filters WHERE is_active = 1").fetchall()
        return [dict(r) for r in rows]

    def delete_filter(self, filter_id: int) -> None:
        self._conn.execute("UPDATE search_filters SET is_active = 0 WHERE id = ?", (filter_id,))
        self._conn.commit()

    def get_schedule(self) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM search_filters WHERE frequency_hours IS NOT NULL AND is_active = 1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def save_schedule(self, filter_id: int, frequency_hours: int) -> None:
        self._conn.execute(
            "UPDATE search_filters SET frequency_hours = ? WHERE id = ?",
            (frequency_hours, filter_id),
        )
        self._conn.commit()

    def update_last_run(self, filter_id: int) -> None:
        self._conn.execute(
            "UPDATE search_filters SET last_run = datetime('now') WHERE id = ?",
            (filter_id,),
        )
        self._conn.commit()
