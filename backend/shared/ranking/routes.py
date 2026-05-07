"""Ranking API routes — interaction tracking and weight debugging.

POST /api/ranking/interact — fire-and-forget behavioral tracking
GET  /api/ranking/profile/{agent} — current learned terms (debugging only)
"""

import sqlite3

from fastapi import APIRouter

from shared.ranking.learning_machine import record_interaction, get_learned_weights
from shared.ranking.term_extractor import extract_job_terms, extract_apartment_terms


def create_ranking_router(connection: sqlite3.Connection) -> APIRouter:
    """Create ranking routes. Called from main.py lifespan."""
    router = APIRouter(prefix="/api/ranking")

    @router.post("/interact")
    def track_interaction(data: dict):
        """Record a user interaction for ranking learning.

        Fire-and-forget — frontend doesn't wait for response.
        Body: {agent, entity_id, interaction_type, terms, duration_seconds}
        """
        agent = data.get("agent")
        entity_id = data.get("entity_id")
        interaction_type = data.get("interaction_type")
        terms = data.get("terms") or []

        if not agent or not entity_id or not interaction_type:
            return {"status": "skipped", "reason": "missing required fields"}

        valid_types = {"click", "save", "apply", "skip", "rate_good", "rate_partial", "rate_poor"}
        if interaction_type not in valid_types:
            return {"status": "skipped", "reason": f"invalid type: {interaction_type}"}

        # If no terms provided, try to extract from entity
        if not terms:
            terms = _extract_terms_for_entity(agent, entity_id, connection)

        interaction_id = record_interaction(
            connection=connection,
            profile_id=None,  # TODO: multi-user support
            agent=agent,
            entity_id=entity_id,
            interaction_type=interaction_type,
            terms=terms,
            duration_seconds=data.get("duration_seconds"),
        )

        return {"status": "recorded", "interaction_id": interaction_id}

    @router.get("/profile/{agent}")
    def get_ranking_profile(agent: str):
        """Get current learned term weights — for debugging/transparency."""
        weights = get_learned_weights(connection, profile_id=None, agent=agent)
        if not weights:
            return {"agent": agent, "status": "cold_start", "terms": {}, "count": 0}

        # Sort by weight descending, show top positive and negative
        sorted_terms = sorted(weights.items(), key=lambda pair: pair[1], reverse=True)
        top_positive = [(term, round(weight, 2)) for term, weight in sorted_terms[:15] if weight > 0]
        top_negative = [(term, round(weight, 2)) for term, weight in sorted_terms if weight < 0][-10:]

        return {
            "agent": agent,
            "status": "active",
            "total_terms": len(weights),
            "top_positive": top_positive,
            "top_negative": top_negative,
        }

    return router


def _extract_terms_for_entity(agent: str, entity_id: int, connection: sqlite3.Connection) -> list[str]:
    """Fallback: extract terms from the entity if frontend didn't send them."""
    try:
        if agent == "job":
            row = connection.execute(
                "SELECT title, company, parsed_data, source_url FROM jobs WHERE id = ?",
                (entity_id,),
            ).fetchone()
            if row:
                import json
                parsed = json.loads(row["parsed_data"]) if isinstance(row["parsed_data"], str) else (row["parsed_data"] or {})
                return extract_job_terms({
                    "title": row["title"],
                    "company": row["company"],
                    "description": parsed.get("description", ""),
                    "location": parsed.get("location", ""),
                    "salary": parsed.get("salary"),
                })
        elif agent == "apartment":
            row = connection.execute(
                "SELECT title, address, price, bedrooms, bathrooms, amenities FROM apartment_listings WHERE id = ?",
                (entity_id,),
            ).fetchone()
            if row:
                import json
                amenities = json.loads(row["amenities"]) if isinstance(row["amenities"], str) else (row["amenities"] or [])
                return extract_apartment_terms({
                    "title": row["title"],
                    "address": row["address"],
                    "price": row["price"],
                    "bedrooms": row["bedrooms"],
                    "bathrooms": row["bathrooms"],
                    "amenities": amenities,
                })
    except Exception:
        pass
    return []
