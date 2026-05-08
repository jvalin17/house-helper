"""Place cache — grid-based geographic caching for nearby place data.

Properties in the same ~10-mile grid share cached place data.
Individual places cached by Google place_id (never re-fetched).
Reviews encrypted at rest.

Reusable: apartment agent, travel agent, any location-aware agent.
"""

import sqlite3

from shared.app_logger import get_logger
from shared.ranking.ranking_encryption import encrypt_terms, decrypt_terms

logger = get_logger("intelligence.place_cache")

GRID_PRECISION = 1  # Decimal places for lat/lng rounding (~10 mile grid cells)


def compute_grid_key(latitude: float, longitude: float) -> str:
    """Compute a grid cell key from coordinates.

    Rounds to 1 decimal place: 30.418 → 30.4, -97.740 → -97.7
    Grid cell ~= 7 miles lat × 5 miles lng at Austin's latitude.
    """
    rounded_latitude = round(latitude, GRID_PRECISION)
    rounded_longitude = round(longitude, GRID_PRECISION)
    return f"grid_{rounded_latitude}_{rounded_longitude}"


def get_cached_places_for_grid(
    grid_key: str,
    connection: sqlite3.Connection,
) -> list[dict] | None:
    """Get all cached places in a grid cell. Returns None if grid not cached."""
    rows = connection.execute(
        "SELECT place_id, place_name, place_types, latitude, longitude, "
        "rating, total_ratings, price_level, address, encrypted_reviews, fetched_at "
        "FROM place_cache WHERE grid_key = ?",
        (grid_key,),
    ).fetchall()

    if not rows:
        return None

    places = []
    for row in rows:
        decrypted_reviews = []
        if row["encrypted_reviews"]:
            decrypted_reviews = decrypt_terms(row["encrypted_reviews"])

        places.append({
            "place_id": row["place_id"],
            "name": row["place_name"],
            "types": row["place_types"].split(",") if row["place_types"] else [],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "rating": row["rating"],
            "total_ratings": row["total_ratings"],
            "price_level": row["price_level"],
            "address": row["address"],
            "customer_reviews": decrypted_reviews,
            "fetched_at": row["fetched_at"],
            "from_cache": True,
        })

    return places


def save_place_to_cache(
    place: dict,
    grid_key: str,
    connection: sqlite3.Connection,
) -> None:
    """Save a single place with encrypted reviews to cache."""
    reviews = place.get("customer_reviews") or []
    encrypted_reviews = encrypt_terms(reviews) if reviews else None

    place_types = ",".join(place.get("types") or [])

    connection.execute(
        """INSERT OR REPLACE INTO place_cache
           (place_id, place_name, place_types, latitude, longitude,
            rating, total_ratings, price_level, address,
            encrypted_reviews, grid_key, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            place["place_id"],
            place.get("name", ""),
            place_types,
            place.get("latitude"),
            place.get("longitude"),
            place.get("rating"),
            place.get("total_ratings"),
            place.get("price_level"),
            place.get("address"),
            encrypted_reviews,
            grid_key,
        ),
    )


def save_places_to_cache(
    places: list[dict],
    grid_key: str,
    connection: sqlite3.Connection,
) -> int:
    """Save multiple places to cache using batch insert. Returns count saved."""
    rows = []
    for place in places:
        reviews = place.get("customer_reviews") or []
        encrypted_reviews = encrypt_terms(reviews) if reviews else None
        place_types = ",".join(place.get("types") or [])
        rows.append((
            place["place_id"],
            place.get("name", ""),
            place_types,
            place.get("latitude"),
            place.get("longitude"),
            place.get("rating"),
            place.get("total_ratings"),
            place.get("price_level"),
            place.get("address"),
            encrypted_reviews,
            grid_key,
        ))

    if rows:
        connection.executemany(
            """INSERT OR REPLACE INTO place_cache
               (place_id, place_name, place_types, latitude, longitude,
                rating, total_ratings, price_level, address,
                encrypted_reviews, grid_key, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            rows,
        )
        connection.commit()

    return len(rows)


def get_cached_place_by_id(
    place_id: str,
    connection: sqlite3.Connection,
) -> dict | None:
    """Get a single cached place by Google place_id."""
    row = connection.execute(
        "SELECT * FROM place_cache WHERE place_id = ?",
        (place_id,),
    ).fetchone()

    if not row:
        return None

    decrypted_reviews = []
    if row["encrypted_reviews"]:
        decrypted_reviews = decrypt_terms(row["encrypted_reviews"])

    return {
        "place_id": row["place_id"],
        "name": row["place_name"],
        "types": row["place_types"].split(",") if row["place_types"] else [],
        "rating": row["rating"],
        "total_ratings": row["total_ratings"],
        "address": row["address"],
        "customer_reviews": decrypted_reviews,
        "from_cache": True,
    }


def has_reviews_cached(place_id: str, connection: sqlite3.Connection) -> bool:
    """Check if a place already has reviews cached."""
    row = connection.execute(
        "SELECT encrypted_reviews FROM place_cache WHERE place_id = ?",
        (place_id,),
    ).fetchone()
    return row is not None and row["encrypted_reviews"] is not None


def update_place_reviews(
    place_id: str,
    reviews: list[str],
    connection: sqlite3.Connection,
) -> None:
    """Update just the reviews for an already-cached place."""
    encrypted_reviews = encrypt_terms(reviews) if reviews else None
    connection.execute(
        "UPDATE place_cache SET encrypted_reviews = ?, fetched_at = datetime('now') WHERE place_id = ?",
        (encrypted_reviews, place_id),
    )
    connection.commit()
