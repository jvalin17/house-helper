"""Cover letter generation service.

Uses LLM for AI-drafted content when available.
Falls back to template-based assembly from knowledge bank.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from shared.algorithms.resume_builder import build_cover_letter
from shared.export.markdown import MarkdownExporter
from shared.export.text import TextExporter
from shared.export.pdf import PdfExporter
from shared.export.docx import DocxExporter
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.cover_letter_repo import CoverLetterRepository

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider

EXPORTERS = {
    "md": MarkdownExporter(),
    "txt": TextExporter(),
    "pdf": PdfExporter(),
    "docx": DocxExporter(),
}


class CoverLetterService:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        cover_letter_repo: CoverLetterRepository,
        db_conn: sqlite3.Connection,
        llm_provider: LLMProvider | None = None,
    ):
        self._knowledge_repo = knowledge_repo
        self._cl_repo = cover_letter_repo
        self._conn = db_conn
        self._llm = llm_provider

    def generate(self, job_id: int, preferences: dict) -> dict:
        """Generate a cover letter tailored to a job posting."""
        knowledge = self._knowledge_repo.get_full_knowledge_bank()

        job_row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        job = dict(job_row) if job_row else {}
        parsed = json.loads(job.get("parsed_data", "{}")) if isinstance(job.get("parsed_data"), str) else job.get("parsed_data", {})
        job["parsed_data"] = parsed

        if self._llm:
            import asyncio
            from agents.job.prompts.generate_cover_letter import build_prompt, SYSTEM_PROMPT

            prompt = build_prompt(knowledge, job, preferences)
            content = asyncio.run(self._llm.complete(prompt, system=SYSTEM_PROMPT))
        else:
            content = build_cover_letter(knowledge, job, preferences)

        cl_id = self._cl_repo.save_cover_letter(
            job_id=job_id,
            content=content,
            preferences=preferences,
        )

        return {"id": cl_id, "content": content, "job_id": job_id}

    def update(self, cl_id: int, content: str) -> dict:
        """Save user-edited cover letter content."""
        self._cl_repo.update_content(cl_id, content)
        return {"id": cl_id, "content": content}

    def export(self, cl_id: int, format: str = "md") -> bytes:
        """Export a cover letter in the specified format."""
        cl = self._cl_repo.get_cover_letter(cl_id)
        if not cl:
            raise ValueError(f"Cover letter {cl_id} not found")

        exporter = EXPORTERS.get(format)
        if not exporter:
            raise ValueError(f"Unsupported format: {format}")

        return exporter.export(cl["content"], {})
