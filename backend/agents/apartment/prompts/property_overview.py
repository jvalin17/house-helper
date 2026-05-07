"""Prompt for property overview analysis — LLM returns structured JSON.

Includes neighborhood questions (Layer 1 — LLM training data).
The LLM analyzes listing data + user preferences + comparable listings
and returns: overview, price verdict, neighborhood intel, red flags,
green lights, questions to ask on tour, and match score.
"""

import json

SYSTEM_PROMPT = (
    "You are a real estate analyst helping someone find their perfect apartment. "
    "Analyze the listing data honestly — highlight both strengths and concerns. "
    "Be specific: use real place names from your knowledge when discussing the neighborhood. "
    "If you're not confident about something, say so rather than guessing."
)

RESPONSE_SCHEMA = """{
  "overview": "2-3 sentence summary of the property — what makes it unique",
  "price_verdict": "below_market | fair | overpriced",
  "price_reasoning": "Why this verdict (compare to area, features for the price)",
  "neighborhood": {
    "summary": "2-3 sentence neighborhood description",
    "nearby_grocery": ["Store name (~distance)", ...],
    "ethnic_grocery": ["Indian/Asian/Mexican store name (~distance)", ...],
    "farmers_markets": ["Market name — day/time (~distance)", ...],
    "nearby_restaurants": ["Restaurant name — cuisine (~distance)", ...],
    "nearby_parks": ["Park name (~distance)", ...],
    "weekend_activities": ["Activity/event — details", ...],
    "family_friendly": "Assessment of schools, playgrounds, safety",
    "transit_access": "Public transit options and quality",
    "walkability": "How walkable is daily life here",
    "noise_concerns": "Any noise issues (highway, airport, nightlife)",
    "nearest_airport": "Airport name and approximate distance"
  },
  "red_flags": ["Specific concern 1", "Specific concern 2"],
  "green_lights": ["Specific strength 1", "Specific strength 2"],
  "questions_to_ask": ["Question 1 to ask on tour", "Question 2"],
  "match_score": 0-100,
  "match_reasoning": "Why this score based on user's must-haves and deal-breakers"
}"""


def build_overview_prompt(
    listing: dict,
    user_preferences: dict | None = None,
    comparable_listings: list[dict] | None = None,
) -> str:
    """Build the property overview prompt with all context.

    Args:
        listing: Full listing data (title, address, price, beds, baths, amenities, etc.)
        user_preferences: {must_haves: [...], deal_breakers: [...]}
        comparable_listings: Similar listings for price comparison
    """
    sections = []

    # Property data
    sections.append("## Property to Analyze\n")
    property_fields = {
        "Title": listing.get("title"),
        "Address": listing.get("address"),
        "Price": f"${listing['price']:,.0f}/month" if listing.get("price") else "Not listed",
        "Bedrooms": listing.get("bedrooms"),
        "Bathrooms": listing.get("bathrooms"),
        "Square feet": listing.get("sqft"),
        "Source": listing.get("source"),
    }
    for field_label, field_value in property_fields.items():
        if field_value is not None:
            sections.append(f"- {field_label}: {field_value}")

    # Amenities/features
    amenities = listing.get("amenities") or []
    if amenities:
        sections.append(f"\nFeatures: {', '.join(amenities)}")

    # Coordinates for neighborhood analysis
    latitude = listing.get("latitude")
    longitude = listing.get("longitude")
    if latitude and longitude:
        sections.append(f"\nCoordinates: {latitude}, {longitude}")

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

    # Comparable listings for price context
    if comparable_listings:
        sections.append("\n## Comparable Listings in Area\n")
        for comparable in comparable_listings[:5]:
            comparable_price = comparable.get("price")
            comparable_beds = comparable.get("bedrooms")
            comparable_title = comparable.get("title", "")[:50]
            if comparable_price:
                sections.append(f"- {comparable_title}: ${comparable_price:,.0f}/mo, {comparable_beds}BR")

    # Neighborhood analysis request
    address = listing.get("address") or "this location"
    sections.append(f"""
## Neighborhood Analysis

Based on your knowledge of {address}:
1. What grocery stores are nearby? Include:
   - Major chains (H-E-B, Whole Foods, Trader Joe's, etc.)
   - Multi-cultural/ethnic grocery stores (Indian, Asian, Mexican, Middle Eastern, etc.)
   - Farmers markets or weekend markets (name, day/time if known)
2. Top-rated restaurants within walking/driving distance? Include diverse cuisines.
3. Parks, playgrounds, or family-friendly places nearby?
4. Weekend activities — farmers markets, community events, outdoor areas?
5. How is public transit access?
6. How walkable is daily life (grocery, coffee, errands)?
7. Any noise concerns? (highway proximity, airport flight path, nightlife district)
8. What is the nearest major airport and approximate distance?
9. General safety feel and neighborhood character?

Use real place names from your knowledge. If unsure, note that.
""")

    # Response format
    sections.append(f"\n## Response Format\n\nReturn valid JSON matching this schema:\n```\n{RESPONSE_SCHEMA}\n```")

    return "\n".join(sections)
