"""Feature preferences repository — tests for 3-state tag system.

Preferences cycle: neutral → must_have → deal_breaker.
Global across all listings — "I need parking" applies everywhere.
"""

import sqlite3

import pytest

from shared.db import migrate
from agents.apartment.repositories.feature_preferences_repo import (
    FeaturePreferencesRepository,
    VALID_PREFERENCES,
)


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def preferences_repo(database_connection):
    return FeaturePreferencesRepository(database_connection)


class TestGetPreferences:
    def test_get_all_returns_empty_initially(self, preferences_repo):
        result = preferences_repo.get_all_preferences()
        assert result == []

    def test_set_and_get_preference(self, preferences_repo):
        preferences_repo.set_preference("In-unit W/D", "unit", "must_have")
        result = preferences_repo.get_all_preferences()
        assert len(result) == 1
        assert result[0]["feature_name"] == "In-unit W/D"
        assert result[0]["category"] == "unit"
        assert result[0]["preference"] == "must_have"

    def test_set_preference_upserts_on_duplicate(self, preferences_repo):
        preferences_repo.set_preference("Pool", "building", "must_have")
        preferences_repo.set_preference("Pool", "building", "deal_breaker")
        result = preferences_repo.get_preference("Pool")
        assert result["preference"] == "deal_breaker"

    def test_get_preference_returns_none_for_unknown(self, preferences_repo):
        result = preferences_repo.get_preference("Nonexistent Feature")
        assert result is None

    def test_multiple_preferences_across_categories(self, preferences_repo):
        preferences_repo.set_preference("In-unit W/D", "unit", "must_have")
        preferences_repo.set_preference("Pool", "building", "must_have")
        preferences_repo.set_preference("Near transit", "neighborhood", "deal_breaker")
        result = preferences_repo.get_all_preferences()
        assert len(result) == 3
        categories = {pref["category"] for pref in result}
        assert categories == {"unit", "building", "neighborhood"}


class TestMustHavesAndDealBreakers:
    def test_get_must_haves_returns_only_must_haves(self, preferences_repo):
        preferences_repo.set_preference("In-unit W/D", "unit", "must_have")
        preferences_repo.set_preference("Pool", "building", "deal_breaker")
        preferences_repo.set_preference("Parking", "building", "must_have")
        must_haves = preferences_repo.get_must_haves()
        assert "In-unit W/D" in must_haves
        assert "Parking" in must_haves
        assert "Pool" not in must_haves

    def test_get_deal_breakers_returns_only_deal_breakers(self, preferences_repo):
        preferences_repo.set_preference("No dishwasher", "unit", "deal_breaker")
        preferences_repo.set_preference("Pool", "building", "must_have")
        deal_breakers = preferences_repo.get_deal_breakers()
        assert "No dishwasher" in deal_breakers
        assert "Pool" not in deal_breakers

    def test_empty_when_no_preferences_set(self, preferences_repo):
        assert preferences_repo.get_must_haves() == []
        assert preferences_repo.get_deal_breakers() == []


class TestResetPreference:
    def test_reset_removes_preference(self, preferences_repo):
        preferences_repo.set_preference("Pool", "building", "must_have")
        preferences_repo.reset_preference("Pool")
        result = preferences_repo.get_preference("Pool")
        assert result is None

    def test_reset_nonexistent_does_not_crash(self, preferences_repo):
        preferences_repo.reset_preference("Nonexistent")  # should not raise


class TestValidation:
    def test_rejects_invalid_preference_value(self, preferences_repo):
        with pytest.raises(ValueError, match="Invalid preference"):
            preferences_repo.set_preference("Pool", "building", "love_it")

    def test_accepts_all_valid_values(self, preferences_repo):
        for preference_value in VALID_PREFERENCES:
            preferences_repo.set_preference(f"Feature {preference_value}", "unit", preference_value)
        all_prefs = preferences_repo.get_all_preferences()
        # neutral is excluded from get_all
        non_neutral = [preference for preference in all_prefs if preference["preference"] != "neutral"]
        assert len(non_neutral) == 2  # must_have and deal_breaker
