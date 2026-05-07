"""Repository for cached Nest Lab LLM analysis results.

Caches analysis per listing+type with 24-hour TTL.
Types: 'overview', 'price_verdict', 'floor_plan', 'neighborhood'.
"""

import json
import sqlite3

CACHE_TTL_HOURS = 24


class LabAnalysisRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_cached_analysis(self, listing_id: int, analysis_type: str) -> dict | None:
        """Get cached analysis if it exists and is fresh (< 24h old)."""
        row = self._connection.execute(
            """SELECT result, created_at FROM apartment_lab_analysis
               WHERE listing_id = ? AND analysis_type = ?
               AND created_at > datetime('now', ?)""",
            (listing_id, analysis_type, f"-{CACHE_TTL_HOURS} hours"),
        ).fetchone()
        if not row:
            return None
        result = row["result"]
        if isinstance(result, str):
            return json.loads(result)
        return result

    def save_analysis(
        self,
        listing_id: int,
        analysis_type: str,
        result: dict,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        estimated_cost: float | None = None,
    ) -> int:
        """Save or replace analysis result for a listing."""
        cursor = self._connection.execute(
            """INSERT INTO apartment_lab_analysis
               (listing_id, analysis_type, result, prompt_tokens, completion_tokens, estimated_cost)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(listing_id, analysis_type) DO UPDATE SET
                 result = excluded.result,
                 prompt_tokens = excluded.prompt_tokens,
                 completion_tokens = excluded.completion_tokens,
                 estimated_cost = excluded.estimated_cost,
                 created_at = datetime('now')""",
            (listing_id, analysis_type, json.dumps(result), prompt_tokens, completion_tokens, estimated_cost),
        )
        self._connection.commit()
        return cursor.lastrowid

    def get_all_for_listing(self, listing_id: int) -> dict[str, dict]:
        """Get all cached analyses for a listing (fresh only)."""
        rows = self._connection.execute(
            """SELECT analysis_type, result FROM apartment_lab_analysis
               WHERE listing_id = ? AND created_at > datetime('now', ?)""",
            (listing_id, f"-{CACHE_TTL_HOURS} hours"),
        ).fetchall()
        analyses = {}
        for row in rows:
            result = row["result"]
            if isinstance(result, str):
                result = json.loads(result)
            analyses[row["analysis_type"]] = result
        return analyses

    def invalidate(self, listing_id: int) -> None:
        """Delete all cached analyses for a listing (force re-analysis)."""
        self._connection.execute(
            "DELETE FROM apartment_lab_analysis WHERE listing_id = ?",
            (listing_id,),
        )
        self._connection.commit()
