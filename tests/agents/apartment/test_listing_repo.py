"""NestScout listing repository — TDD tests.

Covers:
- Save a listing and retrieve it by ID
- List all listings returns saved ones
- Save to shortlist marks listing as saved
- Remove from shortlist clears the flag
- List with saved_only=True filters correctly
- Delete listing removes it and all related data
- Listing fields are stored and retrieved correctly
"""

import sqlite3
import pytest

from shared.db import migrate
from agents.apartment.repositories.listing_repo import ApartmentListingRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_repo(database_connection):
    return ApartmentListingRepository(database_connection)


class TestSaveListing:
    def test_save_and_retrieve_by_id(self, listing_repo):
        """Saving a listing should return an ID that can be retrieved."""
        listing_id = listing_repo.save_listing(
            title="Luxury 2BR Downtown",
            address="123 Main St, Dallas, TX 75001",
            price=1750.00,
            bedrooms=2,
            bathrooms=2.0,
            sqft=1100,
            source="rentcast",
            source_url="https://rentcast.io/listing/123",
            amenities=["elevator", "pool", "gym"],
        )

        retrieved = listing_repo.get_listing(listing_id)
        assert retrieved is not None
        assert retrieved["title"] == "Luxury 2BR Downtown"
        assert retrieved["address"] == "123 Main St, Dallas, TX 75001"
        assert retrieved["price"] == 1750.00
        assert retrieved["bedrooms"] == 2
        assert retrieved["bathrooms"] == 2.0
        assert retrieved["sqft"] == 1100
        assert retrieved["source"] == "rentcast"
        assert "elevator" in retrieved["amenities"]
        assert "pool" in retrieved["amenities"]

    def test_get_nonexistent_returns_none(self, listing_repo):
        """Getting a listing that doesn't exist should return None."""
        result = listing_repo.get_listing(9999)
        assert result is None


class TestListListings:
    def test_list_returns_all_listings(self, listing_repo):
        """Listing all should return every saved listing."""
        listing_repo.save_listing(title="Apartment A", price=1500)
        listing_repo.save_listing(title="Apartment B", price=1800)

        all_listings = listing_repo.list_listings()
        assert len(all_listings) == 2
        titles = [listing["title"] for listing in all_listings]
        assert "Apartment A" in titles
        assert "Apartment B" in titles

    def test_list_saved_only(self, listing_repo):
        """saved_only=True should return only shortlisted listings."""
        listing_id_a = listing_repo.save_listing(title="Apartment A", price=1500)
        listing_repo.save_listing(title="Apartment B", price=1800)
        listing_repo.save_to_shortlist(listing_id_a)

        saved = listing_repo.list_listings(saved_only=True)
        assert len(saved) == 1
        assert saved[0]["title"] == "Apartment A"

    def test_list_empty_returns_empty(self, listing_repo):
        """No listings should return empty list."""
        assert listing_repo.list_listings() == []


class TestShortlist:
    def test_save_to_shortlist(self, listing_repo):
        """Saving to shortlist should set is_saved=1."""
        listing_id = listing_repo.save_listing(title="Nice Place", price=1600)
        listing_repo.save_to_shortlist(listing_id)

        listing = listing_repo.get_listing(listing_id)
        assert listing["is_saved"] == 1

    def test_remove_from_shortlist(self, listing_repo):
        """Removing from shortlist should set is_saved=0."""
        listing_id = listing_repo.save_listing(title="Nice Place", price=1600)
        listing_repo.save_to_shortlist(listing_id)
        listing_repo.remove_from_shortlist(listing_id)

        listing = listing_repo.get_listing(listing_id)
        assert listing["is_saved"] == 0


class TestDeleteListing:
    def test_delete_removes_listing(self, listing_repo):
        """Deleting should remove the listing entirely."""
        listing_id = listing_repo.save_listing(title="Temporary", price=1000)
        listing_repo.delete_listing(listing_id)

        assert listing_repo.get_listing(listing_id) is None
        assert len(listing_repo.list_listings()) == 0

    def test_delete_nonexistent_does_not_crash(self, listing_repo):
        """Deleting a nonexistent listing should not raise."""
        listing_repo.delete_listing(9999)
