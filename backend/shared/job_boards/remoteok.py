"""RemoteOK — free open API for remote jobs. No API key needed.

Endpoint: https://remoteok.com/api
"""

import httpx

from shared.job_boards.base import SearchFilters, JobResult

API_URL = "https://remoteok.com/api"


class RemoteOKPlugin:
    def search(self, filters: SearchFilters) -> list[JobResult]:
        try:
            response = httpx.get(API_URL, headers={"User-Agent": "HouseHelper/1.0"}, timeout=15.0)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        # First item is metadata, skip it
        jobs = data[1:] if len(data) > 1 else []

        # Build search terms — split multi-word title into individual terms
        search_terms = []
        if filters.title:
            search_terms.extend(filters.title.lower().split())
        search_terms.extend(kw.lower() for kw in filters.keywords)
        # Remove very common words that match everything
        stop = {"the", "a", "an", "and", "or", "in", "at", "for", "of", "to"}
        search_terms = [t for t in search_terms if t not in stop and len(t) > 2]

        results = []
        for job in jobs:
            job_text = f"{job.get('position', '')} {job.get('company', '')} {' '.join(job.get('tags', []))}".lower()
            # If search terms provided, at least one must match
            if search_terms and not any(term in job_text for term in search_terms):
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

            if len(results) >= 30:
                break

        return results

    def board_name(self) -> str:
        return "remoteok"

    def requires_api_key(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True
