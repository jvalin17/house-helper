"""Property overview prompt — tests for prompt construction.

Verifies the prompt includes all necessary context for the LLM.
"""

from agents.apartment.prompts.property_overview import build_overview_prompt, SYSTEM_PROMPT
from shared.llm.token_counter import count_text_tokens


SAMPLE_LISTING = {
    "title": "Alexan Braker Pointe",
    "address": "10801 N Mopac Expy, Austin, TX, 78759",
    "price": 1445.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "sqft": 720,
    "amenities": ["24 units", "Lounge (17%)", "Special Offer"],
    "latitude": 30.4186,
    "longitude": -97.7404,
    "source": "realtyapi",
}


class TestBuildOverviewPrompt:
    def test_prompt_includes_listing_title_and_address(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "Alexan Braker Pointe" in prompt
        assert "10801 N Mopac Expy" in prompt

    def test_prompt_includes_price_and_beds_baths(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "$1,445" in prompt
        assert "1" in prompt  # bedrooms

    def test_prompt_includes_amenities(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "24 units" in prompt
        assert "Lounge (17%)" in prompt

    def test_prompt_includes_coordinates(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "30.4186" in prompt
        assert "-97.7404" in prompt

    def test_prompt_includes_user_must_haves(self):
        preferences = {"must_haves": ["Parking", "In-unit W/D"], "deal_breakers": ["No dishwasher"]}
        prompt = build_overview_prompt(SAMPLE_LISTING, user_preferences=preferences)
        assert "Parking" in prompt
        assert "In-unit W/D" in prompt
        assert "No dishwasher" in prompt

    def test_prompt_includes_comparable_prices(self):
        comparables = [
            {"title": "Camden Stoneleigh", "price": 1109.0, "bedrooms": 1},
            {"title": "The Met", "price": 1600.0, "bedrooms": 1},
        ]
        prompt = build_overview_prompt(SAMPLE_LISTING, comparable_listings=comparables)
        assert "Camden Stoneleigh" in prompt
        assert "$1,109" in prompt

    def test_prompt_includes_neighborhood_questions(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "grocery" in prompt.lower()
        assert "restaurant" in prompt.lower()
        assert "transit" in prompt.lower()
        assert "airport" in prompt.lower()
        assert "noise" in prompt.lower()

    def test_prompt_includes_json_response_schema(self):
        prompt = build_overview_prompt(SAMPLE_LISTING)
        assert "price_verdict" in prompt
        assert "red_flags" in prompt
        assert "match_score" in prompt
        assert "neighborhood" in prompt

    def test_prompt_fits_within_reasonable_token_budget(self):
        """Full prompt with all context should fit in a single LLM call."""
        preferences = {"must_haves": ["Parking"], "deal_breakers": ["No dishwasher"]}
        comparables = [{"title": f"Comp {i}", "price": 1400 + i * 100, "bedrooms": 1} for i in range(5)]
        prompt = build_overview_prompt(SAMPLE_LISTING, preferences, comparables)
        token_count = count_text_tokens(prompt)
        assert token_count < 5000  # Should easily fit in any model's context

    def test_prompt_handles_missing_fields_gracefully(self):
        minimal_listing = {"title": "Basic Listing", "price": 1200}
        prompt = build_overview_prompt(minimal_listing)
        assert "Basic Listing" in prompt
        assert "$1,200" in prompt


class TestSystemPrompt:
    def test_system_prompt_is_concise(self):
        assert len(SYSTEM_PROMPT) < 500  # Should be brief
        assert "real estate" in SYSTEM_PROMPT.lower()
