"""Apartment preferences + custom sources — TDD tests.

Covers:
- Save and retrieve preferences
- Update existing preferences
- Custom sources CRUD (add, list, delete, toggle)
- Max 5 custom sources enforced
- Validation (name and URL required)
"""

import sqlite3
import pytest

from shared.db import migrate
from agents.apartment.repositories.preferences_repo import ApartmentPreferencesRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def preferences_repo(database_connection):
    return ApartmentPreferencesRepository(database_connection)


class TestPreferences:
    def test_get_defaults_when_none_saved(self, preferences_repo):
        """Should return default empty preferences when none saved."""
        preferences = preferences_repo.get_preferences()
        assert preferences["location"] is None
        assert preferences["max_price"] is None
        assert preferences["must_haves"] == []
        assert preferences["auto_search_active"] is False

    def test_save_and_retrieve_preferences(self, preferences_repo):
        """Saved preferences should be retrievable."""
        preferences_repo.save_preferences(
            location="Dallas, TX 75001",
            max_price=1800.0,
            min_bedrooms=2,
            must_haves=["elevator", "parking"],
            layout_requirements=["kitchen not sharing wall with bathroom"],
            auto_search_active=True,
        )
        saved = preferences_repo.get_preferences()
        assert saved["location"] == "Dallas, TX 75001"
        assert saved["max_price"] == 1800.0
        assert saved["min_bedrooms"] == 2
        assert "elevator" in saved["must_haves"]
        assert "parking" in saved["must_haves"]
        assert saved["auto_search_active"] is True

    def test_update_existing_preferences(self, preferences_repo):
        """Updating should modify existing record, not create new."""
        preferences_repo.save_preferences(location="Dallas", max_price=1500)
        preferences_repo.save_preferences(location="Austin", max_price=2000)
        saved = preferences_repo.get_preferences()
        assert saved["location"] == "Austin"
        assert saved["max_price"] == 2000.0


class TestCustomSources:
    def test_add_and_list_source(self, preferences_repo):
        """Adding a source should make it appear in the list."""
        result = preferences_repo.add_custom_source(
            name="RentCast", api_url="https://api.rentcast.io/v1/listings"
        )
        assert result["name"] == "RentCast"
        assert result["id"].startswith("apt_custom_")

        sources = preferences_repo.list_custom_sources()
        assert len(sources) == 1
        assert sources[0]["name"] == "RentCast"

    def test_add_source_with_api_key(self, preferences_repo):
        """Source with API key should have has_api_key=True and masked key."""
        result = preferences_repo.add_custom_source(
            name="Zillow", api_url="https://api.zillow.com", api_key="sk-test-key"
        )
        assert result["has_api_key"] is True
        assert result["api_key"] == "***"

    def test_max_5_sources(self, preferences_repo):
        """Should not allow more than 5 custom sources."""
        for index in range(5):
            preferences_repo.add_custom_source(
                name=f"Source {index + 1}", api_url=f"https://source{index + 1}.com"
            )
        with pytest.raises(ValueError, match="maximum"):
            preferences_repo.add_custom_source(name="Source 6", api_url="https://source6.com")

    def test_delete_source(self, preferences_repo):
        """Deleting a source should remove it from the list."""
        result = preferences_repo.add_custom_source(name="Temp", api_url="https://temp.com")
        preferences_repo.delete_custom_source(result["id"])
        assert len(preferences_repo.list_custom_sources()) == 0

    def test_toggle_source(self, preferences_repo):
        """Toggling should change the enabled flag."""
        result = preferences_repo.add_custom_source(name="Toggler", api_url="https://toggler.com")
        preferences_repo.toggle_custom_source(result["id"], False)
        sources = preferences_repo.list_custom_sources()
        assert sources[0]["enabled"] is False

    def test_validation_requires_name(self, preferences_repo):
        with pytest.raises(ValueError, match="name"):
            preferences_repo.add_custom_source(name="", api_url="https://example.com")

    def test_validation_requires_url(self, preferences_repo):
        with pytest.raises(ValueError, match="url"):
            preferences_repo.add_custom_source(name="Test", api_url="")

    def test_list_empty_returns_empty(self, preferences_repo):
        assert preferences_repo.list_custom_sources() == []
