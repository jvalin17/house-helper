"""Data processing engine — deduplicate and merge listings from multiple sources.

When the same property appears from Zillow, Apartments.com, and RentCast,
this engine merges them into a single enriched listing instead of showing
3 duplicate cards.

Matching strategy:
  1. Exact zpid match (same Zillow property across RealtyAPI sources)
  2. Address similarity (normalized street + city + state)
  3. Proximity match (lat/lng within ~100m AND price within 20%)

Merging strategy:
  - Keep the richest data: most images, most amenities, longest title
  - Prefer RealtyAPI data (has images) over RentCast (no images)
  - Track all sources a listing was found on
  - Availability: latest listing date wins
"""

import re

from shared.app_logger import get_logger

logger = get_logger("apartment.data_processor")

# ~100 meters in degrees (rough, works for US latitudes)
LOCATION_MATCH_THRESHOLD_DEGREES = 0.001
PRICE_MATCH_THRESHOLD_PERCENT = 0.20


def deduplicate_listings(listings: list[dict]) -> list[dict]:
    """Merge duplicate listings from multiple sources into unique properties.

    Returns a list of merged listings, each with a 'sources' field
    listing all APIs that found this property.
    """
    if not listings:
        return []

    merged_listings: list[dict] = []
    used_indices: set[int] = set()

    for listing_index, listing in enumerate(listings):
        if listing_index in used_indices:
            continue

        # Find all duplicates of this listing
        duplicates = [listing]
        for compare_index in range(listing_index + 1, len(listings)):
            if compare_index in used_indices:
                continue
            if _are_same_property(listing, listings[compare_index]):
                duplicates.append(listings[compare_index])
                used_indices.add(compare_index)

        # Merge duplicates into one enriched listing
        merged = _merge_listings(duplicates)
        merged_listings.append(merged)

    duplicate_count = len(listings) - len(merged_listings)
    if duplicate_count > 0:
        logger.info(
            "Deduplicated %d listings → %d unique (%d duplicates merged)",
            len(listings), len(merged_listings), duplicate_count,
        )

    return merged_listings


def _are_same_property(listing_a: dict, listing_b: dict) -> bool:
    """Determine if two listings refer to the same physical property."""
    # 1. Exact zpid match (same Zillow property from different RealtyAPI sources)
    zpid_a = _extract_zpid(listing_a)
    zpid_b = _extract_zpid(listing_b)
    if zpid_a and zpid_b and zpid_a == zpid_b:
        return True

    # 2. Address similarity
    normalized_address_a = _normalize_address(listing_a.get("address") or "")
    normalized_address_b = _normalize_address(listing_b.get("address") or "")
    if normalized_address_a and normalized_address_b and normalized_address_a == normalized_address_b:
        return True

    # 3. Proximity match (location + price)
    if _locations_match(listing_a, listing_b) and _prices_match(listing_a, listing_b):
        return True

    return False


def _extract_zpid(listing: dict) -> int | None:
    """Extract Zillow property ID from listing or its parsed_data."""
    parsed_data = listing.get("parsed_data") or {}
    if isinstance(parsed_data, dict):
        property_data = parsed_data.get("property") or parsed_data
        zpid = property_data.get("zpid")
        if zpid:
            return int(zpid)
    return None


def _normalize_address(address: str) -> str:
    """Normalize an address for comparison.

    Strips apt/unit numbers, normalizes abbreviations, lowercases.
    '500 Elm St Apt 12, Dallas, TX, 75201' → '500 elm st dallas tx'
    """
    if not address:
        return ""

    normalized = address.lower().strip()

    # Remove zip codes
    normalized = re.sub(r'\b\d{5}(-\d{4})?\b', '', normalized)

    # Remove apartment/unit/suite numbers
    normalized = re.sub(r'\b(apt|unit|ste|suite|#)\s*\w+', '', normalized)

    # Normalize common abbreviations
    abbreviation_map = {
        r'\bst\b': 'street',
        r'\bdr\b': 'drive',
        r'\bave\b': 'avenue',
        r'\bblvd\b': 'boulevard',
        r'\bln\b': 'lane',
        r'\brd\b': 'road',
        r'\bct\b': 'court',
        r'\bpl\b': 'place',
        r'\bpkwy\b': 'parkway',
        r'\bexpy\b': 'expressway',
        r'\bhwy\b': 'highway',
    }
    for pattern, replacement in abbreviation_map.items():
        normalized = re.sub(pattern, replacement, normalized)

    # Remove extra whitespace and punctuation
    normalized = re.sub(r'[,.\-#]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def _locations_match(listing_a: dict, listing_b: dict) -> bool:
    """Check if two listings are within ~100m of each other."""
    latitude_a = listing_a.get("latitude")
    longitude_a = listing_a.get("longitude")
    latitude_b = listing_b.get("latitude")
    longitude_b = listing_b.get("longitude")

    if None in (latitude_a, longitude_a, latitude_b, longitude_b):
        return False

    latitude_distance = abs(float(latitude_a) - float(latitude_b))
    longitude_distance = abs(float(longitude_a) - float(longitude_b))

    return (latitude_distance < LOCATION_MATCH_THRESHOLD_DEGREES
            and longitude_distance < LOCATION_MATCH_THRESHOLD_DEGREES)


def _prices_match(listing_a: dict, listing_b: dict) -> bool:
    """Check if two listings have prices within 20% of each other."""
    price_a = listing_a.get("price")
    price_b = listing_b.get("price")

    if price_a is None or price_b is None:
        return True  # Can't compare, don't reject

    price_a = float(price_a)
    price_b = float(price_b)

    if price_a == 0 or price_b == 0:
        return price_a == price_b

    price_ratio = abs(price_a - price_b) / max(price_a, price_b)
    return price_ratio <= PRICE_MATCH_THRESHOLD_PERCENT


def _merge_listings(duplicates: list[dict]) -> dict:
    """Merge multiple listings of the same property into one enriched record.

    Strategy: keep the richest data from each source.
    """
    if len(duplicates) == 1:
        merged = duplicates[0].copy()
        merged["sources"] = [merged.get("source", "unknown")]
        return merged

    # Sort by richness: most images first, then most amenities
    duplicates.sort(
        key=lambda listing: (len(listing.get("images") or []), len(listing.get("amenities") or [])),
        reverse=True,
    )

    # Start with the richest listing as base
    merged = duplicates[0].copy()
    merged["sources"] = []

    for duplicate in duplicates:
        source = duplicate.get("source", "unknown")
        if source not in merged["sources"]:
            merged["sources"].append(source)

        # Take longer title (usually more descriptive)
        duplicate_title = duplicate.get("title") or ""
        if len(duplicate_title) > len(merged.get("title") or ""):
            merged["title"] = duplicate_title

        # Merge images (deduplicate by URL)
        existing_images = set(merged.get("images") or [])
        for image_url in (duplicate.get("images") or []):
            if image_url not in existing_images:
                merged.setdefault("images", []).append(image_url)
                existing_images.add(image_url)

        # Merge amenities (deduplicate by name)
        existing_amenities = set(merged.get("amenities") or [])
        for amenity in (duplicate.get("amenities") or []):
            if amenity not in existing_amenities:
                merged.setdefault("amenities", []).append(amenity)
                existing_amenities.add(amenity)

        # Fill in missing fields from other sources
        for field in ("price", "bedrooms", "bathrooms", "sqft", "latitude", "longitude", "source_url"):
            if merged.get(field) is None and duplicate.get(field) is not None:
                merged[field] = duplicate[field]

    return merged
