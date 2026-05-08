"""Nearby places service — fetch points of interest around a property.

Uses Google Places Nearby Search API to find restaurants, grocery stores,
schools, parks, gyms, transit, pharmacies, etc. within walking/driving distance.

Same google_maps API key as Distance Matrix and Places Details.
"""

import sqlite3

import httpx

from shared.app_logger import get_logger
from shared.credentials import CredentialStore

logger = get_logger("apartment.nearby_places")

GOOGLE_NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_API_TIMEOUT = 15.0

# Categories to search — each becomes a section in Intel
NEARBY_CATEGORIES = [
    {"type": "restaurant", "label": "Restaurants", "icon": "🍽️", "radius": 1500},
    {"type": "grocery_or_supermarket", "label": "Grocery Stores", "icon": "🛒", "radius": 2000},
    {"type": "park", "label": "Parks & Recreation", "icon": "🌳", "radius": 2000},
    {"type": "gym", "label": "Fitness & Gyms", "icon": "💪", "radius": 2000},
    {"type": "school", "label": "Schools", "icon": "🏫", "radius": 3000},
    {"type": "pharmacy", "label": "Pharmacies", "icon": "💊", "radius": 2000},
    {"type": "hospital", "label": "Hospitals & Clinics", "icon": "🏥", "radius": 5000},
    {"type": "transit_station", "label": "Transit Stations", "icon": "🚇", "radius": 2000},
    {"type": "gas_station", "label": "Gas Stations", "icon": "⛽", "radius": 2000},
    {"type": "shopping_mall", "label": "Shopping", "icon": "🛍️", "radius": 3000},
    {"type": "cafe", "label": "Coffee & Cafes", "icon": "☕", "radius": 1000},
    {"type": "bank", "label": "Banks & ATMs", "icon": "🏦", "radius": 2000},
]


def fetch_nearby_places(
    listing_id: int,
    connection: sqlite3.Connection,
    categories: list[dict] | None = None,
) -> dict | None:
    """Fetch nearby points of interest for all categories.

    Returns structured data with top 5 places per category,
    including name, rating, distance, and address.
    """
    api_key = CredentialStore(connection).get_key("google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping nearby places")
        return None

    listing_row = connection.execute(
        "SELECT latitude, longitude, address FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not listing_row:
        return None

    latitude = listing_row["latitude"]
    longitude = listing_row["longitude"]

    if not latitude or not longitude:
        logger.info("No coordinates for listing %d — skipping nearby places", listing_id)
        return None

    search_categories = categories or NEARBY_CATEGORIES
    nearby_results = {}
    total_places_found = 0

    for category in search_categories:
        places = _search_nearby(
            latitude=latitude,
            longitude=longitude,
            place_type=category["type"],
            radius=category["radius"],
            api_key=api_key,
        )

        if places:
            nearby_results[category["type"]] = {
                "label": category["label"],
                "icon": category["icon"],
                "count": len(places),
                "places": places[:5],  # Top 5 per category
            }
            total_places_found += len(places)

    return {
        "categories": nearby_results,
        "total_places": total_places_found,
        "location": {"latitude": latitude, "longitude": longitude},
        "address": listing_row["address"],
    }


def _search_nearby(
    latitude: float,
    longitude: float,
    place_type: str,
    radius: int,
    api_key: str,
) -> list[dict]:
    """Search for nearby places of a specific type."""
    try:
        response = httpx.get(
            GOOGLE_NEARBY_SEARCH_URL,
            params={
                "location": f"{latitude},{longitude}",
                "radius": radius,
                "type": place_type,
                "key": api_key,
                "rankby": "prominence",
            },
            timeout=PLACES_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            logger.warning("Nearby Search returned status: %s for type %s", data.get("status"), place_type)
            return []

        places = []
        for place in data.get("results", []):
            place_location = place.get("geometry", {}).get("location", {})
            places.append({
                "name": place.get("name"),
                "rating": place.get("rating"),
                "total_ratings": place.get("user_ratings_total"),
                "address": place.get("vicinity"),
                "price_level": place.get("price_level"),
                "open_now": (place.get("opening_hours") or {}).get("open_now"),
                "latitude": place_location.get("lat"),
                "longitude": place_location.get("lng"),
            })

        # Sort by rating (highest first), then by number of reviews
        places.sort(
            key=lambda place_entry: (
                place_entry.get("rating") or 0,
                place_entry.get("total_ratings") or 0,
            ),
            reverse=True,
        )

        return places

    except Exception as search_error:
        logger.error("Nearby search failed for type %s: %s", place_type, search_error)
        return []
