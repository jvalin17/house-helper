"""Repository for apartment listings — CRUD operations."""

import json
import sqlite3


class ApartmentListingRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def save_listing(self, **fields) -> int:
        """Insert a new apartment listing, or return existing ID if duplicate.

        Dedup: matches by source_url (if present) or by title+address+price.
        """
        source_url = fields.get("source_url") or ""
        title = fields.get("title", "")
        address = fields.get("address")
        price = fields.get("price")

        # Check for existing listing by source_url
        if source_url:
            existing = self._connection.execute(
                "SELECT id FROM apartment_listings WHERE source_url = ? AND source_url != ''",
                (source_url,),
            ).fetchone()
            if existing:
                return existing["id"]

        # Check for existing listing by title + address + price
        if title and address:
            existing = self._connection.execute(
                "SELECT id FROM apartment_listings WHERE title = ? AND address = ? AND price = ?",
                (title, address, price),
            ).fetchone()
            if existing:
                return existing["id"]

        amenities_json = json.dumps(fields.get("amenities") or [])
        # Merge images into parsed_data so they're accessible later
        parsed_data = fields.get("parsed_data") or {}
        if isinstance(parsed_data, str):
            parsed_data = json.loads(parsed_data)
        if fields.get("images") and "images" not in parsed_data:
            parsed_data["images"] = fields["images"]
        parsed_data_json = json.dumps(parsed_data)
        cursor = self._connection.execute(
            """INSERT INTO apartment_listings
               (title, address, price, bedrooms, bathrooms, sqft,
                source, source_url, amenities, parsed_data, match_score, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title,
                address,
                price,
                fields.get("bedrooms"),
                fields.get("bathrooms"),
                fields.get("sqft"),
                fields.get("source"),
                source_url,
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
        parsed = result.get("parsed_data") or {}
        result["images"] = parsed.get("images") or parsed.get("photoUrls") or []
        return result

    def list_listings(self, saved_only: bool = False) -> list[dict]:
        """List all listings, optionally filtered to saved/shortlisted.

        Returns parsed_data stripped down — only images extracted, rest omitted
        to keep the response lightweight (parsed_data can be megabytes).
        """
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
            # Extract images from parsed_data, then drop it to save bandwidth
            parsed = {}
            if isinstance(listing.get("parsed_data"), str):
                try:
                    parsed = json.loads(listing["parsed_data"])
                except (json.JSONDecodeError, TypeError):
                    pass
            listing["images"] = parsed.get("images") or parsed.get("photoUrls") or []
            del listing["parsed_data"]
            listings.append(listing)
        return listings

    def find_comparables(self, city: str, exclude_listing_id: int, limit: int = 10) -> list[dict]:
        """Find comparable listings in the same city — SQL-level filtering."""
        rows = self._connection.execute(
            "SELECT id, title, address, price, bedrooms, bathrooms, sqft "
            "FROM apartment_listings "
            "WHERE address LIKE ? AND id != ? AND price IS NOT NULL "
            "ORDER BY price LIMIT ?",
            (f"%{city}%", exclude_listing_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

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
