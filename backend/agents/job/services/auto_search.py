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

    def search(self, filters: dict, quota_tracker=None) -> list[dict]:
        """Run search across all available job boards.

        Empty filters are OK — defaults to knowledge bank skills + US location.
        """
        title = filters.get("title") or ""
        keywords = filters.get("keywords", [])
        location = filters.get("location") or ""

        # Auto-fill from knowledge bank if empty
        if not title and not keywords:
            skills = self._knowledge_repo.list_skills()
            # Use top skills as a search title (more effective than keywords array)
            skill_names = [
                s["name"] for s in skills[:5]
                if len(s["name"]) > 1 and "(" not in s["name"]  # skip broken names
            ]
            if skill_names:
                title = " ".join(skill_names[:3]) + " engineer"
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
        all_results = self._search_all_boards_sync(boards, search_filters, quota_tracker=quota_tracker)

        # Two-level dedup: URL-based (exact) + title+company (fuzzy, cross-source)
        unique_results = self._deduplicate_results(all_results)

        # Load existing URLs from DB in one query (not N+1)
        existing_url_map = self._job_repo.get_existing_urls()

        # Save to DB and match
        from shared.algorithms.entity_extractor import extract_skills_from_text

        saved_jobs = []
        for result in unique_results:
            skills = extract_skills_from_text(result.description)
            is_existing = False

            # Check DB: URL match first, then title+company fuzzy match
            existing_job_id = existing_url_map.get(result.url)
            if not existing_job_id and result.title and result.company:
                existing_job_id = self._job_repo.find_by_title_and_company(
                    result.title, result.company
                )

            if existing_job_id:
                job_id = existing_job_id
                is_existing = True
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
                # Track new URL for subsequent dedup within this batch
                if result.url:
                    existing_url_map[result.url] = job_id

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
                "description": result.description[:2000],
                "is_existing": is_existing,
            })

        # Sort by algorithmic score — fast, no LLM delay
        saved_jobs.sort(key=lambda j: j.get("match_score") or 0, reverse=True)

        return saved_jobs

    @staticmethod
    def _deduplicate_results(results: list[JobResult]) -> list[JobResult]:
        """Dedup search results by URL (exact) and title+company (cross-source).

        Same job on LinkedIn and Indeed has different URLs but same title+company.
        """
        seen_urls: set[str] = set()
        seen_title_company: set[str] = set()
        unique_results: list[JobResult] = []

        for result in results:
            # URL-based dedup
            if result.url and result.url in seen_urls:
                continue

            # Title+company fuzzy dedup (lowercase, stripped)
            # Only dedup when both title AND company are non-empty
            title_normalized = (result.title or "").lower().strip()
            company_normalized = (result.company or "").lower().strip()
            if title_normalized and company_normalized:
                dedup_key = f"{title_normalized}|{company_normalized}"
                if dedup_key in seen_title_company:
                    continue
                seen_title_company.add(dedup_key)

            if result.url:
                seen_urls.add(result.url)
            unique_results.append(result)

        return unique_results

    def _search_all_boards_sync(self, boards, filters, quota_tracker=None) -> list[JobResult]:
        """Run each board search. All boards use sync httpx — no async, no threads.

        If all premium boards fail (429, network error), falls back to free boards.
        Skips boards whose quota is exhausted (if quota_tracker is provided).
        """
        import logging
        search_logger = logging.getLogger("job.search")

        all_results = []
        premium_failures = []
        for board in boards:
            service_name = board.credential_service_name() if hasattr(board, "credential_service_name") else None
            if service_name and quota_tracker and quota_tracker.is_exhausted(service_name):
                search_logger.info("Skipping %s — quota exhausted", board.board_name())
                premium_failures.append(board.board_name())
                continue

            try:
                results = board.search(filters)
                if service_name and quota_tracker:
                    quota_tracker.record_request(service_name)
                all_results.extend(results)
            except Exception as board_error:
                search_logger.warning("%s search failed: %s", board.board_name(), board_error)
                if board.requires_api_key():
                    premium_failures.append(board.board_name())

        # If premium boards all failed and we got nothing, try free boards as fallback
        if not all_results and premium_failures:
            search_logger.info("All premium boards failed, falling back to free boards")
            from shared.job_boards.factory import get_all_boards
            free_boards = [board for board in get_all_boards() if not board.requires_api_key() and board.is_available()]
            for board in free_boards:
                try:
                    results = board.search(filters)
                    all_results.extend(results)
                except Exception as fallback_error:
                    search_logger.warning("Fallback %s failed: %s", board.board_name(), fallback_error)

        return all_results
