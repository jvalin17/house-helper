"""Neighborhood data service — Walk Score + Google Distance Matrix.

Layer 2 (free): Walk Score API for walk/transit/bike scores.
Layer 3 (cheap): Google Distance Matrix for airport + commute distance.

Both are user-triggered ("Get more info" button) — not called automatically.
Results cached in apartment_neighborhood table.
"""

import json
import sqlite3

import httpx

from shared.app_logger import get_logger

logger = get_logger("apartment.neighborhood")

WALK_SCORE_BASE_URL = "https://api.walkscore.com/score"
GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def _get_api_key(connection: sqlite3.Connection, key_name: str) -> str | None:
    """Get an API key from the apartment_api_keys settings."""
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
    ).fetchone()
    if not row:
        return None
    try:
        keys = json.loads(row["value"])
        return keys.get(key_name)
    except (json.JSONDecodeError, TypeError):
        return None


def get_walk_scores(
    latitude: float,
    longitude: float,
    address: str,
    connection: sqlite3.Connection,
) -> dict | None:
    """Fetch Walk Score, Transit Score, and Bike Score.

    Free tier: 5,000 calls/day. Requires walkscore API key in Settings.
    """
    api_key = _get_api_key(connection, "walkscore")
    if not api_key:
        logger.info("Walk Score API key not configured — skipping")
        return None

    try:
        response = httpx.get(
            WALK_SCORE_BASE_URL,
            params={
                "format": "json",
                "lat": latitude,
                "lon": longitude,
                "address": address,
                "transit": 1,
                "bike": 1,
                "wsapikey": api_key,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        walk_score_result = {
            "walk_score": data.get("walkscore"),
            "walk_description": data.get("description"),
            "transit_score": None,
            "transit_description": None,
            "bike_score": None,
            "bike_description": None,
        }

        transit_data = data.get("transit") or {}
        if transit_data:
            walk_score_result["transit_score"] = transit_data.get("score")
            walk_score_result["transit_description"] = transit_data.get("description")

        bike_data = data.get("bike") or {}
        if bike_data:
            walk_score_result["bike_score"] = bike_data.get("score")
            walk_score_result["bike_description"] = bike_data.get("description")

        logger.info(
            "Walk Score for %s: walk=%s, transit=%s, bike=%s",
            address[:30], walk_score_result["walk_score"],
            walk_score_result["transit_score"], walk_score_result["bike_score"],
        )
        return walk_score_result

    except httpx.HTTPStatusError as http_error:
        logger.error("Walk Score API error: %s", http_error.response.status_code)
        return None
    except Exception as error:
        logger.error("Walk Score fetch failed: %s", error)
        return None


def get_distance_to_airport(
    latitude: float,
    longitude: float,
    connection: sqlite3.Connection,
) -> dict | None:
    """Get driving distance and time to nearest airport.

    Uses Google Distance Matrix API. ~$0.005/call.
    """
    api_key = _get_api_key(connection, "google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping airport distance")
        return None

    try:
        response = httpx.get(
            GOOGLE_DISTANCE_MATRIX_URL,
            params={
                "origins": f"{latitude},{longitude}",
                "destinations": "nearest airport",
                "mode": "driving",
                "key": api_key,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            logger.warning("Distance Matrix returned status: %s", data.get("status"))
            return None

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return None

        distance_meters = element["distance"]["value"]
        duration_seconds = element["duration"]["value"]

        return {
            "airport_distance_km": round(distance_meters / 1000, 1),
            "airport_drive_minutes": round(duration_seconds / 60),
            "airport_distance_text": element["distance"]["text"],
            "airport_drive_text": element["duration"]["text"],
        }

    except Exception as error:
        logger.error("Airport distance fetch failed: %s", error)
        return None


def get_commute_time(
    origin_latitude: float,
    origin_longitude: float,
    destination_address: str,
    connection: sqlite3.Connection,
    travel_mode: str = "transit",
) -> dict | None:
    """Get commute time to user's workplace.

    travel_mode: 'driving', 'transit', 'walking', 'bicycling'.
    """
    api_key = _get_api_key(connection, "google_maps")
    if not api_key:
        logger.info("Google Maps API key not configured — skipping commute")
        return None

    if not destination_address:
        return None

    try:
        response = httpx.get(
            GOOGLE_DISTANCE_MATRIX_URL,
            params={
                "origins": f"{origin_latitude},{origin_longitude}",
                "destinations": destination_address,
                "mode": travel_mode,
                "key": api_key,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            return None

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return None

        return {
            "commute_distance_km": round(element["distance"]["value"] / 1000, 1),
            "commute_duration_minutes": round(element["duration"]["value"] / 60),
            "commute_distance_text": element["distance"]["text"],
            "commute_duration_text": element["duration"]["text"],
            "commute_mode": travel_mode,
            "commute_destination": destination_address,
        }

    except Exception as error:
        logger.error("Commute time fetch failed: %s", error)
        return None


def fetch_and_cache_neighborhood(
    listing_id: int,
    connection: sqlite3.Connection,
) -> dict:
    """Orchestrate all neighborhood data fetches and cache results.

    Called when user clicks "Get more info". Fetches what's possible
    based on available API keys, caches everything.
    """
    # Get listing coordinates
    listing_row = connection.execute(
        "SELECT latitude, longitude, address FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not listing_row:
        return {"error": "Listing not found"}

    latitude = listing_row["latitude"]
    longitude = listing_row["longitude"]
    address = listing_row["address"] or ""

    if not latitude or not longitude:
        return {"error": "Listing has no coordinates — cannot fetch neighborhood data"}

    result = {
        "listing_id": listing_id,
        "walk_scores": None,
        "airport_distance": None,
        "commute": None,
        "sources_used": [],
        "sources_skipped": [],
    }

    # Walk Score (Layer 2 — free)
    walk_scores = get_walk_scores(latitude, longitude, address, connection)
    if walk_scores:
        result["walk_scores"] = walk_scores
        result["sources_used"].append("Walk Score")
    else:
        result["sources_skipped"].append("Walk Score")

    # Airport distance (Layer 3 — Google)
    airport_data = get_distance_to_airport(latitude, longitude, connection)
    if airport_data:
        result["airport_distance"] = airport_data
        result["sources_used"].append("Google Distance Matrix")
    else:
        result["sources_skipped"].append("Google Distance Matrix (airport)")

    # Commute time (Layer 3 — Google, needs user workplace)
    preferences_row = connection.execute(
        "SELECT location FROM apartment_preferences LIMIT 1"
    ).fetchone()
    workplace_address = preferences_row["location"] if preferences_row else None

    if workplace_address:
        commute_data = get_commute_time(latitude, longitude, workplace_address, connection)
        if commute_data:
            result["commute"] = commute_data
            result["sources_used"].append("Google Distance Matrix (commute)")
        else:
            result["sources_skipped"].append("Google Distance Matrix (commute)")

    # Cache in apartment_neighborhood table
    _cache_neighborhood_data(listing_id, result, connection)

    return result


def get_cached_neighborhood(listing_id: int, connection: sqlite3.Connection) -> dict | None:
    """Get cached neighborhood data if available."""
    row = connection.execute(
        "SELECT * FROM apartment_neighborhood WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def _cache_neighborhood_data(listing_id: int, data: dict, connection: sqlite3.Connection) -> None:
    """Save neighborhood data to cache table."""
    walk_scores = data.get("walk_scores") or {}
    airport = data.get("airport_distance") or {}

    connection.execute(
        """INSERT OR REPLACE INTO apartment_neighborhood
           (listing_id, crime_score, grocery_distance_km, school_rating,
            airport_distance_km, airport_drive_minutes, raw_data, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            listing_id,
            walk_scores.get("walk_score"),  # reusing crime_score column for walk score
            None,
            None,
            airport.get("airport_distance_km"),
            airport.get("airport_drive_minutes"),
            json.dumps(data),
        ),
    )
    connection.commit()
