"""Photo repository — tests for apartment visit photo management."""

import sqlite3
import pytest
from shared.db import migrate
from agents.apartment.repositories.photo_repo import PhotoRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    connection.execute(
        "INSERT INTO apartment_listings (id, title, address, price, latitude, longitude) "
        "VALUES (1, 'Alexan Braker Pointe', '11011 Domain Dr, Austin, TX 78758', 1445, 30.4518, -97.7428)"
    )
    connection.execute(
        "INSERT INTO apartment_listings (id, title, address, price) "
        "VALUES (2, 'Windsor Ridge', '4701 Staggerbrush Rd, Austin, TX 78749', 1650)"
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def photo_repo(database_connection):
    return PhotoRepository(database_connection)


class TestSaveAndListPhotos:
    def test_save_single_photo_and_list(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc123-def4-5678-9abc-def012345678.jpg", "label": "Kitchen view", "room_tag": "kitchen"},
        ])
        assert len(inserted_ids) == 1
        photos = photo_repo.list_photos(1)
        assert len(photos) == 1
        assert photos[0]["label"] == "Kitchen view"
        assert photos[0]["room_tag"] == "kitchen"

    def test_save_multiple_photos_batch(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg", "room_tag": "kitchen", "display_order": 1},
            {"file_path": "photos/1/bbbb1111-2222-3333-4444-555566667777.png", "room_tag": "bedroom", "display_order": 2},
            {"file_path": "photos/1/cccc1111-2222-3333-4444-555566667777.webp", "room_tag": "bathroom", "display_order": 3},
        ])
        assert len(inserted_ids) == 3
        photos = photo_repo.list_photos(1)
        assert len(photos) == 3
        assert photos[0]["display_order"] == 1
        assert photos[2]["display_order"] == 3

    def test_list_photos_ordered_by_display_order(self, photo_repo):
        photo_repo.save_photos(1, [
            {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg", "display_order": 3},
            {"file_path": "photos/1/bbbb1111-2222-3333-4444-555566667777.jpg", "display_order": 1},
        ])
        photos = photo_repo.list_photos(1)
        assert photos[0]["display_order"] == 1
        assert photos[1]["display_order"] == 3

    def test_list_photos_empty_listing(self, photo_repo):
        photos = photo_repo.list_photos(999)
        assert photos == []


class TestPathValidation:
    def test_path_traversal_rejected(self, photo_repo):
        with pytest.raises(ValueError, match="Invalid file_path"):
            photo_repo.save_photos(1, [
                {"file_path": "photos/1/../../../etc/passwd"},
            ])

    def test_absolute_path_rejected(self, photo_repo):
        with pytest.raises(ValueError, match="Invalid file_path"):
            photo_repo.save_photos(1, [
                {"file_path": "/etc/passwd"},
            ])

    def test_invalid_extension_rejected(self, photo_repo):
        with pytest.raises(ValueError, match="Invalid file_path"):
            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.exe"},
            ])

    def test_missing_directory_prefix_rejected(self, photo_repo):
        with pytest.raises(ValueError, match="Invalid file_path"):
            photo_repo.save_photos(1, [
                {"file_path": "abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])


class TestRoomTagValidation:
    def test_invalid_room_tag_rejected(self, photo_repo):
        with pytest.raises(ValueError, match="Invalid room_tag"):
            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "room_tag": "garage"},
            ])

    def test_all_valid_room_tags_accepted(self, photo_repo):
        valid_tags = ["kitchen", "bedroom", "bathroom", "living", "exterior", "other"]
        for index, tag in enumerate(valid_tags):
            photo_repo.save_photos(1, [
                {"file_path": f"photos/1/abc12345-6789-0abc-def0-12345678{index:04d}.jpg", "room_tag": tag},
            ])
        photos = photo_repo.list_photos(1)
        assert len(photos) == len(valid_tags)

    def test_none_room_tag_accepted(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "room_tag": None},
        ])
        assert len(inserted_ids) == 1


class TestGetAndDeletePhoto:
    def test_get_photo_by_id(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "label": "Living room"},
        ])
        photo = photo_repo.get_photo(inserted_ids[0])
        assert photo is not None
        assert photo["label"] == "Living room"

    def test_get_nonexistent_photo_returns_none(self, photo_repo):
        assert photo_repo.get_photo(999) is None

    def test_delete_returns_file_path(self, photo_repo):
        expected_path = "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": expected_path},
        ])
        returned_path = photo_repo.delete_photo(inserted_ids[0])
        assert returned_path == expected_path
        assert photo_repo.get_photo(inserted_ids[0]) is None

    def test_delete_nonexistent_returns_none(self, photo_repo):
        assert photo_repo.delete_photo(999) is None


class TestUpdatePhoto:
    def test_update_label_only(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "label": "Old label", "room_tag": "kitchen"},
        ])
        photo_repo.update_photo(inserted_ids[0], label="New label")
        photo = photo_repo.get_photo(inserted_ids[0])
        assert photo["label"] == "New label"
        assert photo["room_tag"] == "kitchen"  # unchanged

    def test_update_room_tag_validates(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
        ])
        with pytest.raises(ValueError, match="Invalid room_tag"):
            photo_repo.update_photo(inserted_ids[0], room_tag="garage")

    def test_update_display_order(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "display_order": 0},
        ])
        photo_repo.update_photo(inserted_ids[0], display_order=5)
        photo = photo_repo.get_photo(inserted_ids[0])
        assert photo["display_order"] == 5


class TestBatchPhotoCounts:
    def test_batch_counts_multiple_listings(self, photo_repo):
        photo_repo.save_photos(1, [
            {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg"},
            {"file_path": "photos/1/bbbb1111-2222-3333-4444-555566667777.jpg"},
        ])
        photo_repo.save_photos(2, [
            {"file_path": "photos/2/cccc1111-2222-3333-4444-555566667777.jpg"},
        ])
        counts = photo_repo.batch_get_photo_counts([1, 2])
        assert counts[1] == 2
        assert counts[2] == 1

    def test_batch_counts_empty_listing_returns_zero(self, photo_repo):
        counts = photo_repo.batch_get_photo_counts([1, 2])
        assert counts[1] == 0
        assert counts[2] == 0

    def test_batch_counts_empty_list(self, photo_repo):
        counts = photo_repo.batch_get_photo_counts([])
        assert counts == {}

    def test_single_photo_count(self, photo_repo):
        photo_repo.save_photos(1, [
            {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg"},
        ])
        assert photo_repo.get_photo_count(1) == 1
        assert photo_repo.get_photo_count(2) == 0


class TestAnalysis:
    def test_save_and_get_analysis(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
        ])
        analysis_data = {"condition": "good", "features": ["granite counters", "stainless appliances"]}
        photo_repo.save_analysis(inserted_ids[0], analysis_data)
        result = photo_repo.get_analysis(inserted_ids[0])
        assert result == analysis_data

    def test_get_analysis_no_data_returns_none(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
        ])
        assert photo_repo.get_analysis(inserted_ids[0]) is None

    def test_get_analysis_nonexistent_photo_returns_none(self, photo_repo):
        assert photo_repo.get_analysis(999) is None

    def test_analysis_visible_in_list_photos(self, photo_repo):
        inserted_ids = photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
        ])
        photo_repo.save_analysis(inserted_ids[0], {"score": 8.5})
        photos = photo_repo.list_photos(1)
        assert photos[0]["ai_analysis"] == {"score": 8.5}
