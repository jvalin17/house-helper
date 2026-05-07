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

    def get_existing_urls(self) -> dict[str, int]:
        """Return {source_url: job_id} for all jobs with URLs. One query, no N+1."""
        rows = self._conn.execute(
            "SELECT id, source_url FROM jobs WHERE source_url IS NOT NULL AND source_url != ''"
        ).fetchall()
        return {row["source_url"]: row["id"] for row in rows}

    def find_by_title_and_company(self, title: str, company: str) -> int | None:
        """Find existing job by title + company (case-insensitive). For cross-source dedup."""
        row = self._conn.execute(
            "SELECT id FROM jobs WHERE LOWER(title) = LOWER(?) AND LOWER(company) = LOWER(?) LIMIT 1",
            (title, company),
        ).fetchone()
        return row["id"] if row else None

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
