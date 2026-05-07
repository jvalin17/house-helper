"""Policy extractor — tests for LLM-based lease policy extraction.

Covers: prompt building, full extraction flow with realistic page text,
skip when no URL/no LLM, fetch error handling.
"""

import json
import sqlite3
from unittest.mock import patch

import pytest

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from agents.apartment.services.policy_extractor import extract_policies
from agents.apartment.prompts.policy_extraction import build_policy_prompt


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_with_url(database_connection):
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings (title, address, price, source_url)
           VALUES (?, ?, ?, ?)""",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX 78759",
         1445.0, "https://www.alexanbrakerpointe.com/"),
    )
    database_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def listing_without_url(database_connection):
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, price) VALUES (?, ?)",
        ("Manual Entry", 1200.0),
    )
    database_connection.commit()
    return cursor.lastrowid


MOCK_POLICY_RESPONSE = {
    "pet_policy": {
        "allowed": True,
        "breed_restrictions": "No aggressive breeds (Pit Bulls, Rottweilers, Dobermans)",
        "weight_limit_lbs": 75,
        "max_pets": 2,
        "monthly_pet_rent": 25.0,
        "one_time_deposit": 300.0,
    },
    "lease_terms": {
        "minimum_months": 12,
        "maximum_months": 15,
        "early_termination_fee": "2 months rent plus 60 days notice",
        "month_to_month_available": True,
        "month_to_month_premium": 250.0,
    },
    "subletting": {
        "allowed": False,
        "conditions": "Subletting is not permitted under any circumstances",
    },
    "guest_policy": {
        "max_consecutive_days": 14,
        "requires_registration": True,
        "notes": "Guests staying more than 3 days must be registered with the office",
    },
    "parking": {
        "included": False,
        "covered_monthly": 75.0,
        "uncovered_monthly": None,
        "garage_monthly": 150.0,
        "ev_charging": True,
    },
    "utilities": {
        "included": ["water", "trash", "pest control"],
        "tenant_responsible": ["electric", "internet", "renters insurance"],
        "estimated_monthly": None,
    },
    "move_in_requirements": {
        "credit_score_minimum": 620,
        "income_requirement": "3x monthly rent gross income",
        "background_check": True,
    },
}

REALISTIC_PAGE_TEXT = """
Alexan Braker Pointe - Apartment Community Policies

Pet Policy:
We welcome your furry friends! Up to 2 pets allowed per apartment.
Breed restrictions apply: No aggressive breeds (Pit Bulls, Rottweilers, Dobermans)
Weight limit: 75 lbs per pet
Monthly pet rent: $25/pet
One-time pet deposit: $300

Lease Terms:
Lease terms available from 12 to 15 months
Early termination: 2 months rent plus 60 days notice required
Month-to-month available at $250/mo premium after initial lease

No Subletting:
Subletting is not permitted under any circumstances.

Guest Policy:
Guests staying more than 3 days must be registered with the office.
Maximum consecutive stay: 14 days.

Parking:
Covered parking: $75/month
Garage parking: $150/month
EV charging stations available

Utilities Included: Water, trash, pest control
Tenant Pays: Electric, internet, renters insurance

Move-In Requirements:
Minimum credit score: 620
Income: 3x monthly rent gross income
Background check required
"""


class MockLLMProvider(LLMProviderBase):
    def __init__(self, response_json):
        self._response = json.dumps(response_json)

    def complete(self, prompt, system=None, feature=None):
        return self._response

    def provider_name(self):
        return "mock"

    def model_name(self):
        return "mock-4o"

    def is_configured(self):
        return True


# ── Prompt building ──────────────────────────────────

def test_prompt_includes_property_name():
    prompt = build_policy_prompt("Some page text", "Alexan Braker Pointe")
    assert "Alexan Braker Pointe" in prompt
    assert "pet_policy" in prompt
    assert "lease_terms" in prompt


def test_prompt_truncates_long_text():
    long_text = "Policy text. " * 2000
    prompt = build_policy_prompt(long_text, "Test Property")
    assert "[...page truncated]" in prompt


# ── Full extraction flow ─────────────────────────────

@patch("agents.apartment.services.policy_extractor.fetch_page")
@patch("agents.apartment.services.policy_extractor.extract_text_from_page")
def test_extract_policies_full_flow(mock_extract, mock_fetch, database_connection, listing_with_url):
    """Full extraction: fetch page → extract text → LLM → structured policies."""
    mock_fetch.return_value = "<html>page</html>"
    mock_extract.return_value = REALISTIC_PAGE_TEXT

    provider = MockLLMProvider(MOCK_POLICY_RESPONSE)
    result = extract_policies(listing_with_url, database_connection, provider)

    assert result is not None

    # Pet policy
    assert result["pet_policy"]["allowed"] is True
    assert result["pet_policy"]["weight_limit_lbs"] == 75
    assert result["pet_policy"]["max_pets"] == 2
    assert "Pit Bulls" in result["pet_policy"]["breed_restrictions"]

    # Lease terms
    assert result["lease_terms"]["minimum_months"] == 12
    assert result["lease_terms"]["month_to_month_available"] is True
    assert result["lease_terms"]["month_to_month_premium"] == 250.0

    # Subletting
    assert result["subletting"]["allowed"] is False

    # Parking
    assert result["parking"]["covered_monthly"] == 75.0
    assert result["parking"]["ev_charging"] is True

    # Move-in
    assert result["move_in_requirements"]["credit_score_minimum"] == 620
    assert result["move_in_requirements"]["income_requirement"] == "3x monthly rent gross income"


# ── Skip conditions ──────────────────────────────────

def test_skips_without_url(database_connection, listing_without_url):
    provider = MockLLMProvider(MOCK_POLICY_RESPONSE)
    assert extract_policies(listing_without_url, database_connection, provider) is None


def test_skips_without_llm(database_connection, listing_with_url):
    assert extract_policies(listing_with_url, database_connection, llm_provider=None) is None


@patch("agents.apartment.services.policy_extractor.fetch_page")
def test_handles_fetch_error(mock_fetch, database_connection, listing_with_url):
    from shared.url_fetcher import FetchError
    mock_fetch.side_effect = FetchError("403 Forbidden")

    provider = MockLLMProvider(MOCK_POLICY_RESPONSE)
    result = extract_policies(listing_with_url, database_connection, provider)

    assert result is not None
    assert "error" in result
    assert "403" in result["error"]
