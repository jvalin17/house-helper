"""Job parser service — parse job postings from text or URL.

Detects whether input is a URL or raw text.
URLs are fetched (with JSON-LD extraction), then parsed.
Uses LLM when available, falls back to regex/BeautifulSoup parsing.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from shared.scraping.extractors import detect_input_type, extract_text_from_html, extract_job_from_jsonld
from shared.scraping.fetcher import fetch_url
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

    def parse_input(self, user_input: str) -> dict:
        """Parse a job posting from a URL or raw text."""
        input_type = detect_input_type(user_input)

        if input_type == "url":
            return self._parse_url(user_input.strip())
        else:
            return self._parse_text(user_input)

    def _parse_url(self, url: str) -> dict:
        """Fetch a URL, extract content, and parse the job posting."""
        try:
            html = asyncio.run(fetch_url(url))
        except Exception as e:
            # If fetch fails, save what we have with the URL
            job_id = self._job_repo.save_job(
                title="(failed to fetch)",
                company=None,
                parsed_data={"error": str(e), "source_url": url},
                source_url=url,
            )
            return {
                "id": job_id,
                "title": "(failed to fetch)",
                "company": None,
                "error": f"Could not fetch URL: {e}",
                "extracted_skills": [],
            }

        # Try JSON-LD first (most reliable for job boards)
        jsonld = extract_job_from_jsonld(html)
        if jsonld:
            return self._save_from_jsonld(jsonld, url, html)

        # Fall back to text extraction + regex parsing
        text = extract_text_from_html(html)
        parsed = parse_job_text(text)

        title = parsed.get("title") or "(untitled)"
        job_id = self._job_repo.save_job(
            title=title,
            company=parsed.get("company"),
            parsed_data=parsed,
            source_url=url,
            source_text=text,
        )

        return {
            "id": job_id,
            "title": title,
            "company": parsed.get("company"),
            "location": parsed.get("location"),
            "salary_range": parsed.get("salary_range"),
            "remote_status": parsed.get("remote_status"),
            "extracted_skills": parsed.get("extracted_skills", []),
        }

    def _save_from_jsonld(self, jsonld: dict, url: str, html: str) -> dict:
        """Save a job parsed from JSON-LD structured data."""
        from shared.algorithms.entity_extractor import extract_skills_from_text

        description = jsonld.get("description", "")
        skills = extract_skills_from_text(description)
        locations = jsonld.get("locations", [])

        parsed_data = {
            "required_skills": skills,
            "description": description,
            "locations": locations,
        }

        title = jsonld.get("title") or "(untitled)"
        company = jsonld.get("company")

        job_id = self._job_repo.save_job(
            title=title,
            company=company,
            parsed_data=parsed_data,
            source_url=url,
            source_text=description[:2000],
        )

        return {
            "id": job_id,
            "title": title,
            "company": company,
            "location": "; ".join(locations) if locations else None,
            "salary_range": None,
            "remote_status": None,
            "extracted_skills": skills,
        }

    def _parse_text(self, text: str) -> dict:
        """Parse a job posting from raw pasted text."""
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
            "title": title,
            "company": parsed.get("company"),
            "location": parsed.get("location"),
            "salary_range": parsed.get("salary_range"),
            "remote_status": parsed.get("remote_status"),
            "extracted_skills": parsed.get("extracted_skills", []),
        }

    def parse_batch(self, inputs: list[str]) -> list[dict]:
        """Parse multiple job postings (URLs or text)."""
        return [self.parse_input(inp) for inp in inputs]
