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

    # Exclude docx_binary from JSON-returning queries (BLOB can't serialize to JSON)
    _LIST_COLS = "id, profile_id, job_id, content, preferences, export_path, export_format, feedback, created_at"

    def get_resume(self, resume_id: int) -> dict | None:
        row = self._conn.execute(
            f"SELECT {self._LIST_COLS} FROM resumes WHERE id = ?", (resume_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_resumes(self, job_id: int | None = None) -> list[dict]:
        if job_id:
            rows = self._conn.execute(
                f"SELECT {self._LIST_COLS} FROM resumes WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"SELECT {self._LIST_COLS} FROM resumes ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def list_resumes_with_jobs(self) -> list[dict]:
        """List resumes with job title/company — lightweight, no content or binary."""
        rows = self._conn.execute(
            """SELECT r.id, r.job_id, r.created_at, r.feedback,
                      j.title AS job_title, j.company AS job_company,
                      CASE WHEN r.docx_binary IS NOT NULL THEN 1 ELSE 0 END AS has_docx
               FROM resumes r
               LEFT JOIN jobs j ON r.job_id = j.id
               ORDER BY r.created_at DESC"""
        ).fetchall()
        return [
            {**dict(r), "has_docx": bool(r["has_docx"])}
            for r in rows
        ]

    def delete_resume(self, resume_id: int) -> None:
        self._conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        self._conn.commit()

    def save_resume_explicit(self, resume_id: int, name: str) -> None:
        """Mark a resume as explicitly saved by the user. Max 5."""
        count = self.count_saved()
        if count >= 5:
            raise ValueError("Cannot save more than 5 resumes (maximum reached). Remove one first.")
        self._conn.execute(
            "UPDATE resumes SET is_saved = 1, save_name = ? WHERE id = ?",
            (name, resume_id),
        )
        self._conn.commit()

    def unsave_resume(self, resume_id: int) -> None:
        """Remove a resume from the saved collection (keeps it in DB as ephemeral)."""
        self._conn.execute(
            "UPDATE resumes SET is_saved = 0, save_name = NULL WHERE id = ?",
            (resume_id,),
        )
        self._conn.commit()

    def count_saved(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 1").fetchone()[0]

    def list_saved_resumes(self) -> list[dict]:
        """List only explicitly saved resumes with job info."""
        rows = self._conn.execute(
            """SELECT r.id, r.job_id, r.save_name, r.created_at, r.feedback, r.is_saved,
                      j.title AS job_title, j.company AS job_company,
                      CASE WHEN r.docx_binary IS NOT NULL THEN 1 ELSE 0 END AS has_docx
               FROM resumes r
               LEFT JOIN jobs j ON r.job_id = j.id
               WHERE r.is_saved = 1
               ORDER BY r.created_at DESC"""
        ).fetchall()
        return [{**dict(r), "has_docx": bool(r["has_docx"])} for r in rows]

    def generate_save_name(self) -> str:
        """Generate next name like resume_26_v1, resume_26_v2."""
        from datetime import datetime
        year = datetime.now().year % 100
        rows = self._conn.execute(
            "SELECT save_name FROM resumes WHERE is_saved = 1 AND save_name LIKE ?",
            (f"resume_{year}_v%",),
        ).fetchall()
        max_version = 0
        for row in rows:
            name = row["save_name"]
            try:
                version = int(name.split("_v")[-1])
                max_version = max(max_version, version)
            except (ValueError, IndexError):
                pass
        return f"resume_{year}_v{max_version + 1}"

    def cleanup_old_unsaved(self, max_age_hours: int = 24) -> int:
        """Delete unsaved resumes older than max_age_hours. Returns count deleted."""
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM resumes WHERE is_saved = 0 AND created_at < ?",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

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
