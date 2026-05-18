"""Dashboard routes — integration tests for NestScout dashboard and photo endpoints.

Covers:
- GET funnel returns stages
- GET stats returns counts
- PUT advance moves stage forward
- PUT advance on final stage returns error
- PUT stage with invalid stage returns 400
- GET/POST notes round-trip
- POST photos with valid data
- POST photos with path traversal rejected
- DELETE photo returns 200
- PUT archive sets is_saved=0
- GET achievements returns list
- GET/PUT/DELETE photo CRUD
- POST analyze returns stub message
"""

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


def _create_saved_listing(test_client, title="Alexan Braker Pointe", price=1445):
    """Helper to create a listing and save it to shortlist. Returns listing ID."""
    create_response = test_client.post("/api/apartments/listings", json={
        "title": title,
        "address": "11011 Domain Dr, Austin, TX 78758",
        "price": price,
    })
    listing_id = create_response.json()["id"]
    test_client.post(f"/api/apartments/listings/{listing_id}/save")
    return listing_id


class TestDashboardFunnel:
    def test_funnel_returns_all_stages(self, test_client):
        response = test_client.get("/api/apartments/dashboard/funnel")
        assert response.status_code == 200
        funnel = response.json()
        assert "stages" in funnel
        assert "total_saved" in funnel
        for stage in ("interested", "visited", "applied", "approved", "moved_in"):
            assert stage in funnel["stages"]
            assert "count" in funnel["stages"][stage]
            assert "listings" in funnel["stages"][stage]

    def test_funnel_places_saved_listing_in_interested(self, test_client):
        _create_saved_listing(test_client)
        response = test_client.get("/api/apartments/dashboard/funnel")
        funnel = response.json()
        assert funnel["stages"]["interested"]["count"] == 1
        assert funnel["stages"]["interested"]["listings"][0]["title"] == "Alexan Braker Pointe"
        assert funnel["total_saved"] == 1

    def test_funnel_empty_when_no_saved_listings(self, test_client):
        response = test_client.get("/api/apartments/dashboard/funnel")
        funnel = response.json()
        assert funnel["total_saved"] == 0
        for stage_name in funnel["stages"]:
            assert funnel["stages"][stage_name]["count"] == 0
            assert funnel["stages"][stage_name]["listings"] == []


class TestDashboardStats:
    def test_stats_returns_counts(self, test_client):
        _create_saved_listing(test_client, title="Apt A")
        _create_saved_listing(test_client, title="Apt B", price=1800)

        response = test_client.get("/api/apartments/dashboard/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_saved"] == 2
        assert "stage_counts" in stats
        assert "hunt_duration_days" in stats
        assert "average_rent" in stats

    def test_stats_empty_when_no_listings(self, test_client):
        response = test_client.get("/api/apartments/dashboard/stats")
        stats = response.json()
        assert stats["total_saved"] == 0


class TestAdvanceStage:
    def test_advance_moves_from_interested_to_visited(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.put(f"/api/apartments/dashboard/advance/{listing_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["previous_stage"] == "interested"
        assert result["new_stage"] == "visited"

    def test_advance_on_final_stage_returns_error(self, test_client):
        listing_id = _create_saved_listing(test_client)
        # Advance through all stages to reach moved_in
        for _ in range(4):  # interested -> visited -> applied -> approved -> moved_in
            test_client.put(f"/api/apartments/dashboard/advance/{listing_id}")

        # Verify we are at moved_in
        funnel_response = test_client.get("/api/apartments/dashboard/funnel")
        funnel = funnel_response.json()
        assert funnel["stages"]["moved_in"]["count"] == 1

        # Advancing again should fail
        response = test_client.put(f"/api/apartments/dashboard/advance/{listing_id}")
        assert response.status_code == 400
        assert "final stage" in response.json()["detail"]

    def test_advance_nonexistent_listing_returns_404(self, test_client):
        response = test_client.put("/api/apartments/dashboard/advance/99999")
        assert response.status_code == 404


class TestSetStage:
    def test_set_stage_to_applied(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.put(
            f"/api/apartments/dashboard/stage/{listing_id}",
            json={"stage": "applied"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["new_stage"] == "applied"

    def test_set_stage_with_invalid_stage_returns_400(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.put(
            f"/api/apartments/dashboard/stage/{listing_id}",
            json={"stage": "rejected"},
        )
        assert response.status_code == 400
        assert "Invalid stage" in response.json()["detail"]

    def test_set_stage_with_missing_stage_returns_400(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.put(
            f"/api/apartments/dashboard/stage/{listing_id}",
            json={},
        )
        assert response.status_code == 400


class TestNotes:
    def test_get_notes_returns_empty_for_new_listing(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.get(f"/api/apartments/dashboard/notes/{listing_id}")
        assert response.status_code == 200
        notes = response.json()
        assert notes["notes"] is None

    def test_save_and_get_notes_round_trip(self, test_client):
        listing_id = _create_saved_listing(test_client)
        save_response = test_client.post(
            f"/api/apartments/dashboard/notes/{listing_id}",
            json={
                "notes": "Nice kitchen, spacious bedroom",
                "structured_data": {"visited_date": "2026-05-01", "rating": 4},
            },
        )
        assert save_response.status_code == 200
        saved_result = save_response.json()
        assert saved_result["notes"] == "Nice kitchen, spacious bedroom"
        assert saved_result["structured_data"]["rating"] == 4

        get_response = test_client.get(f"/api/apartments/dashboard/notes/{listing_id}")
        assert get_response.status_code == 200
        retrieved_notes = get_response.json()
        assert retrieved_notes["notes"] == "Nice kitchen, spacious bedroom"

    def test_get_notes_for_nonexistent_listing_returns_404(self, test_client):
        response = test_client.get("/api/apartments/dashboard/notes/99999")
        assert response.status_code == 404

    def test_save_notes_for_nonexistent_listing_returns_404(self, test_client):
        response = test_client.post(
            "/api/apartments/dashboard/notes/99999",
            json={"notes": "test"},
        )
        assert response.status_code == 404


class TestPhotos:
    def test_save_photos_with_valid_data(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.post(
            f"/api/apartments/photos/{listing_id}",
            json=[
                {
                    "file_path": f"photos/{listing_id}/abcd1234-5678-9abc-def0-123456789abc.jpg",
                    "label": "Kitchen view",
                    "room_tag": "kitchen",
                },
            ],
        )
        assert response.status_code == 200
        result = response.json()
        assert result["listing_id"] == listing_id
        assert len(result["photo_ids"]) == 1

    def test_save_photos_with_path_traversal_rejected(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.post(
            f"/api/apartments/photos/{listing_id}",
            json=[
                {
                    "file_path": "../../../etc/passwd",
                    "label": "Sneaky",
                    "room_tag": "other",
                },
            ],
        )
        assert response.status_code == 400
        assert "Invalid file_path" in response.json()["detail"]

    def test_list_photos_for_listing(self, test_client):
        listing_id = _create_saved_listing(test_client)
        test_client.post(
            f"/api/apartments/photos/{listing_id}",
            json=[
                {"file_path": f"photos/{listing_id}/aaaa1111-2222-3333-4444-555566667777.jpg", "room_tag": "kitchen"},
                {"file_path": f"photos/{listing_id}/bbbb1111-2222-3333-4444-555566667777.png", "room_tag": "bedroom"},
            ],
        )
        response = test_client.get(f"/api/apartments/photos/{listing_id}")
        assert response.status_code == 200
        photos = response.json()
        assert len(photos) == 2

    def test_list_photos_for_nonexistent_listing_returns_404(self, test_client):
        response = test_client.get("/api/apartments/photos/99999")
        assert response.status_code == 404

    def test_update_photo_label(self, test_client):
        listing_id = _create_saved_listing(test_client)
        save_response = test_client.post(
            f"/api/apartments/photos/{listing_id}",
            json=[
                {"file_path": f"photos/{listing_id}/cccc1111-2222-3333-4444-555566667777.jpg", "label": "Original"},
            ],
        )
        photo_id = save_response.json()["photo_ids"][0]

        update_response = test_client.put(
            f"/api/apartments/photos/{photo_id}/update",
            json={"label": "Updated Kitchen"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["label"] == "Updated Kitchen"

    def test_update_nonexistent_photo_returns_404(self, test_client):
        response = test_client.put(
            "/api/apartments/photos/99999/update",
            json={"label": "Does not exist"},
        )
        assert response.status_code == 404

    def test_delete_photo_returns_200(self, test_client):
        listing_id = _create_saved_listing(test_client)
        save_response = test_client.post(
            f"/api/apartments/photos/{listing_id}",
            json=[
                {"file_path": f"photos/{listing_id}/dddd1111-2222-3333-4444-555566667777.jpg", "label": "To delete"},
            ],
        )
        photo_id = save_response.json()["photo_ids"][0]

        delete_response = test_client.delete(f"/api/apartments/photos/{photo_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] == photo_id

        # Verify photo is gone
        photos = test_client.get(f"/api/apartments/photos/{listing_id}")
        assert len(photos.json()) == 0

    def test_delete_nonexistent_photo_returns_404(self, test_client):
        response = test_client.delete("/api/apartments/photos/99999")
        assert response.status_code == 404

    def test_save_photos_with_empty_list_returns_400(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.post(f"/api/apartments/photos/{listing_id}", json=[])
        assert response.status_code == 400

    def test_save_photos_for_nonexistent_listing_returns_404(self, test_client):
        response = test_client.post(
            "/api/apartments/photos/99999",
            json=[{"file_path": "photos/99999/eeee1111-2222-3333-4444-555566667777.jpg"}],
        )
        assert response.status_code == 404


class TestAnalyzePhotos:
    def test_analyze_with_no_photos_returns_400(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.post(f"/api/apartments/photos/{listing_id}/analyze")
        assert response.status_code == 400
        assert "No photos found" in response.json()["detail"]

    def test_analyze_nonexistent_listing_returns_404(self, test_client):
        response = test_client.post("/api/apartments/photos/99999/analyze")
        assert response.status_code == 404


class TestArchive:
    def test_archive_sets_listing_unsaved(self, test_client):
        listing_id = _create_saved_listing(test_client)

        # Verify it appears in funnel before archiving
        funnel_before = test_client.get("/api/apartments/dashboard/funnel").json()
        assert funnel_before["stages"]["interested"]["count"] == 1

        # Archive
        response = test_client.put(f"/api/apartments/dashboard/archive/{listing_id}")
        assert response.status_code == 200
        assert response.json()["archived"] is True

        # Verify it no longer appears in funnel
        funnel_after = test_client.get("/api/apartments/dashboard/funnel").json()
        assert funnel_after["stages"]["interested"]["count"] == 0

    def test_archive_nonexistent_listing_returns_404(self, test_client):
        response = test_client.put("/api/apartments/dashboard/archive/99999")
        assert response.status_code == 404


class TestProfile:
    def test_get_profile_returns_structure(self, test_client):
        response = test_client.get("/api/apartments/dashboard/profile")
        assert response.status_code == 200
        profile = response.json()
        assert "ready" in profile


class TestCompromise:
    def test_post_compromise_returns_matching_count(self, test_client):
        response = test_client.post(
            "/api/apartments/dashboard/compromise",
            json={
                "enabled_preferences": ["parking"],
                "disabled_preferences": ["pool"],
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert "matching_count" in result
        assert "average_rent" in result
        assert "per_preference_impact" in result
        assert "suggestions" in result


class TestAnalyzePhotosNoPhotos:
    def test_analyze_with_no_photos_returns_error(self, test_client):
        listing_id = _create_saved_listing(test_client)
        response = test_client.post(f"/api/apartments/photos/{listing_id}/analyze")
        assert response.status_code == 400
        assert "No photos found" in response.json()["detail"]


class TestAchievements:
    def test_achievements_returns_list(self, test_client):
        response = test_client.get("/api/apartments/dashboard/achievements")
        assert response.status_code == 200
        achievements = response.json()
        assert isinstance(achievements, list)
        assert len(achievements) > 0
        first_achievement = achievements[0]
        assert "id" in first_achievement
        assert "name" in first_achievement
        assert "unlocked" in first_achievement

    def test_achievements_unlocks_explorer_after_visit(self, test_client):
        listing_id = _create_saved_listing(test_client)
        test_client.put(f"/api/apartments/dashboard/advance/{listing_id}")

        response = test_client.get("/api/apartments/dashboard/achievements")
        achievements = response.json()
        explorer = next(
            achievement for achievement in achievements
            if achievement["id"] == "explorer"
        )
        assert explorer["unlocked"] is True
