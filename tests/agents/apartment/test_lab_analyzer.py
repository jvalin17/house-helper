"""Lab analyzer service — tests for the analysis pipeline.

Tests cover: data gathering, cache usage, LLM integration, no-LLM mode,
comparable listing context, and streaming.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.feature_preferences_repo import FeaturePreferencesRepository
from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository
from agents.apartment.services.lab_analyzer import LabAnalyzerService
from shared.llm.base import LLMProviderBase


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_repo(database_connection):
    return ApartmentListingRepository(database_connection)


@pytest.fixture
def feature_preferences_repo(database_connection):
    return FeaturePreferencesRepository(database_connection)


@pytest.fixture
def lab_analysis_repo(database_connection):
    return LabAnalysisRepository(database_connection)


@pytest.fixture
def sample_listing_id(listing_repo):
    """Create a realistic listing and return its ID."""
    return listing_repo.save_listing(
        title="Alexan Braker Pointe",
        address="10801 N Mopac Expy, Austin, TX, 78759",
        price=1445.0,
        bedrooms=1,
        bathrooms=1,
        sqft=720,
        source="realtyapi",
        source_url="https://www.zillow.com/homedetails/12345_zpid/",
        amenities=["24 units", "Lounge (17%)", "Special Offer"],
        latitude=30.4186,
        longitude=-97.7404,
    )


@pytest.fixture
def comparable_listing_id(listing_repo):
    """Create a comparable listing in the same city."""
    return listing_repo.save_listing(
        title="Camden Stoneleigh",
        address="4825 Davis Ln, Austin, TX, 78749",
        price=1109.0,
        bedrooms=1,
        bathrooms=1,
        sqft=680,
        source="realtyapi",
    )


MOCK_LLM_RESPONSE = json.dumps({
    "overview": "Alexan Braker Pointe is a modern complex in North Austin near the Mopac corridor.",
    "price_verdict": "below_market",
    "price_reasoning": "At $1,445/mo for a 1BR, this is below the Austin median of ~$1,600.",
    "neighborhood": {
        "summary": "North Austin tech corridor, convenient to Domain and major employers.",
        "nearby_grocery": ["H-E-B (~1.2 miles)", "Trader Joe's (~2 miles)"],
        "nearby_restaurants": ["Torchy's Tacos — Mexican (~0.5 miles)"],
        "nearby_parks": ["Bull Creek Park (~1 mile)"],
        "transit_access": "Limited — car-dependent area with some bus routes.",
        "walkability": "Moderate — some errands walkable but car needed for most.",
        "noise_concerns": "Mopac highway noise possible for units facing east.",
        "nearest_airport": "Austin-Bergstrom International Airport (~20 miles)",
    },
    "red_flags": ["Highway noise from Mopac", "Limited transit"],
    "green_lights": ["Below market price", "24 units available", "Special offer"],
    "questions_to_ask": ["What's the lease break penalty?", "Which units face away from Mopac?"],
    "match_score": 82,
    "match_reasoning": "Good price and availability, but limited transit may be a concern.",
})


class FakeLLMProvider(LLMProviderBase):
    """Mock LLM that returns a canned analysis response."""

    def __init__(self, response: str = MOCK_LLM_RESPONSE):
        self._response = response
        self._configured = True
        self.call_count = 0

    def complete(self, prompt, system=None, feature="unknown", force_override=False):
        self.call_count += 1
        return self._response

    def complete_stream(self, prompt, system=None, feature="unknown", force_override=False):
        self.call_count += 1
        # Yield in chunks to simulate streaming
        words = self._response.split(" ")
        for i in range(0, len(words), 5):
            yield " ".join(words[i:i + 5])
            if i + 5 < len(words):
                yield " "

    def is_configured(self):
        return self._configured

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "fake-lab-v1"


class FakeUnconfiguredLLM(LLMProviderBase):
    """Mock LLM that is not configured."""

    def complete(self, prompt, system=None):
        raise RuntimeError("Not configured")

    def is_configured(self):
        return False

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "none"


# ── Tests ─────────────────────────────────────────────────

class TestAnalyzeWithLLM:
    def test_analyze_returns_structured_result(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        result = analyzer.analyze(sample_listing_id)

        assert result["listing"]["title"] == "Alexan Braker Pointe"
        assert result["listing"]["price"] == 1445.0
        assert "overview" in result["analyses"]
        analysis = result["analyses"]["overview"]
        assert analysis["price_verdict"] == "below_market"
        assert analysis["match_score"] == 82
        assert "Mopac" in analysis["red_flags"][0]
        assert len(analysis["neighborhood"]["nearby_grocery"]) >= 1

    def test_analyze_includes_user_preferences(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        feature_preferences_repo.set_preference("Parking", "building", "must_have")
        feature_preferences_repo.set_preference("No dishwasher", "unit", "deal_breaker")
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        result = analyzer.analyze(sample_listing_id)

        assert "Parking" in result["must_haves"]
        assert "No dishwasher" in result["deal_breakers"]

    def test_analyze_includes_comparables_count(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo,
        sample_listing_id, comparable_listing_id,
    ):
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        result = analyzer.analyze(sample_listing_id)
        assert result["comparable_count"] >= 1


class TestAnalyzeCache:
    def test_uses_cache_when_fresh(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        """Second analyze should use cache — no LLM call."""
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        # First call — hits LLM
        analyzer.analyze(sample_listing_id)
        assert mock_llm.call_count == 1

        # Second call — should use cache
        result = analyzer.analyze(sample_listing_id)
        assert mock_llm.call_count == 1  # No additional call
        assert "overview" in result["analyses"]

    def test_calls_llm_when_cache_expired(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id, database_connection,
    ):
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        # First call
        analyzer.analyze(sample_listing_id)
        assert mock_llm.call_count == 1

        # Expire cache
        database_connection.execute(
            "UPDATE apartment_lab_analysis SET created_at = datetime('now', '-25 hours')"
        )
        database_connection.commit()

        # Should call LLM again
        analyzer.analyze(sample_listing_id)
        assert mock_llm.call_count == 2


class TestAnalyzeWithoutLLM:
    def test_returns_data_without_analysis(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        """Without LLM, should still return listing + preferences."""
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, llm_provider=None)

        result = analyzer.get_lab_data(sample_listing_id)

        assert result["listing"]["title"] == "Alexan Braker Pointe"
        assert result["analyses"] == {}
        assert "pipeline_steps" in result

    def test_unconfigured_llm_returns_data_only(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        unconfigured_llm = FakeUnconfiguredLLM()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, unconfigured_llm)

        result = analyzer.analyze(sample_listing_id)

        assert result["listing"]["title"] == "Alexan Braker Pointe"
        assert result["analyses"] == {}


class TestAnalyzeStream:
    def test_stream_yields_chunks(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        chunks = list(analyzer.analyze_stream(sample_listing_id))
        assert len(chunks) > 1  # Multiple chunks, not a single blob
        full_text = "".join(chunks)
        assert "below_market" in full_text

    def test_stream_uses_cache(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        """If cache exists, stream should yield cached result as one chunk."""
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        # Populate cache
        analyzer.analyze(sample_listing_id)
        assert mock_llm.call_count == 1

        # Stream should use cache
        chunks = list(analyzer.analyze_stream(sample_listing_id))
        assert mock_llm.call_count == 1  # No additional LLM call
        assert len(chunks) == 1  # Single cached chunk


class TestAnalyzeErrorHandling:
    def test_handles_nonexistent_listing(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo,
    ):
        mock_llm = FakeLLMProvider()
        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, mock_llm)

        result = analyzer.analyze(99999)
        assert "gather_listing" in result["pipeline_errors"]

    def test_handles_llm_error_gracefully(
        self, listing_repo, feature_preferences_repo, lab_analysis_repo, sample_listing_id,
    ):
        """LLM failure should not crash — returns gathered data without analysis."""
        class FailingLLM(LLMProviderBase):
            def complete(self, prompt, system=None, feature="unknown", force_override=False):
                raise RuntimeError("API timeout")
            def is_configured(self): return True
            def provider_name(self): return "failing"
            def model_name(self): return "fail-v1"

        analyzer = LabAnalyzerService(listing_repo, feature_preferences_repo, lab_analysis_repo, FailingLLM())

        result = analyzer.analyze(sample_listing_id)
        assert result["listing"]["title"] == "Alexan Braker Pointe"
        assert "run_llm_analysis" in result["pipeline_errors"]
