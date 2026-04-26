"""Repository for auto-apply queue."""

import sqlite3


class ApplyQueueRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_entry(self, job_id: int, apply_method: str | None = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO auto_apply_queue (job_id, apply_method) VALUES (?, ?)",
            (job_id, apply_method),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_entry(self, entry_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM auto_apply_queue WHERE id = ?", (entry_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_queue(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM auto_apply_queue WHERE status = ? ORDER BY created_at",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM auto_apply_queue ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_status(self, entry_id: int, status: str) -> None:
        extra = ""
        if status == "confirmed":
            extra = ", confirmed_at = datetime('now')"
        elif status == "applied":
            extra = ", applied_at = datetime('now')"
        self._conn.execute(
            f"UPDATE auto_apply_queue SET status = ?{extra} WHERE id = ?",
            (status, entry_id),
        )
        self._conn.commit()

    def set_resume(self, entry_id: int, resume_id: int, cover_letter_id: int) -> None:
        self._conn.execute(
            "UPDATE auto_apply_queue SET resume_id = ?, cover_letter_id = ? WHERE id = ?",
            (resume_id, cover_letter_id, entry_id),
        )
        self._conn.commit()
