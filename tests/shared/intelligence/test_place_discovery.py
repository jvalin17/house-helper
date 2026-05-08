"""Place discovery — tests for adaptive rating filter and caching.

Covers: adaptive filter (4★→3★→2★→all), target count filling,
sort order (highest rated first), empty results handling.
"""

import pytest

from shared.intelligence.place_discovery import _adaptive_rating_filter


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
