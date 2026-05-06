"""Concession extractor — tests for LLM-based fee extraction from listing pages.

Covers: prompt building, extraction with realistic page text, auto-fill cost table,
graceful handling of fetch failures, skip when no URL or no LLM.
"""

import json
import sqlite3
from unittest.mock import patch

import pytest

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from agents.apartment.services.concession_extractor import (
    extract_concessions,
    _auto_fill_cost_table,
)
from agents.apartment.prompts.concession_extraction import build_concession_prompt


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_with_url(database_connection):
    """Listing with a source URL for scraping."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url)
           VALUES (?, ?, ?, ?)""",
        ("Ellwood at Lake Travis", "7500 Serene Hills Dr, Austin, TX 78738",
         1832.0, "https://www.ellwoodlaketravis.com/"),
    )
    database_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def listing_without_url(database_connection):
    """Listing with no source URL."""
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, price) VALUES (?, ?)",
        ("Manual Entry", 1200.0),
    )
    database_connection.commit()
    return cursor.lastrowid


class MockLLMProvider(LLMProviderBase):
    """Mock LLM that returns structured concession data."""

    def __init__(self, response_json: dict):
        self._response = json.dumps(response_json)

    def complete(self, prompt, system=None, feature=None):
        return self._response

    def provider_name(self):
        return "mock"

    def model_name(self):
        return "mock-4o"

    def is_configured(self):
        return True


REALISTIC_CONCESSION_RESPONSE = {
    "concessions": [
        {"description": "2 months free on 14-month lease", "lease_months": 14, "monthly_discount": 261.71},
    ],
    "application_fee": 50.0,
    "admin_fee": 250.0,
    "pet_deposit": 300.0,
    "pet_monthly": 25.0,
    "parking_monthly": 150.0,
    "move_in_total": 2282.0,
    "lease_terms_available": ["12 months", "14 months"],
}

REALISTIC_PAGE_TEXT = """
Ellwood at Lake Travis - Luxury Apartments

Now Leasing! 2 Months Free on 14-Month Lease

Studio from $1,445 | 1BR from $1,832 | 2BR from $2,231

Application Fee: $50 per applicant
Administrative Fee: $250
Pet Deposit: $300 (per pet)
Monthly Pet Rent: $25/pet
Reserved Parking: $150/month

Amenities: Pool, Fitness Center, Dog Park, Package Lockers
"""


# ── Prompt building ───────────────────────────────────

def test_prompt_includes_listing_title():
    """Prompt includes the listing name for context."""
    prompt = build_concession_prompt("Some page text here", "Ellwood at Lake Travis")
    assert "Ellwood at Lake Travis" in prompt


def test_prompt_truncates_long_text():
    """Very long page text is truncated to stay in token budget."""
    long_text = "Lorem ipsum dolor sit amet. " * 1000  # ~28,000 chars
    prompt = build_concession_prompt(long_text, "Test Property")
    assert "[...page truncated]" in prompt
    assert len(prompt) < 12000  # Prompt should be bounded


# ── Extraction with mocked fetch ──────────────────────

@patch("agents.apartment.services.concession_extractor.fetch_page")
@patch("agents.apartment.services.concession_extractor.extract_text_from_page")
def test_extract_concessions_full_flow(
    mock_extract_text, mock_fetch_page,
    database_connection, listing_with_url,
):
    """Full extraction flow: fetch → extract text → LLM → structured result."""
    mock_fetch_page.return_value = "<html>page content</html>"
    mock_extract_text.return_value = REALISTIC_PAGE_TEXT

    provider = MockLLMProvider(REALISTIC_CONCESSION_RESPONSE)
    result = extract_concessions(listing_with_url, database_connection, provider)

    assert result is not None
    assert len(result["concessions"]) == 1
    assert result["concessions"][0]["description"] == "2 months free on 14-month lease"
    assert result["application_fee"] == 50.0
    assert result["parking_monthly"] == 150.0
    assert result["pet_monthly"] == 25.0


@patch("agents.apartment.services.concession_extractor.fetch_page")
@patch("agents.apartment.services.concession_extractor.extract_text_from_page")
def test_auto_fills_cost_table(
    mock_extract_text, mock_fetch_page,
    database_connection, listing_with_url,
):
    """Extracted concessions auto-fill the apartment_cost table."""
    mock_fetch_page.return_value = "<html>page</html>"
    mock_extract_text.return_value = REALISTIC_PAGE_TEXT

    provider = MockLLMProvider(REALISTIC_CONCESSION_RESPONSE)
    extract_concessions(listing_with_url, database_connection, provider, auto_fill_cost=True)

    cost_row = database_connection.execute(
        "SELECT * FROM apartment_cost WHERE listing_id = ?",
        (listing_with_url,),
    ).fetchone()

    assert cost_row is not None
    assert cost_row["parking_fee"] == 150.0
    assert cost_row["pet_fee"] == 25.0
    assert cost_row["base_rent"] == 1832.0
    assert "2 months free" in cost_row["special_description"]


@patch("agents.apartment.services.concession_extractor.fetch_page")
@patch("agents.apartment.services.concession_extractor.extract_text_from_page")
def test_auto_fill_does_not_overwrite_user_values(
    mock_extract_text, mock_fetch_page,
    database_connection, listing_with_url,
):
    """Auto-fill doesn't overwrite values the user has already entered."""
    # User already entered parking = $200
    database_connection.execute(
        "INSERT INTO apartment_cost (listing_id, base_rent, parking_fee, pet_fee) VALUES (?, ?, ?, ?)",
        (listing_with_url, 1832.0, 200.0, 0),
    )
    database_connection.commit()

    mock_fetch_page.return_value = "<html>page</html>"
    mock_extract_text.return_value = REALISTIC_PAGE_TEXT

    provider = MockLLMProvider(REALISTIC_CONCESSION_RESPONSE)
    extract_concessions(listing_with_url, database_connection, provider)

    cost_row = database_connection.execute(
        "SELECT * FROM apartment_cost WHERE listing_id = ?",
        (listing_with_url,),
    ).fetchone()

    # User's $200 parking is preserved, pet_fee auto-filled
    assert cost_row["parking_fee"] == 200.0
    assert cost_row["pet_fee"] == 25.0


# ── Skip conditions ──────────────────────────────────

def test_skip_when_no_url(database_connection, listing_without_url):
    """Extraction returns None when listing has no source URL."""
    provider = MockLLMProvider(REALISTIC_CONCESSION_RESPONSE)
    result = extract_concessions(listing_without_url, database_connection, provider)
    assert result is None


def test_skip_when_no_llm(database_connection, listing_with_url):
    """Extraction returns None when no LLM is configured."""
    result = extract_concessions(listing_with_url, database_connection, llm_provider=None)
    assert result is None


@patch("agents.apartment.services.concession_extractor.fetch_page")
def test_handles_fetch_error(mock_fetch_page, database_connection, listing_with_url):
    """Returns error dict when page fetch fails (403, timeout, etc)."""
    from shared.url_fetcher import FetchError
    mock_fetch_page.side_effect = FetchError("403 Forbidden — bot detection")

    provider = MockLLMProvider(REALISTIC_CONCESSION_RESPONSE)
    result = extract_concessions(listing_with_url, database_connection, provider)

    assert result is not None
    assert "error" in result
    assert "403" in result["error"]
