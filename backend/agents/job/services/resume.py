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
        self._export_dir = export_dir or Path.home() / ".panini" / "exports" / "resumes"

    def generate(self, job_id: int, preferences: dict) -> dict:
        """Generate a resume tailored to a job posting."""
        self._default_template_cache = None  # reset per generate call
        knowledge = self._knowledge_repo.get_full_knowledge_bank()

        job_row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        job = dict(job_row) if job_row else {}
        parsed = json.loads(job.get("parsed_data", "{}")) if isinstance(job.get("parsed_data"), str) else job.get("parsed_data", {})
        job["parsed_data"] = parsed

        # LLM path: get content decisions from Claude, assemble with our template
        docx_binary = None
        if self._llm:
            from agents.job.prompts.generate_resume import build_prompt, SYSTEM_PROMPT

            original_resume = self._get_original_resume()
            prompt = build_prompt(knowledge, job, preferences, original_resume=original_resume)
            force = preferences.get("force_override", False)
            response = self._llm.complete(prompt, system=SYSTEM_PROMPT, feature="resume_gen", force_override=force)

            # Parse Claude's JSON decisions
            llm_edits = self._parse_llm_response(response)

            analysis = None
            if llm_edits and original_resume:
                content = self._assemble_from_template(original_resume, llm_edits, knowledge)
                analysis = self._extract_analysis(llm_edits)
                # DOCX surgery: apply edits to original DOCX preserving formatting
                try:
                    if self._has_original_docx():
                        from shared.docx_surgery import apply_edits
                        original_docx = self._get_original_docx()
                        para_map = self._get_paragraph_map()
                        if original_docx and para_map:
                            docx_binary = apply_edits(original_docx, para_map, llm_edits)
                except (ImportError, ValueError, KeyError, IndexError, TypeError) as e:
                    import logging
                    logging.getLogger(__name__).warning("DOCX surgery failed (text content still generated): %s", e)
            elif llm_edits:
                content = self._assemble_from_knowledge(llm_edits, knowledge)
                analysis = self._extract_analysis(llm_edits)
            else:
                content = build_resume(knowledge, job, preferences)
        else:
            content = build_resume(knowledge, job, preferences)
            analysis = None

        # Save to database
        cursor = self._conn.execute(
            """INSERT INTO resumes (job_id, content, preferences, docx_binary)
               VALUES (?, ?, ?, ?)""",
            (job_id, content, json.dumps(preferences), docx_binary),
        )
        self._conn.commit()

        # Cleanup old ephemeral resumes (unsaved, older than 24h)
        try:
            from agents.job.repositories.resume_repo import ResumeRepository
            ResumeRepository(self._conn).cleanup_old_unsaved(max_age_hours=24)
        except Exception:
            pass

        result = {"id": cursor.lastrowid, "content": content, "job_id": job_id}
        if analysis:
            result["analysis"] = analysis
        return result

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
        experience_edits = {e.get("company", ""): e for e in edits.get("experience_edits", []) if e.get("company")}
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

                # Unedited role — pass through but add bullet prefix for text format
                if line.strip() and not line.strip().startswith("-"):
                    result.append(f"- {line.strip()}")
                    continue

            result.append(line)

        # Add RELEVANT PROJECTS section if Claude suggested any
        # Skip if resume already has a PROJECTS section (avoid duplication)
        has_projects_section = any(
            line.strip().upper() in ("PROJECTS", "SIDE PROJECTS", "PERSONAL PROJECTS")
            for line in result
        )
        relevant_projects = edits.get("relevant_projects", [])
        if relevant_projects and not has_projects_section:
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

        # No analysis in resume content — returned separately
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
            for education_entry in knowledge["education"]:
                lines.append(f"{education_entry.get('degree','')} in {education_entry.get('field','')}, {education_entry.get('institution','')}")

        return "\n".join(lines)

    def _extract_analysis(self, edits: dict) -> dict:
        """Extract match analysis from Claude's response — returned separately from resume."""
        swaps = []
        for edit in edits.get("experience_edits", []):
            for swap in edit.get("swaps", []):
                swaps.append({
                    "removed": swap.get("removed", ""),
                    "added": swap.get("added", ""),
                    "reason": swap.get("reason", ""),
                    "improvement": swap.get("match_improvement", ""),
                })

        return {
            "original_match": edits.get("original_match_percent"),
            "new_match": edits.get("new_match_percent", edits.get("match_percent")),
            "improvement": edits.get("match_improvement", ""),
            "swaps": swaps,
            "strengths": edits.get("strengths", []),
            "gaps": edits.get("gaps", []),
            "suggestions": edits.get("suggestions", []),
            "relevant_projects": edits.get("relevant_projects", []),
        }

    def _get_original_resume(self) -> str | None:
        """Get the user's original resume text — from default template first, settings as fallback."""
        template = self._get_default_template()
        if template and template.get("raw_text"):
            return template["raw_text"]

        # Fallback to settings key (backward compat)
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = 'original_resume'"
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def _get_default_template(self) -> dict | None:
        """Get the default resume template. Cached per generate() call to avoid 4x DB fetch."""
        if hasattr(self, "_default_template_cache") and self._default_template_cache is not None:
            return self._default_template_cache if self._default_template_cache != {} else None

        try:
            from agents.job.repositories.template_repo import ResumeTemplateRepo
            result = ResumeTemplateRepo(self._conn).get_default_template()
            self._default_template_cache = result if result else {}
            return result
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Template lookup failed: %s", e)
            self._default_template_cache = {}
            return None

    def _has_original_docx(self) -> bool:
        """Check if a DOCX template with paragraph map is available."""
        template = self._get_default_template()
        if template and template.get("docx_binary") and template.get("paragraph_map"):
            return True
        # Fallback to settings
        docx_row = self._conn.execute(
            "SELECT 1 FROM settings WHERE key = 'original_resume_docx'"
        ).fetchone()
        map_row = self._conn.execute(
            "SELECT 1 FROM settings WHERE key = 'original_resume_map'"
        ).fetchone()
        return docx_row is not None and map_row is not None

    def _get_original_docx(self) -> bytes | None:
        """Retrieve DOCX binary — from default template first, settings as fallback."""
        template = self._get_default_template()
        if template and template.get("docx_binary"):
            return template["docx_binary"]

        import base64
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = 'original_resume_docx'"
        ).fetchone()
        if not row:
            return None
        base64_encoded = json.loads(row["value"])
        return base64.b64decode(base64_encoded)

    def _get_paragraph_map(self) -> dict | None:
        """Retrieve paragraph map — from default template first, settings as fallback."""
        template = self._get_default_template()
        if template and template.get("paragraph_map"):
            return template["paragraph_map"]

        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = 'original_resume_map'"
        ).fetchone()
        if not row:
            return None
        return json.loads(row["value"])

    def export(self, resume_id: int, format: str = "md") -> bytes:
        """Export a resume in the specified format."""
        row = self._conn.execute(
            "SELECT content, docx_binary FROM resumes WHERE id = ?", (resume_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Resume {resume_id} not found")

        # Use preserved DOCX when available
        if format == "docx" and row["docx_binary"]:
            return row["docx_binary"]

        exporter = EXPORTERS.get(format)
        if not exporter:
            raise ValueError(f"Unsupported format: {format}")

        return exporter.export(row["content"], {})
