"""Ranking API routes — interaction tracking and weight debugging.

POST /api/ranking/interact — fire-and-forget behavioral tracking
GET  /api/ranking/profile/{agent} — current learned terms (debugging only)
"""

import json
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.app_logger import get_logger
from shared.ranking.learning_machine import record_interaction, get_learned_weights
from shared.ranking.term_extractor import extract_job_terms, extract_apartment_terms

logger = get_logger("ranking.routes")

VALID_INTERACTION_TYPES = frozenset({
    "click", "save", "apply", "skip",
    "rate_good", "rate_partial", "rate_poor",
})
VALID_AGENTS = frozenset({"job", "apartment"})


class InteractionRequest(BaseModel):
    """Validated request body for interaction tracking."""
    agent: str
    entity_id: int
    interaction_type: str
    terms: list[str] = Field(default_factory=list)
    duration_seconds: int | None = Field(default=None, ge=0, le=3600)


def create_ranking_router(connection: sqlite3.Connection) -> APIRouter:
    """Create ranking routes. Called from main.py lifespan."""
    router = APIRouter(prefix="/api/ranking")

    @router.post("/interact")
    def track_interaction(request_body: InteractionRequest):
        """Record a user interaction for ranking learning.

        Fire-and-forget — frontend doesn't wait for response.
        """
        if request_body.agent not in VALID_AGENTS:
            raise HTTPException(400, detail=f"Invalid agent: {request_body.agent}")
        if request_body.interaction_type not in VALID_INTERACTION_TYPES:
            raise HTTPException(400, detail=f"Invalid interaction type: {request_body.interaction_type}")

        terms = request_body.terms
        if not terms:
            terms = _extract_terms_for_entity(request_body.agent, request_body.entity_id, connection)

        interaction_id = record_interaction(
            connection=connection,
            profile_id=None,
            agent=request_body.agent,
            entity_id=request_body.entity_id,
            interaction_type=request_body.interaction_type,
            terms=terms,
            duration_seconds=request_body.duration_seconds,
        )

        return {"status": "recorded", "interaction_id": interaction_id}

    @router.get("/profile/{agent}")
    def get_ranking_profile(agent: str):
        """Get current learned term weights — for debugging/transparency."""
        if agent not in VALID_AGENTS:
            raise HTTPException(400, detail=f"Invalid agent: {agent}")

        weights = get_learned_weights(connection, profile_id=None, agent=agent)
        if not weights:
            return {"agent": agent, "status": "cold_start", "terms": {}, "count": 0}

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
                amenities = json.loads(row["amenities"]) if isinstance(row["amenities"], str) else (row["amenities"] or [])
                return extract_apartment_terms({
                    "title": row["title"],
                    "address": row["address"],
                    "price": row["price"],
                    "bedrooms": row["bedrooms"],
                    "bathrooms": row["bathrooms"],
                    "amenities": amenities,
                })
    except Exception as extraction_error:
        logger.warning("Failed to extract terms for %s/%d: %s", agent, entity_id, extraction_error)
    return []
