"""Place discovery — find nearby places with adaptive rating filter.

Uses Google Places Nearby Search API. Adaptive filter:
  Start at 4★+ → if <20 results, drop to 3★ → 2★ → 1★ → all.
  Always tries to fill to 20 quality places.

Reusable: apartment, travel, any location-aware agent.
"""

import sqlite3

import httpx

from shared.app_logger import get_logger
from shared.credentials import CredentialStore
from shared.intelligence.place_cache import (
    compute_grid_key,
    get_cached_places_for_grid,
    save_places_to_cache,
)

logger = get_logger("intelligence.place_discovery")

GOOGLE_NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_API_TIMEOUT = 15.0
TARGET_PLACE_COUNT = 20

# Categories to search
DEFAULT_CATEGORIES = [
    {"type": "restaurant", "label": "Restaurants", "radius": 5000},
    {"type": "grocery_or_supermarket", "label": "Grocery", "radius": 5000},
    {"type": "park", "label": "Parks", "radius": 5000},
    {"type": "gym", "label": "Gyms", "radius": 5000},
    {"type": "school", "label": "Schools", "radius": 8000},
    {"type": "pharmacy", "label": "Pharmacies", "radius": 5000},
    {"type": "hospital", "label": "Hospitals", "radius": 8000},
    {"type": "transit_station", "label": "Transit", "radius": 5000},
    {"type": "cafe", "label": "Cafes", "radius": 3000},
    {"type": "library", "label": "Libraries", "radius": 8000},
    {"type": "shopping_mall", "label": "Shopping", "radius": 8000},
    {"type": "bank", "label": "Banks", "radius": 5000},
]


def discover_nearby_places(
    latitude: float,
    longitude: float,
    connection: sqlite3.Connection,
    categories: list[dict] | None = None,
    max_places: int = TARGET_PLACE_COUNT,
) -> dict:
    """Discover nearby places with grid-based caching and adaptive rating filter.

    Returns {grid_key, places, from_cache, api_calls_made}.
    """
    api_key = CredentialStore(connection).get_key("google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping place discovery")
        return {"grid_key": None, "places": [], "from_cache": False, "api_calls_made": 0}

    grid_key = compute_grid_key(latitude, longitude)

    # Check cache first
    cached_places = get_cached_places_for_grid(grid_key, connection)
    if cached_places:
        logger.info("Place cache hit for grid %s: %d places", grid_key, len(cached_places))
        return {
            "grid_key": grid_key,
            "places": cached_places,
            "from_cache": True,
            "api_calls_made": 0,
        }

    # Fetch from Google Places API
    search_categories = categories or DEFAULT_CATEGORIES
    all_discovered_places = []
    seen_place_ids = set()
    api_calls_made = 0

    for category in search_categories:
        raw_places = _search_nearby_api(
            latitude=latitude,
            longitude=longitude,
            place_type=category["type"],
            radius=category["radius"],
            api_key=api_key,
        )
        api_calls_made += 1

        for raw_place in raw_places:
            place_id = raw_place.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                place_location = raw_place.get("geometry", {}).get("location", {})
                all_discovered_places.append({
                    "place_id": place_id,
                    "name": raw_place.get("name", ""),
                    "types": raw_place.get("types", []),
                    "latitude": place_location.get("lat"),
                    "longitude": place_location.get("lng"),
                    "rating": raw_place.get("rating"),
                    "total_ratings": raw_place.get("user_ratings_total"),
                    "price_level": raw_place.get("price_level"),
                    "address": raw_place.get("vicinity"),
                    "category_label": category["label"],
                    "customer_reviews": [],  # Filled in deep-dive step
                })

    # Adaptive rating filter: start high, drop until we have enough
    filtered_places = _adaptive_rating_filter(all_discovered_places, max_places)

    # Cache the results
    if filtered_places:
        save_places_to_cache(filtered_places, grid_key, connection)
        logger.info(
            "Discovered %d places (from %d raw) for grid %s, %d API calls",
            len(filtered_places), len(all_discovered_places), grid_key, api_calls_made,
        )

    return {
        "grid_key": grid_key,
        "places": filtered_places,
        "from_cache": False,
        "api_calls_made": api_calls_made,
    }


def _adaptive_rating_filter(
    places: list[dict],
    target_count: int,
) -> list[dict]:
    """Filter places by rating, adapting threshold to fill target count.

    Strategy: 4★+ → 3★+ → 2★+ → 1★+ → all
    At each level, if we have enough places, stop.
    Within each level, sort by rating descending then by review count.
    """
    rating_thresholds = [4.0, 3.0, 2.0, 1.0, 0.0]

    for minimum_rating in rating_thresholds:
        if minimum_rating > 0:
            filtered = [
                place for place in places
                if (place.get("rating") or 0) >= minimum_rating
            ]
        else:
            filtered = list(places)  # All places, including unrated

        if len(filtered) >= target_count or minimum_rating == 0.0:
            # Sort: highest rated first, then most reviewed
            filtered.sort(
                key=lambda place_entry: (
                    place_entry.get("rating") or 0,
                    place_entry.get("total_ratings") or 0,
                ),
                reverse=True,
            )
            result = filtered[:target_count]
            logger.info(
                "Adaptive filter: %d places at %.1f★+ threshold (from %d total)",
                len(result), minimum_rating, len(places),
            )
            return result

    return []


def _search_nearby_api(
    latitude: float,
    longitude: float,
    place_type: str,
    radius: int,
    api_key: str,
) -> list[dict]:
    """Call Google Places Nearby Search API."""
    try:
        response = httpx.get(
            GOOGLE_NEARBY_SEARCH_URL,
            params={
                "location": f"{latitude},{longitude}",
                "radius": radius,
                "type": place_type,
                "key": api_key,
            },
            timeout=PLACES_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            logger.warning("Nearby Search status: %s for type %s", data.get("status"), place_type)
            return []

        return data.get("results", [])

    except Exception as search_error:
        logger.error("Nearby search failed for type %s: %s", place_type, search_error)
        return []
