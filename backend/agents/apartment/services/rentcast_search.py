"""RentCast API integration — search apartment listings.

API docs: https://developers.rentcast.io/reference
Free tier: 50 requests/month.
"""

import json
import sqlite3

import httpx

from shared.app_logger import get_logger

logger = get_logger(__name__)

RENTCAST_BASE_URL = "https://api.rentcast.io/v1"


def get_rentcast_api_key(connection: sqlite3.Connection) -> str | None:
    """Retrieve stored RentCast API key from settings."""
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
    ).fetchone()
    if not row:
        return None
    try:
        keys = json.loads(row["value"])
        return keys.get("rentcast")
    except (json.JSONDecodeError, TypeError):
        return None


def search_rentcast(
    connection: sqlite3.Connection,
    city: str | None = None,
    zip_code: str | None = None,
    bedrooms: int | None = None,
    max_rent: float | None = None,
    bathrooms: int | None = None,
) -> list[dict]:
    """Search RentCast for rental listings."""
    api_key = get_rentcast_api_key(connection)
    if not api_key:
        logger.warning("RentCast API key not configured")
        return []

    # Build query params
    params: dict[str, str | int | float] = {
        "status": "Active",
        "propertyType": "Apartment",
        "limit": 20,
    }
    if city:
        params["city"] = city
    if zip_code:
        params["zipCode"] = zip_code
    if bedrooms is not None:
        params["bedrooms"] = bedrooms
    if max_rent is not None:
        params["maxPrice"] = max_rent
    if bathrooms is not None:
        params["bathrooms"] = bathrooms

    # Need at least city or zip
    if "city" not in params and "zipCode" not in params:
        return []

    logger.info("Searching RentCast: %s", params)

    try:
        response = httpx.get(
            f"{RENTCAST_BASE_URL}/listings/rental/long-term",
            params=params,
            headers={
                "Accept": "application/json",
                "X-Api-Key": api_key,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        listings_data = response.json()

        if not isinstance(listings_data, list):
            logger.warning("RentCast returned non-list: %s", type(listings_data))
            return []

        # Normalize to our listing format
        normalized_listings = []
        for raw_listing in listings_data:
            normalized_listing = {
                "title": _build_title(raw_listing),
                "address": raw_listing.get("formattedAddress") or raw_listing.get("addressLine1", ""),
                "price": raw_listing.get("price"),
                "bedrooms": raw_listing.get("bedrooms"),
                "bathrooms": raw_listing.get("bathrooms"),
                "sqft": raw_listing.get("squareFootage"),
                "source": "rentcast",
                "source_url": raw_listing.get("listingUrl") or raw_listing.get("propertyUrl", ""),
                "latitude": raw_listing.get("latitude"),
                "longitude": raw_listing.get("longitude"),
                "amenities": _extract_amenities(raw_listing),
                "images": raw_listing.get("photoUrls") or ([raw_listing["imageUrl"]] if raw_listing.get("imageUrl") else []),
                "parsed_data": raw_listing,
            }
            normalized_listings.append(normalized_listing)

        logger.info("RentCast returned %d listings", len(normalized_listings))
        return normalized_listings

    except httpx.HTTPStatusError as http_error:
        logger.error("RentCast API error: %s %s", http_error.response.status_code, http_error.response.text[:200])
        return []
    except Exception as error:
        logger.error("RentCast search failed: %s", error)
        return []


def _build_title(raw_listing: dict) -> str:
    """Build a readable title from listing data."""
    parts = []
    bedrooms = raw_listing.get("bedrooms")
    if bedrooms is not None:
        parts.append(f"{bedrooms}BR" if bedrooms > 0 else "Studio")
    bathrooms = raw_listing.get("bathrooms")
    if bathrooms is not None:
        parts.append(f"{bathrooms}BA")
    property_type = raw_listing.get("propertyType", "Apartment")
    parts.append(property_type)
    city = raw_listing.get("city", "")
    if city:
        parts.append(f"in {city}")
    return " ".join(parts) if parts else "Rental Listing"


def _extract_amenities(raw_listing: dict) -> list[str]:
    """Extract amenities from RentCast listing features."""
    amenities = []
    features = raw_listing.get("features") or {}
    if isinstance(features, dict):
        for feature_key, feature_value in features.items():
            if feature_value is True:
                amenities.append(feature_key.replace("has", "").replace("_", " ").strip().title())
    return amenities


# ── Strategy pattern adapter ─────────────────────────────

class RentCastProvider:
    """RentCast search adapter — implements ApartmentSearchProvider contract."""

    def __init__(self, connection):
        self.connection = connection

    @property
    def source_name(self) -> str:
        return "RentCast"

    def is_configured(self) -> bool:
        return get_rentcast_api_key(self.connection) is not None

    def search(self, criteria) -> list[dict]:
        return search_rentcast(
            self.connection,
            city=criteria.city,
            zip_code=criteria.zip_code,
            bedrooms=criteria.bedrooms,
            max_rent=criteria.max_rent,
            bathrooms=criteria.bathrooms,
        )
