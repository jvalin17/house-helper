"""Job parser service — parse job postings from text or URL.

Uses LLM when available, falls back to regex/BeautifulSoup parsing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shared.scraping.parsers import parse_job_text
from agents.job.repositories.job_repo import JobRepository

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider


class JobParserService:
    def __init__(
        self,
        job_repo: JobRepository,
        llm_provider: LLMProvider | None = None,
    ):
        self._job_repo = job_repo
        self._llm = llm_provider

    def parse_text(self, text: str) -> dict:
        """Parse a job posting from raw text and save to database."""
        parsed = parse_job_text(text)

        title = parsed.get("title") or "(untitled)"

        job_id = self._job_repo.save_job(
            title=title,
            company=parsed.get("company"),
            parsed_data=parsed,
            source_text=text,
        )

        return {
            "id": job_id,
            "title": parsed.get("title"),
            "company": parsed.get("company"),
            "location": parsed.get("location"),
            "salary_range": parsed.get("salary_range"),
            "remote_status": parsed.get("remote_status"),
            "extracted_skills": parsed.get("extracted_skills", []),
        }

    def parse_batch(self, texts: list[str]) -> list[dict]:
        """Parse multiple job postings."""
        return [self.parse_text(text) for text in texts]
