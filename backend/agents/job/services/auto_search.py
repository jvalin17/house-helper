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
        """Run search across all available job boards."""
        search_filters = SearchFilters(
            keywords=filters.get("keywords", []),
            title=filters.get("title"),
            location=filters.get("location"),
            remote=filters.get("remote"),
            salary_min=filters.get("salary_min"),
            salary_max=filters.get("salary_max"),
            posted_within_days=filters.get("posted_within_days", 7),
        )

        # Auto-add skills from knowledge bank as keywords if none provided
        if not search_filters.keywords:
            skills = self._knowledge_repo.list_skills()
            search_filters.keywords = [s["name"] for s in skills[:10]]

        boards = get_available_boards()
        if not boards:
            return []

        all_results = asyncio.run(self._search_all_boards(boards, search_filters))

        # Dedup by URL
        seen_urls = set()
        existing_urls = {j.get("source_url") for j in self._job_repo.list_jobs() if j.get("source_url")}
        unique_results = []
        for result in all_results:
            if result.url in seen_urls or result.url in existing_urls:
                continue
            seen_urls.add(result.url)
            unique_results.append(result)

        # Save to DB and match
        saved_jobs = []
        for result in unique_results:
            from shared.algorithms.entity_extractor import extract_skills_from_text

            skills = extract_skills_from_text(result.description)
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

        # Sort by match score
        saved_jobs.sort(key=lambda j: j.get("match_score") or 0, reverse=True)
        return saved_jobs

    async def _search_all_boards(self, boards, filters) -> list[JobResult]:
        tasks = [board.search(filters) for board in boards]
        results_per_board = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for results in results_per_board:
            if isinstance(results, list):
                all_results.extend(results)
        return all_results
