"""Intel service — tests for cost estimation and budget enforcement.

Covers: estimate with all sources configured, partial sources, no sources,
budget caps (per-listing and daily), floor plan detection, cached Intel detection.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from shared.credentials import CredentialStore
from agents.apartment.services.intel_service import IntelService, PER_LISTING_COST_CAP
from agents.apartment.repositories.intel_repo import IntelRepository


# ── Fixtures ──────────────────────────────────────────

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
def sample_listing_id(database_connection):
    """Create a realistic listing and return its ID."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, bedrooms, bathrooms, sqft, source, source_url, amenities, latitude, longitude)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Alexan Braker Pointe",
            "10801 N Mopac Expy, Austin, TX 78759",
            1445.0, 1, 1, 720, "realtyapi",
            "https://www.zillow.com/homedetails/12345_zpid/",
            json.dumps(["Pool", "Gym", "Concierge"]),
            30.4186, -97.7404,
        ),
    )
    database_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def listing_without_url(database_connection):
    """Create a listing with no source_url."""
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, address, price) VALUES (?, ?, ?)",
        ("Manual Entry Apartment", "123 Oak St, Austin, TX", 1200.0),
    )
    database_connection.commit()
    return cursor.lastrowid


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, configured=True, vision=False):
        self._configured = configured
        self._vision = vision

    def is_configured(self):
        return self._configured

    @property
    def supports_vision(self):
        return self._vision

    def complete(self, prompt, system=None, feature=None):
        return '{"mock": true}'


# ── Cost estimation ──────────────────────────────────

def test_estimate_all_sources_configured(database_connection, credential_store, sample_listing_id):
    """With all APIs configured + vision LLM + floor plan, all sources are available."""
    credential_store.set_key("realtyapi", "rk-test-key-realtyapi-12345")
    credential_store.set_key("walkscore", "ws-test-key-walkscore-67890")
    credential_store.set_key("google_maps", "gm-test-key-google-maps-abcde")

    # Add a floor plan
    database_connection.execute(
        "INSERT INTO apartment_floor_plans (listing_id, image_url) VALUES (?, ?)",
        (sample_listing_id, "https://example.com/floor-plan-studio-a.jpg"),
    )
    database_connection.commit()

    service = IntelService(database_connection, llm_provider=MockLLMProvider(vision=True))
    estimate = service.estimate_cost(sample_listing_id)

    assert estimate["can_proceed"] is True
    assert len(estimate["available_sources"]) == 7
    assert len(estimate["unavailable_sources"]) == 0

    available_names = [source["name"] for source in estimate["available_sources"]]
    assert "unit_details" in available_names
    assert "verified_scores" in available_names
    assert "distances" in available_names
    assert "floor_plan_analysis" in available_names
    assert "concessions" in available_names
    assert "reviews" in available_names
    assert "policies" in available_names

    # Estimated cost should be sum of all (7 sources)
    assert estimate["estimated_cost"] > 0.05


def test_estimate_no_sources_configured(database_connection, sample_listing_id):
    """With no APIs and no LLM, nothing is available."""
    service = IntelService(database_connection, llm_provider=None)
    estimate = service.estimate_cost(sample_listing_id)

    assert estimate["can_proceed"] is False
    assert len(estimate["available_sources"]) == 0
    assert len(estimate["unavailable_sources"]) == 7


def test_estimate_partial_sources(database_connection, credential_store, sample_listing_id):
    """With only Walk Score configured, only verified_scores is available."""
    credential_store.set_key("walkscore", "ws-test-key-walkscore-12345")

    service = IntelService(database_connection, llm_provider=None)
    estimate = service.estimate_cost(sample_listing_id)

    assert estimate["can_proceed"] is True
    assert len(estimate["available_sources"]) == 1
    assert estimate["available_sources"][0]["name"] == "verified_scores"
    assert estimate["estimated_cost"] == 0.0  # Walk Score is free


def test_estimate_floor_plan_requires_both_vision_and_image(database_connection, credential_store, sample_listing_id):
    """Floor plan analysis requires both vision LLM AND a floor plan image."""
    # Vision LLM but no floor plan
    service = IntelService(database_connection, llm_provider=MockLLMProvider(vision=True))
    estimate = service.estimate_cost(sample_listing_id)

    floor_plan_unavailable = [
        source for source in estimate["unavailable_sources"]
        if source["name"] == "floor_plan_analysis"
    ]
    assert len(floor_plan_unavailable) == 1
    assert "No floor plan" in floor_plan_unavailable[0]["reason"]


def test_estimate_concessions_requires_both_llm_and_url(database_connection, listing_without_url):
    """Concession extraction requires both LLM AND a source URL."""
    service = IntelService(database_connection, llm_provider=MockLLMProvider())
    estimate = service.estimate_cost(listing_without_url)

    concession_unavailable = [
        source for source in estimate["unavailable_sources"]
        if source["name"] == "concessions"
    ]
    assert len(concession_unavailable) == 1
    assert "No listing URL" in concession_unavailable[0]["reason"]


def test_estimate_nonexistent_listing(database_connection):
    """Estimating for a nonexistent listing returns specific error."""
    service = IntelService(database_connection)
    estimate = service.estimate_cost(99999)
    assert estimate.get("error") == "Listing not found"


# ── Budget enforcement ────────────────────────────────

def test_budget_per_listing_cap(database_connection, credential_store, sample_listing_id):
    """Cannot proceed if per-listing cap is reached."""
    credential_store.set_key("walkscore", "ws-test-key-walkscore-12345")

    # Simulate previous Intel spend at the cap
    intel_repo = IntelRepository(database_connection)
    intel_repo.save_intel(sample_listing_id, "floor_plan_analysis", {}, actual_cost=4.99)

    service = IntelService(database_connection, llm_provider=None)
    estimate = service.estimate_cost(sample_listing_id)

    assert estimate["per_listing_remaining"] < 0.02
    assert estimate["already_gathered"] is True
    assert len(estimate["gathered_types"]) == 1


def test_budget_daily_limit_warning(database_connection, credential_store, sample_listing_id):
    """Budget warning appears when daily limit is close."""
    credential_store.set_key("realtyapi", "rk-test-key-realtyapi-12345")

    # Create another listing and spend some budget today
    database_connection.execute(
        "INSERT INTO apartment_listings (title, price) VALUES (?, ?)",
        ("Other Apartment", 1500.0),
    )
    database_connection.commit()
    intel_repo = IntelRepository(database_connection)
    intel_repo.save_intel(2, "unit_details", {}, actual_cost=0.95)

    service = IntelService(database_connection)
    estimate = service.estimate_cost(sample_listing_id)

    assert estimate["daily_spent"] == 0.95
    assert estimate["daily_remaining"] < 0.1


# ── Cached Intel ──────────────────────────────────────

def test_get_cached_intel(database_connection, sample_listing_id):
    """Cached Intel returns all gathered data with total cost."""
    intel_repo = IntelRepository(database_connection)
    intel_repo.save_intel(sample_listing_id, "unit_details", {"units": 20}, actual_cost=0.001)
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72}, actual_cost=0.0)

    service = IntelService(database_connection)
    cached = service.get_cached_intel(sample_listing_id)

    assert cached is not None
    assert cached["listing_id"] == sample_listing_id
    assert "unit_details" in cached["intel"]
    assert "verified_scores" in cached["intel"]
    assert cached["intel"]["unit_details"]["result"]["units"] == 20
    assert abs(cached["total_cost"] - 0.001) < 0.0001


def test_get_cached_intel_empty(database_connection, sample_listing_id):
    """No cached Intel returns None."""
    service = IntelService(database_connection)
    assert service.get_cached_intel(sample_listing_id) is None
