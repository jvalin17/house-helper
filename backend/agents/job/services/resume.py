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

        # LLM path: get content decisions from Claude, assemble with our template
        if self._llm:
            from agents.job.prompts.generate_resume import build_prompt, SYSTEM_PROMPT

            original_resume = self._get_original_resume()
            prompt = build_prompt(knowledge, job, preferences, original_resume=original_resume)
            response = self._llm.complete(prompt, system=SYSTEM_PROMPT)

            # Parse Claude's JSON decisions
            llm_edits = self._parse_llm_response(response)

            if llm_edits and original_resume:
                # Assemble: original template + Claude's content decisions
                content = self._assemble_from_template(original_resume, llm_edits, knowledge)
            elif llm_edits:
                # No original resume — use our template with Claude's content
                content = self._assemble_from_knowledge(llm_edits, knowledge)
            else:
                # Claude response unparseable — fall back to template
                content = build_resume(knowledge, job, preferences)
        else:
            content = build_resume(knowledge, job, preferences)

        # Save to database
        cursor = self._conn.execute(
            """INSERT INTO resumes (job_id, content, preferences)
               VALUES (?, ?, ?)""",
            (job_id, content, json.dumps(preferences)),
        )
        self._conn.commit()

        return {"id": cursor.lastrowid, "content": content, "job_id": job_id}

    def _parse_llm_response(self, response: str) -> dict | None:
        """Parse Claude's JSON response, handling markdown fences."""
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        try:
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            return None

    def _assemble_from_template(self, original: str, edits: dict, knowledge: dict) -> str:
        """Replace content in the original resume with Claude's decisions.

        Keeps exact format — only swaps out the text inside each section.
        """
        lines = original.split("\n")
        result = []
        in_summary = False
        in_experience = False
        current_company = None
        experience_edits = {e["company"]: e for e in edits.get("experience_edits", [])}
        summary_replaced = False
        skip_until_next_section = False

        section_headers = {"SUMMARY", "TECHNICAL SKILLS", "WORK EXPERIENCE", "EDUCATION", "PROJECTS"}

        for line in lines:
            stripped = line.strip().upper()

            # Detect section changes
            if stripped in section_headers:
                in_summary = stripped == "SUMMARY"
                in_experience = stripped == "WORK EXPERIENCE"
                skip_until_next_section = False
                current_company = None
                result.append(line)
                continue

            # Replace summary
            if in_summary and not summary_replaced and edits.get("summary"):
                result.append(edits["summary"])
                summary_replaced = True
                in_summary = False
                continue
            elif in_summary and not summary_replaced:
                result.append(line)
                continue

            # Replace experience bullets
            if in_experience:
                # Detect company/title lines (contain tab or " | ")
                is_role_header = ("\t" in line or " | " in line) and not line.strip().startswith("-") and line.strip()

                if is_role_header:
                    skip_until_next_section = False
                    result.append(line)
                    # Find matching company in edits
                    for company_name in experience_edits:
                        if company_name.lower() in line.lower():
                            current_company = company_name
                            skip_until_next_section = True
                            # Add Claude's reworded bullets
                            for bullet in experience_edits[company_name].get("bullets", []):
                                result.append(bullet if bullet.startswith("-") else f"- {bullet}")
                            break
                    continue

                # Skip ALL original content for this role (bullets, plain text, etc.)
                if skip_until_next_section:
                    if not line.strip():
                        result.append("")  # Keep blank lines between roles
                    continue

            result.append(line)

        # Add RELEVANT PROJECTS section if Claude suggested any
        relevant_projects = edits.get("relevant_projects", [])
        if relevant_projects:
            # Insert before EDUCATION
            edu_idx = None
            for i, line in enumerate(result):
                if line.strip().upper() == "EDUCATION":
                    edu_idx = i
                    break
            project_lines = ["RELEVANT PROJECTS"]
            for proj in relevant_projects:
                project_lines.append(f"{proj.get('name', '')}")
                if proj.get("description"):
                    project_lines.append(proj["description"])
                if proj.get("tech_stack"):
                    project_lines.append(f"Tech: {', '.join(proj['tech_stack'])}")
                project_lines.append("")
            if edu_idx:
                for i, pl in enumerate(project_lines):
                    result.insert(edu_idx + i, pl)
            else:
                result.extend(project_lines)

        # Match analysis
        orig_pct = edits.get("original_match_percent", "N/A")
        new_pct = edits.get("new_match_percent", edits.get("match_percent", "N/A"))
        improvement = edits.get("match_improvement", "")
        strengths = edits.get("strengths", [])
        gaps = edits.get("gaps", [])
        suggestions = edits.get("suggestions", [])

        result.append("")
        result.append("---")
        if orig_pct != "N/A" and new_pct != "N/A":
            result.append(f"MATCH: {new_pct}% (was {orig_pct}%, {improvement})")
        else:
            result.append(f"MATCH: {new_pct}%")

        # Show swap reasoning
        for edit in edits.get("experience_edits", []):
            for swap in edit.get("swaps", []):
                result.append(f"  Swap: replaced '{swap.get('removed','')[:50]}...' with '{swap.get('added','')[:50]}...' — {swap.get('reason','')} ({swap.get('match_improvement','')})")

        if strengths:
            result.append(f"Strengths: {', '.join(strengths)}")
        if gaps:
            result.append(f"Gaps: {', '.join(gaps)}")
        if suggestions:
            result.append(f"To improve: {', '.join(suggestions)}")

        return "\n".join(result)

    def _assemble_from_knowledge(self, edits: dict, knowledge: dict) -> str:
        """Build resume from edits + knowledge when no original template exists."""
        lines = []
        # Contact from knowledge
        for exp in knowledge.get("experiences", [])[:1]:
            pass  # No contact info without original

        if edits.get("summary"):
            lines.append("SUMMARY")
            lines.append(edits["summary"])
            lines.append("")

        lines.append("WORK EXPERIENCE")
        for edit in edits.get("experience_edits", []):
            lines.append(f"{edit['company']} | {edit['title']}")
            for bullet in edit.get("bullets", []):
                lines.append(bullet if bullet.startswith("-") else f"- {bullet}")
            lines.append("")

        if knowledge.get("education"):
            lines.append("EDUCATION")
            for edu in knowledge["education"]:
                lines.append(f"{edu.get('degree','')} in {edu.get('field','')}, {edu.get('institution','')}")

        return "\n".join(lines)

    def _get_original_resume(self) -> str | None:
        """Get the user's original resume text saved during import."""
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = 'original_resume'"
        ).fetchone()
        if row:
            import json as _json
            return _json.loads(row["value"])
        return None

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
