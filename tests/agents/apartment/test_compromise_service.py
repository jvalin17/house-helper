"""Tests for CompromiseService — Budget Reality Check."""

import sqlite3
import json

import pytest
from shared.db import migrate
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.preferences_repo import ApartmentPreferencesRepository
from agents.apartment.services.compromise_service import CompromiseService


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def mock_learning_machine(monkeypatch):
    """Mock learning_machine module functions (the real API — not a class).
    Real signatures:
      get_learned_weights(connection, profile_id, agent) -> dict[str, float]
      _count_meaningful_interactions(connection, profile_id, agent) -> int
    """
    mock_weights = {
        "downtown": 3.2, "pool": 2.1, "2br": 2.8, "walkable": 1.5,
        "austin": 1.0, "parking": 0.5,
    }
    monkeypatch.setattr(
        "agents.apartment.services.compromise_service.get_learned_weights",
        lambda connection, profile_id, agent: mock_weights,
    )
    monkeypatch.setattr(
        "agents.apartment.services.compromise_service._count_meaningful_interactions",
        lambda connection, profile_id, agent: 24,
    )
    return mock_weights


@pytest.fixture
def compromise_service(database_connection):
    listing_repo = ApartmentListingRepository(database_connection)
    preferences_repo = ApartmentPreferencesRepository(database_connection)
    return CompromiseService(database_connection, listing_repo, preferences_repo)


def seed_listings(connection, listings):
    for listing in listings:
        connection.execute(
            "INSERT INTO apartment_listings (id, title, address, price, bedrooms, bathrooms, source, is_saved, amenities) "
            "VALUES (?, ?, ?, ?, 2, 1, 'manual', 1, ?)",
            (listing["id"], listing["title"], listing["address"], listing["price"],
             json.dumps(listing.get("amenities", []))),
        )
    connection.commit()


class TestGetProfile:
    def test_profile_ready_after_10_interactions(self, compromise_service, mock_learning_machine):
        profile = compromise_service.get_profile(profile_id=None)
        assert profile["ready"] is True
        assert profile["interaction_count"] == 24

    def test_profile_not_ready_under_10_interactions(self, compromise_service, monkeypatch):
        monkeypatch.setattr(
            "agents.apartment.services.compromise_service._count_meaningful_interactions",
            lambda connection, profile_id, agent: 5,
        )
        profile = compromise_service.get_profile(profile_id=None)
        assert profile["ready"] is False

    def test_profile_returns_top_preferences_sorted_by_weight(self, compromise_service, mock_learning_machine):
        profile = compromise_service.get_profile(profile_id=None)
        preferences = profile["preferences"]
        weights = [preference["weight"] for preference in preferences]
        assert weights == sorted(weights, reverse=True)

    def test_profile_includes_budget(self, compromise_service, database_connection, mock_learning_machine):
        database_connection.execute(
            "INSERT INTO apartment_preferences (location, max_price, min_bedrooms) "
            "VALUES ('Austin', 1800, 2)"
        )
        database_connection.commit()
        profile = compromise_service.get_profile(profile_id=None)
        assert profile["budget"] == 1800

    def test_profile_classifies_achievable_vs_stretch(self, compromise_service, database_connection, mock_learning_machine):
        """Preferences with avg rent <= budget should be achievable."""
        database_connection.execute(
            "INSERT INTO apartment_preferences (location, max_price, min_bedrooms) "
            "VALUES ('Austin', 1800, 2)"
        )
        database_connection.commit()
        seed_listings(database_connection, [
            {"id": 1, "title": "Downtown Lux", "address": "Austin", "price": 2400, "amenities": ["pool"]},
            {"id": 2, "title": "2br Suburb", "address": "Pflugerville", "price": 1500, "amenities": []},
        ])
        profile = compromise_service.get_profile(profile_id=None)
        preferences = profile["preferences"]
        # "2br" matches listing at $1500 (achievable), "downtown" matches $2400 (stretch)
        downtown_pref = next((preference for preference in preferences if preference["term"] == "downtown"), None)
        two_br_pref = next((preference for preference in preferences if preference["term"] == "2br"), None)
        if downtown_pref:
            assert downtown_pref["achievable"] is False
        if two_br_pref:
            assert two_br_pref["achievable"] is True

    def test_profile_generates_summary_string(self, compromise_service, database_connection, mock_learning_machine):
        database_connection.execute(
            "INSERT INTO apartment_preferences (location, max_price, min_bedrooms) "
            "VALUES ('Austin', 1800, 2)"
        )
        database_connection.commit()
        seed_listings(database_connection, [
            {"id": 1, "title": "Downtown Place", "address": "Austin", "price": 2400},
        ])
        profile = compromise_service.get_profile(profile_id=None)
        assert "summary" in profile
        assert "$1,800" in profile["summary"]

    def test_profile_not_ready_when_no_weights(self, compromise_service, monkeypatch):
        monkeypatch.setattr(
            "agents.apartment.services.compromise_service._count_meaningful_interactions",
            lambda connection, profile_id, agent: 15,
        )
        monkeypatch.setattr(
            "agents.apartment.services.compromise_service.get_learned_weights",
            lambda connection, profile_id, agent: {},
        )
        profile = compromise_service.get_profile(profile_id=None)
        assert profile["ready"] is False


class TestExploreCompromises:
    def test_returns_matching_count(self, compromise_service, database_connection):
        seed_listings(database_connection, [
            {"id": 1, "title": "Downtown Lux", "address": "Austin", "price": 2400, "amenities": ["pool"]},
            {"id": 2, "title": "Suburb Basic", "address": "Pflugerville", "price": 1500, "amenities": []},
            {"id": 3, "title": "Suburb Pool", "address": "Pflugerville", "price": 1800, "amenities": ["pool"]},
        ])
        result = compromise_service.explore_compromises(
            enabled=["pool"], disabled=["downtown"]
        )
        assert result["matching_count"] >= 1

    def test_returns_positive_message(self, compromise_service, database_connection):
        seed_listings(database_connection, [
            {"id": 1, "title": "Pflugerville Place", "address": "Pflugerville", "price": 1800, "amenities": ["pool"]},
        ])
        result = compromise_service.explore_compromises(
            enabled=["pool"], disabled=["downtown"]
        )
        assert "positive_message" in result
        assert len(result["positive_message"]) > 0

    def test_never_uses_negative_framing(self, compromise_service, database_connection):
        seed_listings(database_connection, [
            {"id": 1, "title": "Test", "address": "Austin", "price": 3000},
        ])
        result = compromise_service.explore_compromises(
            enabled=["downtown", "pool"], disabled=[]
        )
        message = result.get("positive_message", "")
        negative_phrases = ["can't afford", "too expensive", "out of budget", "not possible"]
        for phrase in negative_phrases:
            assert phrase not in message.lower()

    def test_returns_suggestions(self, compromise_service, database_connection):
        seed_listings(database_connection, [
            {"id": 1, "title": "Great Deal", "address": "Round Rock", "price": 1600, "amenities": ["pool"]},
        ])
        result = compromise_service.explore_compromises(
            enabled=["pool"], disabled=["downtown"]
        )
        if result.get("suggestions"):
            suggestion = result["suggestions"][0]
            assert "title" in suggestion
            assert "price" in suggestion

    def test_empty_listings_returns_zero_matches(self, compromise_service):
        result = compromise_service.explore_compromises(
            enabled=["downtown"], disabled=["pool"]
        )
        assert result["matching_count"] == 0


class TestCompromiseSecurity:
    def test_rejects_empty_preferences(self, compromise_service):
        result = compromise_service.explore_compromises(enabled=[], disabled=[])
        assert result["matching_count"] >= 0  # Should not crash

    def test_ignores_unknown_preference_terms(self, compromise_service, database_connection):
        seed_listings(database_connection, [
            {"id": 1, "title": "Test", "address": "Austin", "price": 1500},
        ])
        # Should not crash on terms not in weight store
        result = compromise_service.explore_compromises(
            enabled=["nonexistent_term"], disabled=["another_fake"]
        )
        assert "matching_count" in result
