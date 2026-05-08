"""Distance calculator — tests for haversine distance and radius bucketing.

Covers: known distance calculations, radius bucket assignment,
places sorted by distance within buckets, edge cases.
"""

import pytest

from shared.intelligence.distance_calculator import (
    haversine_distance_miles,
    add_distances_to_places,
    group_places_by_radius,
    _get_radius_bucket,
)


# ── Haversine distance ───────────────────────────────

def test_same_point_is_zero():
    assert haversine_distance_miles(30.2672, -97.7431, 30.2672, -97.7431) == 0.0


def test_austin_to_round_rock():
    """Austin downtown to Round Rock is roughly 17-20 miles."""
    distance = haversine_distance_miles(30.2672, -97.7431, 30.5083, -97.6789)
    assert 15 < distance < 25


def test_short_distance_quarter_mile():
    """Two points ~0.25 miles apart."""
    # Roughly 0.004 degrees latitude = 0.27 miles
    distance = haversine_distance_miles(30.2672, -97.7431, 30.2712, -97.7431)
    assert 0.2 < distance < 0.4


def test_cross_equator():
    """Distance works across equator."""
    distance = haversine_distance_miles(1.0, 0.0, -1.0, 0.0)
    assert distance > 100  # ~138 miles


# ── Radius buckets ───────────────────────────────────

def test_bucket_walking_distance():
    assert "Walking distance" in _get_radius_bucket(0.3)


def test_bucket_short_walk():
    assert "Short walk" in _get_radius_bucket(0.8)


def test_bucket_quick_drive():
    assert "Quick drive" in _get_radius_bucket(1.5)


def test_bucket_far_away():
    assert "Far away" in _get_radius_bucket(15.0)


# ── Add distances to places ──────────────────────────

def test_add_distances():
    """Each place gets distance_miles and radius_bucket added."""
    listing_lat, listing_lng = 30.2672, -97.7431
    places = [
        {"name": "Nearby Cafe", "latitude": 30.2680, "longitude": -97.7440},
        {"name": "Far Grocery", "latitude": 30.3000, "longitude": -97.7000},
    ]

    result = add_distances_to_places(places, listing_lat, listing_lng)

    assert result[0]["distance_miles"] is not None
    assert result[0]["distance_miles"] < 0.5  # Very close
    assert result[0]["radius_bucket"] is not None

    assert result[1]["distance_miles"] is not None
    assert result[1]["distance_miles"] > 2.0  # Further away


def test_add_distances_missing_coordinates():
    """Places without lat/lng get None for distance."""
    places = [{"name": "No Location", "latitude": None, "longitude": None}]
    result = add_distances_to_places(places, 30.0, -97.0)
    assert result[0]["distance_miles"] is None
    assert result[0]["radius_bucket"] is None


# ── Group by radius ──────────────────────────────────

def test_group_by_radius():
    """Places sorted into correct radius buckets."""
    places = [
        {"name": "A", "distance_miles": 0.3},
        {"name": "B", "distance_miles": 0.8},
        {"name": "C", "distance_miles": 1.5},
        {"name": "D", "distance_miles": 4.0},
    ]

    grouped = group_places_by_radius(places)

    assert "0.5mi" in grouped
    assert grouped["0.5mi"][0]["name"] == "A"
    assert "1.0mi" in grouped
    assert grouped["1.0mi"][0]["name"] == "B"


def test_group_empty_places():
    assert group_places_by_radius([]) == {}
