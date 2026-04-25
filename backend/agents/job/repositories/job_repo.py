"""Repository for job postings."""

import json
import sqlite3


class JobRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_job(
        self,
        title: str,
        company: str | None = None,
        parsed_data: dict | None = None,
        source_url: str | None = None,
        source_text: str | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO jobs (title, company, parsed_data, source_url, source_text)
               VALUES (?, ?, ?, ?, ?)""",
            (title, company, json.dumps(parsed_data or {}), source_url, source_text),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_job(self, job_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_jobs(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_job(self, job_id: int) -> None:
        self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self._conn.commit()

    def update_match_score(
        self, job_id: int, score: float, breakdown: dict
    ) -> None:
        self._conn.execute(
            "UPDATE jobs SET match_score = ?, match_breakdown = ? WHERE id = ?",
            (score, json.dumps(breakdown), job_id),
        )
        self._conn.commit()
