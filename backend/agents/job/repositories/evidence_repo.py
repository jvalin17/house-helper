"""Repository for evidence logging — tracks source of knowledge bank entries."""

import sqlite3


class EvidenceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def log(self, entity_type: str, entity_id: int, source: str, original_text: str | None = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO evidence_log (entity_type, entity_id, source, original_text) VALUES (?, ?, ?, ?)",
            (entity_type, entity_id, source, original_text),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_evidence(self, entity_type: str, entity_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM evidence_log WHERE entity_type = ? AND entity_id = ?",
            (entity_type, entity_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_by_source(self, source: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM evidence_log WHERE source = ?", (source,)
        ).fetchall()
        return [dict(r) for r in rows]
