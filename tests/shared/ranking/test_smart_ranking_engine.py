"""Smart Ranking Engine — tests for scoring, sorting, and normalization.

Covers: single result scoring, batch scoring with sort, search intent boost,
cold start (no ranking), normalization to 0-100, graceful empty input.
"""

import sqlite3

import pytest

from shared.db import migrate
from shared.ranking.smart_ranking_engine import (
    score_single_result,
    score_and_sort_results,
    _normalize_scores,
    RankingResult,
    SEARCH_TERM_BOOST,
)
from shared.ranking.term_extractor import extract_job_terms, extract_apartment_terms
from shared.ranking.learning_machine import record_interaction, recalculate_and_store_weights


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


# ── Single result scoring ────────────────────────────

def test_score_with_learned_weights():
    """Result with terms matching learned weights gets positive score."""
    learned_weights = {"python": 3.0, "remote": 2.0, "senior": 1.5}
    result_terms = ["python", "remote", "java", "onsite"]
    search_terms = []

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    assert ranking.raw_score == 5.0  # python(3.0) + remote(2.0)
    assert ranking.matched_learned_terms == {"python": 3.0, "remote": 2.0}
    assert "java" not in ranking.matched_learned_terms


def test_score_with_search_boost():
    """Search terms add SEARCH_TERM_BOOST per match."""
    learned_weights = {}
    result_terms = ["python", "remote", "austin"]
    search_terms = ["python", "austin"]

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    assert ranking.raw_score == 2 * SEARCH_TERM_BOOST
    assert "python" in ranking.matched_search_terms
    assert "austin" in ranking.matched_search_terms


def test_score_combined_learned_and_search():
    """Both learned weights and search boost combine."""
    learned_weights = {"python": 2.0}
    result_terms = ["python", "remote"]
    search_terms = ["remote"]

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    expected_score = 2.0 + SEARCH_TERM_BOOST  # python weight + remote search boost
    assert ranking.raw_score == expected_score


def test_score_no_matches():
    """Result with no matching terms gets zero score."""
    learned_weights = {"python": 3.0}
    result_terms = ["java", "onsite"]
    search_terms = ["golang"]

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    assert ranking.raw_score == 0.0
    assert ranking.matched_learned_terms == {}
    assert ranking.matched_search_terms == []


def test_cold_start_no_composite_score():
    """With fewer than 3 learned terms and no search, composite_score is None."""
    learned_weights = {"python": 1.0}  # only 1 term — below threshold
    result_terms = ["python"]
    search_terms = []

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    assert ranking.composite_score is None  # not enough data


def test_search_terms_enable_scoring_without_learned():
    """Search terms alone are enough to enable scoring (even without learned weights)."""
    learned_weights = {}
    result_terms = ["python", "remote"]
    search_terms = ["python"]

    ranking = score_single_result(result_terms, learned_weights, search_terms)

    assert ranking.composite_score is not None  # search terms enable scoring


# ── Batch scoring + sorting ──────────────────────────

def test_score_and_sort_orders_by_score(database_connection):
    """Results sorted by composite score, highest first."""
    # Seed some learned weights
    for interaction_index in range(6):
        record_interaction(
            database_connection, profile_id=None, agent="job",
            entity_id=interaction_index, interaction_type="save",
            terms=["python", "remote", "senior"],
        )
    recalculate_and_store_weights(database_connection, profile_id=None, agent="job")

    results = [
        {"title": "Java Dev", "company": "Corp", "description": "Java onsite role", "location": "Dallas"},
        {"title": "Senior Python Engineer", "company": "Startup", "description": "Python remote", "location": "Remote", "salary": "$150,000"},
        {"title": "Junior QA", "company": "Agency", "description": "Manual testing", "location": "Austin"},
    ]

    ranked = score_and_sort_results(
        results=results,
        term_extractor=extract_job_terms,
        agent="job",
        search_filters={"title": "python remote"},
        connection=database_connection,
    )

    # Python remote job should rank first (matches learned weights + search terms)
    assert ranked[0]["title"] == "Senior Python Engineer"
    assert ranked[0]["ranking_score"] is not None
    assert ranked[0]["ranking_score"] >= ranked[1].get("ranking_score", 0) or 0


def test_score_and_sort_cold_start(database_connection):
    """With no learned weights and no search terms, results keep original order."""
    results = [
        {"title": "Job A", "company": "Co A", "description": ""},
        {"title": "Job B", "company": "Co B", "description": ""},
    ]

    ranked = score_and_sort_results(
        results=results,
        term_extractor=extract_job_terms,
        agent="job",
        search_filters={},
        connection=database_connection,
    )

    # No learned weights, no search terms → ranking_score is None, original order
    assert ranked[0]["title"] == "Job A"
    assert ranked[0]["ranking_score"] is None


def test_score_and_sort_empty_results(database_connection):
    """Empty results list returns empty."""
    ranked = score_and_sort_results(
        results=[],
        term_extractor=extract_job_terms,
        agent="job",
        search_filters={},
        connection=database_connection,
    )
    assert ranked == []


def test_score_and_sort_apartments(database_connection):
    """Ranking works for apartment listings too."""
    # Teach the system that user likes pool + austin
    for interaction_index in range(6):
        record_interaction(
            database_connection, profile_id=None, agent="apartment",
            entity_id=interaction_index, interaction_type="click",
            terms=["pool", "austin", "2br"],
        )
    recalculate_and_store_weights(database_connection, profile_id=None, agent="apartment")

    listings = [
        {"title": "No Pool Apt", "address": "Dallas, TX", "amenities": ["Gym"], "bedrooms": 1, "price": 1200},
        {"title": "Pool Haven", "address": "Austin, TX", "amenities": ["Pool", "Gym"], "bedrooms": 2, "price": 1800},
    ]

    ranked = score_and_sort_results(
        results=listings,
        term_extractor=extract_apartment_terms,
        agent="apartment",
        search_filters={"location": "Austin"},
        connection=database_connection,
    )

    # Pool + Austin + 2br listing should rank first
    assert ranked[0]["title"] == "Pool Haven"
    assert ranked[0]["ranking_score"] > ranked[1]["ranking_score"]


# ── Normalization ────────────────────────────────────

def test_normalization_spread():
    """Scores normalized to 20-100 range."""
    result_a = RankingResult(composite_score=0, raw_score=10.0, matched_learned_terms={}, matched_search_terms=[], result_terms=[])
    result_b = RankingResult(composite_score=0, raw_score=0.0, matched_learned_terms={}, matched_search_terms=[], result_terms=[])
    result_c = RankingResult(composite_score=0, raw_score=5.0, matched_learned_terms={}, matched_search_terms=[], result_terms=[])

    scored = [({}, result_a), ({}, result_b), ({}, result_c)]
    _normalize_scores(scored)

    assert result_a.composite_score == 100  # highest
    assert result_b.composite_score == 20   # lowest (floor at 20)
    assert 40 < result_c.composite_score < 80  # middle


def test_normalization_all_equal():
    """All equal raw scores → everyone gets 50."""
    result_a = RankingResult(composite_score=0, raw_score=5.0, matched_learned_terms={}, matched_search_terms=[], result_terms=[])
    result_b = RankingResult(composite_score=0, raw_score=5.0, matched_learned_terms={}, matched_search_terms=[], result_terms=[])

    scored = [({}, result_a), ({}, result_b)]
    _normalize_scores(scored)

    assert result_a.composite_score == 50
    assert result_b.composite_score == 50
