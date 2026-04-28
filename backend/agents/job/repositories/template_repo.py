"""Repository for resume templates — store up to 5 resume files as generation templates."""

import json
import sqlite3

MAX_TEMPLATES = 5


class ResumeTemplateRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_template(
        self,
        name: str,
        filename: str,
        file_format: str,
        raw_text: str | None = None,
        docx_binary: bytes | None = None,
        paragraph_map: dict | None = None,
    ) -> int:
        """Save a resume template. Raises ValueError if at max capacity."""
        # Atomic check + insert to prevent race condition
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            count = self._conn.execute("SELECT COUNT(*) FROM resume_templates").fetchone()[0]
            if count >= MAX_TEMPLATES:
                self._conn.rollback()
                raise ValueError(f"Cannot store more than {MAX_TEMPLATES} templates (maximum reached)")

            is_default = 1 if count == 0 else 0

            cursor = self._conn.execute(
                """INSERT INTO resume_templates (name, filename, format, raw_text, docx_binary, paragraph_map, is_default)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    name, filename, file_format, raw_text,
                    docx_binary,
                    json.dumps(paragraph_map) if paragraph_map else None,
                    is_default,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid
        except ValueError:
            raise
        except Exception:
            self._conn.rollback()
            raise

    def list_templates(self) -> list[dict]:
        """List all templates without binary data (too large for JSON)."""
        rows = self._conn.execute(
            "SELECT id, name, filename, format, is_default, created_at FROM resume_templates ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_template(self, template_id: int) -> dict | None:
        """Get a template including binary data."""
        row = self._conn.execute(
            "SELECT * FROM resume_templates WHERE id = ?", (template_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        if result.get("paragraph_map"):
            result["paragraph_map"] = json.loads(result["paragraph_map"])
        return result

    def get_default_template(self) -> dict | None:
        """Get the default template including binary data."""
        row = self._conn.execute(
            "SELECT * FROM resume_templates WHERE is_default = 1"
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        if result.get("paragraph_map"):
            result["paragraph_map"] = json.loads(result["paragraph_map"])
        return result

    def set_default(self, template_id: int) -> None:
        """Set a template as the default (unsets all others). Raises ValueError if not found."""
        row = self._conn.execute("SELECT 1 FROM resume_templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            raise ValueError(f"Template {template_id} not found")
        self._conn.execute("UPDATE resume_templates SET is_default = 0")
        self._conn.execute("UPDATE resume_templates SET is_default = 1 WHERE id = ?", (template_id,))
        self._conn.commit()

    def delete_template(self, template_id: int) -> None:
        """Delete a template. If it was the default, promote the oldest remaining."""
        was_default = self._conn.execute(
            "SELECT is_default FROM resume_templates WHERE id = ?", (template_id,)
        ).fetchone()
        self._conn.execute("DELETE FROM resume_templates WHERE id = ?", (template_id,))
        # Promote oldest remaining to default if we deleted the default
        if was_default and was_default["is_default"]:
            next_template = self._conn.execute(
                "SELECT id FROM resume_templates ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if next_template:
                self._conn.execute("UPDATE resume_templates SET is_default = 1 WHERE id = ?", (next_template["id"],))
        self._conn.commit()
