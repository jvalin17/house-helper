"""Repository for generated resumes."""

import json
import sqlite3


class ResumeRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_resume(
        self,
        job_id: int,
        content: str,
        preferences: dict,
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO resumes (job_id, content, preferences) VALUES (?, ?, ?)",
            (job_id, content, json.dumps(preferences)),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_resume(self, resume_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM resumes WHERE id = ?", (resume_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_resumes(self, job_id: int | None = None) -> list[dict]:
        if job_id:
            rows = self._conn.execute(
                "SELECT * FROM resumes WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM resumes ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def save_feedback(self, resume_id: int, feedback: int) -> None:
        self._conn.execute(
            "UPDATE resumes SET feedback = ? WHERE id = ?", (feedback, resume_id)
        )
        self._conn.commit()

    def update_export(self, resume_id: int, export_path: str, export_format: str) -> None:
        self._conn.execute(
            "UPDATE resumes SET export_path = ?, export_format = ? WHERE id = ?",
            (export_path, export_format, resume_id),
        )
        self._conn.commit()
