"""Floor plan analyzer — tests for vision LLM analysis of floor plans.

Covers: prompt building, image retrieval, response parsing,
graceful skip when no vision/no image, livability score clamping.
"""

import base64
import json
import sqlite3

import pytest

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from agents.apartment.services.floor_plan_analyzer import (
    analyze_floor_plan,
    _detect_image_type,
    _get_floor_plan_image,
)
from agents.apartment.prompts.floor_plan_analysis import build_floor_plan_prompt


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_with_floor_plan(database_connection):
    """Create listing + floor plan image."""
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, address, price) VALUES (?, ?, ?)",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX 78759", 1445.0),
    )
    listing_id = cursor.lastrowid

    # Insert a floor plan with URL
    database_connection.execute(
        "INSERT INTO apartment_floor_plans (listing_id, image_url, unit_type) VALUES (?, ?, ?)",
        (listing_id, "https://example.com/floor-plan-studio-a.jpg", "Studio A"),
    )
    database_connection.commit()
    return listing_id


@pytest.fixture
def listing_without_floor_plan(database_connection):
    """Create listing with no floor plan."""
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, address, price) VALUES (?, ?, ?)",
        ("Camden North End", "4730 E Palm Valley Blvd, Round Rock, TX 78665", 1650.0),
    )
    database_connection.commit()
    return cursor.lastrowid


class MockVisionProvider(LLMProviderBase):
    """Mock LLM provider with vision support."""

    def __init__(self, response_json: dict):
        self._response = json.dumps(response_json)
        self._configured = True

    def complete(self, prompt, system=None, feature=None):
        return self._response

    def complete_with_images(self, prompt, images, system=None, feature=None):
        return self._response

    def provider_name(self):
        return "mock_vision"

    def model_name(self):
        return "mock-vision-4o"

    @property
    def supports_vision(self):
        return True

    def is_configured(self):
        return self._configured


class MockNonVisionProvider(LLMProviderBase):
    """Mock LLM provider WITHOUT vision support."""

    def complete(self, prompt, system=None, feature=None):
        return "{}"

    def provider_name(self):
        return "mock_text"

    def model_name(self):
        return "mock-text-only"

    def is_configured(self):
        return True


# ── Prompt building ───────────────────────────────────

def test_prompt_includes_property_context():
    """Prompt includes property name and address."""
    prompt = build_floor_plan_prompt(
        listing_title="Alexan Braker Pointe",
        address="10801 N Mopac Expy, Austin, TX 78759",
    )
    assert "Alexan Braker Pointe" in prompt
    assert "10801 N Mopac" in prompt
    assert "livability" in prompt.lower()
    assert "furniture" in prompt.lower()


def test_prompt_includes_unit_context():
    """When unit_context is provided, prompt includes floor/facing."""
    prompt = build_floor_plan_prompt(
        listing_title="Test Property",
        unit_context={"unit_type": "1BR Deluxe", "floor_number": 3, "direction": "South"},
    )
    assert "1BR Deluxe" in prompt
    assert "Floor: 3" in prompt
    assert "Facing: South" in prompt


# ── Image retrieval ───────────────────────────────────

def test_get_floor_plan_image_url(database_connection, listing_with_floor_plan):
    """Returns URL-based image data when only URL is stored."""
    images = _get_floor_plan_image(listing_with_floor_plan, database_connection)
    assert images is not None
    assert len(images) == 1
    assert "url" in images[0]
    assert images[0]["url"] == "https://example.com/floor-plan-studio-a.jpg"


def test_get_floor_plan_image_binary(database_connection, listing_with_floor_plan):
    """Returns base64-encoded binary when image_binary is stored."""
    # Add binary data to the existing floor plan
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header
    database_connection.execute(
        "UPDATE apartment_floor_plans SET image_binary = ? WHERE listing_id = ?",
        (fake_jpeg, listing_with_floor_plan),
    )
    database_connection.commit()

    images = _get_floor_plan_image(listing_with_floor_plan, database_connection)
    assert images is not None
    assert "data" in images[0]
    assert images[0]["media_type"] == "image/jpeg"


def test_get_floor_plan_image_none(database_connection, listing_without_floor_plan):
    """Returns None when no floor plan exists."""
    assert _get_floor_plan_image(listing_without_floor_plan, database_connection) is None


# ── Image type detection ──────────────────────────────

def test_detect_jpeg():
    assert _detect_image_type(b"\xff\xd8\xff\xe0JFIF") == "image/jpeg"

def test_detect_png():
    assert _detect_image_type(b"\x89PNG\r\n\x1a\n") == "image/png"

def test_detect_webp():
    assert _detect_image_type(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"

def test_detect_unknown_defaults_jpeg():
    assert _detect_image_type(b"\x00\x00\x00\x00") == "image/jpeg"


# ── Full analysis flow ────────────────────────────────

def test_analyze_returns_structured_result(database_connection, listing_with_floor_plan):
    """Full analysis returns structured JSON with livability score."""
    mock_response = {
        "livability_score": 78,
        "room_assessment": {"bedroom": "Adequate for queen bed", "kitchen": "Galley style, narrow"},
        "red_flags": ["Kitchen too narrow for two people"],
        "green_lights": ["Good natural light from south-facing windows"],
        "furniture_fit": {"queen_bed": True, "desk": True, "dining_table": False, "couch": True},
        "wfh_suitability": "Good — bedroom has space for desk by window",
        "efficiency_rating": "78% usable space",
        "questions_to_ask": ["Ask about closet depth"],
    }

    provider = MockVisionProvider(mock_response)
    result = analyze_floor_plan(listing_with_floor_plan, database_connection, provider)

    assert result is not None
    assert result["livability_score"] == 78
    assert result["furniture_fit"]["queen_bed"] is True
    assert result["furniture_fit"]["dining_table"] is False
    assert "Kitchen too narrow" in result["red_flags"][0]
    assert result["wfh_suitability"] == "Good — bedroom has space for desk by window"


def test_analyze_skips_without_vision(database_connection, listing_with_floor_plan):
    """Analysis returns None when LLM doesn't support vision."""
    provider = MockNonVisionProvider()
    result = analyze_floor_plan(listing_with_floor_plan, database_connection, provider)
    assert result is None


def test_analyze_skips_without_floor_plan(database_connection, listing_without_floor_plan):
    """Analysis returns None when no floor plan image exists."""
    provider = MockVisionProvider({"livability_score": 50})
    result = analyze_floor_plan(listing_without_floor_plan, database_connection, provider)
    assert result is None


def test_analyze_clamps_livability_score(database_connection, listing_with_floor_plan):
    """Livability score is clamped to 0-100 range."""
    provider = MockVisionProvider({"livability_score": 150})
    result = analyze_floor_plan(listing_with_floor_plan, database_connection, provider)
    assert result["livability_score"] == 100
