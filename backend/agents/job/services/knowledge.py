"""Knowledge bank service — resume import and knowledge management.

Parses resume files and populates the knowledge bank with
structured entries. No LLM needed.
"""

import sqlite3
from pathlib import Path

from shared.scraping.resume_parser import parse_resume
from agents.job.repositories.knowledge_repo import KnowledgeRepository


class KnowledgeService:
    def __init__(self, knowledge_repo: KnowledgeRepository, conn: sqlite3.Connection | None = None):
        self._repo = knowledge_repo
        self._conn = conn

    def import_resume(self, file_path: Path, save: bool = True) -> dict:
        """Parse a resume file and populate the knowledge bank.

        Args:
            file_path: Path to DOCX, PDF, or TXT resume.
            save: If True, saves to DB. If False, returns preview only.
        """
        parsed = parse_resume(file_path)

        if not save:
            return {"preview": parsed}

        # Store the raw text from the file — preserves exact format
        if self._conn:
            import json
            import base64
            try:
                from docx import Document as DocxDoc
                doc = DocxDoc(str(file_path))
                raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except Exception:
                doc = None
                raw_text = "\n".join([
                    parsed.get("contact", {}).get("name", ""),
                    parsed.get("summary", ""),
                ] + [f"{e.get('company','')} | {e.get('title','')}" for e in parsed.get("experiences", [])])

            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume', ?, datetime('now'))",
                (json.dumps(raw_text),),
            )

            # Store DOCX binary + paragraph map for format-preserving generation
            if file_path.suffix.lower() == ".docx" and doc is not None:
                try:
                    from shared.docx_surgery import build_paragraph_map

                    docx_bytes = file_path.read_bytes()
                    b64 = base64.b64encode(docx_bytes).decode("ascii")
                    self._conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume_docx', ?, datetime('now'))",
                        (json.dumps(b64),),
                    )

                    paragraph_map = build_paragraph_map(doc)
                    self._conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume_map', ?, datetime('now'))",
                        (json.dumps(paragraph_map),),
                    )
                except Exception:
                    pass  # DOCX surgery is optional — import still works without it

            self._conn.commit()

        existing_exps = self._repo.list_experiences()
        existing_by_key = {}
        for e in existing_exps:
            key = (e["company"], e.get("title"), e["start_date"])
            existing_by_key[key] = e

        counts = {"experiences": 0, "experiences_merged": 0, "skills": 0, "education": 0, "projects": 0, "duplicates_skipped": 0}

        # Save experiences — merge unique bullets into existing entries
        for exp in parsed.get("experiences", []):
            key = (exp.get("company"), exp.get("title"), exp.get("start_date"))
            new_bullets = exp.get("bullets", [])

            if key in existing_by_key:
                # Merge: find bullets that don't already exist
                existing = existing_by_key[key]
                existing_bullets = (existing.get("description") or "").split("\n")
                existing_normalized = {b.strip().lower() for b in existing_bullets if b.strip()}

                unique_bullets = [
                    b for b in new_bullets
                    if b.strip().lower() not in existing_normalized
                ]

                if unique_bullets:
                    merged = existing.get("description", "") + "\n" + "\n".join(unique_bullets)
                    self._repo.update_experience(existing["id"], description=merged.strip())
                    counts["experiences_merged"] += 1
                else:
                    counts["duplicates_skipped"] += 1
                continue

            description = "\n".join(new_bullets)
            self._repo.save_experience(
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
            result = self._repo.save_skill(
                name=skill["name"],
                category=skill.get("category", "extracted"),
            )
            if result is not None:
                counts["skills"] += 1

        # Save education (dedup by institution)
        existing_edu = self._repo.list_education()
        existing_institutions = {e["institution"].lower() for e in existing_edu if e.get("institution")}
        for edu in parsed.get("education", []):
            inst = edu.get("institution", "")
            if inst.lower() in existing_institutions:
                counts["duplicates_skipped"] += 1
                continue
            self._repo.save_education(
                institution=inst,
                degree=edu.get("degree"),
                field=edu.get("field"),
                end_date=edu.get("end_date"),
            )
            counts["education"] += 1

        # Save projects (dedup by name)
        existing_projects = self._repo.list_projects()
        existing_project_names = {p["name"].lower() for p in existing_projects if p.get("name")}
        for project in parsed.get("projects", []):
            import json

            name = project.get("name", "")
            if name.lower() in existing_project_names:
                counts["duplicates_skipped"] += 1
                continue
            self._repo.save_project(
                name=name,
                description=project.get("description"),
                tech_stack=json.dumps(project.get("tech_stack", [])),
                url=project.get("url"),
            )
            counts["projects"] += 1

        return counts
