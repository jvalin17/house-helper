"""Indeed job scraper using BeautifulSoup."""

import httpx
from bs4 import BeautifulSoup

from shared.job_boards.base import SearchFilters, JobResult

SEARCH_URL = "https://www.indeed.com/jobs"


class IndeedScraper:
    async def search(self, filters: SearchFilters) -> list[JobResult]:
        query_parts = []
        if filters.title:
            query_parts.append(filters.title)
        query_parts.extend(filters.keywords)

        params = {
            "q": " ".join(query_parts),
            "fromage": str(filters.posted_within_days),
        }
        if filters.location:
            params["l"] = filters.location
        if filters.remote:
            params["remotejob"] = "032b3046-06a3-4876-8dfd-474eb5e7ed11"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(SEARCH_URL, params=params, headers=headers, timeout=15.0)
                response.raise_for_status()
        except Exception:
            return []

        return _parse_results(response.text)

    def board_name(self) -> str:
        return "indeed"

    def requires_api_key(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True


def _parse_results(html: str) -> list[JobResult]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for card in soup.select(".job_seen_beacon, .jobsearch-ResultsList .result"):
        title_el = card.select_one("h2 a, .jobTitle a")
        company_el = card.select_one("[data-testid='company-name'], .companyName")
        location_el = card.select_one("[data-testid='text-location'], .companyLocation")

        if not title_el:
            continue

        href = title_el.get("href", "")
        url = f"https://www.indeed.com{href}" if href.startswith("/") else href

        results.append(JobResult(
            title=title_el.get_text(strip=True),
            company=company_el.get_text(strip=True) if company_el else "",
            url=url,
            location=location_el.get_text(strip=True) if location_el else None,
            source="indeed",
        ))

    return results
