"""Review mining service — tests for Google Places review fetching + sentiment analysis.

Covers: place search, review retrieval, LLM sentiment parsing,
graceful handling when no place found / no reviews / no API key.
"""

import json
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from shared.db import migrate
from shared.credentials import CredentialStore
from shared.llm.base import LLMProviderBase
from agents.apartment.services.review_mining_service import (
    fetch_and_analyze_reviews,
    _find_place_id,
    _get_place_details,
)
from agents.apartment.prompts.review_sentiment import build_review_sentiment_prompt


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def sample_listing_id(database_connection):
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings (title, address, price, latitude, longitude)
           VALUES (?, ?, ?, ?, ?)""",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX 78759", 1445.0, 30.4186, -97.7404),
    )
    database_connection.commit()
    return cursor.lastrowid


MOCK_SENTIMENT_RESPONSE = {
    "themes": [
        {"topic": "Maintenance", "sentiment": "positive", "mention_count": 7, "summary": "Generally responsive within 24 hours"},
        {"topic": "Noise", "sentiment": "negative", "mention_count": 3, "summary": "Highway noise from east-facing units"},
        {"topic": "Pool", "sentiment": "positive", "mention_count": 5, "summary": "Well-maintained, great for summer"},
    ],
    "key_quotes": [
        {"text": "Maintenance fixed my AC within 2 hours on a Saturday", "sentiment": "positive", "topic": "Maintenance"},
        {"text": "Can hear Mopac traffic at night from bedroom", "sentiment": "negative", "topic": "Noise"},
    ],
    "overall_sentiment": "positive",
    "average_rating": 4.2,
    "recommendation": "Good for professionals who prioritize quick maintenance, avoid east-facing units",
}

MOCK_GOOGLE_REVIEWS = [
    {"author_name": "Sarah Martinez", "rating": 5, "text": "Maintenance fixed my AC within 2 hours on a Saturday. Love this place!", "relative_time_description": "2 months ago"},
    {"author_name": "James Chen", "rating": 3, "text": "Nice amenities but can hear Mopac traffic at night from bedroom.", "relative_time_description": "3 months ago"},
    {"author_name": "Priya Patel", "rating": 4, "text": "Pool is great and well-maintained. Parking can be tight on weekends.", "relative_time_description": "1 month ago"},
]


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
    """Prompt includes the property name for context."""
    prompt = build_review_sentiment_prompt(MOCK_GOOGLE_REVIEWS, "Alexan Braker Pointe")
    assert "Alexan Braker Pointe" in prompt
    assert "Sarah Martinez" in prompt
    assert "Maintenance fixed my AC" in prompt


def test_prompt_limits_review_count():
    """Prompt truncates to 20 reviews max."""
    many_reviews = [{"author_name": f"Reviewer {index}", "rating": 4, "text": f"Review text {index}"} for index in range(30)]
    prompt = build_review_sentiment_prompt(many_reviews, "Test Property", review_count=30)
    assert "Showing 20 of 30" in prompt


# ── Full flow with mocked APIs ───────────────────────

@patch("agents.apartment.services.review_mining_service._get_place_details")
@patch("agents.apartment.services.review_mining_service._find_place_id")
def test_full_review_mining_with_sentiment(
    mock_find_place, mock_get_details,
    database_connection, sample_listing_id,
):
    """Full flow: find place → get reviews → LLM sentiment → structured result."""
    mock_find_place.return_value = "ChIJtest12345"
    mock_get_details.return_value = {
        "name": "Alexan Braker Pointe",
        "rating": 4.2,
        "user_ratings_total": 156,
        "reviews": MOCK_GOOGLE_REVIEWS,
    }

    CredentialStore(database_connection).set_key("google_maps", "gm-test-key-12345")
    provider = MockLLMProvider(MOCK_SENTIMENT_RESPONSE)

    result = fetch_and_analyze_reviews(sample_listing_id, database_connection, provider)

    assert result is not None
    assert result["google_rating"] == 4.2
    assert result["total_ratings"] == 156
    assert result["review_count"] == 3
    assert len(result["reviews"]) == 3
    assert result["reviews"][0]["author_name"] == "Sarah Martinez"

    # Sentiment analysis
    assert "sentiment" in result
    sentiment = result["sentiment"]
    assert len(sentiment["themes"]) == 3
    assert sentiment["themes"][0]["topic"] == "Maintenance"
    assert sentiment["themes"][0]["sentiment"] == "positive"
    assert sentiment["themes"][0]["mention_count"] == 7
    assert sentiment["overall_sentiment"] == "positive"
    assert "avoid east-facing" in sentiment["recommendation"]


@patch("agents.apartment.services.review_mining_service._get_place_details")
@patch("agents.apartment.services.review_mining_service._find_place_id")
def test_returns_raw_reviews_without_llm(
    mock_find_place, mock_get_details,
    database_connection, sample_listing_id,
):
    """Without LLM, returns raw reviews without sentiment analysis."""
    mock_find_place.return_value = "ChIJtest12345"
    mock_get_details.return_value = {
        "name": "Alexan Braker Pointe",
        "rating": 4.2,
        "user_ratings_total": 156,
        "reviews": MOCK_GOOGLE_REVIEWS,
    }

    CredentialStore(database_connection).set_key("google_maps", "gm-test-key-12345")

    result = fetch_and_analyze_reviews(sample_listing_id, database_connection, llm_provider=None)

    assert result is not None
    assert result["review_count"] == 3
    assert "sentiment" not in result  # No LLM = no sentiment


# ── Edge cases ───────────────────────────────────────

@patch("agents.apartment.services.review_mining_service._find_place_id")
def test_place_not_found(mock_find_place, database_connection, sample_listing_id):
    """Returns place_not_found when Google can't find the property."""
    mock_find_place.return_value = None
    CredentialStore(database_connection).set_key("google_maps", "gm-test-key-12345")

    result = fetch_and_analyze_reviews(sample_listing_id, database_connection)

    assert result is not None
    assert result["place_not_found"] is True
    assert "Alexan Braker Pointe" in result["property_name"]


@patch("agents.apartment.services.review_mining_service._get_place_details")
@patch("agents.apartment.services.review_mining_service._find_place_id")
def test_no_reviews_returns_rating(mock_find_place, mock_get_details, database_connection, sample_listing_id):
    """When place exists but has no reviews, returns Google rating only."""
    mock_find_place.return_value = "ChIJtest12345"
    mock_get_details.return_value = {
        "name": "Alexan Braker Pointe",
        "rating": 3.8,
        "user_ratings_total": 12,
        "reviews": [],
    }
    CredentialStore(database_connection).set_key("google_maps", "gm-test-key-12345")

    result = fetch_and_analyze_reviews(sample_listing_id, database_connection)

    assert result["no_reviews"] is True
    assert result["google_rating"] == 3.8
    assert result["total_ratings"] == 12


def test_skips_without_api_key(database_connection, sample_listing_id):
    """Returns None when Google Maps key not configured."""
    result = fetch_and_analyze_reviews(sample_listing_id, database_connection)
    assert result is None
