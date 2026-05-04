"""NestScout routes — integration tests for apartment agent endpoints.

Covers:
- Health endpoint returns agent name
- Create listing via POST returns ID
- Get listing by ID returns correct data
- List listings returns all
- Save/unsave shortlist
- Delete listing
- Search failover (Strategy pattern — provider-level mocking)
- Jobsmith endpoints still work (no interference)
"""

import sqlite3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.db import migrate
from agents.apartment.routes import create_router as create_apartment_router
from agents.job.routes import create_router as create_job_router


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def test_client(database_connection):
    application = FastAPI()
    application.include_router(create_apartment_router(database_connection))
    application.include_router(create_job_router(database_connection))
    return TestClient(application)


class TestApartmentHealth:
    def test_health_returns_nestscout(self, test_client):
        response = test_client.get("/api/apartments/health")
        assert response.status_code == 200
        assert response.json()["agent"] == "nestscout"
        assert response.json()["status"] == "ok"


class TestApartmentCRUD:
    def test_create_listing(self, test_client):
        response = test_client.post("/api/apartments/listings", json={
            "title": "Modern 2BR in Uptown",
            "address": "456 Oak Ave, Dallas, TX 75201",
            "price": 1850,
            "bedrooms": 2,
        })
        assert response.status_code == 200
        assert response.json()["id"] is not None
        assert response.json()["title"] == "Modern 2BR in Uptown"

    def test_get_listing(self, test_client):
        create_response = test_client.post("/api/apartments/listings", json={
            "title": "Cozy Studio",
            "price": 1200,
        })
        listing_id = create_response.json()["id"]

        get_response = test_client.get(f"/api/apartments/listings/{listing_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Cozy Studio"
        assert get_response.json()["price"] == 1200

    def test_list_listings(self, test_client):
        test_client.post("/api/apartments/listings", json={"title": "Apt A", "price": 1500})
        test_client.post("/api/apartments/listings", json={"title": "Apt B", "price": 1800})

        response = test_client.get("/api/apartments/listings")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_save_and_unsave_shortlist(self, test_client):
        create_response = test_client.post("/api/apartments/listings", json={"title": "Maybe", "price": 1600})
        listing_id = create_response.json()["id"]

        test_client.post(f"/api/apartments/listings/{listing_id}/save")
        saved = test_client.get("/api/apartments/listings?saved_only=true")
        assert len(saved.json()) == 1

        test_client.post(f"/api/apartments/listings/{listing_id}/unsave")
        saved_after = test_client.get("/api/apartments/listings?saved_only=true")
        assert len(saved_after.json()) == 0

    def test_delete_listing(self, test_client):
        create_response = test_client.post("/api/apartments/listings", json={"title": "Temp", "price": 1000})
        listing_id = create_response.json()["id"]

        delete_response = test_client.delete(f"/api/apartments/listings/{listing_id}")
        assert delete_response.status_code == 200

        get_response = test_client.get(f"/api/apartments/listings/{listing_id}")
        assert get_response.status_code == 404


class TestSearchFailover:
    """Search uses Strategy pattern — mock at provider registry level."""

    def _make_listing(self, title, source):
        return {
            "title": title, "address": f"123 Test St, Austin, TX",
            "price": 1500, "bedrooms": 1, "bathrooms": 1, "sqft": 700,
            "source": source, "source_url": "", "amenities": [], "images": [],
            "latitude": 30.27, "longitude": -97.74, "parsed_data": {},
        }

    def test_search_continues_when_first_provider_fails(self, test_client, monkeypatch):
        from agents.apartment.services import provider_registry

        class FailingProvider:
            source_name = "BrokenSource"
            def is_configured(self): return True
            def search(self, criteria): raise RuntimeError("API timeout")

        class WorkingProvider:
            source_name = "GoodSource"
            def is_configured(self): return True
            def search(self_inner, criteria): return [self._make_listing("Austin Apartment", "test")]

        monkeypatch.setattr(provider_registry, "get_all_providers", lambda conn: [FailingProvider(), WorkingProvider()])

        response = test_client.post("/api/apartments/search", json={"city": "Austin, TX"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "GoodSource" in data["sources"]
        assert "BrokenSource" in data.get("sources_failed", [])

    def test_search_continues_when_second_provider_fails(self, test_client, monkeypatch):
        from agents.apartment.services import provider_registry

        class WorkingProvider:
            source_name = "GoodSource"
            def is_configured(self): return True
            def search(self_inner, criteria): return [self._make_listing("Dallas Loft", "test")]

        class FailingProvider:
            source_name = "BrokenSource"
            def is_configured(self): return True
            def search(self, criteria): raise RuntimeError("API down")

        monkeypatch.setattr(provider_registry, "get_all_providers", lambda conn: [WorkingProvider(), FailingProvider()])

        response = test_client.post("/api/apartments/search", json={"city": "Dallas, TX"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Dallas Loft"
        assert "BrokenSource" in data.get("sources_failed", [])

    def test_search_reports_all_failures(self, test_client, monkeypatch):
        from agents.apartment.services import provider_registry

        class FailingA:
            source_name = "SourceA"
            def is_configured(self): return True
            def search(self, criteria): raise RuntimeError("boom")

        class FailingB:
            source_name = "SourceB"
            def is_configured(self): return True
            def search(self, criteria): raise RuntimeError("boom")

        monkeypatch.setattr(provider_registry, "get_all_providers", lambda conn: [FailingA(), FailingB()])

        response = test_client.post("/api/apartments/search", json={"city": "Austin, TX"})
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("sources_failed", [])) == 2
        assert data["results"] == []


class TestFeaturePreferencesAPI:
    """Integration tests for the 3-state feature preferences endpoints."""

    def test_set_and_get_feature_preference(self, test_client):
        set_response = test_client.put("/api/apartments/preferences/features/Parking", json={
            "category": "building", "preference": "must_have",
        })
        assert set_response.status_code == 200
        assert set_response.json()["preference"] == "must_have"

        get_response = test_client.get("/api/apartments/preferences/features")
        preferences = get_response.json()
        assert len(preferences) >= 1
        parking_pref = next(preference for preference in preferences if preference["feature_name"] == "Parking")
        assert parking_pref["preference"] == "must_have"

    def test_cycle_through_three_states(self, test_client):
        # Set to must_have
        test_client.put("/api/apartments/preferences/features/Pool", json={
            "category": "building", "preference": "must_have",
        })
        # Change to deal_breaker
        test_client.put("/api/apartments/preferences/features/Pool", json={
            "category": "building", "preference": "deal_breaker",
        })
        prefs = test_client.get("/api/apartments/preferences/features").json()
        pool_pref = next(preference for preference in prefs if preference["feature_name"] == "Pool")
        assert pool_pref["preference"] == "deal_breaker"

        # Reset to neutral
        test_client.delete("/api/apartments/preferences/features/Pool")
        prefs_after = test_client.get("/api/apartments/preferences/features").json()
        pool_prefs = [preference for preference in prefs_after if preference["feature_name"] == "Pool"]
        assert len(pool_prefs) == 0  # Neutral = not in list

    def test_rejects_invalid_preference(self, test_client):
        response = test_client.put("/api/apartments/preferences/features/Pool", json={
            "category": "building", "preference": "love_it",
        })
        assert response.status_code == 400


class TestLabDataAPI:
    """Integration tests for the Nest Lab data endpoint."""

    def test_lab_returns_listing_data(self, test_client):
        create_response = test_client.post("/api/apartments/listings", json={
            "title": "Alexan Braker Pointe",
            "address": "10801 N Mopac Expy, Austin, TX 78759",
            "price": 1445,
            "bedrooms": 1,
        })
        listing_id = create_response.json()["id"]

        lab_response = test_client.get(f"/api/apartments/lab/{listing_id}")
        assert lab_response.status_code == 200
        data = lab_response.json()
        assert data["listing"]["title"] == "Alexan Braker Pointe"
        assert data["listing"]["price"] == 1445
        assert "feature_preferences" in data
        assert "analyses" in data
        assert "must_haves" in data
        assert "deal_breakers" in data

    def test_lab_returns_404_for_nonexistent(self, test_client):
        response = test_client.get("/api/apartments/lab/99999")
        assert response.status_code == 404

    def test_lab_includes_user_preferences(self, test_client):
        # Set a preference first
        test_client.put("/api/apartments/preferences/features/Pool", json={
            "category": "building", "preference": "must_have",
        })

        # Create listing and get lab data
        create_response = test_client.post("/api/apartments/listings", json={
            "title": "Test Listing", "price": 1500,
        })
        listing_id = create_response.json()["id"]

        lab_response = test_client.get(f"/api/apartments/lab/{listing_id}")
        data = lab_response.json()
        assert "Pool" in data["must_haves"]


class TestJobsmithNotBroken:
    def test_jobsmith_knowledge_entries_still_works(self, test_client):
        """Jobsmith endpoints must still respond correctly."""
        response = test_client.get("/api/knowledge/entries")
        assert response.status_code == 200

    def test_jobsmith_jobs_still_works(self, test_client):
        response = test_client.get("/api/jobs")
        assert response.status_code == 200
