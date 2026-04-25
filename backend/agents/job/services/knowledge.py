"""Knowledge bank service — resume import and knowledge management.

Parses resume files and populates the knowledge bank with
structured entries. No LLM needed.
"""

from pathlib import Path

from shared.scraping.resume_parser import parse_resume
from agents.job.repositories.knowledge_repo import KnowledgeRepository


class KnowledgeService:
    def __init__(self, knowledge_repo: KnowledgeRepository):
        self._repo = knowledge_repo

    def import_resume(self, file_path: Path, save: bool = True) -> dict:
        """Parse a resume file and populate the knowledge bank.

        Args:
            file_path: Path to DOCX, PDF, or TXT resume.
            save: If True, saves to DB. If False, returns preview only.
        """
        parsed = parse_resume(file_path)

        if not save:
            return {"preview": parsed}

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

        # Save education
        for edu in parsed.get("education", []):
            self._repo.save_education(
                institution=edu.get("institution", ""),
                degree=edu.get("degree"),
                field=edu.get("field"),
                end_date=edu.get("end_date"),
            )
            counts["education"] += 1

        # Save projects
        for project in parsed.get("projects", []):
            import json

            self._repo.save_project(
                name=project.get("name", ""),
                description=project.get("description"),
                tech_stack=json.dumps(project.get("tech_stack", [])),
                url=project.get("url"),
            )
            counts["projects"] += 1

        return counts
