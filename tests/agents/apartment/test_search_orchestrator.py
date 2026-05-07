"""Search orchestrator — tests for multi-provider failover and merging.

Tests the Strategy pattern orchestrator that runs all providers,
handles per-provider failures, and merges results.
"""

import pytest

from agents.apartment.services.base_provider import SearchCriteria
from agents.apartment.services.search_orchestrator import run_search


# ── Fake providers for testing ────────────────────────────

class WorkingProvider:
    """Provider that returns realistic listings."""
    source_name = "TestSource"

    def __init__(self, listings=None, configured=True):
        self._listings = listings or []
        self._configured = configured

    def is_configured(self):
        return self._configured

    def search(self, criteria):
        return self._listings


class FailingProvider:
    """Provider that crashes on search."""
    source_name = "BrokenSource"

    def is_configured(self):
        return True

    def search(self, criteria):
        raise RuntimeError("API connection timeout")


class UnconfiguredProvider:
    """Provider without an API key."""
    source_name = "NoKeySource"

    def is_configured(self):
        return False

    def search(self, criteria):
        raise RuntimeError("Should never be called")


AUSTIN_LISTING = {
    "title": "Alexan Braker Pointe",
    "address": "10801 N Mopac Expy, Austin, TX, 78759",
    "price": 1445.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "sqft": 720,
    "source": "realtyapi",
    "images": ["https://photos.zillowstatic.com/fp/photo1.jpg"],
    "amenities": [],
}

DALLAS_LISTING = {
    "title": "Downtown Dallas Loft",
    "address": "500 Elm St, Dallas, TX, 75201",
    "price": 1500.0,
    "bedrooms": 0,
    "bathrooms": 1,
    "sqft": 500,
    "source": "rentcast",
    "images": [],
    "amenities": ["Parking"],
}

CRITERIA = SearchCriteria(city="Austin, TX")


# ── Tests ─────────────────────────────────────────────────

class TestOrchestratorMergesResults:
    def test_merges_results_from_two_providers(self):
        provider_one = WorkingProvider(listings=[AUSTIN_LISTING])
        provider_two = WorkingProvider(listings=[DALLAS_LISTING])
        provider_two.source_name = "SecondSource"

        result = run_search([provider_one, provider_two], CRITERIA)

        assert len(result.listings) == 2
        assert result.listings[0]["title"] == "Alexan Braker Pointe"
        assert result.listings[1]["title"] == "Downtown Dallas Loft"
        assert "TestSource" in result.sources_searched
        assert "SecondSource" in result.sources_searched
        assert result.sources_failed == []

    def test_single_provider_returns_results(self):
        provider = WorkingProvider(listings=[AUSTIN_LISTING])

        result = run_search([provider], CRITERIA)

        assert len(result.listings) == 1
        assert result.sources_searched == ["TestSource"]


class TestOrchestratorHandlesFailures:
    def test_continues_when_first_provider_fails(self):
        failing = FailingProvider()
        working = WorkingProvider(listings=[AUSTIN_LISTING])

        result = run_search([failing, working], CRITERIA)

        assert len(result.listings) == 1
        assert result.listings[0]["title"] == "Alexan Braker Pointe"
        assert "BrokenSource" in result.sources_failed
        assert "TestSource" in result.sources_searched

    def test_continues_when_second_provider_fails(self):
        working = WorkingProvider(listings=[DALLAS_LISTING])
        failing = FailingProvider()

        result = run_search([working, failing], CRITERIA)

        assert len(result.listings) == 1
        assert "TestSource" in result.sources_searched
        assert "BrokenSource" in result.sources_failed

    def test_reports_all_failures_when_both_crash(self):
        failing_one = FailingProvider()
        failing_two = FailingProvider()
        failing_two.source_name = "AnotherBroken"

        result = run_search([failing_one, failing_two], CRITERIA)

        assert result.listings == []
        assert len(result.sources_failed) == 2
        assert "BrokenSource" in result.sources_failed
        assert "AnotherBroken" in result.sources_failed


class TestOrchestratorSkipsUnconfigured:
    def test_skips_provider_without_api_key(self):
        unconfigured = UnconfiguredProvider()
        working = WorkingProvider(listings=[AUSTIN_LISTING])

        result = run_search([unconfigured, working], CRITERIA)

        assert len(result.listings) == 1
        assert "NoKeySource" in result.sources_skipped
        assert "TestSource" in result.sources_searched
        assert result.sources_failed == []

    def test_all_unconfigured_returns_empty(self):
        result = run_search([UnconfiguredProvider()], CRITERIA)

        assert result.listings == []
        assert result.sources_skipped == ["NoKeySource"]
        assert result.sources_searched == []


class TestOrchestratorEmptyResults:
    def test_provider_returns_empty_list(self):
        empty_provider = WorkingProvider(listings=[])

        result = run_search([empty_provider], CRITERIA)

        assert result.listings == []
        assert "TestSource" in result.sources_searched
        assert result.sources_failed == []

    def test_no_providers_returns_empty(self):
        result = run_search([], CRITERIA)

        assert result.listings == []
        assert result.sources_searched == []
