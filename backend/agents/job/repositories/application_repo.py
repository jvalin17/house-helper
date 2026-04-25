"""Repository for application tracking + status history."""

import sqlite3


class ApplicationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_application(
        self,
        job_id: int,
        resume_id: int | None = None,
        cover_letter_id: int | None = None,
        status: str = "applied",
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO applications (job_id, resume_id, cover_letter_id, status)
               VALUES (?, ?, ?, ?)""",
            (job_id, resume_id, cover_letter_id, status),
        )
        app_id = cursor.lastrowid
        # Record initial status in history
        self._conn.execute(
            "INSERT INTO application_status_history (application_id, status) VALUES (?, ?)",
            (app_id, status),
        )
        self._conn.commit()
        return app_id

    def get_application(self, app_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_applications(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM applications ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_status(self, app_id: int, new_status: str) -> None:
        self._conn.execute(
            "UPDATE applications SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, app_id),
        )
        self._conn.execute(
            "INSERT INTO application_status_history (application_id, status) VALUES (?, ?)",
            (app_id, new_status),
        )
        self._conn.commit()

    def get_status_history(self, app_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM application_status_history WHERE application_id = ? ORDER BY changed_at",
            (app_id,),
        ).fetchall()
        return [dict(r) for r in rows]
