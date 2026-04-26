"""Resume guardrails — evidence-based validation.

Ensures generated resumes only contain data from the knowledge bank.
Logs any user additions separately.
"""

from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.evidence_repo import EvidenceRepository


class ResumeGuardrails:
    def __init__(self, knowledge_repo: KnowledgeRepository, evidence_repo: EvidenceRepository):
        self._knowledge = knowledge_repo
        self._evidence = evidence_repo

    def validate_content(self, resume_content: str) -> dict:
        """Check resume content against knowledge bank.

        Returns dict with verified claims and potential fabrications.
        """
        kb = self._knowledge.get_full_knowledge_bank()

        known_companies = {e["company"].lower() for e in kb["experiences"] if e.get("company")}
        known_titles = {e["title"].lower() for e in kb["experiences"] if e.get("title")}
        known_skills = {s["name"].lower() for s in kb["skills"]}

        lines = resume_content.split("\n")
        verified = []
        unverified = []

        for line in lines:
            line_lower = line.lower().strip()
            if not line_lower or line_lower.startswith("#"):
                continue

            is_verified = False
            for company in known_companies:
                if company in line_lower:
                    is_verified = True
                    break
            for title in known_titles:
                if title in line_lower:
                    is_verified = True
                    break
            for skill in known_skills:
                if skill in line_lower:
                    is_verified = True
                    break

            if is_verified:
                verified.append(line.strip())
            elif len(line.strip()) > 20:  # skip short formatting lines
                unverified.append(line.strip())

        return {
            "verified_count": len(verified),
            "unverified_count": len(unverified),
            "unverified_lines": unverified[:10],  # show max 10
            "is_clean": len(unverified) == 0,
        }

    def log_user_addition(self, entity_type: str, entity_id: int, text: str) -> None:
        """Log when user adds content not from the knowledge bank."""
        self._evidence.log(
            entity_type=entity_type,
            entity_id=entity_id,
            source="user_override",
            original_text=text,
        )
