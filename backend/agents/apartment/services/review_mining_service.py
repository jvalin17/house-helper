"""Review mining service — fetch Google Places reviews + LLM sentiment analysis.

Uses Google Places API (Text Search → Place Details) to find the property
and retrieve resident reviews. Then sends reviews to LLM for structured
sentiment extraction.

Requires:
  - Google Maps API key (same key works for Places)
  - Places API enabled in Google Cloud Console
  - LLM provider for sentiment analysis
"""

import sqlite3

import httpx

from shared.app_logger import get_logger
from shared.credentials import CredentialStore
from shared.pipeline import parse_llm_json_response
from agents.apartment.prompts.review_sentiment import (
    build_review_sentiment_prompt,
    SYSTEM_PROMPT,
)

logger = get_logger("apartment.review_mining")

GOOGLE_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

PLACES_API_TIMEOUT = 15.0


def fetch_and_analyze_reviews(
    listing_id: int,
    connection: sqlite3.Connection,
    llm_provider=None,
) -> dict | None:
    """Fetch Google Places reviews for a property and analyze sentiment.

    Two-step process:
    1. Find the place via Text Search (property name + address)
    2. Get reviews via Place Details

    Returns structured sentiment analysis or None if unavailable.
    """
    api_key = CredentialStore(connection).get_key("google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping review mining")
        return None

    # Get listing details for search query
    listing_row = connection.execute(
        "SELECT title, address FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not listing_row:
        return None

    property_name = listing_row["title"] or ""
    address = listing_row["address"] or ""

    if not property_name and not address:
        logger.info("No property name or address for listing %d — skipping reviews", listing_id)
        return None

    # Step 1: Find the place
    place_id = _find_place_id(property_name, address, api_key)
    if not place_id:
        logger.info("Could not find Google Places entry for '%s'", property_name)
        return {"place_not_found": True, "property_name": property_name}

    # Step 2: Get reviews
    place_details = _get_place_details(place_id, api_key)
    if not place_details:
        return {"place_found": True, "no_reviews": True, "property_name": property_name}

    reviews = place_details.get("reviews") or []
    if not reviews:
        return {
            "place_found": True,
            "no_reviews": True,
            "property_name": property_name,
            "google_rating": place_details.get("rating"),
            "total_ratings": place_details.get("user_ratings_total"),
        }

    # Build raw review data (always returned, even without LLM)
    raw_review_data = {
        "property_name": property_name,
        "google_rating": place_details.get("rating"),
        "total_ratings": place_details.get("user_ratings_total"),
        "review_count": len(reviews),
        "reviews": [
            {
                "author_name": review.get("author_name"),
                "rating": review.get("rating"),
                "text": review.get("text"),
                "relative_time_description": review.get("relative_time_description"),
                "time": review.get("time"),
            }
            for review in reviews
        ],
    }

    # Step 3: LLM sentiment analysis (if available)
    if llm_provider and llm_provider.is_configured():
        sentiment_analysis = _analyze_sentiment(reviews, property_name, llm_provider, len(reviews))
        if sentiment_analysis:
            raw_review_data["sentiment"] = sentiment_analysis

    return raw_review_data


def _find_place_id(property_name: str, address: str, api_key: str) -> str | None:
    """Find Google Places ID for the property using Text Search."""
    search_query = f"{property_name} {address}".strip()

    try:
        response = httpx.get(
            GOOGLE_PLACES_SEARCH_URL,
            params={
                "input": search_query,
                "inputtype": "textquery",
                "fields": "place_id,name,formatted_address",
                "key": api_key,
            },
            timeout=PLACES_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            logger.warning("Places Search returned status: %s", data.get("status"))
            return None

        candidates = data.get("candidates") or []
        if not candidates:
            return None

        return candidates[0].get("place_id")

    except Exception as search_error:
        logger.error("Google Places search failed: %s", search_error)
        return None


def _get_place_details(place_id: str, api_key: str) -> dict | None:
    """Get place details including reviews from Google Places API."""
    try:
        response = httpx.get(
            GOOGLE_PLACE_DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": "name,rating,user_ratings_total,reviews",
                "key": api_key,
            },
            timeout=PLACES_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            logger.warning("Place Details returned status: %s", data.get("status"))
            return None

        return data.get("result")

    except Exception as details_error:
        logger.error("Google Place Details failed: %s", details_error)
        return None


def _analyze_sentiment(
    reviews: list[dict],
    property_name: str,
    llm_provider,
    total_review_count: int,
) -> dict | None:
    """Run LLM sentiment analysis on the reviews."""
    prompt = build_review_sentiment_prompt(
        reviews=reviews,
        property_name=property_name,
        review_count=total_review_count,
    )

    try:
        response = llm_provider.complete(
            prompt,
            system=SYSTEM_PROMPT,
            feature="intel_reviews",
        )
        return parse_llm_json_response(response)

    except Exception as analysis_error:
        logger.error("Review sentiment analysis failed: %s", analysis_error)
        return None
