"""RealtyAPI.io integration — search rental listings with images.

API docs: https://realtyapi.io/docs
Base URL: https://zillow.realtyapi.io
Free tier: 250 requests/month.

Actual response schema (verified from live API):
  Response is a JSON array of listing objects.
  Each listing: {"property": {...}, "resultType": "propertyGroup"}
  Property fields:
    - property.title — listing name
    - property.address — {streetAddress, city, state, zipcode}
    - property.minPrice / property.maxPrice — price range
    - property.unitsGroup — [{bedrooms, minPrice, isRoomForRent}]
    - property.media.allPropertyPhotos.medium[] — array of photo URLs
    - property.media.allPropertyPhotos.highResolution[] — hi-res versions
    - property.media.propertyPhotoLinks.mediumSizeLink — single thumbnail
    - property.location.latitude / longitude
    - property.zpid — Zillow property ID
    - property.listingDateTimeOnZillow — listing date
"""

import json
import sqlite3

import httpx

from shared.app_logger import get_logger

logger = get_logger(__name__)

REALTYAPI_BASE_URL = "https://zillow.realtyapi.io"


def get_realtyapi_key(connection: sqlite3.Connection) -> str | None:
    """Retrieve stored RealtyAPI key from settings."""
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
    ).fetchone()
    if not row:
        return None
    try:
        keys = json.loads(row["value"])
        return keys.get("realtyapi")
    except (json.JSONDecodeError, TypeError):
        return None


def search_realtyapi(
    connection: sqlite3.Connection,
    city: str | None = None,
    zip_code: str | None = None,
    bedrooms: int | None = None,
    max_rent: float | None = None,
    bathrooms: int | None = None,
    base_url: str = REALTYAPI_BASE_URL,
    source_tag: str = "realtyapi",
) -> list[dict]:
    """Search RealtyAPI for rental listings."""
    api_key = get_realtyapi_key(connection)
    if not api_key:
        logger.warning("RealtyAPI key not configured")
        return []

    # Build location string — RealtyAPI wants "City, ST" or zip code
    location = ""
    if city:
        location = city
    elif zip_code:
        location = zip_code

    if not location:
        return []

    params: dict[str, str | int] = {
        "location": location,
        "listingStatus": "For_Rent",
        "homeType": "Apartments/Condos/Co-ops",
        "page": 1,
    }

    if bedrooms is not None:
        params["bed_min"] = "Studio" if bedrooms == 0 else str(bedrooms)
    if max_rent is not None:
        params["listPriceRange"] = f"max:{int(max_rent)}"
    if bathrooms is not None:
        params["bathrooms"] = _format_bathrooms_filter(bathrooms)

    logger.info("Searching RealtyAPI: %s", {key: value for key, value in params.items()})

    try:
        response = httpx.get(
            f"{base_url}/search/byaddress",
            params=params,
            headers={
                "Accept": "application/json",
                "x-realtyapi-key": api_key,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        response_data = response.json()

        # Response is either:
        #   - a dict with searchResults: [{property: {...}}, ...]
        #   - or a direct list of [{property: {...}}, ...]
        raw_listings = _extract_listings_from_response(response_data)

        if not raw_listings:
            logger.info("RealtyAPI returned 0 listings")
            return []

        # Normalize to our listing format, filtering out age-restricted communities
        normalized_listings = []
        for raw_listing in raw_listings:
            normalized_listing = _normalize_listing(raw_listing, source_tag=source_tag)
            if normalized_listing and not _is_age_restricted(normalized_listing):
                normalized_listings.append(normalized_listing)

        logger.info("RealtyAPI returned %d listings (%d normalized)", len(raw_listings), len(normalized_listings))
        return normalized_listings

    except httpx.HTTPStatusError as http_error:
        logger.error(
            "RealtyAPI error: %s %s",
            http_error.response.status_code,
            http_error.response.text[:300],
        )
        return []
    except Exception as error:
        logger.error("RealtyAPI search failed: %s", error)
        return []


def _extract_listings_from_response(response_data: dict | list) -> list[dict]:
    """Extract listing array from RealtyAPI response.

    Real response is: {"searchResults": [...], "resultsCount": {...}, "pagesInfo": {...}}
    """
    if isinstance(response_data, list):
        return response_data

    if isinstance(response_data, dict):
        search_results = response_data.get("searchResults")
        if isinstance(search_results, list):
            return search_results

    return []


def _normalize_listing(raw_listing: dict, source_tag: str = "realtyapi") -> dict | None:
    """Normalize a RealtyAPI listing to our common listing format.

    RealtyAPI wraps data in {property: {...}, resultType: ...}.
    All useful data lives under the 'property' key.
    """
    if not isinstance(raw_listing, dict):
        return None

    # Unwrap: everything is under "property"
    property_data = raw_listing.get("property") or raw_listing
    if not isinstance(property_data, dict):
        return None

    address = _extract_address(property_data)
    images = _extract_images(property_data)
    price = _extract_price(property_data)
    bedrooms, bathrooms = _extract_bed_bath(property_data)
    title = property_data.get("title") or _build_title(property_data, bedrooms, address)
    zpid = property_data.get("zpid")

    location = property_data.get("location") or {}
    source_url = f"https://www.zillow.com/homedetails/{zpid}_zpid/" if zpid else ""

    return {
        "title": title,
        "address": address,
        "price": price,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "sqft": property_data.get("livingArea") or property_data.get("squareFootage"),
        "source": source_tag,
        "source_url": source_url,
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "amenities": [],  # Search results don't include amenities — would need detail endpoint
        "images": images,
        "parsed_data": raw_listing,
    }


def _extract_address(property_data: dict) -> str:
    """Extract address from property data."""
    address_object = property_data.get("address")
    if isinstance(address_object, dict):
        parts = [
            address_object.get("streetAddress", ""),
            address_object.get("city", ""),
            address_object.get("state", ""),
            address_object.get("zipcode", ""),
        ]
        joined = ", ".join(part for part in parts if part)
        if joined:
            return joined

    # Fallback: formattedAddress or addressLine1
    if property_data.get("formattedAddress"):
        return property_data["formattedAddress"]

    address_line = property_data.get("addressLine1", "")
    city = property_data.get("city", "")
    if address_line and city:
        return f"{address_line}, {city}"
    return address_line or city or ""


def _extract_images(property_data: dict) -> list[str]:
    """Extract photo URLs from property media data.

    Actual structure: property.media.allPropertyPhotos.highResolution[]
    Fallback: property.media.allPropertyPhotos.medium[]
    Fallback: property.media.propertyPhotoLinks.highResolutionLink (single)
    """
    media = property_data.get("media")
    if not isinstance(media, dict):
        return []

    images = []

    # Primary: allPropertyPhotos — arrays of URL strings
    all_photos = media.get("allPropertyPhotos")
    if isinstance(all_photos, dict):
        # Prefer high resolution, fall back to medium
        photo_urls = all_photos.get("highResolution") or all_photos.get("medium") or []
        if isinstance(photo_urls, list):
            images.extend(url for url in photo_urls if isinstance(url, str))

    # Fallback: single photo link
    if not images:
        photo_links = media.get("propertyPhotoLinks")
        if isinstance(photo_links, dict):
            single_url = photo_links.get("highResolutionLink") or photo_links.get("mediumSizeLink")
            if single_url and isinstance(single_url, str):
                images.append(single_url)

    return images


def _extract_price(property_data: dict) -> float | None:
    """Extract price from property data.

    Properties may have minPrice/maxPrice (range) or price (single or dict).
    For display, use minPrice as the starting price.
    """
    price = property_data.get("price")
    if isinstance(price, dict):
        price = price.get("value")
    if isinstance(price, (int, float)):
        return float(price)

    min_price = property_data.get("minPrice")
    if isinstance(min_price, (int, float)):
        return float(min_price)

    return None


def _extract_bed_bath(property_data: dict) -> tuple[int | None, float | None]:
    """Extract bedrooms and bathrooms from property data.

    For multi-unit properties, bedrooms come from unitsGroup.
    """
    bedrooms = property_data.get("bedrooms")
    bathrooms = property_data.get("bathrooms")

    # If no top-level bedrooms, check unitsGroup for smallest unit
    if bedrooms is None:
        units_group = property_data.get("unitsGroup")
        if isinstance(units_group, list) and units_group:
            first_unit = units_group[0]
            if isinstance(first_unit, dict):
                bedrooms = first_unit.get("bedrooms")

    return bedrooms, bathrooms


def _build_title(property_data: dict, bedrooms: int | None, address: str) -> str:
    """Build a readable title when property.title is not available."""
    parts = []
    if bedrooms is not None:
        parts.append(f"{bedrooms}BR" if bedrooms > 0 else "Studio")

    bathrooms = property_data.get("bathrooms")
    if bathrooms is not None:
        parts.append(f"{bathrooms}BA")

    parts.append("Apartment")

    # Extract city from address string
    if address:
        city_part = address.split(",")[1].strip() if "," in address else ""
        if city_part:
            parts.append(f"in {city_part}")

    return " ".join(parts) if parts else "Rental Listing"


AGE_RESTRICTED_KEYWORDS = ["55+", "55 +", "senior", "active adult", "over 55", "age restricted", "age-restricted"]


def _is_age_restricted(listing: dict) -> bool:
    """Filter out 55+ / senior / age-restricted communities."""
    title = (listing.get("title") or "").lower()
    return any(keyword in title for keyword in AGE_RESTRICTED_KEYWORDS)


def _format_bathrooms_filter(min_bathrooms: int) -> str:
    """Convert numeric bathrooms to RealtyAPI filter format."""
    bathroom_filters = {
        1: "OnePlus",
        2: "TwoPlus",
        3: "ThreePlus",
        4: "FourPlus",
    }
    return bathroom_filters.get(min_bathrooms, "Any")


# ── Strategy pattern adapters ─────────────────────────────

# RealtyAPI supports multiple data sources under different subdomains.
# All use the same API key and similar response format.
REALTYAPI_SOURCES = {
    "zillow": {
        "base_url": "https://zillow.realtyapi.io",
        "display_name": "RealtyAPI (Zillow)",
        "source_tag": "realtyapi",
    },
    "apartments": {
        "base_url": "https://apartments.realtyapi.io",
        "display_name": "RealtyAPI (Apartments.com)",
        "source_tag": "realtyapi_apartments",
    },
    "redfin": {
        "base_url": "https://redfin.realtyapi.io",
        "display_name": "RealtyAPI (Redfin)",
        "source_tag": "realtyapi_redfin",
    },
    "realtor": {
        "base_url": "https://realtor.realtyapi.io",
        "display_name": "RealtyAPI (Realtor.com)",
        "source_tag": "realtyapi_realtor",
    },
}


class RealtyApiProvider:
    """RealtyAPI search adapter — configurable per data source.

    Same API key works across all RealtyAPI subdomains (Zillow, Apartments.com,
    Redfin, Realtor.com). Each returns rental listings in a similar format.
    """

    def __init__(self, connection, source_key: str = "zillow"):
        self.connection = connection
        source_config = REALTYAPI_SOURCES.get(source_key, REALTYAPI_SOURCES["zillow"])
        self._base_url = source_config["base_url"]
        self._display_name = source_config["display_name"]
        self._source_tag = source_config["source_tag"]

    @property
    def source_name(self) -> str:
        return self._display_name

    def is_configured(self) -> bool:
        return get_realtyapi_key(self.connection) is not None

    def search(self, criteria) -> list[dict]:
        return search_realtyapi(
            self.connection,
            city=criteria.city,
            zip_code=criteria.zip_code,
            bedrooms=criteria.bedrooms,
            max_rent=criteria.max_rent,
            bathrooms=criteria.bathrooms,
            base_url=self._base_url,
            source_tag=self._source_tag,
        )
