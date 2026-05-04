"""Q&A prompt — tests for prompt construction with listing context."""

from agents.apartment.prompts.qa_response import build_qa_prompt, SYSTEM_PROMPT


SAMPLE_LISTING = {
    "title": "Alexan Braker Pointe",
    "address": "10801 N Mopac Expy, Austin, TX, 78759",
    "price": 1445.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "amenities": ["24 units", "Pool", "Lounge"],
    "source_url": "https://www.zillow.com/homedetails/12345_zpid/",
}


class TestBuildQaPrompt:
    def test_prompt_includes_listing_context(self):
        prompt = build_qa_prompt(SAMPLE_LISTING, "Is parking included?")
        assert "Alexan Braker Pointe" in prompt
        assert "$1,445" in prompt
        assert "Is parking included?" in prompt

    def test_prompt_includes_previous_qa(self):
        previous = [
            {"question": "Is it pet friendly?", "answer": "Yes, the listing mentions pet amenities."},
        ]
        prompt = build_qa_prompt(SAMPLE_LISTING, "What about large dogs?", previous_qa=previous)
        assert "Is it pet friendly?" in prompt
        assert "pet amenities" in prompt
        assert "What about large dogs?" in prompt

    def test_prompt_includes_analysis_context(self):
        analysis = {
            "overview": "Modern complex in North Austin.",
            "neighborhood": {"summary": "Tech corridor near Domain."},
            "red_flags": ["Highway noise"],
            "green_lights": ["Below market price"],
        }
        prompt = build_qa_prompt(SAMPLE_LISTING, "Is it noisy?", analysis=analysis)
        assert "North Austin" in prompt
        assert "Highway noise" in prompt

    def test_prompt_includes_user_preferences(self):
        preferences = {"must_haves": ["Parking"], "deal_breakers": ["No dishwasher"]}
        prompt = build_qa_prompt(SAMPLE_LISTING, "Does it have parking?", user_preferences=preferences)
        assert "Parking" in prompt
        assert "No dishwasher" in prompt

    def test_prompt_limits_previous_qa_to_five(self):
        previous = [{"question": f"Q{index}?", "answer": f"A{index}."} for index in range(10)]
        prompt = build_qa_prompt(SAMPLE_LISTING, "New question?", previous_qa=previous)
        assert "Q5?" in prompt  # 6th entry (index 5) should be included (last 5)
        assert "Q9?" in prompt
        assert "Q0?" not in prompt  # First entries trimmed


class TestSystemPrompt:
    def test_system_prompt_instructs_helpful_answers(self):
        assert "knowledge" in SYSTEM_PROMPT.lower()
        assert "landlord" in SYSTEM_PROMPT.lower()
