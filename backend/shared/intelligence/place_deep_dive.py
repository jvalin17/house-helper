"""Place deep-dive — fetch Google Place Details + reviews for top places.

Takes discovered places, fetches reviews for each, mines customer words
for truth (not Google categories). Newest 20% of reviews per place.

Reusable: apartment, travel, any location-aware agent.
"""

import math
import sqlite3

import httpx

from shared.app_logger import get_logger
from shared.credentials import CredentialStore
from shared.intelligence.place_cache import (
    has_reviews_cached,
    update_place_reviews,
    get_cached_place_by_id,
)

logger = get_logger("intelligence.place_deep_dive")

GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_API_TIMEOUT = 15.0
MIN_REVIEWS_PER_PLACE = 1
MAX_REVIEWS_PER_PLACE = 5
REVIEW_PERCENTAGE = 0.20  # Newest 20%


def enrich_places_with_reviews(
    places: list[dict],
    connection: sqlite3.Connection,
    max_detail_calls: int = 20,
) -> list[dict]:
    """Fetch reviews for places that don't have them cached.

    For each place:
    1. Check cache — if reviews exist, use them
    2. If not cached, call Google Place Details API
    3. Take newest 20% of reviews (min 1, max 5)
    4. Cache the reviews (encrypted)

    Returns enriched places list with customer_reviews populated.
    """
    api_key = CredentialStore(connection).get_key("google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping review deep-dive")
        return places

    enriched_places = []
    api_calls_made = 0

    for place in places:
        place_id = place.get("place_id")
        if not place_id:
            enriched_places.append(place)
            continue

        # Check if reviews already cached
        if has_reviews_cached(place_id, connection):
            cached_place = get_cached_place_by_id(place_id, connection)
            if cached_place:
                place["customer_reviews"] = cached_place["customer_reviews"]
                enriched_places.append(place)
                continue

        # Fetch from Google Place Details
        if api_calls_made >= max_detail_calls:
            enriched_places.append(place)
            continue

        reviews = _fetch_place_reviews(place_id, api_key)
        api_calls_made += 1

        if reviews:
            # Take newest 20% (sorted by time, newest first)
            selected_reviews = _select_newest_reviews(reviews)
            review_texts = [review.get("text", "") for review in selected_reviews if review.get("text")]
            place["customer_reviews"] = review_texts

            # Cache the reviews
            update_place_reviews(place_id, review_texts, connection)
        else:
            place["customer_reviews"] = []

        enriched_places.append(place)

    logger.info(
        "Deep-dive complete: %d places enriched, %d API calls",
        len(enriched_places), api_calls_made,
    )
    return enriched_places


def _fetch_place_reviews(place_id: str, api_key: str) -> list[dict]:
    """Fetch reviews from Google Place Details API."""
    try:
        response = httpx.get(
            GOOGLE_PLACE_DETAILS_URL,
            params={
                "place_id": place_id,
                "fields": "reviews",
                "reviews_sort": "newest",
                "key": api_key,
            },
            timeout=PLACES_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            logger.warning("Place Details status: %s for %s", data.get("status"), place_id)
            return []

        result = data.get("result") or {}
        return result.get("reviews") or []

    except Exception as detail_error:
        logger.error("Place Details failed for %s: %s", place_id, detail_error)
        return []


def _select_newest_reviews(reviews: list[dict]) -> list[dict]:
    """Select newest 20% of reviews. Min 1, max 5.

    Google returns reviews sorted by relevance by default.
    We request sorted by newest, then take the top 20%.
    """
    if not reviews:
        return []

    total_review_count = len(reviews)
    target_count = max(
        MIN_REVIEWS_PER_PLACE,
        min(MAX_REVIEWS_PER_PLACE, math.ceil(total_review_count * REVIEW_PERCENTAGE)),
    )

    # Reviews should already be sorted newest first (reviews_sort=newest)
    # But sort by time as fallback
    sorted_reviews = sorted(
        reviews,
        key=lambda review_entry: review_entry.get("time", 0),
        reverse=True,
    )

    return sorted_reviews[:target_count]
