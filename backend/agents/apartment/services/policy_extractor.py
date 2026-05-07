"""Policy extractor — extract lease policies from listing URL via LLM.

Fetches the listing page (reuses SSRF-protected url_fetcher) and sends
text to LLM for structured policy extraction: pet rules, lease terms,
subletting, guest policy, parking, utilities, move-in requirements.

Requires:
  - LLM provider configured
  - Listing has a source_url
"""

import sqlite3

from shared.app_logger import get_logger
from shared.pipeline import parse_llm_json_response
from shared.url_fetcher import fetch_page, extract_text_from_page, FetchError, SSRFError
from agents.apartment.prompts.policy_extraction import (
    build_policy_prompt,
    SYSTEM_PROMPT,
)

logger = get_logger("apartment.policy_extractor")

MIN_PAGE_TEXT_LENGTH = 50
MAX_PAGE_TEXT_LENGTH = 15_000


def extract_policies(
    listing_id: int,
    connection: sqlite3.Connection,
    llm_provider,
    prefetched_page_text: str | None = None,
) -> dict | None:
    """Extract lease policies from listing URL via LLM.

    Returns structured policy data or None if prerequisites aren't met.
    """
    if not llm_provider or not llm_provider.is_configured():
        logger.info("No LLM configured — skipping policy extraction")
        return None

    listing_row = connection.execute(
        "SELECT title, source_url FROM apartment_listings WHERE id = ?",
        (listing_id,),
    ).fetchone()
    if not listing_row:
        return None

    source_url = listing_row["source_url"]
    property_name = listing_row["title"] or "Unknown Property"

    if not source_url and not prefetched_page_text:
        logger.info("No source URL for listing %d — skipping policy extraction", listing_id)
        return None

    # Use pre-fetched text or fetch fresh
    if prefetched_page_text:
        page_text = prefetched_page_text
    else:
        try:
            page_html = fetch_page(source_url)
            page_text = extract_text_from_page(page_html)
        except (FetchError, SSRFError) as fetch_error:
            logger.warning("Could not fetch listing page for policies: %s", fetch_error)
            return {"error": str(fetch_error), "source_url": source_url}

    if not page_text or len(page_text.strip()) < MIN_PAGE_TEXT_LENGTH:
        logger.info("Page text too short for policy extraction")
        return None

    page_text = page_text[:MAX_PAGE_TEXT_LENGTH]

    # LLM extraction
    prompt = build_policy_prompt(page_text, property_name)

    try:
        response = llm_provider.complete(
            prompt,
            system=SYSTEM_PROMPT,
            feature="intel_policies",
        )

        parsed_result = parse_llm_json_response(response)
        if not parsed_result:
            logger.warning("LLM returned non-JSON for policy extraction")
            return {"overview": response, "parse_error": True}

        return parsed_result

    except Exception as extraction_error:
        logger.error("Policy extraction failed: %s", extraction_error)
        return None
