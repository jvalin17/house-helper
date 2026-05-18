"""Dashboard service for the NestScout apartment hunting funnel.

Aggregates data from listings, notes, costs, and photos into a
stage-based funnel view with achievements and statistics.
"""

import sqlite3
from datetime import datetime

from agents.apartment.repositories.cost_repo import CostRepository
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.photo_repo import PhotoRepository


STAGE_ORDER = ["interested", "visited", "applied", "approved", "moved_in"]

ACHIEVEMENTS = [
    {
        "id": "explorer",
        "name": "Explorer",
        "description": "Visit your first apartment",
        "icon": "compass",
        "threshold_stage": "visited",
        "threshold_count": 1,
    },
    {
        "id": "scout",
        "name": "Scout",
        "description": "Visit 5 apartments",
        "icon": "binoculars",
        "threshold_stage": "visited",
        "threshold_count": 5,
    },
    {
        "id": "applicant",
        "name": "First Application",
        "description": "Submit your first application",
        "icon": "file-text",
        "threshold_stage": "applied",
        "threshold_count": 1,
    },
    {
        "id": "contender",
        "name": "Contender",
        "description": "Apply to 3 apartments",
        "icon": "target",
        "threshold_stage": "applied",
        "threshold_count": 3,
    },
    {
        "id": "approved",
        "name": "Approved",
        "description": "Get your first approval",
        "icon": "check-circle",
        "threshold_stage": "approved",
        "threshold_count": 1,
    },
    {
        "id": "home_sweet_home",
        "name": "Home Sweet Home",
        "description": "Move into your new apartment",
        "icon": "home",
        "threshold_stage": "moved_in",
        "threshold_count": 1,
    },
    {
        "id": "photographer",
        "name": "Photographer",
        "description": "Upload 10 visit photos",
        "icon": "camera",
        "threshold_type": "photos",
        "threshold_count": 10,
    },
]


class DashboardService:
    def __init__(
        self,
        connection: sqlite3.Connection,
        listing_repo: ApartmentListingRepository,
        cost_repo: CostRepository,
        photo_repo: PhotoRepository,
    ):
        self._connection = connection
        self._listing_repo = listing_repo
        self._cost_repo = cost_repo
        self._photo_repo = photo_repo

    def get_funnel(self) -> dict:
        """Build the stage-based funnel with card data for each listing.

        Uses 4 batch queries to avoid N+1:
        1. All saved listings
        2. Latest status per listing from apartment_notes
        3. Cost breakdowns
        4. Photo counts
        """
        saved_listings = self._listing_repo.list_listings(saved_only=True)
        if not saved_listings:
            return {
                "stages": {stage: {"count": 0, "listings": []} for stage in STAGE_ORDER},
                "total_saved": 0,
            }

        listing_ids = [listing["id"] for listing in saved_listings]

        # Batch: latest status per listing from apartment_notes
        status_map = self._batch_get_latest_statuses(listing_ids)

        # Batch: cost breakdowns
        cost_map = self._batch_get_costs(listing_ids)

        # Batch: photo counts
        photo_count_map = self._photo_repo.batch_get_photo_counts(listing_ids)

        # Group by stage
        funnel = {stage: [] for stage in STAGE_ORDER}
        for listing in saved_listings:
            listing_id = listing["id"]
            stage = status_map.get(listing_id, "interested")
            if stage not in funnel:
                stage = "interested"

            card = {
                "id": listing_id,
                "title": listing["title"],
                "address": listing.get("address"),
                "price": listing.get("price"),
                "stage": stage,
                "total_monthly": cost_map.get(listing_id, {}).get("total_monthly"),
                "photo_count": photo_count_map.get(listing_id, 0),
            }
            funnel[stage].append(card)

        return {
            "stages": {
                stage: {"count": len(listings), "listings": listings}
                for stage, listings in funnel.items()
            },
            "total_saved": len(saved_listings),
        }

    def get_stats(self) -> dict:
        """Compute dashboard statistics: counts per stage, hunt duration, avg rent."""
        saved_listings = self._listing_repo.list_listings(saved_only=True)
        listing_ids = [listing["id"] for listing in saved_listings]
        status_map = self._batch_get_latest_statuses(listing_ids) if listing_ids else {}

        stage_counts = {stage: 0 for stage in STAGE_ORDER}
        for listing_id in listing_ids:
            stage = status_map.get(listing_id, "interested")
            if stage in stage_counts:
                stage_counts[stage] += 1

        # Hunt duration: days since earliest saved listing
        hunt_duration_days = 0
        if saved_listings:
            earliest_created = min(
                listing.get("created_at", "") for listing in saved_listings
            )
            if earliest_created:
                try:
                    start_date = datetime.fromisoformat(earliest_created)
                    hunt_duration_days = (datetime.now() - start_date).days
                except (ValueError, TypeError):
                    hunt_duration_days = 0

        # Average rent from prices
        prices = [listing["price"] for listing in saved_listings if listing.get("price")]
        average_rent = round(sum(prices) / len(prices), 2) if prices else 0

        return {
            "stage_counts": stage_counts,
            "total_saved": len(saved_listings),
            "hunt_duration_days": hunt_duration_days,
            "average_rent": average_rent,
        }

    def advance_stage(self, listing_id: int) -> dict:
        """Advance a listing to the next stage in the funnel.

        Returns celebration data including any newly unlocked achievements.
        """
        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")
        if not listing.get("is_saved"):
            raise ValueError(f"Listing {listing_id} is not saved/shortlisted")

        current_stage = self._get_latest_status(listing_id)
        current_index = STAGE_ORDER.index(current_stage) if current_stage in STAGE_ORDER else 0

        if current_index >= len(STAGE_ORDER) - 1:
            raise ValueError(
                f"Listing {listing_id} is already at final stage '{STAGE_ORDER[-1]}'"
            )

        next_stage = STAGE_ORDER[current_index + 1]
        self._insert_notes_row(listing_id, next_stage)

        # Check achievements after stage change
        newly_unlocked = self._check_new_achievements(next_stage)

        return {
            "listing_id": listing_id,
            "previous_stage": current_stage,
            "new_stage": next_stage,
            "achievements_unlocked": newly_unlocked,
        }

    def set_stage(self, listing_id: int, stage: str) -> dict:
        """Set a listing to a specific stage."""
        if stage not in STAGE_ORDER:
            raise ValueError(
                f"Invalid stage '{stage}'. Must be one of: {', '.join(STAGE_ORDER)}"
            )

        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")

        previous_stage = self._get_latest_status(listing_id)
        self._insert_notes_row(listing_id, stage)

        newly_unlocked = self._check_new_achievements(stage)

        return {
            "listing_id": listing_id,
            "previous_stage": previous_stage,
            "new_stage": stage,
            "achievements_unlocked": newly_unlocked,
        }

    def get_achievements(self) -> list[dict]:
        """Calculate achievements on-demand from current data."""
        saved_listings = self._listing_repo.list_listings(saved_only=True)
        listing_ids = [listing["id"] for listing in saved_listings]
        status_map = self._batch_get_latest_statuses(listing_ids) if listing_ids else {}

        # Count listings per stage
        stage_counts = {stage: 0 for stage in STAGE_ORDER}
        for listing_id in listing_ids:
            stage = status_map.get(listing_id, "interested")
            if stage in stage_counts:
                stage_counts[stage] += 1
                # Count cumulative: visited also counts for interested threshold, etc.
                stage_index = STAGE_ORDER.index(stage)
                for earlier_stage in STAGE_ORDER[:stage_index]:
                    stage_counts[earlier_stage] += 1

        # Total photos across all listings
        total_photos = sum(
            self._photo_repo.batch_get_photo_counts(listing_ids).values()
        ) if listing_ids else 0

        results = []
        for achievement in ACHIEVEMENTS:
            unlocked = False
            if achievement.get("threshold_type") == "photos":
                unlocked = total_photos >= achievement["threshold_count"]
            elif "threshold_stage" in achievement:
                target_stage = achievement["threshold_stage"]
                unlocked = stage_counts.get(target_stage, 0) >= achievement["threshold_count"]

            results.append({
                "id": achievement["id"],
                "name": achievement["name"],
                "description": achievement["description"],
                "icon": achievement["icon"],
                "unlocked": unlocked,
            })

        return results

    def get_notes(self, listing_id: int) -> dict | None:
        """Get the latest notes row for a listing."""
        row = self._connection.execute(
            "SELECT * FROM apartment_notes WHERE listing_id = ? ORDER BY id DESC LIMIT 1",
            (listing_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        if isinstance(result.get("structured_data"), str):
            import json
            result["structured_data"] = json.loads(result["structured_data"])
        if isinstance(result.get("specials"), str):
            import json
            result["specials"] = json.loads(result["specials"])
        return result

    def save_notes(self, listing_id: int, notes: str, structured_data: dict | None = None) -> dict:
        """Insert a new notes row for a listing (append-only history)."""
        import json

        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")

        current_status = self._get_latest_status(listing_id)
        structured_json = json.dumps(structured_data) if structured_data else None

        cursor = self._connection.execute(
            """INSERT INTO apartment_notes (listing_id, notes, structured_data, status)
               VALUES (?, ?, ?, ?)""",
            (listing_id, notes, structured_json, current_status),
        )
        self._connection.commit()

        return {
            "id": cursor.lastrowid,
            "listing_id": listing_id,
            "notes": notes,
            "structured_data": structured_data,
            "status": current_status,
        }

    def archive_listing(self, listing_id: int) -> dict:
        """Archive a listing by setting is_saved=0."""
        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")

        self._connection.execute(
            "UPDATE apartment_listings SET is_saved = 0 WHERE id = ?",
            (listing_id,),
        )
        self._connection.commit()

        return {
            "listing_id": listing_id,
            "archived": True,
        }

    # -- Private helpers --

    def _batch_get_latest_statuses(self, listing_ids: list[int]) -> dict[int, str]:
        """Get the latest status for each listing from apartment_notes (single query)."""
        if not listing_ids:
            return {}
        placeholders = ",".join("?" for _ in listing_ids)
        rows = self._connection.execute(
            f"""SELECT listing_id, status FROM apartment_notes
                WHERE id IN (
                    SELECT MAX(id) FROM apartment_notes
                    WHERE listing_id IN ({placeholders})
                    GROUP BY listing_id
                )""",
            listing_ids,
        ).fetchall()
        return {row["listing_id"]: row["status"] for row in rows}

    def _get_latest_status(self, listing_id: int) -> str:
        """Get the latest status for a single listing."""
        row = self._connection.execute(
            "SELECT status FROM apartment_notes WHERE listing_id = ? ORDER BY id DESC LIMIT 1",
            (listing_id,),
        ).fetchone()
        return row["status"] if row else "interested"

    def _batch_get_costs(self, listing_ids: list[int]) -> dict[int, dict]:
        """Get cost breakdowns for multiple listings in a single query."""
        if not listing_ids:
            return {}
        placeholders = ",".join("?" for _ in listing_ids)
        rows = self._connection.execute(
            f"SELECT * FROM apartment_cost WHERE listing_id IN ({placeholders})",
            listing_ids,
        ).fetchall()
        return {row["listing_id"]: dict(row) for row in rows}

    def _insert_notes_row(self, listing_id: int, stage: str) -> None:
        """Insert a notes row to record a stage change."""
        now = datetime.now().isoformat()
        self._connection.execute(
            """INSERT INTO apartment_notes (listing_id, status, status_changed_at)
               VALUES (?, ?, ?)""",
            (listing_id, stage, now),
        )
        self._connection.commit()

    def _check_new_achievements(self, new_stage: str) -> list[dict]:
        """Check if advancing to new_stage unlocks any achievements."""
        all_achievements = self.get_achievements()
        return [
            achievement for achievement in all_achievements
            if achievement["unlocked"]
        ]
