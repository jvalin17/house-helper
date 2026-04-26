"""Adzuna API — free job search API (250 requests/day free).

Sign up at https://developer.adzuna.com for app_id and app_key.
"""

import os

import httpx

from shared.job_boards.base import SearchFilters, JobResult

API_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"


class AdzunaPlugin:
    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        self._app_id = app_id or os.environ.get("ADZUNA_APP_ID")
        self._app_key = app_key or os.environ.get("ADZUNA_APP_KEY")

    async def search(self, filters: SearchFilters) -> list[JobResult]:
        if not self._app_id or not self._app_key:
            return []

        query_parts = []
        if filters.title:
            query_parts.append(filters.title)
        query_parts.extend(filters.keywords)

        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": " ".join(query_parts) or "software engineer",
            "results_per_page": "20",
            "max_days_old": str(filters.posted_within_days),
        }
        if filters.location:
            params["where"] = filters.location
        if filters.salary_min:
            params["salary_min"] = str(filters.salary_min)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(API_URL, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results = []
        for job in data.get("results", []):
            salary = None
            if job.get("salary_min") and job.get("salary_max"):
                salary = f"${int(job['salary_min']):,} - ${int(job['salary_max']):,}"

            results.append(JobResult(
                title=job.get("title", ""),
                company=job.get("company", {}).get("display_name", ""),
                url=job.get("redirect_url", ""),
                location=job.get("location", {}).get("display_name", ""),
                salary=salary,
                description=job.get("description", "")[:2000],
                source="adzuna",
                posted_date=job.get("created"),
            ))

        return results

    def board_name(self) -> str:
        return "adzuna"

    def requires_api_key(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self._app_id and self._app_key)
