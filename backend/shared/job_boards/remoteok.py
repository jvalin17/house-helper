"""RemoteOK — free open API for remote jobs. No API key needed.

Endpoint: https://remoteok.com/api
"""

import httpx

from shared.job_boards.base import SearchFilters, JobResult

API_URL = "https://remoteok.com/api"


class RemoteOKPlugin:
    async def search(self, filters: SearchFilters) -> list[JobResult]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    API_URL,
                    headers={"User-Agent": "HouseHelper/1.0"},
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        # First item is metadata, skip it
        jobs = data[1:] if len(data) > 1 else []

        query_lower = " ".join(filters.keywords).lower()
        if filters.title:
            query_lower += " " + filters.title.lower()

        results = []
        for job in jobs:
            # Filter by keywords if provided
            job_text = f"{job.get('position', '')} {job.get('company', '')} {' '.join(job.get('tags', []))}".lower()
            if query_lower.strip() and not any(kw in job_text for kw in query_lower.split()):
                continue

            results.append(JobResult(
                title=job.get("position", ""),
                company=job.get("company", ""),
                url=job.get("url", ""),
                location="Remote",
                salary=job.get("salary", None),
                description=job.get("description", "")[:2000],
                source="remoteok",
                posted_date=job.get("date"),
            ))

            if len(results) >= 20:
                break

        return results

    def board_name(self) -> str:
        return "remoteok"

    def requires_api_key(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True
