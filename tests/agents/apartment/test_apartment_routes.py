"""NestScout routes — integration tests for apartment agent endpoints.

Covers:
- Health endpoint returns agent name
- Create listing via POST returns ID
- Get listing by ID returns correct data
- List listings returns all
- Save/unsave shortlist
- Delete listing
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


class TestJobsmithNotBroken:
    def test_jobsmith_knowledge_entries_still_works(self, test_client):
        """Jobsmith endpoints must still respond correctly."""
        response = test_client.get("/api/knowledge/entries")
        assert response.status_code == 200

    def test_jobsmith_jobs_still_works(self, test_client):
        response = test_client.get("/api/jobs")
        assert response.status_code == 200
