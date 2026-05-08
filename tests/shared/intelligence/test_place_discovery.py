"""Place discovery — tests for adaptive rating filter, full discovery, and coordinate validation.

Covers: adaptive filter (4★→3★→2★→all), target count filling,
sort order (highest rated first), empty results handling,
discover_nearby_places() with mocked API, coordinate validation.
"""

import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from shared.db import migrate
from shared.intelligence.place_discovery import (
    _adaptive_rating_filter,
    discover_nearby_places,
)


SAMPLE_PLACES = [
    {"name": "Five Star Restaurant", "rating": 4.8, "total_ratings": 500},
    {"name": "Good Cafe", "rating": 4.2, "total_ratings": 200},
    {"name": "Decent Diner", "rating": 3.5, "total_ratings": 100},
    {"name": "Average Joint", "rating": 3.0, "total_ratings": 50},
    {"name": "Below Average", "rating": 2.5, "total_ratings": 30},
    {"name": "Poor Place", "rating": 1.8, "total_ratings": 10},
    {"name": "No Rating", "rating": None, "total_ratings": 0},
]


# ── Adaptive rating filter ───────────────────────────

def test_filter_starts_at_4_stars():
    """With enough 4★+ places, only returns those."""
    many_good_places = [
        {"name": f"Place {index}", "rating": 4.0 + index * 0.1, "total_ratings": 100}
        for index in range(25)
    ]
    result = _adaptive_rating_filter(many_good_places, target_count=20)
    assert len(result) == 20
    assert all(place["rating"] >= 4.0 for place in result)


def test_filter_drops_to_3_stars_when_needed():
    """Not enough 4★+ → includes 3★+ places."""
    few_good_places = [
        {"name": "Great", "rating": 4.5, "total_ratings": 100},
        {"name": "Good", "rating": 3.8, "total_ratings": 80},
        {"name": "OK", "rating": 3.2, "total_ratings": 50},
        {"name": "Meh", "rating": 2.5, "total_ratings": 20},
    ]
    result = _adaptive_rating_filter(few_good_places, target_count=3)
    assert len(result) == 3
    # All should be 3★+ since we have exactly 3 at that threshold
    assert all(place["rating"] >= 3.0 for place in result)


def test_filter_drops_to_all_when_few_places():
    """Very few places → take everything including unrated."""
    sparse_places = [
        {"name": "Only Option", "rating": 2.0, "total_ratings": 5},
        {"name": "No Stars", "rating": None, "total_ratings": 0},
    ]
    result = _adaptive_rating_filter(sparse_places, target_count=20)
    assert len(result) == 2  # Take everything available
    assert result[0]["name"] == "Only Option"  # Rated first


def test_filter_sorted_by_rating_then_reviews():
    """Results sorted: highest rating first, then most reviewed."""
    result = _adaptive_rating_filter(SAMPLE_PLACES, target_count=5)
    ratings = [place.get("rating") or 0 for place in result]
    assert ratings == sorted(ratings, reverse=True)


def test_filter_empty_input():
    """Empty places list returns empty."""
    assert _adaptive_rating_filter([], target_count=20) == []


def test_filter_respects_target_count():
    """Never returns more than target_count."""
    many_places = [
        {"name": f"Place {index}", "rating": 3.5, "total_ratings": 50}
        for index in range(100)
    ]
    result = _adaptive_rating_filter(many_places, target_count=20)
    assert len(result) == 20


def test_filter_includes_unrated_when_needed():
    """Unrated places included at the 0★ threshold."""
    only_unrated = [
        {"name": "Mystery Place 1", "rating": None, "total_ratings": 0},
        {"name": "Mystery Place 2", "rating": None, "total_ratings": 0},
    ]
    result = _adaptive_rating_filter(only_unrated, target_count=20)
    assert len(result) == 2


# ── Fixtures ─────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def database_with_google_key(database_connection):
    """Database with a Google Maps API key configured."""
    database_connection.execute(
        "UPDATE api_credentials SET api_key = ? WHERE service_name = ?",
        ("test_google_maps_api_key_abc123", "google_maps"),
    )
    database_connection.commit()
    return database_connection


FAKE_GOOGLE_API_RESPONSE = {
    "status": "OK",
    "results": [
        {
            "place_id": "ChIJ_uchi_austin_tx",
            "name": "Uchi",
            "types": ["restaurant", "food"],
            "geometry": {"location": {"lat": 30.2563, "lng": -97.7528}},
            "rating": 4.7,
            "user_ratings_total": 2847,
            "price_level": 3,
            "vicinity": "801 S Lamar Blvd, Austin, TX",
        },
        {
            "place_id": "ChIJ_heb_austin_tx",
            "name": "H-E-B",
            "types": ["grocery_or_supermarket", "store"],
            "geometry": {"location": {"lat": 30.2590, "lng": -97.7500}},
            "rating": 4.5,
            "user_ratings_total": 1234,
            "price_level": 2,
            "vicinity": "1000 E 41st St, Austin, TX",
        },
    ],
}


def _build_mock_httpx_response(response_data):
    """Build a mock httpx response that returns the given JSON data."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status.return_value = None
    return mock_response


# ── Coordinate validation ────────────────────────────

def test_invalid_latitude_too_high(database_connection):
    """Latitude above 90 returns empty result with no API calls."""
    result = discover_nearby_places(
        latitude=91.0,
        longitude=-97.7,
        connection=database_connection,
    )
    assert result["grid_key"] is None
    assert result["places"] == []
    assert result["from_cache"] is False
    assert result["api_calls_made"] == 0


def test_invalid_latitude_too_low(database_connection):
    """Latitude below -90 returns empty result."""
    result = discover_nearby_places(
        latitude=-91.0,
        longitude=-97.7,
        connection=database_connection,
    )
    assert result["grid_key"] is None
    assert result["places"] == []


def test_invalid_longitude_too_high(database_connection):
    """Longitude above 180 returns empty result."""
    result = discover_nearby_places(
        latitude=30.26,
        longitude=181.0,
        connection=database_connection,
    )
    assert result["grid_key"] is None
    assert result["places"] == []


def test_invalid_longitude_too_low(database_connection):
    """Longitude below -180 returns empty result."""
    result = discover_nearby_places(
        latitude=30.26,
        longitude=-181.0,
        connection=database_connection,
    )
    assert result["grid_key"] is None
    assert result["places"] == []


def test_boundary_coordinates_are_valid(database_with_google_key):
    """Exact boundary values (-90, 90, -180, 180) are accepted as valid."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response({"status": "ZERO_RESULTS", "results": []})
        result = discover_nearby_places(
            latitude=90.0,
            longitude=-180.0,
            connection=database_with_google_key,
        )
        # Valid coordinates — should proceed (grid_key is set, not None)
        assert result["grid_key"] is not None
        assert result["api_calls_made"] > 0


# ── No API key ───────────────────────────────────────

def test_no_api_key_returns_empty(database_connection):
    """Without a Google Maps API key configured, returns empty result."""
    result = discover_nearby_places(
        latitude=30.2672,
        longitude=-97.7431,
        connection=database_connection,
    )
    assert result["grid_key"] is None
    assert result["places"] == []
    assert result["from_cache"] is False
    assert result["api_calls_made"] == 0


# ── Cache hit ────────────────────────────────────────

def test_cache_hit_returns_cached_places(database_with_google_key):
    """When places are cached for a grid, returns them without API calls."""
    from shared.intelligence.place_cache import save_places_to_cache, compute_grid_key

    austin_latitude = 30.2672
    austin_longitude = -97.7431
    grid_key = compute_grid_key(austin_latitude, austin_longitude)

    cached_place = {
        "place_id": "ChIJ_cached_barchi",
        "name": "Barchi",
        "types": ["restaurant"],
        "latitude": 30.2650,
        "longitude": -97.7400,
        "rating": 4.6,
        "total_ratings": 890,
        "price_level": 2,
        "address": "2508 S Lamar Blvd, Austin, TX",
        "customer_reviews": ["Excellent ramen"],
    }
    save_places_to_cache([cached_place], grid_key, database_with_google_key)

    result = discover_nearby_places(
        latitude=austin_latitude,
        longitude=austin_longitude,
        connection=database_with_google_key,
    )
    assert result["from_cache"] is True
    assert result["api_calls_made"] == 0
    assert result["grid_key"] == grid_key
    assert len(result["places"]) == 1
    assert result["places"][0]["name"] == "Barchi"


# ── Full discovery with mocked API ───────────────────

def test_discover_fetches_from_api_and_caches(database_with_google_key):
    """Full discovery: calls API, deduplicates, filters, caches results."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_GOOGLE_API_RESPONSE)

        test_categories = [
            {"type": "restaurant", "label": "Restaurants", "radius": 5000},
        ]
        result = discover_nearby_places(
            latitude=30.2672,
            longitude=-97.7431,
            connection=database_with_google_key,
            categories=test_categories,
        )

        assert result["from_cache"] is False
        assert result["api_calls_made"] == 1
        assert result["grid_key"] is not None
        assert len(result["places"]) == 2

        place_names = [place["name"] for place in result["places"]]
        assert "Uchi" in place_names
        assert "H-E-B" in place_names

        # Verify place data is correctly mapped
        uchi_place = next(place for place in result["places"] if place["name"] == "Uchi")
        assert uchi_place["place_id"] == "ChIJ_uchi_austin_tx"
        assert uchi_place["rating"] == 4.7
        assert uchi_place["total_ratings"] == 2847
        assert uchi_place["address"] == "801 S Lamar Blvd, Austin, TX"
        assert uchi_place["category_label"] == "Restaurants"
        assert uchi_place["latitude"] == 30.2563
        assert uchi_place["longitude"] == -97.7528


def test_discover_deduplicates_across_categories(database_with_google_key):
    """Places appearing in multiple category searches are only included once."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_GOOGLE_API_RESPONSE)

        # Two categories that return the same places
        test_categories = [
            {"type": "restaurant", "label": "Restaurants", "radius": 5000},
            {"type": "cafe", "label": "Cafes", "radius": 3000},
        ]
        result = discover_nearby_places(
            latitude=30.2672,
            longitude=-97.7431,
            connection=database_with_google_key,
            categories=test_categories,
        )

        assert result["api_calls_made"] == 2
        # Should still be 2 unique places, not 4 duplicates
        assert len(result["places"]) == 2


def test_discover_empty_api_response(database_with_google_key):
    """API returning zero results produces empty places list."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response({"status": "ZERO_RESULTS", "results": []})

        test_categories = [
            {"type": "restaurant", "label": "Restaurants", "radius": 5000},
        ]
        result = discover_nearby_places(
            latitude=30.2672,
            longitude=-97.7431,
            connection=database_with_google_key,
            categories=test_categories,
        )

        assert result["places"] == []
        assert result["api_calls_made"] == 1
        assert result["from_cache"] is False


def test_discover_uses_default_categories_when_none_provided(database_with_google_key):
    """Without custom categories, uses all DEFAULT_CATEGORIES (12 types)."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response({"status": "ZERO_RESULTS", "results": []})

        result = discover_nearby_places(
            latitude=30.2672,
            longitude=-97.7431,
            connection=database_with_google_key,
        )

        # DEFAULT_CATEGORIES has 12 entries → 12 API calls
        assert result["api_calls_made"] == 12


def test_discover_places_have_empty_reviews_initially(database_with_google_key):
    """Discovered places have empty customer_reviews (filled in deep-dive step)."""
    with patch("shared.intelligence.place_discovery.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_GOOGLE_API_RESPONSE)

        test_categories = [
            {"type": "restaurant", "label": "Restaurants", "radius": 5000},
        ]
        result = discover_nearby_places(
            latitude=30.2672,
            longitude=-97.7431,
            connection=database_with_google_key,
            categories=test_categories,
        )

        for place in result["places"]:
            assert place["customer_reviews"] == []
