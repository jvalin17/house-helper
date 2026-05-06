"""Intel repository — tests for apartment_intel CRUD.

Covers: save/get/upsert, get_all, type validation, cost tracking,
has_intel, gathered_ids, delete, daily spend calculation.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from agents.apartment.repositories.intel_repo import IntelRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def intel_repo(database_connection):
    return IntelRepository(database_connection)


@pytest.fixture
def sample_listing_id(database_connection):
    """Create a realistic listing and return its ID."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, bedrooms, bathrooms, sqft, source, source_url, amenities, latitude, longitude)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "The Domain at Midtown Park",
            "11511 Domain Dr, Austin, TX 78758",
            1832.0, 1, 1, 780, "realtyapi",
            "https://www.zillow.com/homedetails/98765_zpid/",
            json.dumps(["Pool", "Gym", "Dog Park"]),
            30.4024, -97.7253,
        ),
    )
    database_connection.commit()
    return cursor.lastrowid


# ── Save and retrieve ─────────────────────────────

def test_save_and_get_unit_details(intel_repo, sample_listing_id):
    """Save unit details result and retrieve it by type."""
    unit_data = {
        "floor_plans": [
            {"name": "Studio A", "beds": 0, "baths": 1, "price_range": "$1,445 - $1,595", "available_units": 8},
            {"name": "1BR B", "beds": 1, "baths": 1, "price_range": "$1,832 - $2,100", "available_units": 12},
        ],
        "total_available": 20,
    }
    intel_repo.save_intel(
        listing_id=sample_listing_id,
        intel_type="unit_details",
        result=unit_data,
        source_api="realtyapi",
        estimated_cost=0.001,
        actual_cost=0.001,
    )

    retrieved = intel_repo.get_intel(sample_listing_id, "unit_details")
    assert retrieved is not None
    assert retrieved["intel_type"] == "unit_details"
    assert retrieved["source_api"] == "realtyapi"
    assert retrieved["actual_cost"] == 0.001
    assert retrieved["result"]["total_available"] == 20
    assert len(retrieved["result"]["floor_plans"]) == 2
    assert retrieved["result"]["floor_plans"][0]["name"] == "Studio A"


def test_get_nonexistent_intel_returns_none(intel_repo, sample_listing_id):
    """Getting Intel that doesn't exist returns None."""
    assert intel_repo.get_intel(sample_listing_id, "unit_details") is None


def test_upsert_overwrites_previous_result(intel_repo, sample_listing_id):
    """Re-saving the same intel_type overwrites the previous result."""
    first_result = {"walk_score": 65, "transit_score": 30}
    intel_repo.save_intel(sample_listing_id, "verified_scores", first_result, actual_cost=0.0)

    updated_result = {"walk_score": 72, "transit_score": 45, "bike_score": 61}
    intel_repo.save_intel(sample_listing_id, "verified_scores", updated_result, actual_cost=0.0)

    retrieved = intel_repo.get_intel(sample_listing_id, "verified_scores")
    assert retrieved["result"]["walk_score"] == 72
    assert retrieved["result"]["bike_score"] == 61


def test_invalid_intel_type_raises_error(intel_repo, sample_listing_id):
    """Saving with an invalid intel_type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid intel_type 'weather_forecast'"):
        intel_repo.save_intel(sample_listing_id, "weather_forecast", {"temp": 75})


# ── Get all Intel for a listing ─────────────────────

def test_get_all_intel_multiple_types(intel_repo, sample_listing_id):
    """Get all Intel results for a listing, keyed by type."""
    intel_repo.save_intel(sample_listing_id, "unit_details", {"units": 20}, actual_cost=0.001)
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72}, actual_cost=0.0)
    intel_repo.save_intel(sample_listing_id, "concessions", {"discount": "2 months free"}, actual_cost=0.01)

    all_intel = intel_repo.get_all_intel(sample_listing_id)
    assert len(all_intel) == 3
    assert "unit_details" in all_intel
    assert "verified_scores" in all_intel
    assert "concessions" in all_intel
    assert all_intel["unit_details"]["result"]["units"] == 20
    assert all_intel["concessions"]["result"]["discount"] == "2 months free"


def test_get_all_intel_empty_listing(intel_repo, sample_listing_id):
    """Get all Intel for a listing with no Intel data returns empty dict."""
    assert intel_repo.get_all_intel(sample_listing_id) == {}


# ── Cost tracking ──────────────────────────────────

def test_total_cost_for_listing(intel_repo, sample_listing_id):
    """Sum of actual_cost across all Intel types for a listing."""
    intel_repo.save_intel(sample_listing_id, "unit_details", {}, actual_cost=0.001)
    intel_repo.save_intel(sample_listing_id, "verified_scores", {}, actual_cost=0.0)
    intel_repo.save_intel(sample_listing_id, "floor_plan_analysis", {}, actual_cost=0.032)
    intel_repo.save_intel(sample_listing_id, "concessions", {}, actual_cost=0.011)

    total = intel_repo.get_total_cost_for_listing(sample_listing_id)
    assert abs(total - 0.044) < 0.001


def test_total_cost_no_intel(intel_repo, sample_listing_id):
    """Total cost for a listing with no Intel is 0."""
    assert intel_repo.get_total_cost_for_listing(sample_listing_id) == 0.0


def test_daily_spend(intel_repo, sample_listing_id):
    """Daily spend sums all Intel costs from today."""
    intel_repo.save_intel(sample_listing_id, "unit_details", {}, actual_cost=0.001)
    intel_repo.save_intel(sample_listing_id, "concessions", {}, actual_cost=0.015)

    daily = intel_repo.get_daily_spend()
    assert abs(daily - 0.016) < 0.001


# ── has_intel and gathered_ids ─────────────────────

def test_has_intel_true(intel_repo, sample_listing_id):
    """has_intel returns True when Intel data exists."""
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72})
    assert intel_repo.has_intel(sample_listing_id) is True


def test_has_intel_false(intel_repo, sample_listing_id):
    """has_intel returns False when no Intel data exists."""
    assert intel_repo.has_intel(sample_listing_id) is False


def test_get_intel_gathered_ids(intel_repo, database_connection):
    """Returns distinct listing IDs that have any Intel data."""
    # Create two listings
    for listing_title in ["Camden North End", "Windsor Ridge"]:
        database_connection.execute(
            "INSERT INTO apartment_listings (title, address, price) VALUES (?, ?, ?)",
            (listing_title, "Austin, TX", 1500.0),
        )
    database_connection.commit()

    intel_repo.save_intel(1, "unit_details", {"units": 10})
    intel_repo.save_intel(1, "verified_scores", {"walk_score": 80})
    intel_repo.save_intel(2, "concessions", {"discount": "1 month free"})

    gathered_ids = intel_repo.get_intel_gathered_ids()
    assert set(gathered_ids) == {1, 2}


# ── Delete ─────────────────────────────────────────

def test_delete_single_type(intel_repo, sample_listing_id):
    """Delete a specific Intel type, keep others."""
    intel_repo.save_intel(sample_listing_id, "unit_details", {"units": 20})
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72})

    deleted_count = intel_repo.delete_intel(sample_listing_id, "unit_details")
    assert deleted_count == 1
    assert intel_repo.get_intel(sample_listing_id, "unit_details") is None
    assert intel_repo.get_intel(sample_listing_id, "verified_scores") is not None


def test_delete_all_for_listing(intel_repo, sample_listing_id):
    """Delete all Intel data for a listing."""
    intel_repo.save_intel(sample_listing_id, "unit_details", {"units": 20})
    intel_repo.save_intel(sample_listing_id, "verified_scores", {"walk_score": 72})
    intel_repo.save_intel(sample_listing_id, "concessions", {"discount": "2mo free"})

    deleted_count = intel_repo.delete_intel(sample_listing_id)
    assert deleted_count == 3
    assert intel_repo.get_all_intel(sample_listing_id) == {}
