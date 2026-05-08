"""Place cache — tests for grid-based geographic caching.

Covers: grid key computation, save/retrieve places, encrypted reviews,
cache hit/miss, review update, place_id lookup.
"""

import sqlite3

import pytest

from shared.db import migrate
from shared.intelligence.place_cache import (
    compute_grid_key,
    get_cached_places_for_grid,
    save_places_to_cache,
    get_cached_place_by_id,
    has_reviews_cached,
    update_place_reviews,
)


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


SAMPLE_PLACE = {
    "place_id": "ChIJ_uchi_austin",
    "name": "Uchi",
    "types": ["restaurant", "food"],
    "latitude": 30.2563,
    "longitude": -97.7528,
    "rating": 4.7,
    "total_ratings": 2847,
    "price_level": 3,
    "address": "801 S Lamar Blvd, Austin, TX",
    "customer_reviews": [
        "Best omakase in Austin, worth the wait",
        "Innovative Japanese fusion, try the hama chili",
    ],
}


# ── Grid key computation ─────────────────────────────

def test_grid_key_rounds_coordinates():
    assert compute_grid_key(30.418, -97.740) == "grid_30.4_-97.7"

def test_grid_key_different_cells():
    assert compute_grid_key(30.51, -97.3) == "grid_30.5_-97.3"
    assert compute_grid_key(30.49, -97.3) == "grid_30.5_-97.3"  # rounds up

def test_grid_key_negative_coordinates():
    assert compute_grid_key(-33.8688, 151.2093) == "grid_-33.9_151.2"


# ── Save and retrieve ────────────────────────────────

def test_save_and_retrieve_places(database_connection):
    grid_key = "grid_30.4_-97.7"
    save_places_to_cache([SAMPLE_PLACE], grid_key, database_connection)

    cached = get_cached_places_for_grid(grid_key, database_connection)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["name"] == "Uchi"
    assert cached[0]["rating"] == 4.7
    assert cached[0]["total_ratings"] == 2847
    assert cached[0]["from_cache"] is True


def test_reviews_encrypted_in_db(database_connection):
    grid_key = "grid_30.4_-97.7"
    save_places_to_cache([SAMPLE_PLACE], grid_key, database_connection)

    # Raw DB has encrypted blob, not readable text
    raw_row = database_connection.execute(
        "SELECT encrypted_reviews FROM place_cache WHERE place_id = ?",
        (SAMPLE_PLACE["place_id"],),
    ).fetchone()
    assert raw_row["encrypted_reviews"] is not None
    assert b"omakase" not in raw_row["encrypted_reviews"]

    # But decrypted via cache gives real reviews
    cached = get_cached_places_for_grid(grid_key, database_connection)
    assert "Best omakase" in cached[0]["customer_reviews"][0]


def test_cache_miss_returns_none(database_connection):
    assert get_cached_places_for_grid("grid_99.9_99.9", database_connection) is None


def test_multiple_places_same_grid(database_connection):
    grid_key = "grid_30.4_-97.7"
    places = [
        {**SAMPLE_PLACE, "place_id": "place_1", "name": "Restaurant A"},
        {**SAMPLE_PLACE, "place_id": "place_2", "name": "Restaurant B"},
        {**SAMPLE_PLACE, "place_id": "place_3", "name": "Grocery C"},
    ]
    save_places_to_cache(places, grid_key, database_connection)

    cached = get_cached_places_for_grid(grid_key, database_connection)
    assert len(cached) == 3
    names = {place["name"] for place in cached}
    assert names == {"Restaurant A", "Restaurant B", "Grocery C"}


# ── Place ID lookup ──────────────────────────────────

def test_get_place_by_id(database_connection):
    save_places_to_cache([SAMPLE_PLACE], "grid_30.4_-97.7", database_connection)

    place = get_cached_place_by_id(SAMPLE_PLACE["place_id"], database_connection)
    assert place is not None
    assert place["name"] == "Uchi"
    assert len(place["customer_reviews"]) == 2


def test_get_nonexistent_place_returns_none(database_connection):
    assert get_cached_place_by_id("nonexistent_id", database_connection) is None


# ── Review caching ───────────────────────────────────

def test_has_reviews_cached(database_connection):
    save_places_to_cache([SAMPLE_PLACE], "grid_30.4_-97.7", database_connection)
    assert has_reviews_cached(SAMPLE_PLACE["place_id"], database_connection) is True


def test_has_reviews_cached_false_when_no_reviews(database_connection):
    no_review_place = {**SAMPLE_PLACE, "place_id": "no_reviews_place", "customer_reviews": []}
    save_places_to_cache([no_review_place], "grid_30.4_-97.7", database_connection)
    assert has_reviews_cached("no_reviews_place", database_connection) is False


def test_update_reviews(database_connection):
    no_review_place = {**SAMPLE_PLACE, "place_id": "update_test", "customer_reviews": []}
    save_places_to_cache([no_review_place], "grid_30.4_-97.7", database_connection)

    assert has_reviews_cached("update_test", database_connection) is False

    update_place_reviews("update_test", ["Great food!", "Loved the ambiance"], database_connection)

    assert has_reviews_cached("update_test", database_connection) is True
    place = get_cached_place_by_id("update_test", database_connection)
    assert len(place["customer_reviews"]) == 2
    assert "Great food!" in place["customer_reviews"]
