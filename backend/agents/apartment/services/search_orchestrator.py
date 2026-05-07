"""Search orchestrator — runs all enabled providers, deduplicates, and merges.

Uses the Strategy pattern: each provider implements ApartmentSearchProvider.
The orchestrator handles failures per-provider, so one bad source
never kills the entire search. After collecting results from all sources,
the data processor deduplicates and merges listings that refer to the
same physical property.
"""

from dataclasses import dataclass, field

from shared.app_logger import get_logger
from agents.apartment.services.base_provider import (
    ApartmentSearchProvider,
    SearchCriteria,
)
from agents.apartment.services.data_processor import deduplicate_listings

logger = get_logger("apartment.search")


@dataclass
class SearchResult:
    """Aggregated results from all providers."""
    listings: list[dict] = field(default_factory=list)
    sources_searched: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    sources_skipped: list[str] = field(default_factory=list)
    total_before_dedup: int = 0


def run_search(
    providers: list[ApartmentSearchProvider],
    criteria: SearchCriteria,
) -> SearchResult:
    """Run search across all configured providers.

    - Skips providers without API keys (reported in sources_skipped).
    - Catches failures per-provider (reported in sources_failed).
    - Deduplicates listings from multiple sources into unique properties.
    """
    result = SearchResult()

    for provider in providers:
        if not provider.is_configured():
            result.sources_skipped.append(provider.source_name)
            logger.info("Skipping %s — not configured", provider.source_name)
            continue

        try:
            listings = provider.search(criteria)
            if listings:
                result.listings.extend(listings)
            result.sources_searched.append(provider.source_name)
            logger.info("%s returned %d listings", provider.source_name, len(listings))
        except Exception as search_error:
            logger.error("%s failed: %s", provider.source_name, search_error)
            result.sources_failed.append(provider.source_name)

    # Deduplicate across sources
    result.total_before_dedup = len(result.listings)
    if len(result.sources_searched) > 1 and result.listings:
        result.listings = deduplicate_listings(result.listings)

    return result
