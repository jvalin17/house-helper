"""Repository for apartment visit photos — upload, tag, and analyze."""

import json
import re
import sqlite3

VALID_FILE_PATH_PATTERN = re.compile(r"^photos/\d+/[a-f0-9\-]+\.(jpg|jpeg|png|webp)$")
VALID_ROOM_TAGS = {"kitchen", "bedroom", "bathroom", "living", "exterior", "other"}


class PhotoRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def save_photos(self, listing_id: int, photos: list[dict]) -> list[int]:
        """Batch insert photos for a listing. Returns list of new photo IDs.

        Each photo dict must have 'file_path' and optionally 'label', 'room_tag', 'display_order'.
        Validates file_path against safe pattern and room_tag against whitelist.
        """
        inserted_ids = []
        for photo in photos:
            file_path = photo.get("file_path", "")
            if not VALID_FILE_PATH_PATTERN.match(file_path):
                raise ValueError(
                    f"Invalid file_path '{file_path}'. "
                    f"Must match pattern: photos/<listing_id>/<uuid>.<ext>"
                )

            room_tag = photo.get("room_tag")
            if room_tag is not None and room_tag not in VALID_ROOM_TAGS:
                raise ValueError(
                    f"Invalid room_tag '{room_tag}'. "
                    f"Must be one of: {', '.join(sorted(VALID_ROOM_TAGS))}"
                )

            cursor = self._connection.execute(
                """INSERT INTO apartment_visit_photos
                   (listing_id, file_path, label, room_tag, display_order)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    listing_id,
                    file_path,
                    photo.get("label"),
                    room_tag,
                    photo.get("display_order", 0),
                ),
            )
            inserted_ids.append(cursor.lastrowid)
        self._connection.commit()
        return inserted_ids

    def list_photos(self, listing_id: int) -> list[dict]:
        """List all photos for a listing, ordered by display_order."""
        rows = self._connection.execute(
            "SELECT * FROM apartment_visit_photos WHERE listing_id = ? ORDER BY display_order",
            (listing_id,),
        ).fetchall()
        results = []
        for row in rows:
            photo = dict(row)
            if isinstance(photo.get("ai_analysis"), str):
                photo["ai_analysis"] = json.loads(photo["ai_analysis"])
            results.append(photo)
        return results

    def get_photo(self, photo_id: int) -> dict | None:
        """Get a single photo by ID."""
        row = self._connection.execute(
            "SELECT * FROM apartment_visit_photos WHERE id = ?",
            (photo_id,),
        ).fetchone()
        if not row:
            return None
        photo = dict(row)
        if isinstance(photo.get("ai_analysis"), str):
            photo["ai_analysis"] = json.loads(photo["ai_analysis"])
        return photo

    def update_photo(self, photo_id: int, **fields) -> None:
        """Partial update of photo fields (label, room_tag, display_order)."""
        allowed_fields = {"label", "room_tag", "display_order"}
        update_parts = []
        update_values = []

        for field_name, field_value in fields.items():
            if field_name not in allowed_fields:
                continue
            if field_name == "room_tag" and field_value is not None and field_value not in VALID_ROOM_TAGS:
                raise ValueError(
                    f"Invalid room_tag '{field_value}'. "
                    f"Must be one of: {', '.join(sorted(VALID_ROOM_TAGS))}"
                )
            update_parts.append(f"{field_name} = ?")
            update_values.append(field_value)

        if not update_parts:
            return

        update_values.append(photo_id)
        self._connection.execute(
            f"UPDATE apartment_visit_photos SET {', '.join(update_parts)} WHERE id = ?",
            update_values,
        )
        self._connection.commit()

    def delete_photo(self, photo_id: int) -> str | None:
        """Delete a photo. Returns file_path for disk cleanup, or None if not found."""
        row = self._connection.execute(
            "SELECT file_path FROM apartment_visit_photos WHERE id = ?",
            (photo_id,),
        ).fetchone()
        if not row:
            return None
        file_path = row["file_path"]
        self._connection.execute(
            "DELETE FROM apartment_visit_photos WHERE id = ?",
            (photo_id,),
        )
        self._connection.commit()
        return file_path

    def get_photo_count(self, listing_id: int) -> int:
        """Get total photo count for a single listing."""
        row = self._connection.execute(
            "SELECT COUNT(*) as count FROM apartment_visit_photos WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        return row["count"]

    def batch_get_photo_counts(self, listing_ids: list[int]) -> dict[int, int]:
        """Get photo counts for multiple listings in a single query (no N+1)."""
        if not listing_ids:
            return {}
        placeholders = ",".join("?" for _ in listing_ids)
        rows = self._connection.execute(
            f"SELECT listing_id, COUNT(*) as count "
            f"FROM apartment_visit_photos "
            f"WHERE listing_id IN ({placeholders}) "
            f"GROUP BY listing_id",
            listing_ids,
        ).fetchall()
        counts = {row["listing_id"]: row["count"] for row in rows}
        # Fill in zeros for listings with no photos
        for listing_id in listing_ids:
            if listing_id not in counts:
                counts[listing_id] = 0
        return counts

    def save_analysis(self, photo_id: int, analysis: dict) -> None:
        """Save AI analysis results to a photo's ai_analysis column."""
        self._connection.execute(
            "UPDATE apartment_visit_photos SET ai_analysis = ? WHERE id = ?",
            (json.dumps(analysis), photo_id),
        )
        self._connection.commit()

    def get_analysis(self, photo_id: int) -> dict | None:
        """Get AI analysis for a photo."""
        row = self._connection.execute(
            "SELECT ai_analysis FROM apartment_visit_photos WHERE id = ?",
            (photo_id,),
        ).fetchone()
        if not row or not row["ai_analysis"]:
            return None
        if isinstance(row["ai_analysis"], str):
            return json.loads(row["ai_analysis"])
        return row["ai_analysis"]
