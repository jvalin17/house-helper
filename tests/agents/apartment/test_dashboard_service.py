"""Dashboard service — tests for NestScout funnel, achievements, and stage management."""

import sqlite3
import pytest
from shared.db import migrate
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.cost_repo import CostRepository
from agents.apartment.repositories.photo_repo import PhotoRepository
from agents.apartment.services.dashboard_service import DashboardService, STAGE_ORDER


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
def cost_repo(database_connection):
    return CostRepository(database_connection)


@pytest.fixture
def photo_repo(database_connection):
    return PhotoRepository(database_connection)


@pytest.fixture
def dashboard_service(database_connection, listing_repo, cost_repo, photo_repo):
    return DashboardService(database_connection, listing_repo, cost_repo, photo_repo)


def _create_saved_listing(listing_repo, title="Alexan Braker Pointe", address="11011 Domain Dr, Austin, TX 78758", price=1445):
    """Helper to create a saved listing and return its ID."""
    listing_id = listing_repo.save_listing(
        title=title,
        address=address,
        price=price,
        latitude=30.4518,
        longitude=-97.7428,
    )
    listing_repo.save_to_shortlist(listing_id)
    return listing_id


def _set_listing_stage(database_connection, listing_id, stage):
    """Helper to set a listing's stage by inserting a notes row."""
    database_connection.execute(
        "INSERT INTO apartment_notes (listing_id, status, status_changed_at) VALUES (?, ?, datetime('now'))",
        (listing_id, stage),
    )
    database_connection.commit()


class TestGetFunnel:
    def test_empty_funnel_no_listings(self, dashboard_service):
        funnel = dashboard_service.get_funnel()
        for stage in STAGE_ORDER:
            assert stage in funnel
            assert funnel[stage] == []

    def test_funnel_with_listings_grouped_by_stage(self, dashboard_service, listing_repo, database_connection):
        listing_one_id = _create_saved_listing(listing_repo, title="Alexan Braker Pointe")
        listing_two_id = _create_saved_listing(listing_repo, title="Windsor Ridge", address="4701 Staggerbrush Rd, Austin, TX 78749", price=1650)
        listing_three_id = _create_saved_listing(listing_repo, title="Gables Park Tower", address="111 Sandra Muraida Way, Austin, TX 78703", price=2200)

        _set_listing_stage(database_connection, listing_two_id, "visited")
        _set_listing_stage(database_connection, listing_three_id, "applied")

        funnel = dashboard_service.get_funnel()
        assert len(funnel["interested"]) == 1
        assert funnel["interested"][0]["title"] == "Alexan Braker Pointe"
        assert len(funnel["visited"]) == 1
        assert funnel["visited"][0]["title"] == "Windsor Ridge"
        assert len(funnel["applied"]) == 1
        assert funnel["applied"][0]["title"] == "Gables Park Tower"

    def test_funnel_card_includes_photo_count(self, dashboard_service, listing_repo, photo_repo):
        listing_id = _create_saved_listing(listing_repo)
        photo_repo.save_photos(listing_id, [
            {"file_path": f"photos/{listing_id}/aaaa1111-2222-3333-4444-555566667777.jpg"},
            {"file_path": f"photos/{listing_id}/bbbb1111-2222-3333-4444-555566667777.jpg"},
        ])
        funnel = dashboard_service.get_funnel()
        assert funnel["interested"][0]["photo_count"] == 2

    def test_funnel_card_includes_total_monthly(self, dashboard_service, listing_repo, cost_repo):
        listing_id = _create_saved_listing(listing_repo)
        cost_repo.save_cost(listing_id, base_rent=1445, parking_fee=150)
        funnel = dashboard_service.get_funnel()
        assert funnel["interested"][0]["total_monthly"] == 1595


class TestAdvanceStage:
    def test_advance_interested_to_visited(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        result = dashboard_service.advance_stage(listing_id)
        assert result["previous_stage"] == "interested"
        assert result["new_stage"] == "visited"

    def test_advance_visited_to_applied(self, dashboard_service, listing_repo, database_connection):
        listing_id = _create_saved_listing(listing_repo)
        _set_listing_stage(database_connection, listing_id, "visited")
        result = dashboard_service.advance_stage(listing_id)
        assert result["new_stage"] == "applied"

    def test_advance_already_at_moved_in_raises_error(self, dashboard_service, listing_repo, database_connection):
        listing_id = _create_saved_listing(listing_repo)
        _set_listing_stage(database_connection, listing_id, "moved_in")
        with pytest.raises(ValueError, match="already at final stage"):
            dashboard_service.advance_stage(listing_id)

    def test_advance_invalid_listing_raises_error(self, dashboard_service):
        with pytest.raises(ValueError, match="not found"):
            dashboard_service.advance_stage(999)

    def test_advance_unsaved_listing_raises_error(self, dashboard_service, listing_repo):
        listing_id = listing_repo.save_listing(
            title="Not Saved Apartment",
            address="123 Unsaved St, Austin, TX",
            price=1000,
        )
        with pytest.raises(ValueError, match="not saved"):
            dashboard_service.advance_stage(listing_id)


class TestSetStage:
    def test_set_stage_to_arbitrary_stage(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        result = dashboard_service.set_stage(listing_id, "applied")
        assert result["new_stage"] == "applied"

    def test_set_invalid_stage_raises_error(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        with pytest.raises(ValueError, match="Invalid stage"):
            dashboard_service.set_stage(listing_id, "invalid_stage")

    def test_set_stage_nonexistent_listing_raises_error(self, dashboard_service):
        with pytest.raises(ValueError, match="not found"):
            dashboard_service.set_stage(999, "visited")


class TestAchievements:
    def test_no_visits_no_explorer_badge(self, dashboard_service):
        achievements = dashboard_service.get_achievements()
        explorer = next(achievement for achievement in achievements if achievement["id"] == "explorer")
        assert explorer["unlocked"] is False

    def test_one_visit_unlocks_explorer(self, dashboard_service, listing_repo, database_connection):
        listing_id = _create_saved_listing(listing_repo)
        _set_listing_stage(database_connection, listing_id, "visited")
        achievements = dashboard_service.get_achievements()
        explorer = next(achievement for achievement in achievements if achievement["id"] == "explorer")
        assert explorer["unlocked"] is True

    def test_five_visits_unlocks_scout(self, dashboard_service, listing_repo, database_connection):
        for index in range(5):
            listing_id = _create_saved_listing(
                listing_repo,
                title=f"Apartment {index}",
                address=f"{100 + index} Test St, Austin, TX 78701",
                price=1400 + index * 50,
            )
            _set_listing_stage(database_connection, listing_id, "visited")
        achievements = dashboard_service.get_achievements()
        scout = next(achievement for achievement in achievements if achievement["id"] == "scout")
        assert scout["unlocked"] is True

    def test_application_unlocks_applicant(self, dashboard_service, listing_repo, database_connection):
        listing_id = _create_saved_listing(listing_repo)
        _set_listing_stage(database_connection, listing_id, "applied")
        achievements = dashboard_service.get_achievements()
        applicant = next(achievement for achievement in achievements if achievement["id"] == "applicant")
        assert applicant["unlocked"] is True

    def test_advance_stage_returns_unlocked_achievements(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        result = dashboard_service.advance_stage(listing_id)
        # Should unlock explorer at minimum
        unlocked_ids = [achievement["id"] for achievement in result["achievements_unlocked"]]
        assert "explorer" in unlocked_ids


class TestNotes:
    def test_get_notes_no_notes_returns_none(self, dashboard_service):
        assert dashboard_service.get_notes(999) is None

    def test_save_notes_creates_note(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        result = dashboard_service.save_notes(listing_id, "Nice kitchen, good light")
        assert result["notes"] == "Nice kitchen, good light"
        assert result["listing_id"] == listing_id

    def test_save_notes_with_structured_data(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        structured = {"pros": ["quiet neighborhood", "pool"], "cons": ["small closet"]}
        result = dashboard_service.save_notes(listing_id, "Visit notes", structured_data=structured)
        assert result["structured_data"] == structured

    def test_get_notes_returns_latest(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        dashboard_service.save_notes(listing_id, "First visit")
        dashboard_service.save_notes(listing_id, "Second visit - better impression")
        notes = dashboard_service.get_notes(listing_id)
        assert notes["notes"] == "Second visit - better impression"

    def test_save_notes_invalid_listing_raises_error(self, dashboard_service):
        with pytest.raises(ValueError, match="not found"):
            dashboard_service.save_notes(999, "some notes")


class TestArchiveListing:
    def test_archive_listing_sets_unsaved(self, dashboard_service, listing_repo):
        listing_id = _create_saved_listing(listing_repo)
        result = dashboard_service.archive_listing(listing_id)
        assert result["archived"] is True
        # Verify it no longer appears in saved listings
        listing = listing_repo.get_listing(listing_id)
        assert listing["is_saved"] == 0

    def test_archive_nonexistent_listing_raises_error(self, dashboard_service):
        with pytest.raises(ValueError, match="not found"):
            dashboard_service.archive_listing(999)


class TestGetStats:
    def test_stats_empty(self, dashboard_service):
        stats = dashboard_service.get_stats()
        assert stats["total_saved"] == 0
        assert stats["average_rent"] == 0
        assert all(count == 0 for count in stats["stage_counts"].values())

    def test_stats_counts_per_stage(self, dashboard_service, listing_repo, database_connection):
        listing_one_id = _create_saved_listing(listing_repo, title="Alexan Braker Pointe")
        listing_two_id = _create_saved_listing(listing_repo, title="Windsor Ridge", address="4701 Staggerbrush Rd, Austin, TX 78749", price=1650)
        _set_listing_stage(database_connection, listing_two_id, "visited")

        stats = dashboard_service.get_stats()
        assert stats["total_saved"] == 2
        assert stats["stage_counts"]["interested"] == 1
        assert stats["stage_counts"]["visited"] == 1

    def test_stats_average_rent(self, dashboard_service, listing_repo):
        _create_saved_listing(listing_repo, title="Alexan Braker Pointe", price=1400)
        _create_saved_listing(listing_repo, title="Windsor Ridge", address="4701 Staggerbrush Rd, Austin, TX 78749", price=1600)
        stats = dashboard_service.get_stats()
        assert stats["average_rent"] == 1500.0
