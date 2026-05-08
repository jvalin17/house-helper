"""Place deep-dive — tests for review fetching, selection, and enrichment.

Covers: newest 20% selection, min/max bounds, cache hit skips API,
enrichment with real review texts, enrich_places_with_reviews() full flow.
"""

import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from shared.db import migrate
from shared.intelligence.place_deep_dive import (
    _select_newest_reviews,
    enrich_places_with_reviews,
)
from shared.intelligence.place_cache import save_places_to_cache, update_place_reviews


# ── Review selection (newest 20%) ────────────────────

def _make_reviews(count: int) -> list[dict]:
    """Generate mock reviews with timestamps."""
    return [
        {"text": f"Review {index}", "time": 1700000000 + index * 86400, "rating": 4}
        for index in range(count)
    ]


def test_select_from_50_reviews_takes_10():
    """50 reviews × 20% = 10, but capped at max 5."""
    reviews = _make_reviews(50)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 5  # Max cap


def test_select_from_10_reviews_takes_2():
    """10 reviews × 20% = 2."""
    reviews = _make_reviews(10)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 2


def test_select_from_3_reviews_takes_1():
    """3 reviews × 20% = 0.6, rounded up to 1 (minimum)."""
    reviews = _make_reviews(3)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1


def test_select_from_1_review_takes_1():
    """1 review × 20% = 0.2, rounded up to 1 (minimum)."""
    reviews = _make_reviews(1)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1


def test_select_from_empty_returns_empty():
    assert _select_newest_reviews([]) == []


def test_select_returns_newest_first():
    """Selected reviews are the most recent ones."""
    reviews = _make_reviews(20)
    selected = _select_newest_reviews(reviews)  # 20 × 20% = 4
    assert len(selected) == 4

    # Newest should have highest timestamps
    selected_times = [review["time"] for review in selected]
    assert selected_times == sorted(selected_times, reverse=True)

    # The newest review in the selection should be the overall newest
    all_times = sorted([review["time"] for review in reviews], reverse=True)
    assert selected_times[0] == all_times[0]


def test_select_from_25_reviews_takes_5():
    """25 reviews × 20% = 5, exactly at max cap."""
    reviews = _make_reviews(25)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 5


def test_select_preserves_review_text():
    """Selected reviews keep their text content."""
    reviews = [
        {"text": "Amazing indo-chinese food here", "time": 1700086400, "rating": 5},
        {"text": "Best dosa in Austin", "time": 1700000000, "rating": 4},
    ]
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1
    assert "indo-chinese" in selected[0]["text"]  # Newest one selected


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


SAMPLE_UCHI_PLACE = {
    "place_id": "ChIJ_uchi_austin_tx",
    "name": "Uchi",
    "types": ["restaurant", "food"],
    "latitude": 30.2563,
    "longitude": -97.7528,
    "rating": 4.7,
    "total_ratings": 2847,
    "price_level": 3,
    "address": "801 S Lamar Blvd, Austin, TX",
    "customer_reviews": [],
}

SAMPLE_HEB_PLACE = {
    "place_id": "ChIJ_heb_austin_tx",
    "name": "H-E-B",
    "types": ["grocery_or_supermarket", "store"],
    "latitude": 30.2590,
    "longitude": -97.7500,
    "rating": 4.5,
    "total_ratings": 1234,
    "price_level": 2,
    "address": "1000 E 41st St, Austin, TX",
    "customer_reviews": [],
}

FAKE_PLACE_DETAILS_RESPONSE = {
    "status": "OK",
    "result": {
        "reviews": [
            {"text": "Best omakase in Austin, the wagyu was incredible", "time": 1700500000, "rating": 5},
            {"text": "Innovative Japanese fusion, try the hama chili", "time": 1700400000, "rating": 5},
            {"text": "Worth the splurge, every dish was art", "time": 1700300000, "rating": 4},
            {"text": "A bit overpriced but the fish was fresh", "time": 1700200000, "rating": 4},
            {"text": "Solid sushi but service was slow", "time": 1700100000, "rating": 3},
        ],
    },
}


def _build_mock_httpx_response(response_data):
    """Build a mock httpx response that returns the given JSON data."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status.return_value = None
    return mock_response


# ── enrich_places_with_reviews ───────────────────────

def test_enrich_no_api_key_returns_places_unchanged(database_connection):
    """Without API key, returns places as-is without fetching reviews."""
    places = [SAMPLE_UCHI_PLACE.copy()]
    result = enrich_places_with_reviews(places, database_connection)
    assert len(result) == 1
    assert result[0]["name"] == "Uchi"
    assert result[0]["customer_reviews"] == []


def test_enrich_fetches_reviews_from_api(database_with_google_key):
    """With API key, fetches reviews and populates customer_reviews."""
    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_PLACE_DETAILS_RESPONSE)

        places = [SAMPLE_UCHI_PLACE.copy()]
        result = enrich_places_with_reviews(places, database_with_google_key)

        assert len(result) == 1
        assert result[0]["name"] == "Uchi"
        # 5 reviews × 20% = 1, so 1 review selected
        assert len(result[0]["customer_reviews"]) == 1
        assert "omakase" in result[0]["customer_reviews"][0]


def test_enrich_uses_cached_reviews(database_with_google_key):
    """When reviews are already cached, uses them without API calls."""
    # Pre-populate cache with reviews
    cached_place = {**SAMPLE_UCHI_PLACE, "customer_reviews": ["Cached review: amazing wagyu"]}
    save_places_to_cache([cached_place], "grid_30.3_-97.8", database_with_google_key)

    places = [SAMPLE_UCHI_PLACE.copy()]
    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        result = enrich_places_with_reviews(places, database_with_google_key)

        # Should NOT call the API — reviews are cached
        mock_get.assert_not_called()
        assert len(result[0]["customer_reviews"]) == 1
        assert "Cached review" in result[0]["customer_reviews"][0]


def test_enrich_respects_max_detail_calls(database_with_google_key):
    """Stops calling API after max_detail_calls is reached."""
    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_PLACE_DETAILS_RESPONSE)

        places = [
            {**SAMPLE_UCHI_PLACE, "place_id": f"place_{index}"}
            for index in range(5)
        ]
        result = enrich_places_with_reviews(
            places, database_with_google_key, max_detail_calls=2,
        )

        assert len(result) == 5
        assert mock_get.call_count == 2
        # First 2 places get reviews, remaining 3 don't
        enriched_count = sum(1 for place in result if place["customer_reviews"])
        assert enriched_count == 2


def test_enrich_handles_empty_places_list(database_with_google_key):
    """Empty input returns empty output."""
    result = enrich_places_with_reviews([], database_with_google_key)
    assert result == []


def test_enrich_skips_place_without_place_id(database_with_google_key):
    """Places missing place_id are included but not enriched."""
    place_without_id = {"name": "Mystery Spot", "rating": 3.5, "customer_reviews": []}
    result = enrich_places_with_reviews([place_without_id], database_with_google_key)
    assert len(result) == 1
    assert result[0]["name"] == "Mystery Spot"


def test_enrich_handles_api_returning_no_reviews(database_with_google_key):
    """API returning no reviews sets customer_reviews to empty list."""
    empty_reviews_response = {"status": "OK", "result": {"reviews": []}}
    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(empty_reviews_response)

        places = [SAMPLE_HEB_PLACE.copy()]
        result = enrich_places_with_reviews(places, database_with_google_key)

        assert len(result) == 1
        assert result[0]["customer_reviews"] == []


def test_enrich_caches_fetched_reviews(database_with_google_key):
    """After fetching reviews from API, they are cached in the database."""
    # First, save the place to cache (without reviews)
    save_places_to_cache(
        [SAMPLE_UCHI_PLACE], "grid_30.3_-97.8", database_with_google_key,
    )

    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_PLACE_DETAILS_RESPONSE)

        places = [SAMPLE_UCHI_PLACE.copy()]
        enrich_places_with_reviews(places, database_with_google_key)

    # Now fetch again — should use cache, not API
    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get_second:
        places_second = [SAMPLE_UCHI_PLACE.copy()]
        result = enrich_places_with_reviews(places_second, database_with_google_key)

        mock_get_second.assert_not_called()
        assert len(result[0]["customer_reviews"]) == 1


def test_enrich_multiple_places_mixed_cache(database_with_google_key):
    """Mix of cached and uncached places: cached skips API, uncached calls API."""
    # Cache Uchi with reviews
    cached_uchi = {**SAMPLE_UCHI_PLACE, "customer_reviews": ["Cached: incredible fish"]}
    save_places_to_cache([cached_uchi], "grid_30.3_-97.8", database_with_google_key)

    with patch("shared.intelligence.place_deep_dive.httpx.get") as mock_get:
        mock_get.return_value = _build_mock_httpx_response(FAKE_PLACE_DETAILS_RESPONSE)

        places = [SAMPLE_UCHI_PLACE.copy(), SAMPLE_HEB_PLACE.copy()]
        result = enrich_places_with_reviews(places, database_with_google_key)

        # Only H-E-B should trigger an API call
        assert mock_get.call_count == 1
        assert len(result) == 2
        assert "Cached: incredible fish" in result[0]["customer_reviews"][0]
        assert len(result[1]["customer_reviews"]) == 1  # From API
