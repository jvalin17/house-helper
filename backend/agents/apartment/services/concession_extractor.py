"""Concession extractor — scrape listing URL and extract fees via LLM.

Fetches the listing page (SSRF-protected), extracts text content,
sends to LLM for structured fee extraction, and optionally auto-fills
the cost calculator.

Requires:
  - LLM provider configured
  - Listing has a source_url
"""

import json
import sqlite3

from shared.app_logger import get_logger
from shared.pipeline import parse_llm_json_response
from shared.url_fetcher import fetch_page, extract_text_from_page, FetchError, SSRFError
from agents.apartment.prompts.concession_extraction import (
    build_concession_prompt,
    SYSTEM_PROMPT,
)

logger = get_logger("apartment.concession_extractor")

MIN_PAGE_TEXT_LENGTH = 50
MAX_PAGE_TEXT_LENGTH = 15_000


def extract_concessions(
    listing_id: int,
    connection: sqlite3.Connection,
    llm_provider,
    auto_fill_cost: bool = True,
    prefetched_page_text: str | None = None,
) -> dict | None:
    """Extract concessions and fees from listing URL via LLM.

    Returns structured fee data or None if prerequisites aren't met.
    Optionally auto-fills the apartment_cost table.
    """
    if not llm_provider or not llm_provider.is_configured():
        logger.info("No LLM configured — skipping concession extraction")
        return None

    # Get listing URL
    listing_row = connection.execute(
        "SELECT title, source_url FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not listing_row:
        return None

    source_url = listing_row["source_url"]
    listing_title = listing_row["title"] or "Unknown Property"

    if not source_url and not prefetched_page_text:
        logger.info("No source URL for listing %d — skipping concession extraction", listing_id)
        return None

    # Use pre-fetched text or fetch fresh
    if prefetched_page_text:
        page_text = prefetched_page_text
    else:
        try:
            page_html = fetch_page(source_url)
            page_text = extract_text_from_page(page_html)
        except (FetchError, SSRFError) as fetch_error:
            logger.warning("Could not fetch listing page for concessions: %s", fetch_error)
            return {"error": str(fetch_error), "source_url": source_url}

    if not page_text or len(page_text.strip()) < MIN_PAGE_TEXT_LENGTH:
        logger.info("Page text too short for concession extraction")
        return None

    page_text = page_text[:MAX_PAGE_TEXT_LENGTH]

    # Build prompt and call LLM
    prompt = build_concession_prompt(page_text, listing_title)

    try:
        response = llm_provider.complete(
            prompt,
            system=SYSTEM_PROMPT,
            feature="intel_concessions",
        )

        parsed_result = parse_llm_json_response(response)
        if not parsed_result:
            logger.warning("LLM returned non-JSON for concession extraction")
            return {"overview": response, "parse_error": True}

        # Auto-fill cost calculator
        if auto_fill_cost:
            _auto_fill_cost_table(listing_id, parsed_result, connection)

        return parsed_result

    except Exception as extraction_error:
        logger.error("Concession extraction failed: %s", extraction_error)
        return None


def _auto_fill_cost_table(listing_id: int, concession_data: dict, connection: sqlite3.Connection) -> None:
    """Auto-fill the apartment_cost table with extracted fee data.

    Only fills fields that were extracted (non-null). Does not overwrite
    user-entered values — only fills empty fields.
    """
    existing_cost = connection.execute(
        "SELECT * FROM apartment_cost WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()

    parking_fee = concession_data.get("parking_monthly")
    pet_fee = concession_data.get("pet_monthly")
    special_description = None
    special_discount = None

    # Build concession description
    concessions = concession_data.get("concessions") or []
    if concessions:
        descriptions = [
            concession.get("description", "")
            for concession in concessions
            if isinstance(concession, dict) and concession.get("description")
        ]
        if descriptions:
            special_description = "; ".join(descriptions)

        # Use the first concession's monthly discount
        first_discount = next(
            (concession.get("monthly_discount") for concession in concessions
             if isinstance(concession, dict) and concession.get("monthly_discount")),
            None,
        )
        if first_discount:
            special_discount = first_discount

    if existing_cost:
        # Only update fields that are currently 0 or empty
        updates = {}
        if parking_fee and (not existing_cost["parking_fee"] or existing_cost["parking_fee"] == 0):
            updates["parking_fee"] = parking_fee
        if pet_fee and (not existing_cost["pet_fee"] or existing_cost["pet_fee"] == 0):
            updates["pet_fee"] = pet_fee
        if special_description and not existing_cost["special_description"]:
            updates["special_description"] = special_description
        if special_discount and (not existing_cost["special_discount"] or existing_cost["special_discount"] == 0):
            updates["special_discount"] = special_discount

        if updates:
            set_clause = ", ".join(f"{column} = ?" for column in updates)
            values = list(updates.values()) + [listing_id]
            connection.execute(
                f"UPDATE apartment_cost SET {set_clause} WHERE listing_id = ?",
                values,
            )
            connection.commit()
            logger.info("Auto-filled %d cost fields for listing %d", len(updates), listing_id)
    else:
        # Create new cost entry with extracted data
        listing_price = connection.execute(
            "SELECT price FROM apartment_listings WHERE id = ?",
            (listing_id,),
        ).fetchone()
        base_rent = listing_price["price"] if listing_price and listing_price["price"] else 0

        connection.execute(
            """INSERT INTO apartment_cost
               (listing_id, base_rent, parking_fee, pet_fee, special_description, special_discount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (listing_id, base_rent, parking_fee or 0, pet_fee or 0,
             special_description, special_discount or 0),
        )
        connection.commit()
        logger.info("Created cost entry from concessions for listing %d", listing_id)
