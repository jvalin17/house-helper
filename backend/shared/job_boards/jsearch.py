"""JSearch (RapidAPI) — aggregator covering LinkedIn, Indeed, Glassdoor, etc."""

import os

import httpx

from shared.job_boards.base import SearchFilters, JobResult

API_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchPlugin:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("RAPIDAPI_KEY")

    async def search(self, filters: SearchFilters) -> list[JobResult]:
        if not self._api_key:
            return []

        query_parts = []
        if filters.title:
            query_parts.append(filters.title)
        query_parts.extend(filters.keywords)
        query = " ".join(query_parts) or "software engineer"

        params = {
            "query": query,
            "num_pages": "1",
            "date_posted": "week" if filters.posted_within_days <= 7 else "month" if filters.posted_within_days <= 30 else "all",
            "country": "us",
        }
        if filters.location:
            params["query"] += f" in {filters.location}"
        if filters.remote:
            params["remote_jobs_only"] = "true"

        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()

        results = []
        for job in data.get("data", []):
            results.append(JobResult(
                title=job.get("job_title", ""),
                company=job.get("employer_name", ""),
                url=job.get("job_apply_link") or job.get("job_google_link", ""),
                location=f"{job.get('job_city', '')}, {job.get('job_state', '')}".strip(", "),
                salary=_format_salary(job),
                description=job.get("job_description", "")[:2000],
                source="jsearch",
                posted_date=job.get("job_posted_at_datetime_utc"),
            ))

        return results

    def board_name(self) -> str:
        return "jsearch"

    def requires_api_key(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self._api_key)


def _format_salary(job: dict) -> str | None:
    min_sal = job.get("job_min_salary")
    max_sal = job.get("job_max_salary")
    if min_sal and max_sal:
        return f"${int(min_sal):,} - ${int(max_sal):,}"
    if min_sal:
        return f"${int(min_sal):,}+"
    return None
