"""Repository for Nest Lab Q&A history — user questions + LLM answers per listing."""

import sqlite3


class QaHistoryRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_history(self, listing_id: int, limit: int = 20) -> list[dict]:
        """Get Q&A history for a listing, most recent first."""
        rows = self._connection.execute(
            "SELECT id, question, answer, created_at FROM apartment_qa_history "
            "WHERE listing_id = ? ORDER BY id DESC LIMIT ?",
            (listing_id, limit),
        ).fetchall()
        # Reverse to chronological order for display
        return [dict(row) for row in reversed(rows)]

    def save_qa(self, listing_id: int, question: str, answer: str) -> int:
        """Save a Q&A pair."""
        cursor = self._connection.execute(
            "INSERT INTO apartment_qa_history (listing_id, question, answer) VALUES (?, ?, ?)",
            (listing_id, question, answer),
        )
        self._connection.commit()
        return cursor.lastrowid
