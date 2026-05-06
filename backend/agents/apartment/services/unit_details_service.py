"""Unit details service — fetch individual unit availability from RealtyAPI.

Uses the /apartment_details endpoint to get floor plans with exact prices,
sqft, floor, and availability dates per unit. This is a premium Intel step —
the search endpoint only shows price ranges.
"""

import sqlite3

import httpx

from shared.app_logger import get_logger
from shared.credentials import CredentialStore

logger = get_logger("apartment.unit_details")

REALTYAPI_BASE_URL = "https://zillow.realtyapi.io"


def fetch_unit_details(
    listing_id: int,
    connection: sqlite3.Connection,
    base_url: str = REALTYAPI_BASE_URL,
) -> dict | None:
    """Fetch available units with exact prices from RealtyAPI /apartment_details.

    Returns normalized unit data grouped by floor plan type.
    Returns None if API key is missing or listing has no zpid.
    """
    api_key = CredentialStore(connection).get_key("realtyapi")
    if not api_key:
        logger.info("RealtyAPI key not configured — skipping unit details")
        return None

    # Get the zpid from stored listing data
    zpid = _get_zpid_for_listing(listing_id, connection)
    if not zpid:
        logger.info("No zpid available for listing %d — cannot fetch unit details", listing_id)
        return None

    try:
        response = httpx.get(
            f"{base_url}/apartment_details",
            params={"zpid": zpid},
            headers={
                "Accept": "application/json",
                "x-realtyapi-key": api_key,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        raw_data = response.json()

        return normalize_unit_details(raw_data)

    except httpx.HTTPStatusError as http_error:
        logger.error(
            "RealtyAPI apartment_details error: %s %s",
            http_error.response.status_code,
            http_error.response.text[:300],
        )
        return None
    except Exception as error:
        logger.error("Unit details fetch failed: %s", error)
        return None


def normalize_unit_details(raw_data: dict | list) -> dict:
    """Normalize RealtyAPI apartment_details response into structured unit data.

    Expected shapes (API can return either):
    1. {"floorPlans": [...], "buildingName": "...", ...}
    2. {"building": {"floorPlans": [...]}}
    3. [{"beds": 1, "baths": 1, "price": "$1,832", ...}]  (flat list)
    """
    floor_plans = _extract_floor_plans(raw_data)

    if not floor_plans:
        return {"floor_plans": [], "total_available": 0, "summary": {}}

    normalized_plans = []
    total_available = 0

    for plan in floor_plans:
        normalized_plan = _normalize_single_plan(plan)
        if normalized_plan:
            normalized_plans.append(normalized_plan)
            total_available += normalized_plan["available_count"]

    # Build summary by bedroom count
    summary_by_type = {}
    for plan in normalized_plans:
        bedroom_key = plan["bedrooms"]
        if bedroom_key not in summary_by_type:
            summary_by_type[bedroom_key] = {
                "label": "Studio" if bedroom_key == 0 else f"{bedroom_key}BR",
                "min_price": plan["min_price"],
                "max_price": plan["max_price"],
                "total_available": 0,
            }
        entry = summary_by_type[bedroom_key]
        if plan["min_price"] and (entry["min_price"] is None or plan["min_price"] < entry["min_price"]):
            entry["min_price"] = plan["min_price"]
        if plan["max_price"] and (entry["max_price"] is None or plan["max_price"] > entry["max_price"]):
            entry["max_price"] = plan["max_price"]
        entry["total_available"] += plan["available_count"]

    return {
        "floor_plans": normalized_plans,
        "total_available": total_available,
        "summary": summary_by_type,
    }


def _extract_floor_plans(raw_data: dict | list) -> list[dict]:
    """Pull the floor plans array from various response shapes."""
    if isinstance(raw_data, list):
        return raw_data

    if not isinstance(raw_data, dict):
        return []

    # Shape 1: top-level floorPlans
    if "floorPlans" in raw_data:
        plans = raw_data["floorPlans"]
        return plans if isinstance(plans, list) else []

    # Shape 2: nested under building
    building = raw_data.get("building") or {}
    if "floorPlans" in building:
        plans = building["floorPlans"]
        return plans if isinstance(plans, list) else []

    # Shape 3: nested under data
    data = raw_data.get("data") or {}
    if "floorPlans" in data:
        plans = data["floorPlans"]
        return plans if isinstance(plans, list) else []

    return []


def _normalize_single_plan(plan: dict) -> dict | None:
    """Normalize a single floor plan entry with its available units."""
    if not isinstance(plan, dict):
        return None

    plan_name = plan.get("name") or plan.get("planName") or "Unknown Plan"
    bedrooms = _parse_bedrooms(plan)
    bathrooms = _parse_number(plan.get("baths") or plan.get("bathrooms"))

    # Parse sqft — can be range string "450-520" or number
    sqft_raw = plan.get("sqft") or plan.get("squareFeet") or plan.get("area")
    min_sqft, max_sqft = _parse_sqft_range(sqft_raw)

    # Parse price — can be range string "$1,445 - $1,595" or number
    price_raw = plan.get("price") or plan.get("rentRange") or plan.get("rent")
    min_price, max_price = _parse_price_range(price_raw)

    # Individual units (if available)
    raw_units = plan.get("units") or plan.get("availableUnits") or []
    normalized_units = []
    for unit in raw_units:
        if not isinstance(unit, dict):
            continue
        unit_price = _parse_single_price(unit.get("price") or unit.get("rent"))
        normalized_units.append({
            "unit_number": unit.get("unit") or unit.get("unitNumber") or unit.get("name"),
            "sqft": _parse_number(unit.get("sqft") or unit.get("squareFeet")),
            "price": unit_price,
            "floor": _parse_number(unit.get("floor") or unit.get("floorNumber")),
            "available_date": unit.get("available") or unit.get("availableDate") or unit.get("moveInDate"),
        })

    # If no individual units but we have availability count
    available_count = len(normalized_units) or _parse_number(plan.get("availableCount")) or 0

    # Update price range from individual units
    unit_prices = [unit["price"] for unit in normalized_units if unit["price"] is not None]
    if unit_prices:
        if min_price is None or min(unit_prices) < min_price:
            min_price = min(unit_prices)
        if max_price is None or max(unit_prices) > max_price:
            max_price = max(unit_prices)

    return {
        "name": plan_name,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "min_sqft": min_sqft,
        "max_sqft": max_sqft,
        "min_price": min_price,
        "max_price": max_price,
        "available_count": available_count,
        "units": normalized_units,
    }


def _parse_bedrooms(plan: dict) -> int:
    """Parse bedroom count from various formats."""
    beds_raw = plan.get("beds") or plan.get("bedrooms") or plan.get("bed")
    if isinstance(beds_raw, str):
        lower = beds_raw.lower().strip()
        if lower in ("studio", "0", "s"):
            return 0
        try:
            return int(lower.split()[0])
        except (ValueError, IndexError):
            return 0
    if isinstance(beds_raw, (int, float)):
        return int(beds_raw)
    return 0


def _parse_number(value) -> int | float | None:
    """Parse a number from various formats."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("$", "").strip()
        try:
            return float(cleaned) if "." in cleaned else int(cleaned)
        except ValueError:
            return None
    return None


def _parse_sqft_range(value) -> tuple[int | None, int | None]:
    """Parse sqft range from '450-520' or '450' or 450."""
    if isinstance(value, (int, float)):
        return int(value), int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if "-" in cleaned:
            parts = cleaned.split("-")
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except (ValueError, IndexError):
                pass
        try:
            numeric = int(cleaned)
            return numeric, numeric
        except ValueError:
            pass
    return None, None


def _parse_price_range(value) -> tuple[float | None, float | None]:
    """Parse price range from '$1,445 - $1,595' or '$1,445' or 1445."""
    if isinstance(value, (int, float)):
        return float(value), float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        if "-" in cleaned:
            parts = cleaned.split("-")
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except (ValueError, IndexError):
                pass
        try:
            numeric = float(cleaned)
            return numeric, numeric
        except ValueError:
            pass
    return None, None


def _parse_single_price(value) -> float | None:
    """Parse a single price value."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("/mo", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _get_zpid_for_listing(listing_id: int, connection: sqlite3.Connection) -> str | None:
    """Extract zpid from stored listing data.

    The zpid is either:
    1. In parsed_data.property.zpid
    2. Extractable from source_url (e.g., /homedetails/12345_zpid/)
    """
    import json
    import re

    row = connection.execute(
        "SELECT source_url, parsed_data FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not row:
        return None

    # Try source_url first — most reliable
    source_url = row["source_url"] or ""
    zpid_match = re.search(r"(\d+)_zpid", source_url)
    if zpid_match:
        return zpid_match.group(1)

    # Try parsed_data
    if row["parsed_data"]:
        try:
            parsed = json.loads(row["parsed_data"]) if isinstance(row["parsed_data"], str) else row["parsed_data"]
            # Check nested property.zpid
            property_data = parsed.get("property") or parsed
            zpid = property_data.get("zpid")
            if zpid:
                return str(zpid)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    return None
