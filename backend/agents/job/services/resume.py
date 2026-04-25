"""Resume generation service — generate and export resumes.

Uses LLM for AI-tailored content when available.
Falls back to template-based assembly from knowledge bank.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from shared.algorithms.resume_builder import build_resume
from shared.export.markdown import MarkdownExporter
from shared.export.text import TextExporter
from shared.export.pdf import PdfExporter
from shared.export.docx import DocxExporter
from agents.job.repositories.knowledge_repo import KnowledgeRepository

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider

EXPORTERS = {
    "md": MarkdownExporter(),
    "txt": TextExporter(),
    "pdf": PdfExporter(),
    "docx": DocxExporter(),
}


class ResumeService:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        db_conn: sqlite3.Connection,
        llm_provider: LLMProvider | None = None,
        export_dir: Path | None = None,
    ):
        self._knowledge_repo = knowledge_repo
        self._conn = db_conn
        self._llm = llm_provider
        self._export_dir = export_dir or Path.home() / ".house-helper" / "exports" / "resumes"

    def generate(self, job_id: int, preferences: dict) -> dict:
        """Generate a resume tailored to a job posting."""
        knowledge = self._knowledge_repo.get_full_knowledge_bank()

        job_row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        job = dict(job_row) if job_row else {}
        parsed = json.loads(job.get("parsed_data", "{}")) if isinstance(job.get("parsed_data"), str) else job.get("parsed_data", {})
        job["parsed_data"] = parsed

        # Generate content (template-based fallback when no LLM)
        content = build_resume(knowledge, job, preferences)

        # Save to database
        cursor = self._conn.execute(
            """INSERT INTO resumes (job_id, content, preferences)
               VALUES (?, ?, ?)""",
            (job_id, content, json.dumps(preferences)),
        )
        self._conn.commit()

        return {"id": cursor.lastrowid, "content": content, "job_id": job_id}

    def export(self, resume_id: int, format: str = "md") -> bytes:
        """Export a resume in the specified format."""
        row = self._conn.execute(
            "SELECT content FROM resumes WHERE id = ?", (resume_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Resume {resume_id} not found")

        exporter = EXPORTERS.get(format)
        if not exporter:
            raise ValueError(f"Unsupported format: {format}")

        return exporter.export(row["content"], {})
