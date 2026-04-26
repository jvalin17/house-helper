"""LinkedIn job scraper using BeautifulSoup.

Scrapes LinkedIn's public job search pages. No API key needed
but may be rate-limited or blocked.
"""

import httpx
from bs4 import BeautifulSoup

from shared.job_boards.base import SearchFilters, JobResult

SEARCH_URL = "https://www.linkedin.com/jobs/search/"


class LinkedInScraper:
    async def search(self, filters: SearchFilters) -> list[JobResult]:
        query_parts = []
        if filters.title:
            query_parts.append(filters.title)
        query_parts.extend(filters.keywords)

        params = {
            "keywords": " ".join(query_parts),
            "f_TPR": f"r{filters.posted_within_days * 86400}",  # time range in seconds
        }
        if filters.location:
            params["location"] = filters.location
        if filters.remote:
            params["f_WT"] = "2"  # remote filter

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
        return "linkedin"

    def requires_api_key(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True


def _parse_results(html: str) -> list[JobResult]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for card in soup.select(".base-card, .job-search-card"):
        title_el = card.select_one(".base-search-card__title, h3")
        company_el = card.select_one(".base-search-card__subtitle, h4")
        location_el = card.select_one(".job-search-card__location, .base-search-card__metadata")
        link_el = card.select_one("a[href*='/jobs/view/']")

        if not title_el:
            continue

        results.append(JobResult(
            title=title_el.get_text(strip=True),
            company=company_el.get_text(strip=True) if company_el else "",
            url=link_el["href"] if link_el else "",
            location=location_el.get_text(strip=True) if location_el else None,
            source="linkedin",
        ))

    return results
