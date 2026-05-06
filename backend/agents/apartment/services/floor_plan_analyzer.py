"""Floor plan analyzer — vision LLM analysis of floor plan images.

Sends floor plan images to a vision-capable LLM (Claude, GPT-4o) and returns
structured analysis: livability score, furniture fit, WFH suitability, etc.

Requires:
  - Vision-capable LLM provider (supports_vision = True)
  - Floor plan image stored in apartment_floor_plans table
"""

import base64
import json
import sqlite3

from shared.app_logger import get_logger
from shared.pipeline import parse_llm_json_response
from agents.apartment.prompts.floor_plan_analysis import (
    build_floor_plan_prompt,
    SYSTEM_PROMPT,
)

logger = get_logger("apartment.floor_plan_analyzer")

LIVABILITY_SCORE_MIN = 0
LIVABILITY_SCORE_MAX = 100


def analyze_floor_plan(
    listing_id: int,
    connection: sqlite3.Connection,
    llm_provider,
    unit_context: dict | None = None,
) -> dict | None:
    """Analyze floor plan image(s) using vision LLM.

    Returns structured analysis or None if prerequisites aren't met.
    """
    if not llm_provider or not llm_provider.is_configured():
        logger.info("No LLM configured — skipping floor plan analysis")
        return None

    if not llm_provider.supports_vision:
        logger.info("LLM provider does not support vision — skipping floor plan analysis")
        return None

    # Get floor plan image
    image_data = _get_floor_plan_image(listing_id, connection)
    if not image_data:
        logger.info("No floor plan image for listing %d — skipping analysis", listing_id)
        return None

    # Get listing context
    listing_row = connection.execute(
        "SELECT title, address FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    listing_title = listing_row["title"] if listing_row else "Unknown Property"
    listing_address = listing_row["address"] if listing_row else None

    # Build prompt
    prompt = build_floor_plan_prompt(
        listing_title=listing_title,
        address=listing_address,
        unit_context=unit_context,
    )

    # Call vision LLM
    try:
        response = llm_provider.complete_with_images(
            prompt=prompt,
            images=image_data,
            system=SYSTEM_PROMPT,
            feature="intel_floor_plan",
        )

        parsed_result = parse_llm_json_response(response)
        if parsed_result:
            # Validate livability_score is in range
            score = parsed_result.get("livability_score")
            if isinstance(score, (int, float)):
                parsed_result["livability_score"] = max(LIVABILITY_SCORE_MIN, min(LIVABILITY_SCORE_MAX, int(score)))
            return parsed_result

        # Non-JSON response — return raw text as overview
        logger.warning("Vision LLM returned non-JSON for floor plan analysis")
        return {"overview": response, "parse_error": True}

    except Exception as analysis_error:
        logger.error("Floor plan analysis failed: %s", analysis_error)
        return None


def _get_floor_plan_image(listing_id: int, connection: sqlite3.Connection) -> list[dict] | None:
    """Get floor plan image data for vision LLM.

    Returns list of image dicts suitable for complete_with_images():
      [{"data": base64_string, "media_type": "image/jpeg"}]
      or [{"url": "https://..."}]

    Prefers stored binary (works offline). Falls back to URL.
    """
    rows = connection.execute(
        "SELECT image_url, image_binary FROM apartment_floor_plans WHERE listing_id = ? LIMIT 3",
        (listing_id,),
    ).fetchall()

    if not rows:
        return None

    images = []
    for row in rows:
        if row["image_binary"]:
            # Use stored binary — detect format from bytes
            binary_data = row["image_binary"]
            media_type = _detect_image_type(binary_data)
            encoded = base64.b64encode(binary_data).decode("ascii")
            images.append({"data": encoded, "media_type": media_type})
        elif row["image_url"]:
            images.append({"url": row["image_url"]})

    return images if images else None


def _detect_image_type(binary_data: bytes) -> str:
    """Detect image MIME type from file header bytes."""
    if binary_data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if binary_data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if binary_data[:4] == b"RIFF" and binary_data[8:12] == b"WEBP":
        return "image/webp"
    # Default to JPEG
    return "image/jpeg"
