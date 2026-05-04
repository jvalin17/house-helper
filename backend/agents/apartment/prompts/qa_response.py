"""Prompt for Q&A about a listing — LLM answers using listing context.

User asks anything about the property. LLM answers using ONLY the
data we have — listing details, analysis, preferences, neighborhood.
If the data doesn't cover the question, it says so.
"""

SYSTEM_PROMPT = (
    "You are a helpful apartment hunting assistant. Answer the user's question "
    "using ONLY the property data provided below. Be specific and concise. "
    "If the data doesn't contain the answer, say so honestly and suggest "
    "what the user should ask the landlord or check on a tour."
)


def build_qa_prompt(
    listing: dict,
    question: str,
    previous_qa: list[dict] | None = None,
    analysis: dict | None = None,
    user_preferences: dict | None = None,
) -> str:
    """Build a Q&A prompt with full listing context.

    Args:
        listing: Full listing data
        question: User's question
        previous_qa: Previous Q&A for this listing [{question, answer}, ...]
        analysis: Cached LLM analysis (overview, neighborhood, etc.)
        user_preferences: {must_haves, deal_breakers}
    """
    sections = []

    # Property context
    sections.append("## Property Data\n")
    for field_label, field_key in [
        ("Title", "title"), ("Address", "address"), ("Price", "price"),
        ("Bedrooms", "bedrooms"), ("Bathrooms", "bathrooms"),
        ("Square feet", "sqft"), ("Source URL", "source_url"),
    ]:
        value = listing.get(field_key)
        if value is not None:
            if field_key == "price":
                sections.append(f"- {field_label}: ${value:,.0f}/month")
            else:
                sections.append(f"- {field_label}: {value}")

    amenities = listing.get("amenities") or []
    if amenities:
        sections.append(f"\nFeatures: {', '.join(amenities)}")

    # Previous analysis (if available)
    if analysis:
        sections.append("\n## Previous Analysis\n")
        if analysis.get("overview"):
            sections.append(f"Overview: {analysis['overview']}")
        if analysis.get("neighborhood"):
            neighborhood = analysis["neighborhood"]
            if isinstance(neighborhood, dict) and neighborhood.get("summary"):
                sections.append(f"Neighborhood: {neighborhood['summary']}")
        if analysis.get("red_flags"):
            sections.append(f"Red flags: {', '.join(analysis['red_flags'])}")
        if analysis.get("green_lights"):
            sections.append(f"Strengths: {', '.join(analysis['green_lights'])}")

    # User preferences
    if user_preferences:
        must_haves = user_preferences.get("must_haves") or []
        deal_breakers = user_preferences.get("deal_breakers") or []
        if must_haves or deal_breakers:
            sections.append("\n## User Preferences\n")
            if must_haves:
                sections.append(f"Must-haves: {', '.join(must_haves)}")
            if deal_breakers:
                sections.append(f"Deal-breakers: {', '.join(deal_breakers)}")

    # Previous Q&A for context continuity
    if previous_qa:
        sections.append("\n## Previous Questions\n")
        for qa_entry in previous_qa[-5:]:  # Last 5 to keep context manageable
            sections.append(f"Q: {qa_entry['question']}")
            sections.append(f"A: {qa_entry['answer']}\n")

    # Current question
    sections.append(f"\n## User's Question\n\n{question}")

    return "\n".join(sections)
