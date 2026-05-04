"""Compare endpoint — tests for scoring logic and response format."""

import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.db import migrate
from agents.apartment.routes import create_router as create_apartment_router


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
    return TestClient(application)


@pytest.fixture
def two_listings(test_client):
    """Create 2 listings for comparison."""
    listing_a = test_client.post("/api/apartments/listings", json={
        "title": "Alexan Braker Pointe",
        "address": "10801 N Mopac Expy, Austin, TX, 78759",
        "price": 1445,
        "bedrooms": 1,
    }).json()
    listing_b = test_client.post("/api/apartments/listings", json={
        "title": "Camden Stoneleigh",
        "address": "4825 Davis Ln, Austin, TX, 78749",
        "price": 1109,
        "bedrooms": 1,
    }).json()
    return listing_a["id"], listing_b["id"]


@pytest.fixture
def three_listings(test_client, two_listings):
    listing_c = test_client.post("/api/apartments/listings", json={
        "title": "The Met Downtown",
        "address": "301 Brazos St, Austin, TX, 78701",
        "price": 1800,
        "bedrooms": 2,
    }).json()
    return two_listings[0], two_listings[1], listing_c["id"]


class TestCompareEndpoint:
    def test_compare_two_listings_returns_scores(self, test_client, two_listings):
        listing_a_id, listing_b_id = two_listings
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": [listing_a_id, listing_b_id],
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["listings"]) == 2

    def test_compare_three_listings(self, test_client, three_listings):
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(three_listings),
        })
        assert response.status_code == 200
        assert len(response.json()["listings"]) == 3

    def test_compare_rejects_one_listing(self, test_client, two_listings):
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": [two_listings[0]],
        })
        assert response.status_code == 400

    def test_compare_rejects_four_listings(self, test_client, three_listings):
        extra = test_client.post("/api/apartments/listings", json={
            "title": "Extra", "price": 1500,
        }).json()
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(three_listings) + [extra["id"]],
        })
        assert response.status_code == 400

    def test_compare_includes_listing_data(self, test_client, two_listings):
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(two_listings),
        })
        data = response.json()
        titles = [entry["listing"]["title"] for entry in data["listings"]]
        assert "Alexan Braker Pointe" in titles
        assert "Camden Stoneleigh" in titles

    def test_compare_strips_parsed_data(self, test_client, two_listings):
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(two_listings),
        })
        for entry in response.json()["listings"]:
            assert "parsed_data" not in entry["listing"]

    def test_compare_with_preferences_affects_score(self, test_client, two_listings):
        # Set a must-have
        test_client.put("/api/apartments/preferences/features/Parking", json={
            "category": "building", "preference": "must_have",
        })
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(two_listings),
        })
        data = response.json()
        assert "Parking" in data["must_haves"]

    def test_compare_score_null_without_preferences_or_analysis(self, test_client, two_listings):
        """No preferences + no LLM analysis → score is null."""
        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(two_listings),
        })
        for entry in response.json()["listings"]:
            assert entry["score"] is None

    def test_compare_includes_qa_summary(self, test_client, two_listings, database_connection):
        listing_id = two_listings[0]
        database_connection.execute(
            "INSERT INTO apartment_qa_history (listing_id, question, answer) VALUES (?, ?, ?)",
            (listing_id, "Is there parking?", "Yes, covered parking is included."),
        )
        database_connection.commit()

        response = test_client.post("/api/apartments/compare", json={
            "listing_ids": list(two_listings),
        })
        data = response.json()
        listing_with_qa = next(entry for entry in data["listings"] if entry["listing"]["id"] == listing_id)
        assert len(listing_with_qa["qa_summary"]) == 1
        assert listing_with_qa["qa_summary"][0]["question"] == "Is there parking?"
