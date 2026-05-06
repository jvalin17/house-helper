"""Intel gather pipeline — tests for the multi-step Intel orchestration.

Covers: gather with various configured sources, per-step error isolation,
budget enforcement, results caching after gather, actual persistence verification.
"""

import json
import sqlite3
from unittest.mock import patch

import pytest

from shared.db import migrate
from shared.credentials import CredentialStore
from agents.apartment.services.intel_service import IntelService
from agents.apartment.repositories.intel_repo import IntelRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def credential_store(database_connection):
    return CredentialStore(database_connection)


@pytest.fixture
def intel_repo(database_connection):
    return IntelRepository(database_connection)


@pytest.fixture
def sample_listing_id(database_connection):
    """Create a listing with coordinates and source_url."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, bedrooms, bathrooms, sqft, source, source_url,
            amenities, latitude, longitude)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Camden North End",
            "4730 E Palm Valley Blvd, Round Rock, TX 78665",
            1650.0, 1, 1, 740, "realtyapi",
            "https://www.zillow.com/homedetails/55555_zpid/",
            json.dumps(["Pool", "Fitness Center"]),
            30.5280, -97.6670,
        ),
    )
    database_connection.commit()
    return cursor.lastrowid


MOCK_UNIT_DETAILS = {
    "floor_plans": [
        {"name": "1BR Classic", "bedrooms": 1, "bathrooms": 1,
         "min_price": 1650.0, "max_price": 1800.0, "available_count": 5,
         "min_sqft": 720, "max_sqft": 720, "units": []}
    ],
    "total_available": 5,
    "summary": {1: {"label": "1BR", "min_price": 1650.0, "max_price": 1800.0, "total_available": 5}},
}

MOCK_WALK_SCORES = {
    "walk_score": 72,
    "walk_description": "Very Walkable",
    "transit_score": 45,
    "transit_description": "Some Transit",
    "bike_score": 61,
    "bike_description": "Bikeable",
}


# ── Gather with real pipeline, mocked external APIs ────────

@patch("agents.apartment.services.unit_details_service.fetch_unit_details")
def test_gather_persists_unit_details(
    mock_fetch_units, database_connection, credential_store, intel_repo, sample_listing_id
):
    """Gather fetches unit details from RealtyAPI and persists to apartment_intel."""
    credential_store.set_key("realtyapi", "rk-test-realtyapi-key-67890")
    mock_fetch_units.return_value = MOCK_UNIT_DETAILS

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    assert "unit_details" in result["steps_completed"]

    # Verify actual persistence
    saved = intel_repo.get_intel(sample_listing_id, "unit_details")
    assert saved is not None
    assert saved["result"]["total_available"] == 5
    assert saved["result"]["floor_plans"][0]["name"] == "1BR Classic"
    assert saved["source_api"] == "realtyapi"
    assert saved["actual_cost"] == 0.001


@patch("agents.apartment.services.neighborhood_service.get_walk_scores")
def test_gather_persists_verified_scores(
    mock_walk_scores, database_connection, credential_store, intel_repo, sample_listing_id
):
    """Gather fetches Walk Score data and persists to apartment_intel."""
    credential_store.set_key("walkscore", "ws-test-walkscore-key-12345")
    mock_walk_scores.return_value = MOCK_WALK_SCORES

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    assert "verified_scores" in result["steps_completed"]

    saved = intel_repo.get_intel(sample_listing_id, "verified_scores")
    assert saved is not None
    assert saved["result"]["walk_score"] == 72
    assert saved["result"]["transit_score"] == 45
    assert saved["result"]["bike_score"] == 61
    assert saved["source_api"] == "walkscore"
    assert saved["actual_cost"] == 0.0


def test_gather_skips_unconfigured_sources(database_connection, intel_repo, sample_listing_id):
    """Gather skips steps when API keys aren't configured — nothing persisted."""
    service = IntelService(database_connection, llm_provider=None)
    result = service.gather(sample_listing_id)

    assert result["steps_completed"] == []
    assert result["steps_failed"] == {}
    assert result["listing_id"] == sample_listing_id

    # Verify nothing was saved
    assert intel_repo.has_intel(sample_listing_id) is False
    assert result["total_cost"] == 0.0


@patch("agents.apartment.services.neighborhood_service.get_walk_scores")
@patch("agents.apartment.services.unit_details_service.fetch_unit_details")
def test_gather_continues_when_one_step_fails(
    mock_fetch_units, mock_walk_scores,
    database_connection, credential_store, intel_repo, sample_listing_id
):
    """If unit_details fails, verified_scores still runs and persists."""
    credential_store.set_key("realtyapi", "rk-test-realtyapi-key-67890")
    credential_store.set_key("walkscore", "ws-test-walkscore-key-12345")

    mock_fetch_units.side_effect = RuntimeError("RealtyAPI timeout after 20s")
    mock_walk_scores.return_value = MOCK_WALK_SCORES

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    # Unit details failed
    assert "unit_details" in result["steps_failed"]
    assert "RealtyAPI timeout" in result["steps_failed"]["unit_details"]

    # Walk scores succeeded and persisted
    assert "verified_scores" in result["steps_completed"]
    saved_scores = intel_repo.get_intel(sample_listing_id, "verified_scores")
    assert saved_scores is not None
    assert saved_scores["result"]["walk_score"] == 72

    # Only scores are in Intel, not unit details
    assert intel_repo.get_intel(sample_listing_id, "unit_details") is None


def test_gather_blocked_by_per_listing_budget(database_connection, credential_store, intel_repo, sample_listing_id):
    """Gather returns budget error if per-listing $5 cap reached — nothing new saved."""
    credential_store.set_key("walkscore", "ws-test-walkscore-key-12345")

    # Simulate prior spend at cap
    intel_repo.save_intel(sample_listing_id, "floor_plan_analysis", {"score": 78}, actual_cost=5.00)

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    assert result["error"] == "Budget exceeded"
    assert result["per_listing_remaining"] == 0.0

    # Only the pre-existing Intel is there, nothing new
    all_intel = intel_repo.get_all_intel(sample_listing_id)
    assert len(all_intel) == 1
    assert "floor_plan_analysis" in all_intel


def test_gather_nonexistent_listing(database_connection):
    """Gather for nonexistent listing returns specific error."""
    service = IntelService(database_connection)
    result = service.gather(99999)
    assert result["error"] == "Listing not found"


@patch("agents.apartment.services.review_mining_service.fetch_and_analyze_reviews")
@patch("agents.apartment.services.neighborhood_service.get_distance_to_airport")
@patch("agents.apartment.services.neighborhood_service.get_commute_time")
@patch("agents.apartment.services.neighborhood_service.get_walk_scores")
@patch("agents.apartment.services.unit_details_service.fetch_unit_details")
def test_gather_all_sources_persists_all_results(
    mock_fetch_units, mock_walk_scores, mock_commute, mock_airport, mock_reviews,
    database_connection, credential_store, intel_repo, sample_listing_id
):
    """All configured steps run and persist their results independently."""
    credential_store.set_key("realtyapi", "rk-test-realtyapi-key-67890")
    credential_store.set_key("walkscore", "ws-test-walkscore-key-12345")
    credential_store.set_key("google_maps", "gm-test-google-maps-key-abcde")

    mock_fetch_units.return_value = MOCK_UNIT_DETAILS
    mock_walk_scores.return_value = MOCK_WALK_SCORES
    mock_airport.return_value = {
        "airport_distance_km": 32.1, "airport_drive_minutes": 28,
        "airport_distance_text": "20 mi", "airport_drive_text": "28 mins",
    }
    mock_commute.return_value = None  # No workplace configured
    mock_reviews.return_value = {
        "google_rating": 4.2, "total_ratings": 156, "review_count": 5,
        "reviews": [{"author_name": "Sarah Martinez", "rating": 5, "text": "Great place!"}],
    }

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    assert "unit_details" in result["steps_completed"]
    assert "verified_scores" in result["steps_completed"]
    assert "distances" in result["steps_completed"]
    assert "reviews" in result["steps_completed"]
    assert result["steps_failed"] == {}

    # Verify all types persisted
    all_intel = intel_repo.get_all_intel(sample_listing_id)
    assert "unit_details" in all_intel
    assert "verified_scores" in all_intel
    assert "distances" in all_intel
    assert "reviews" in all_intel

    assert all_intel["unit_details"]["result"]["total_available"] == 5
    assert all_intel["verified_scores"]["result"]["walk_score"] == 72
    assert all_intel["distances"]["result"]["airport"]["airport_distance_km"] == 32.1
    assert all_intel["reviews"]["result"]["google_rating"] == 4.2

    # Verify total cost
    assert result["total_cost"] > 0
    assert intel_repo.get_total_cost_for_listing(sample_listing_id) > 0


@patch("agents.apartment.services.unit_details_service.fetch_unit_details")
def test_gather_returns_cached_intel_in_response(
    mock_fetch_units, database_connection, credential_store, intel_repo, sample_listing_id
):
    """Gather response includes all Intel from repo, not just current run."""
    credential_store.set_key("realtyapi", "rk-test-realtyapi-key-67890")

    # Pre-existing Intel from a previous gather
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72}, actual_cost=0.0)

    mock_fetch_units.return_value = MOCK_UNIT_DETAILS

    service = IntelService(database_connection)
    result = service.gather(sample_listing_id)

    # Response includes both old and new Intel
    assert "unit_details" in result["intel"]
    assert "verified_scores" in result["intel"]
    assert result["intel"]["verified_scores"]["result"]["walk_score"] == 72
    assert result["intel"]["unit_details"]["result"]["total_available"] == 5
