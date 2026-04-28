"""Repository for suggestion feedback — stores rejected LLM suggestions."""

import sqlite3


class SuggestionFeedbackRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_rejection(
        self,
        suggestion_text: str,
        reason: str | None = None,
        original_bullet: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO suggestion_feedback (suggestion_text, original_bullet, reason) VALUES (?, ?, ?)",
            (suggestion_text, original_bullet, reason),
        )
        self._conn.commit()
        return cursor.lastrowid

    def list_rejections(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM suggestion_feedback ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_rejection(self, rejection_id: int) -> None:
        self._conn.execute("DELETE FROM suggestion_feedback WHERE id = ?", (rejection_id,))
        self._conn.commit()
