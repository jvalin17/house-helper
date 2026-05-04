"""Neighborhood service — tests for Walk Score + Google Distance Matrix.

Uses mocked HTTP responses to avoid real API calls.
Tests cover: API key handling, response parsing, caching, error handling.
"""

import json
import sqlite3

import pytest
import httpx

from shared.db import migrate
from agents.apartment.services.neighborhood_service import (
    get_walk_scores,
    get_distance_to_airport,
    get_commute_time,
    fetch_and_cache_neighborhood,
    get_cached_neighborhood,
)


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def database_with_keys(database_connection):
    """DB with both Walk Score and Google Maps API keys."""
    database_connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
        [json.dumps({"walkscore": "ws_test_key", "google_maps": "gm_test_key"})],
    )
    database_connection.commit()
    return database_connection


@pytest.fixture
def sample_listing_id(database_connection):
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, address, price, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX, 78759", 1445, 30.4186, -97.7404),
    )
    database_connection.commit()
    return cursor.lastrowid


MOCK_WALK_SCORE_RESPONSE = {
    "status": 1,
    "walkscore": 72,
    "description": "Very Walkable",
    "transit": {"score": 45, "description": "Some Transit"},
    "bike": {"score": 61, "description": "Bikeable"},
}

MOCK_DISTANCE_MATRIX_RESPONSE = {
    "status": "OK",
    "rows": [{
        "elements": [{
            "status": "OK",
            "distance": {"value": 32186, "text": "20 mi"},
            "duration": {"value": 1680, "text": "28 mins"},
        }],
    }],
}


# ── Walk Score ────────────────────────────────────────────

class TestWalkScore:
    def test_returns_scores_with_mocked_response(self, database_with_keys, monkeypatch):
        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200, json=MOCK_WALK_SCORE_RESPONSE,
                request=httpx.Request("GET", args[0] if args else ""),
            )
        monkeypatch.setattr(httpx, "get", mock_get)

        result = get_walk_scores(30.4186, -97.7404, "10801 N Mopac Expy, Austin, TX", database_with_keys)

        assert result is not None
        assert result["walk_score"] == 72
        assert result["walk_description"] == "Very Walkable"
        assert result["transit_score"] == 45
        assert result["bike_score"] == 61

    def test_returns_none_when_no_api_key(self, database_connection):
        result = get_walk_scores(30.4186, -97.7404, "Austin, TX", database_connection)
        assert result is None

    def test_handles_api_error_gracefully(self, database_with_keys, monkeypatch):
        def mock_error(*args, **kwargs):
            response = httpx.Response(status_code=403, text="Forbidden",
                                     request=httpx.Request("GET", ""))
            raise httpx.HTTPStatusError("403", request=response.request, response=response)
        monkeypatch.setattr(httpx, "get", mock_error)

        result = get_walk_scores(30.4186, -97.7404, "Austin, TX", database_with_keys)
        assert result is None


# ── Google Distance Matrix ────────────────────────────────

class TestDistanceToAirport:
    def test_returns_airport_distance_with_mocked_response(self, database_with_keys, monkeypatch):
        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200, json=MOCK_DISTANCE_MATRIX_RESPONSE,
                request=httpx.Request("GET", args[0] if args else ""),
            )
        monkeypatch.setattr(httpx, "get", mock_get)

        result = get_distance_to_airport(30.4186, -97.7404, database_with_keys)

        assert result is not None
        assert result["airport_distance_km"] == 32.2
        assert result["airport_drive_minutes"] == 28
        assert result["airport_distance_text"] == "20 mi"

    def test_returns_none_when_no_google_key(self, database_connection):
        result = get_distance_to_airport(30.4186, -97.7404, database_connection)
        assert result is None

    def test_handles_api_not_ok_status(self, database_with_keys, monkeypatch):
        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200, json={"status": "REQUEST_DENIED"},
                request=httpx.Request("GET", ""),
            )
        monkeypatch.setattr(httpx, "get", mock_get)

        result = get_distance_to_airport(30.4186, -97.7404, database_with_keys)
        assert result is None


class TestCommuteTime:
    def test_returns_commute_with_mocked_response(self, database_with_keys, monkeypatch):
        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200, json=MOCK_DISTANCE_MATRIX_RESPONSE,
                request=httpx.Request("GET", args[0] if args else ""),
            )
        monkeypatch.setattr(httpx, "get", mock_get)

        result = get_commute_time(30.4186, -97.7404, "Apple Park, Cupertino, CA", database_with_keys)

        assert result is not None
        assert result["commute_duration_minutes"] == 28
        assert result["commute_mode"] == "transit"
        assert result["commute_destination"] == "Apple Park, Cupertino, CA"

    def test_returns_none_when_no_destination(self, database_with_keys):
        result = get_commute_time(30.4186, -97.7404, "", database_with_keys)
        assert result is None


# ── Fetch and cache orchestration ─────────────────────────

class TestFetchAndCache:
    def test_caches_results_in_neighborhood_table(self, database_with_keys, sample_listing_id, monkeypatch):
        call_count = {"walk": 0, "distance": 0}

        def mock_get(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "walkscore" in url:
                call_count["walk"] += 1
                return httpx.Response(status_code=200, json=MOCK_WALK_SCORE_RESPONSE,
                                     request=httpx.Request("GET", url))
            else:
                call_count["distance"] += 1
                return httpx.Response(status_code=200, json=MOCK_DISTANCE_MATRIX_RESPONSE,
                                     request=httpx.Request("GET", url))
        monkeypatch.setattr(httpx, "get", mock_get)

        result = fetch_and_cache_neighborhood(sample_listing_id, database_with_keys)

        assert result["walk_scores"]["walk_score"] == 72
        assert result["airport_distance"]["airport_distance_km"] == 32.2
        assert "Walk Score" in result["sources_used"]

        # Verify cached
        cached = get_cached_neighborhood(sample_listing_id, database_with_keys)
        assert cached is not None
        assert cached["listing_id"] == sample_listing_id

    def test_returns_error_for_nonexistent_listing(self, database_with_keys):
        result = fetch_and_cache_neighborhood(99999, database_with_keys)
        assert "error" in result

    def test_returns_error_for_listing_without_coordinates(self, database_with_keys):
        cursor = database_with_keys.execute(
            "INSERT INTO apartment_listings (title, price) VALUES (?, ?)",
            ("No Coords Apartment", 1200),
        )
        database_with_keys.commit()
        listing_id = cursor.lastrowid

        result = fetch_and_cache_neighborhood(listing_id, database_with_keys)
        assert "error" in result
        assert "coordinates" in result["error"].lower()


# ── Integration: sources endpoint ─────────────────────────

class TestSourcesIncludeNeighborhoodAPIs:
    def test_sources_list_includes_walkscore_and_google(self, database_connection):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from agents.apartment.routes import create_router

        application = FastAPI()
        application.include_router(create_router(database_connection))
        test_client = TestClient(application)

        response = test_client.get("/api/apartments/sources")
        source_ids = [source["id"] for source in response.json()]
        assert "walkscore" in source_ids
        assert "google_maps" in source_ids
