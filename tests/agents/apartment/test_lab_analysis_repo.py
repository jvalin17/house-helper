"""Lab analysis cache repository — tests for cached LLM results with TTL.

Analyses are cached per listing+type. Expire after 24 hours.
"""

import sqlite3

import pytest

from shared.db import migrate
from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    # Create a test listing to reference
    connection.execute(
        "INSERT INTO apartment_listings (id, title, price) VALUES (1, 'Alexan Braker Pointe', 1445)"
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def lab_analysis_repo(database_connection):
    return LabAnalysisRepository(database_connection)


SAMPLE_OVERVIEW_RESULT = {
    "overview": "Alexan Braker Pointe is a modern complex in North Austin.",
    "price_verdict": "below_market",
    "red_flags": ["No dishwasher"],
    "green_lights": ["Below market price", "24 units available"],
    "match_score": 85,
}


class TestCachedAnalysis:
    def test_save_and_retrieve_analysis(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(1, "overview", SAMPLE_OVERVIEW_RESULT)
        cached = lab_analysis_repo.get_cached_analysis(1, "overview")
        assert cached is not None
        assert cached["overview"] == "Alexan Braker Pointe is a modern complex in North Austin."
        assert cached["price_verdict"] == "below_market"
        assert cached["match_score"] == 85

    def test_cache_returns_none_when_expired(self, lab_analysis_repo, database_connection):
        """Analysis older than 24h should not be returned."""
        lab_analysis_repo.save_analysis(1, "overview", SAMPLE_OVERVIEW_RESULT)
        # Manually backdate the created_at to 25 hours ago
        database_connection.execute(
            "UPDATE apartment_lab_analysis SET created_at = datetime('now', '-25 hours') WHERE listing_id = 1"
        )
        database_connection.commit()
        cached = lab_analysis_repo.get_cached_analysis(1, "overview")
        assert cached is None

    def test_cache_returns_result_when_fresh(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(1, "overview", SAMPLE_OVERVIEW_RESULT)
        cached = lab_analysis_repo.get_cached_analysis(1, "overview")
        assert cached is not None
        assert cached["match_score"] == 85

    def test_get_nonexistent_returns_none(self, lab_analysis_repo):
        cached = lab_analysis_repo.get_cached_analysis(999, "overview")
        assert cached is None

    def test_save_overwrites_previous(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(1, "overview", {"score": 70})
        lab_analysis_repo.save_analysis(1, "overview", {"score": 90})
        cached = lab_analysis_repo.get_cached_analysis(1, "overview")
        assert cached["score"] == 90

    def test_save_with_token_metadata(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(
            1, "overview", SAMPLE_OVERVIEW_RESULT,
            prompt_tokens=1200, completion_tokens=800, estimated_cost=0.0045,
        )
        cached = lab_analysis_repo.get_cached_analysis(1, "overview")
        assert cached is not None


class TestGetAllForListing:
    def test_returns_all_analysis_types(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(1, "overview", {"text": "overview result"})
        lab_analysis_repo.save_analysis(1, "price_verdict", {"verdict": "fair"})
        all_analyses = lab_analysis_repo.get_all_for_listing(1)
        assert "overview" in all_analyses
        assert "price_verdict" in all_analyses
        assert all_analyses["overview"]["text"] == "overview result"
        assert all_analyses["price_verdict"]["verdict"] == "fair"

    def test_excludes_expired_analyses(self, lab_analysis_repo, database_connection):
        lab_analysis_repo.save_analysis(1, "overview", {"text": "fresh"})
        lab_analysis_repo.save_analysis(1, "old_type", {"text": "stale"})
        database_connection.execute(
            "UPDATE apartment_lab_analysis SET created_at = datetime('now', '-25 hours') WHERE analysis_type = 'old_type'"
        )
        database_connection.commit()
        all_analyses = lab_analysis_repo.get_all_for_listing(1)
        assert "overview" in all_analyses
        assert "old_type" not in all_analyses

    def test_returns_empty_for_no_analyses(self, lab_analysis_repo):
        assert lab_analysis_repo.get_all_for_listing(999) == {}


class TestInvalidate:
    def test_invalidate_deletes_all_for_listing(self, lab_analysis_repo):
        lab_analysis_repo.save_analysis(1, "overview", {"text": "will be deleted"})
        lab_analysis_repo.save_analysis(1, "price", {"verdict": "also deleted"})
        lab_analysis_repo.invalidate(1)
        assert lab_analysis_repo.get_all_for_listing(1) == {}

    def test_invalidate_nonexistent_does_not_crash(self, lab_analysis_repo):
        lab_analysis_repo.invalidate(999)  # should not raise
