"""Intel repository — CRUD for apartment_intel table.

Stores per-listing, per-type Intel results (unit details, verified scores,
floor plan analysis, concessions, reviews). UPSERT semantics — re-gathering
overwrites previous results for the same listing + type.
"""

import json
import sqlite3
from datetime import datetime, timedelta


VALID_INTEL_TYPES = frozenset({
    "unit_details",
    "verified_scores",
    "distances",
    "floor_plan_analysis",
    "concessions",
    "reviews",
    "nearby_places",
    "policies",
})


class IntelRepository:
    """Data access for the apartment_intel table."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def save_intel(
        self,
        listing_id: int,
        intel_type: str,
        result: dict,
        source_api: str | None = None,
        estimated_cost: float | None = None,
        actual_cost: float | None = None,
    ) -> int:
        """Save or update an Intel result. Returns the row ID."""
        if intel_type not in VALID_INTEL_TYPES:
            raise ValueError(f"Invalid intel_type '{intel_type}'. Must be one of: {', '.join(sorted(VALID_INTEL_TYPES))}")

        cursor = self._connection.execute(
            """INSERT INTO apartment_intel
               (listing_id, intel_type, result, source_api, estimated_cost, actual_cost, created_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(listing_id, intel_type) DO UPDATE SET
                   result = excluded.result,
                   source_api = excluded.source_api,
                   estimated_cost = excluded.estimated_cost,
                   actual_cost = excluded.actual_cost,
                   created_at = datetime('now')""",
            (listing_id, intel_type, json.dumps(result), source_api, estimated_cost, actual_cost),
        )
        self._connection.commit()
        return cursor.lastrowid

    def get_intel(self, listing_id: int, intel_type: str) -> dict | None:
        """Get a single Intel result by type. Returns None if not found."""
        row = self._connection.execute(
            "SELECT result, source_api, estimated_cost, actual_cost, created_at "
            "FROM apartment_intel WHERE listing_id = ? AND intel_type = ?",
            (listing_id, intel_type),
        ).fetchone()
        if not row:
            return None
        return {
            "intel_type": intel_type,
            "result": json.loads(row["result"]),
            "source_api": row["source_api"],
            "estimated_cost": row["estimated_cost"],
            "actual_cost": row["actual_cost"],
            "created_at": row["created_at"],
        }

    def get_all_intel(self, listing_id: int) -> dict[str, dict]:
        """Get all Intel results for a listing, keyed by intel_type."""
        rows = self._connection.execute(
            "SELECT intel_type, result, source_api, estimated_cost, actual_cost, created_at "
            "FROM apartment_intel WHERE listing_id = ? ORDER BY created_at",
            (listing_id,),
        ).fetchall()
        return {
            row["intel_type"]: {
                "result": json.loads(row["result"]),
                "source_api": row["source_api"],
                "estimated_cost": row["estimated_cost"],
                "actual_cost": row["actual_cost"],
                "created_at": row["created_at"],
            }
            for row in rows
        }

    def has_intel(self, listing_id: int) -> bool:
        """Check if any Intel data exists for this listing."""
        row = self._connection.execute(
            "SELECT 1 FROM apartment_intel WHERE listing_id = ? LIMIT 1",
            (listing_id,),
        ).fetchone()
        return row is not None

    def get_intel_gathered_ids(self) -> list[int]:
        """Return listing IDs that have any Intel data — for badge display."""
        rows = self._connection.execute(
            "SELECT DISTINCT listing_id FROM apartment_intel"
        ).fetchall()
        return [row["listing_id"] for row in rows]

    def get_total_cost_for_listing(self, listing_id: int) -> float:
        """Sum of actual_cost for all Intel results on a listing."""
        row = self._connection.execute(
            "SELECT COALESCE(SUM(actual_cost), 0) as total "
            "FROM apartment_intel WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        return row["total"]

    def get_daily_spend(self) -> float:
        """Sum of actual_cost for all Intel results gathered today."""
        row = self._connection.execute(
            "SELECT COALESCE(SUM(actual_cost), 0) as total "
            "FROM apartment_intel WHERE date(created_at) = date('now')"
        ).fetchone()
        return row["total"]

    def get_snapshots_for_listings(self, listing_ids: list[int]) -> dict[int, dict]:
        """Get lightweight Intel snapshots for multiple listings in one query.

        Returns {listing_id: {intel_type: result_dict}} for each listing that has Intel.
        """
        if not listing_ids:
            return {}

        placeholders = ",".join("?" for _ in listing_ids)
        rows = self._connection.execute(
            f"SELECT listing_id, intel_type, result FROM apartment_intel "
            f"WHERE listing_id IN ({placeholders}) ORDER BY listing_id",
            listing_ids,
        ).fetchall()

        snapshots: dict[int, dict] = {}
        for row in rows:
            listing_id = row["listing_id"]
            if listing_id not in snapshots:
                snapshots[listing_id] = {}
            snapshots[listing_id][row["intel_type"]] = json.loads(row["result"])

        return snapshots

    def delete_intel(self, listing_id: int, intel_type: str | None = None) -> int:
        """Delete Intel results. If intel_type is None, deletes all for the listing."""
        if intel_type:
            cursor = self._connection.execute(
                "DELETE FROM apartment_intel WHERE listing_id = ? AND intel_type = ?",
                (listing_id, intel_type),
            )
        else:
            cursor = self._connection.execute(
                "DELETE FROM apartment_intel WHERE listing_id = ?",
                (listing_id,),
            )
        self._connection.commit()
        return cursor.rowcount
