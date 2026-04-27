"""Auto search service — orchestrates job board searches."""

from __future__ import annotations

import asyncio
import json

from shared.job_boards.base import SearchFilters, JobResult
from shared.job_boards.factory import get_available_boards
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.job_matcher import JobMatcherService


class AutoSearchService:
    def __init__(
        self,
        job_repo: JobRepository,
        knowledge_repo: KnowledgeRepository,
        matcher: JobMatcherService,
    ):
        self._job_repo = job_repo
        self._knowledge_repo = knowledge_repo
        self._matcher = matcher

    def search(self, filters: dict) -> list[dict]:
        """Run search across all available job boards.

        Empty filters are OK — defaults to knowledge bank skills + US location.
        """
        title = filters.get("title") or ""
        keywords = filters.get("keywords", [])
        location = filters.get("location") or ""

        # Auto-fill from knowledge bank if empty
        if not title and not keywords:
            skills = self._knowledge_repo.list_skills()
            skill_names = [s["name"] for s in skills[:10]]
            if skill_names:
                keywords = skill_names
            else:
                title = "software engineer"  # absolute fallback

        search_filters = SearchFilters(
            keywords=keywords,
            title=title or None,
            location=location or None,
            remote=filters.get("remote"),
            salary_min=filters.get("salary_min"),
            salary_max=filters.get("salary_max"),
            posted_within_days=filters.get("posted_within_days", 7),
        )

        boards = get_available_boards()
        if not boards:
            return []

        # Run searches synchronously using httpx sync — avoids async/thread issues
        all_results = self._search_all_boards_sync(boards, search_filters)

        # Dedup within this search batch only (not against DB — allows re-searching)
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url in seen_urls or not result.url:
                continue
            seen_urls.add(result.url)
            unique_results.append(result)

        # Save to DB and match
        saved_jobs = []
        for result in unique_results:
            from shared.algorithms.entity_extractor import extract_skills_from_text

            skills = extract_skills_from_text(result.description)

            # Skip if already in DB (by URL)
            existing = None
            if result.url:
                existing_rows = [j for j in self._job_repo.list_jobs() if j.get("source_url") == result.url]
                if existing_rows:
                    existing = existing_rows[0]

            if existing:
                job_id = existing["id"]
            else:
                job_id = self._job_repo.save_job(
                    title=result.title,
                    company=result.company,
                    parsed_data={
                        "required_skills": skills,
                        "description": result.description[:2000],
                        "location": result.location,
                        "salary": result.salary,
                        "source": result.source,
                    },
                    source_url=result.url,
                    source_text=result.description[:2000],
                )

            # Match against knowledge bank
            try:
                match = self._matcher.match_job(job_id)
                match_score = match["score"]
            except Exception:
                match_score = None

            saved_jobs.append({
                "id": job_id,
                "title": result.title,
                "company": result.company,
                "url": result.url,
                "location": result.location,
                "salary": result.salary,
                "source": result.source,
                "match_score": match_score,
                "extracted_skills": skills,
            })

        # Sort by algorithmic score — fast, no LLM delay
        saved_jobs.sort(key=lambda j: j.get("match_score") or 0, reverse=True)

        # LLM deep-match is available via "Evaluate Top 5" button in the UI
        # Not done automatically — keeps search under 5 seconds
        return saved_jobs

    def _search_all_boards_sync(self, boards, filters) -> list[JobResult]:
        """Run each board search. All boards use sync httpx — no async, no threads."""
        all_results = []
        for board in boards:
            try:
                results = board.search(filters)
                all_results.extend(results)
            except Exception as e:
                print(f"[search] {board.board_name()} failed: {e}")
        return all_results
