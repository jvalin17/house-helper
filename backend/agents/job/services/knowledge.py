"""Knowledge bank service — resume import and knowledge management.

Parses resume files and populates the knowledge bank.
Uses LLM for structured extraction when available, algorithmic as fallback.
"""

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from shared.scraping.resume_parser import parse_resume
from agents.job.repositories.knowledge_repo import KnowledgeRepository

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        conn: sqlite3.Connection | None = None,
        llm_provider: "LLMProvider | None" = None,
    ):
        self._knowledge_repo = knowledge_repo
        self._conn = conn
        self._llm = llm_provider
        # Lazy import to avoid circular dependency
        self._template_repo = None

    def _get_template_repo(self):
        if self._template_repo is None and self._conn:
            from agents.job.repositories.template_repo import ResumeTemplateRepo
            self._template_repo = ResumeTemplateRepo(self._conn)
        return self._template_repo

    def import_resume(self, file_path: Path, save: bool = True) -> dict:
        """Parse a resume file and populate the knowledge bank."""
        # Try LLM extraction first (better for PDFs), fall back to algorithmic
        parsed = self._parse_with_llm(file_path)
        if not parsed:
            parsed = parse_resume(file_path)

        if not save:
            return {"preview": parsed}

        # Store raw text (settings key — backward compat)
        self._store_raw_text(file_path, parsed)

        # Store DOCX binary + paragraph map for format-preserving generation
        self._store_docx_binary(file_path)

        # Create a template entry so multiple resumes can coexist
        self._create_template_entry(file_path)

        # Save structured data to knowledge bank
        return self._save_to_kb(parsed)

    def _parse_with_llm(self, file_path: Path) -> dict | None:
        """Use LLM to extract structured data from resume text.

        Only used for PDFs (DOCX has a good algorithmic parser).
        Priority: Ollama (free, local) → configured LLM → None (algorithmic fallback).
        """
        # Only use LLM for PDFs — DOCX parser works well algorithmically
        if file_path.suffix.lower() != ".pdf":
            return None

        raw_text = self._extract_raw_text(file_path)
        if not raw_text or len(raw_text.strip()) < 50:
            return None

        # Try Ollama first (free) — only if it's running locally
        provider = self._get_ollama_if_available()
        if not provider:
            provider = self._llm  # fall back to configured LLM (Claude/OpenAI)
        if not provider:
            return None

        try:
            from agents.job.prompts.parse_resume import build_prompt, SYSTEM_PROMPT
            response = provider.complete(build_prompt(raw_text), system=SYSTEM_PROMPT)

            # Parse JSON response
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            data = json.loads(clean.strip())
            if not isinstance(data, dict):
                return None

            return {
                "contact": {},
                "summary": "",
                "experiences": data.get("experiences", []),
                "skills": data.get("skills", []),
                "education": data.get("education", []),
                "projects": data.get("projects", []),
            }
        except Exception as e:
            logger.warning("LLM resume parsing failed, falling back to algorithmic: %s", e)
            return None

    @staticmethod
    def _get_ollama_if_available():
        """Check if Ollama is running locally and return a provider, or None."""
        try:
            import httpx
            ollama_response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if ollama_response.status_code == 200:
                models = ollama_response.json().get("models", [])
                if models:
                    from shared.llm.ollama import OllamaProvider
                    model_name = models[0].get("name", "mistral")
                    return OllamaProvider(model=model_name)
        except Exception:
            pass
        return None

    def _extract_raw_text(self, file_path: Path) -> str:
        """Extract plain text from any resume format."""
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            try:
                from docx import Document as DocxDoc
                doc = DocxDoc(str(file_path))
                return "\n".join(
                    re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", paragraph.text).strip()
                    for paragraph in doc.paragraphs if paragraph.text.strip()
                )
            except Exception:
                return file_path.read_text(errors="replace")
        elif suffix == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(file_path))
                text = "".join(page.get_text() for page in doc)
                doc.close()
                return re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)
            except Exception:
                return ""
        else:
            return file_path.read_text(errors="replace")

    def _store_raw_text(self, file_path: Path, parsed: dict) -> None:
        """Store raw resume text in settings for LLM prompt context."""
        if not self._conn:
            return

        raw_text = self._extract_raw_text(file_path)
        if not raw_text or len(raw_text.strip()) < 50:
            # Fallback: construct from parsed data
            raw_text = "\n".join([
                parsed.get("contact", {}).get("name", ""),
                parsed.get("summary", ""),
            ] + [f"{e.get('company', '')} | {e.get('title', '')}" for e in parsed.get("experiences", [])])

        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume', ?, datetime('now'))",
            (json.dumps(raw_text),),
        )
        self._conn.commit()

    def _store_docx_binary(self, file_path: Path) -> None:
        """Store DOCX binary + paragraph map for format-preserving generation."""
        if not self._conn or file_path.suffix.lower() != ".docx":
            return

        try:
            import base64
            from docx import Document as DocxDoc
            from shared.docx_surgery import build_paragraph_map

            doc = DocxDoc(str(file_path))
            docx_bytes = file_path.read_bytes()
            base64_encoded = base64.b64encode(docx_bytes).decode("ascii")

            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume_docx', ?, datetime('now'))",
                (json.dumps(base64_encoded),),
            )

            paragraph_map = build_paragraph_map(doc)
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume_map', ?, datetime('now'))",
                (json.dumps(paragraph_map),),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("DOCX binary storage failed (import still works): %s", e)

    def _create_template_entry(self, file_path: Path) -> None:
        """Create a resume template entry from the imported file."""
        template_repo = self._get_template_repo()
        if not template_repo:
            return

        try:
            raw_text = self._extract_raw_text(file_path)
            suffix = file_path.suffix.lower()
            docx_binary = None
            paragraph_map = None

            if suffix == ".docx":
                docx_binary = file_path.read_bytes()
                try:
                    from docx import Document as DocxDoc
                    from shared.docx_surgery import build_paragraph_map
                    doc = DocxDoc(str(file_path))
                    paragraph_map = build_paragraph_map(doc)
                except Exception:
                    pass

            # Make the new template the default
            template_id = template_repo.save_template(
                name=file_path.stem.replace("_", " ").title(),
                filename=file_path.name,
                file_format=suffix.lstrip("."),
                raw_text=raw_text,
                docx_binary=docx_binary,
                paragraph_map=paragraph_map,
            )
            template_repo.set_default(template_id)
        except ValueError:
            logger.warning("Max templates reached — template not created")
        except Exception as e:
            logger.warning("Template creation failed (import still works): %s", e)

    def _save_to_kb(self, parsed: dict) -> dict:
        """Save parsed resume data to knowledge bank with merge logic."""
        existing_experiences = self._knowledge_repo.list_experiences()
        existing_by_key = {}
        for e in existing_experiences:
            key = (e["company"], e.get("title"), e["start_date"])
            existing_by_key[key] = e

        counts = {"experiences": 0, "experiences_merged": 0, "skills": 0, "education": 0, "projects": 0, "duplicates_skipped": 0}

        # Save experiences — merge unique bullets into existing entries
        for exp in parsed.get("experiences", []):
            key = (exp.get("company"), exp.get("title"), exp.get("start_date"))
            new_bullets = exp.get("bullets", [])

            if key in existing_by_key:
                existing = existing_by_key[key]
                existing_bullets = (existing.get("description") or "").split("\n")
                existing_normalized = {b.strip().lower() for b in existing_bullets if b.strip()}

                unique_bullets = [
                    b for b in new_bullets
                    if b.strip().lower() not in existing_normalized
                ]

                if unique_bullets:
                    merged = existing.get("description", "") + "\n" + "\n".join(unique_bullets)
                    self._knowledge_repo.update_experience(existing["id"], description=merged.strip())
                    counts["experiences_merged"] += 1
                else:
                    counts["duplicates_skipped"] += 1
                continue

            description = "\n".join(new_bullets)
            self._knowledge_repo.save_experience(
                type="job",
                title=exp.get("title", ""),
                company=exp.get("company", ""),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                description=description,
            )
            counts["experiences"] += 1

        # Save skills
        for skill in parsed.get("skills", []):
            result = self._knowledge_repo.save_skill(
                name=skill["name"],
                category=skill.get("category", "extracted"),
            )
            if result is not None:
                counts["skills"] += 1

        # Save education (dedup by institution)
        existing_education = self._knowledge_repo.list_education()
        existing_institutions = {e["institution"].lower() for e in existing_education if e.get("institution")}
        for education_entry in parsed.get("education", []):
            institution_name = education_entry.get("institution", "")
            if institution_name.lower() in existing_institutions:
                counts["duplicates_skipped"] += 1
                continue
            self._knowledge_repo.save_education(
                institution=institution_name,
                degree=education_entry.get("degree"),
                field=education_entry.get("field"),
                end_date=education_entry.get("end_date"),
            )
            counts["education"] += 1

        # Save projects (dedup by name)
        existing_projects = self._knowledge_repo.list_projects()
        existing_project_names = {project["name"].lower() for project in existing_projects if project.get("name")}
        for project in parsed.get("projects", []):
            name = project.get("name", "")
            if name.lower() in existing_project_names:
                counts["duplicates_skipped"] += 1
                continue
            self._knowledge_repo.save_project(
                name=name,
                description=project.get("description"),
                tech_stack=json.dumps(project.get("tech_stack", [])),
                url=project.get("url"),
            )
            counts["projects"] += 1

        return counts
