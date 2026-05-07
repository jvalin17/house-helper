"""Price analyzer — tests for area median, percentile, comparables."""

import sqlite3
import pytest
from shared.db import migrate
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.services.price_analyzer import get_price_context


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_repo(database_connection):
    return ApartmentListingRepository(database_connection)


@pytest.fixture
def austin_listings(listing_repo):
    """Create several Austin listings for price comparison."""
    listing_ids = []
    listings = [
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX, 78759", 1445, 1),
        ("Camden Stoneleigh", "4825 Davis Ln, Austin, TX, 78749", 1109, 1),
        ("The Met", "301 Brazos St, Austin, TX, 78701", 1800, 1),
        ("Ascend Pioneer Hill", "12400 US-183, Austin, TX, 78750", 1350, 1),
        ("Domain Apartments", "11511 Domain Dr, Austin, TX, 78758", 1650, 1),
    ]
    for title, address, price, bedrooms in listings:
        listing_id = listing_repo.save_listing(
            title=title, address=address, price=price, bedrooms=bedrooms,
        )
        listing_ids.append(listing_id)
    return listing_ids


class TestPriceContext:
    def test_returns_area_median_from_comparables(self, listing_repo, austin_listings):
        target_listing_id = austin_listings[0]  # Alexan at $1,445
        context = get_price_context(target_listing_id, listing_repo)

        assert context["listing_price"] == 1445
        assert context["area_median"] is not None
        # Comparables: 1109, 1350, 1650, 1800 → median = (1350+1650)/2 = 1500
        assert context["area_median"] == 1500
        assert context["comparable_count"] == 4

    def test_returns_percentile_position(self, listing_repo, austin_listings):
        target_listing_id = austin_listings[0]  # $1,445
        context = get_price_context(target_listing_id, listing_repo)

        # $1,445 is cheaper than 1650 and 1800 → 2 cheaper (1109, 1350) out of 4
        assert context["percentile"] == 50  # 2/4 = 50th percentile

    def test_price_vs_median_shows_difference(self, listing_repo, austin_listings):
        target_listing_id = austin_listings[0]  # $1,445, median $1,500
        context = get_price_context(target_listing_id, listing_repo)

        assert context["price_vs_median"] == -55  # Below median

    def test_handles_no_comparables(self, listing_repo):
        listing_id = listing_repo.save_listing(
            title="Isolated Listing", address="100 Main St, Nowhere, TX, 99999", price=1200,
        )
        context = get_price_context(listing_id, listing_repo)
        assert context["comparable_count"] == 0
        assert context["area_median"] is None

    def test_handles_listing_without_price(self, listing_repo):
        listing_id = listing_repo.save_listing(title="No Price Listing", address="Austin, TX")
        context = get_price_context(listing_id, listing_repo)
        assert "error" in context

    def test_comparables_sorted_by_price_proximity(self, listing_repo, austin_listings):
        target_listing_id = austin_listings[0]  # $1,445
        context = get_price_context(target_listing_id, listing_repo)
        comparables = context["comparables"]
        # Closest to $1,445: $1,350 (diff 95), then $1,650 (diff 205)
        assert comparables[0]["price"] == 1350
        assert comparables[1]["price"] == 1650
