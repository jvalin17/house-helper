"""Neighborhood intel prompt — tests for build_neighborhood_intel_prompt().

Covers: prompt construction with realistic data, category formatting,
walk scores, airport distance, reviews summary, empty/missing data handling.
"""

import json

import pytest

from agents.apartment.prompts.neighborhood_intel import (
    build_neighborhood_intel_prompt,
    SYSTEM_PROMPT,
    RESPONSE_SCHEMA,
)


# ── Realistic test data ─────────────────────────────

AUSTIN_NEARBY_PLACES = {
    "categories": {
        "restaurant": {
            "label": "Restaurants",
            "places": [
                {
                    "name": "Uchi",
                    "rating": 4.7,
                    "total_ratings": 2847,
                    "distance_miles": 0.3,
                    "customer_reviews": [
                        "Best omakase in Austin, worth the wait",
                        "Innovative Japanese fusion, try the hama chili",
                    ],
                },
                {
                    "name": "Franklin Barbecue",
                    "rating": 4.8,
                    "total_ratings": 5432,
                    "distance_miles": 1.2,
                    "customer_reviews": ["Life-changing brisket"],
                },
            ],
        },
        "grocery_or_supermarket": {
            "label": "Grocery",
            "places": [
                {
                    "name": "H-E-B",
                    "rating": 4.5,
                    "total_ratings": 1234,
                    "distance_miles": 0.5,
                    "customer_reviews": [],
                },
            ],
        },
        "park": {
            "label": "Parks",
            "places": [
                {
                    "name": "Zilker Park",
                    "rating": 4.8,
                    "total_ratings": 9800,
                    "distance_miles": 0.8,
                    "customer_reviews": [],
                },
            ],
        },
    },
}

SAMPLE_WALK_SCORES = {
    "walk_score": 72,
    "transit_score": 41,
    "bike_score": 65,
}

SAMPLE_AIRPORT_DISTANCE = {
    "airport_distance_text": "12.3 mi",
    "airport_drive_text": "18 min",
}

SAMPLE_REVIEWS_SUMMARY = {
    "sentiment": {
        "recommendation": "Generally positive — residents praise walkability and dining options",
    },
}


# ── Basic prompt construction ────────────────────────

def test_prompt_includes_listing_title():
    """Prompt contains the listing title for context."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Modern 2BR at South Lamar" in prompt


def test_prompt_includes_listing_address():
    """Prompt contains the listing address."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "801 S Lamar Blvd, Austin, TX 78704" in prompt


def test_prompt_includes_place_names():
    """Prompt includes real place names from nearby data."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Uchi" in prompt
    assert "Franklin Barbecue" in prompt
    assert "H-E-B" in prompt
    assert "Zilker Park" in prompt


def test_prompt_includes_ratings():
    """Prompt includes rating values for places."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "4.7" in prompt  # Uchi rating
    assert "4.8" in prompt  # Franklin / Zilker rating


def test_prompt_includes_review_count():
    """Prompt includes total review counts in brackets."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "2847 reviews" in prompt
    assert "5432 reviews" in prompt


def test_prompt_includes_customer_review_excerpts():
    """Prompt embeds customer review text for intel quality."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Best omakase in Austin" in prompt
    assert "hama chili" in prompt
    assert "Life-changing brisket" in prompt


def test_prompt_includes_category_labels_with_counts():
    """Prompt shows category labels with place counts."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Restaurants (2 found)" in prompt
    assert "Grocery (1 found)" in prompt
    assert "Parks (1 found)" in prompt


def test_prompt_includes_distance():
    """Prompt includes distance in miles for places that have it."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "0.3mi" in prompt
    assert "1.2mi" in prompt


# ── Optional context ─────────────────────────────────

def test_prompt_includes_walk_scores():
    """Walk/transit/bike scores appear when provided."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
        walk_scores=SAMPLE_WALK_SCORES,
    )
    assert "Walk Score: 72" in prompt
    assert "Transit Score: 41" in prompt
    assert "Bike Score: 65" in prompt


def test_prompt_includes_airport_distance():
    """Airport distance context appears when provided."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
        airport_distance=SAMPLE_AIRPORT_DISTANCE,
    )
    assert "12.3 mi" in prompt
    assert "18 min" in prompt


def test_prompt_includes_resident_feedback():
    """Resident feedback recommendation appears when provided."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
        reviews_summary=SAMPLE_REVIEWS_SUMMARY,
    )
    assert "Generally positive" in prompt
    assert "walkability" in prompt


def test_prompt_omits_walk_scores_when_none():
    """Walk scores not mentioned when not provided."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Walk Score" not in prompt
    assert "Transit Score" not in prompt


def test_prompt_omits_airport_when_none():
    """Airport info not mentioned when not provided."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "Airport" not in prompt


# ── Edge cases ───────────────────────────────────────

def test_prompt_with_empty_categories():
    """Empty categories dict produces fallback message."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places={"categories": {}},
        listing_title="Empty Listing",
        listing_address="123 Nowhere St",
    )
    assert "No nearby places data available" in prompt


def test_prompt_with_no_categories_key():
    """Missing categories key produces fallback message."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places={},
        listing_title="Empty Listing",
        listing_address="123 Nowhere St",
    )
    assert "No nearby places data available" in prompt


def test_prompt_with_empty_places_in_category():
    """Categories with empty places lists are skipped."""
    nearby_data = {
        "categories": {
            "restaurant": {"label": "Restaurants", "places": []},
            "park": {
                "label": "Parks",
                "places": [
                    {"name": "Zilker Park", "rating": 4.8, "total_ratings": 9800},
                ],
            },
        },
    }
    prompt = build_neighborhood_intel_prompt(
        nearby_places=nearby_data,
        listing_title="Test Listing",
        listing_address="123 Test St",
    )
    # Restaurants section skipped (no places), Parks section included
    assert "Restaurants" not in prompt
    assert "Parks (1 found)" in prompt
    assert "Zilker Park" in prompt


def test_prompt_place_without_rating():
    """Place without rating doesn't show rating star."""
    nearby_data = {
        "categories": {
            "transit_station": {
                "label": "Transit",
                "places": [
                    {"name": "Capitol Metro Station", "total_ratings": 50},
                ],
            },
        },
    }
    prompt = build_neighborhood_intel_prompt(
        nearby_places=nearby_data,
        listing_title="Downtown Apartment",
        listing_address="100 Congress Ave",
    )
    assert "Capitol Metro Station" in prompt
    # Should not have a rating star for this place
    assert "Capitol Metro Station (⭐" not in prompt


def test_prompt_includes_response_schema():
    """Prompt includes the JSON response schema for the LLM."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
    )
    assert "neighborhood_score" in prompt
    assert "dining" in prompt
    assert "daily_essentials" in prompt
    assert "watch_out" in prompt
    assert "best_for" in prompt
    assert "not_ideal_for" in prompt


def test_prompt_limits_to_8_places_per_category():
    """Only first 8 places per category are included in the prompt."""
    many_restaurants = {
        "categories": {
            "restaurant": {
                "label": "Restaurants",
                "places": [
                    {"name": f"Restaurant {index}", "rating": 4.0, "total_ratings": 100}
                    for index in range(15)
                ],
            },
        },
    }
    prompt = build_neighborhood_intel_prompt(
        nearby_places=many_restaurants,
        listing_title="Test Listing",
        listing_address="123 Test St",
    )
    # First 8 should be present
    assert "Restaurant 0" in prompt
    assert "Restaurant 7" in prompt
    # 9th and beyond should not
    assert "Restaurant 8" not in prompt
    assert "Restaurant 14" not in prompt
    # But the count header shows total
    assert "Restaurants (15 found)" in prompt


def test_prompt_with_all_optional_context():
    """Full prompt with all optional context included."""
    prompt = build_neighborhood_intel_prompt(
        nearby_places=AUSTIN_NEARBY_PLACES,
        listing_title="Modern 2BR at South Lamar",
        listing_address="801 S Lamar Blvd, Austin, TX 78704",
        walk_scores=SAMPLE_WALK_SCORES,
        airport_distance=SAMPLE_AIRPORT_DISTANCE,
        reviews_summary=SAMPLE_REVIEWS_SUMMARY,
    )
    # All context sections present
    assert "Walk Score: 72" in prompt
    assert "12.3 mi" in prompt
    assert "Generally positive" in prompt
    assert "Uchi" in prompt


# ── Module-level constants ───────────────────────────

def test_system_prompt_mentions_neighborhood_analyst():
    """System prompt establishes the LLM's role."""
    assert "neighborhood analyst" in SYSTEM_PROMPT


def test_system_prompt_requires_json():
    """System prompt instructs the LLM to return JSON."""
    assert "Return JSON" in SYSTEM_PROMPT


def test_response_schema_has_required_keys():
    """Response schema defines all expected report sections."""
    assert "headline" in RESPONSE_SCHEMA
    assert "neighborhood_score" in RESPONSE_SCHEMA
    assert "dining" in RESPONSE_SCHEMA
    assert "daily_essentials" in RESPONSE_SCHEMA
    assert "schools" in RESPONSE_SCHEMA
    assert "fitness_outdoors" in RESPONSE_SCHEMA
    assert "transit_commute" in RESPONSE_SCHEMA
    assert "watch_out" in RESPONSE_SCHEMA
    assert "best_for" in RESPONSE_SCHEMA
    assert "not_ideal_for" in RESPONSE_SCHEMA
