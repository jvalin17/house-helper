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

        # LLM path: AI-tailored resume using original format
        if self._llm:
            from agents.job.prompts.generate_resume import build_prompt, SYSTEM_PROMPT

            # Get original resume text if user uploaded one
            original_resume = self._get_original_resume()
            prompt = build_prompt(knowledge, job, preferences, original_resume=original_resume)
            content = self._llm.complete(prompt, system=SYSTEM_PROMPT)
        else:
            # Fallback: template-based assembly
            content = build_resume(knowledge, job, preferences)

        # Save to database
        cursor = self._conn.execute(
            """INSERT INTO resumes (job_id, content, preferences)
               VALUES (?, ?, ?)""",
            (job_id, content, json.dumps(preferences)),
        )
        self._conn.commit()

        return {"id": cursor.lastrowid, "content": content, "job_id": job_id}

    def _get_original_resume(self) -> str | None:
        """Get the user's original resume text stored in evidence_log."""
        # Check for uploaded resume text in experiences (the description field contains bullet points)
        knowledge = self._knowledge_repo.get_full_knowledge_bank()
        if not knowledge.get("experiences"):
            return None

        # Rebuild original format from knowledge bank
        lines = []
        for exp in knowledge["experiences"]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            start = exp.get("start_date", "")
            end = exp.get("end_date") or "Present"
            lines.append(f"{company} | {title}\t{start} – {end}")
            desc = exp.get("description", "")
            if desc:
                for bullet in desc.split("\n"):
                    bullet = bullet.strip()
                    if bullet:
                        lines.append(f"- {bullet}")
            lines.append("")

        if knowledge.get("skills"):
            by_cat: dict[str, list[str]] = {}
            for s in knowledge["skills"]:
                cat = s.get("category", "other")
                by_cat.setdefault(cat, []).append(s["name"])
            lines.append("TECHNICAL SKILLS")
            for cat, skills in by_cat.items():
                lines.append(f"{cat.title()}: {', '.join(skills)}")
            lines.append("")

        if knowledge.get("education"):
            lines.append("EDUCATION")
            for edu in knowledge["education"]:
                deg = edu.get("degree", "")
                field = edu.get("field", "")
                inst = edu.get("institution", "")
                date = edu.get("end_date", "")
                lines.append(f"{deg} in {field}, {inst}\t{date}")
            lines.append("")

        if knowledge.get("projects"):
            lines.append("PROJECTS")
            for proj in knowledge["projects"]:
                lines.append(f"{proj.get('name', '')}")
                if proj.get("description"):
                    lines.append(proj["description"])
            lines.append("")

        return "\n".join(lines) if lines else None

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
