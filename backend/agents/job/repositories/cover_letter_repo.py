"""Repository for generated cover letters."""

import json
import sqlite3


class CoverLetterRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_cover_letter(
        self,
        job_id: int,
        content: str,
        preferences: dict | None = None,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO cover_letters (job_id, content, preferences) VALUES (?, ?, ?)",
            (job_id, content, json.dumps(preferences or {})),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_cover_letter(self, cl_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM cover_letters WHERE id = ?", (cl_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_cover_letters(self, job_id: int | None = None) -> list[dict]:
        if job_id:
            rows = self._conn.execute(
                "SELECT * FROM cover_letters WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM cover_letters ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_content(self, cl_id: int, content: str) -> None:
        self._conn.execute(
            "UPDATE cover_letters SET content = ?, updated_at = datetime('now') WHERE id = ?",
            (content, cl_id),
        )
        self._conn.commit()

    def save_feedback(self, cl_id: int, feedback: int) -> None:
        self._conn.execute(
            "UPDATE cover_letters SET feedback = ? WHERE id = ?", (feedback, cl_id)
        )
        self._conn.commit()
