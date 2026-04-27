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

        # Store original resume text for LLM prompt (follows user's format)
        if self._conn:
            import json
            # Rebuild full resume text from parsed data
            raw_lines = []
            contact = parsed.get("contact", {})
            if contact.get("name"):
                raw_lines.append(contact["name"])
            if contact.get("raw_contact"):
                raw_lines.append(contact["raw_contact"])
            if contact.get("raw_links"):
                raw_lines.append(contact["raw_links"])

            summary = parsed.get("summary", "")
            if summary:
                raw_lines.append("SUMMARY")
                raw_lines.append(summary)
                raw_lines.append("")

            for exp in parsed.get("experiences", []):
                start = exp.get("start_date", "")
                end = exp.get("end_date") or "Present"
                raw_lines.append(f"{exp.get('company', '')} | {exp.get('title', '')}\t{start} – {end}")
                for bullet in exp.get("bullets", []):
                    raw_lines.append(f"- {bullet}")
                raw_lines.append("")

            if parsed.get("education"):
                raw_lines.append("EDUCATION")
                for edu in parsed["education"]:
                    deg = edu.get("degree", "")
                    field = edu.get("field", "")
                    inst = edu.get("institution", "")
                    date = edu.get("end_date", "")
                    raw_lines.append(f"{deg} in {field}, {inst}\t{date}")
                raw_lines.append("")

            raw_text = "\n".join(raw_lines)
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('original_resume', ?, datetime('now'))",
                (json.dumps(raw_text),),
            )
            self._conn.commit()

        existing_exps = self._repo.list_experiences()
        existing_companies = {
            (e["company"], e["start_date"]) for e in existing_exps
        }

        counts = {"experiences": 0, "skills": 0, "education": 0, "projects": 0, "duplicates_skipped": 0}

        # Save experiences
        for exp in parsed.get("experiences", []):
            key = (exp.get("company"), exp.get("start_date"))
            if key in existing_companies:
                counts["duplicates_skipped"] += 1
                continue

            description = "\n".join(exp.get("bullets", []))
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
                counts["duplicates_skipped"] = counts.get("duplicates_skipped", 0) + 1
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
                counts["duplicates_skipped"] = counts.get("duplicates_skipped", 0) + 1
                continue
            self._repo.save_project(
                name=name,
                description=project.get("description"),
                tech_stack=json.dumps(project.get("tech_stack", [])),
                url=project.get("url"),
            )
            counts["projects"] += 1

        return counts
