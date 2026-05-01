"""Repository for apartment listings — CRUD operations."""

import json
import sqlite3


class ApartmentListingRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def save_listing(self, **fields) -> int:
        """Insert a new apartment listing."""
        amenities_json = json.dumps(fields.get("amenities") or [])
        parsed_data_json = json.dumps(fields.get("parsed_data") or {})
        cursor = self._connection.execute(
            """INSERT INTO apartment_listings
               (title, address, price, bedrooms, bathrooms, sqft,
                source, source_url, amenities, parsed_data, match_score, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fields.get("title", ""),
                fields.get("address"),
                fields.get("price"),
                fields.get("bedrooms"),
                fields.get("bathrooms"),
                fields.get("sqft"),
                fields.get("source"),
                fields.get("source_url"),
                amenities_json,
                parsed_data_json,
                fields.get("match_score"),
                fields.get("latitude"),
                fields.get("longitude"),
            ),
        )
        self._connection.commit()
        return cursor.lastrowid

    def get_listing(self, listing_id: int) -> dict | None:
        """Get a single listing by ID."""
        row = self._connection.execute(
            "SELECT * FROM apartment_listings WHERE id = ?", (listing_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        if isinstance(result.get("amenities"), str):
            result["amenities"] = json.loads(result["amenities"])
        if isinstance(result.get("parsed_data"), str):
            result["parsed_data"] = json.loads(result["parsed_data"])
        return result

    def list_listings(self, saved_only: bool = False) -> list[dict]:
        """List all listings, optionally filtered to saved/shortlisted."""
        if saved_only:
            rows = self._connection.execute(
                "SELECT * FROM apartment_listings WHERE is_saved = 1 ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM apartment_listings ORDER BY created_at DESC"
            ).fetchall()

        listings = []
        for row in rows:
            listing = dict(row)
            if isinstance(listing.get("amenities"), str):
                listing["amenities"] = json.loads(listing["amenities"])
            if isinstance(listing.get("parsed_data"), str):
                listing["parsed_data"] = json.loads(listing["parsed_data"])
            listings.append(listing)
        return listings

    def save_to_shortlist(self, listing_id: int) -> None:
        """Mark a listing as saved/shortlisted."""
        self._connection.execute(
            "UPDATE apartment_listings SET is_saved = 1 WHERE id = ?", (listing_id,)
        )
        self._connection.commit()

    def remove_from_shortlist(self, listing_id: int) -> None:
        """Remove a listing from the shortlist."""
        self._connection.execute(
            "UPDATE apartment_listings SET is_saved = 0 WHERE id = ?", (listing_id,)
        )
        self._connection.commit()

    def delete_listing(self, listing_id: int) -> None:
        """Delete a listing and all related data."""
        self._connection.execute("DELETE FROM apartment_notes WHERE listing_id = ?", (listing_id,))
        self._connection.execute("DELETE FROM apartment_neighborhood WHERE listing_id = ?", (listing_id,))
        self._connection.execute("DELETE FROM apartment_cost WHERE listing_id = ?", (listing_id,))
        self._connection.execute("DELETE FROM apartment_floor_plans WHERE listing_id = ?", (listing_id,))
        self._connection.execute("DELETE FROM apartment_notifications WHERE listing_id = ?", (listing_id,))
        self._connection.execute("DELETE FROM apartment_listings WHERE id = ?", (listing_id,))
        self._connection.commit()
