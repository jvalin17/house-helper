"""Neighborhood intelligence prompt — curates raw nearby places data into actionable insights.

Takes raw Google Places data (restaurants, schools, grocery, transit, etc.)
and produces a curated, opinionated neighborhood report with:
- Top picks per category (not just counts)
- What's missing or weak
- Red flags (noise, distance to essentials, low-rated schools)
- Daily life assessment
"""

import json

SYSTEM_PROMPT = (
    "You are a neighborhood analyst helping someone decide if an apartment "
    "is right for them. Be honest and specific. Mention real place names. "
    "Flag problems — thin walls, highway noise, missing essentials. "
    "The user is spending money on this Intel — give them information they "
    "can't get from a 5-second Google search. Return JSON."
)

RESPONSE_SCHEMA = {
    "headline": "string — one sentence verdict, e.g. 'Great walkable neighborhood with strong dining but weak transit'",
    "neighborhood_score": "integer 0-100",
    "dining": {
        "verdict": "string — e.g. 'Strong variety, mostly casual'",
        "top_picks": [
            {"name": "string", "cuisine": "string", "rating": "float", "why": "string — one line"}
        ],
        "cuisines_available": ["list of cuisine types found"],
        "missing": "string or null — what's NOT available nearby",
    },
    "daily_essentials": {
        "verdict": "string — e.g. 'Well-served, H-E-B within walking distance'",
        "grocery": [{"name": "string", "distance_note": "string", "rating": "float"}],
        "pharmacy": [{"name": "string", "distance_note": "string"}],
        "library": "string or null — nearest library",
    },
    "schools": {
        "verdict": "string — e.g. 'Mixed — good elementary, weak middle school'",
        "notable": [{"name": "string", "rating": "float", "note": "string"}],
    },
    "fitness_outdoors": {
        "verdict": "string",
        "parks": [{"name": "string", "note": "string"}],
        "gyms": [{"name": "string", "rating": "float"}],
    },
    "transit_commute": {
        "verdict": "string — e.g. 'Car-dependent, limited bus service'",
        "nearest_transit": "string or null",
        "notes": "string",
    },
    "watch_out": [
        "string — red flags: noise sources, missing essentials, safety concerns, low-rated services"
    ],
    "best_for": "string — who would love this neighborhood (e.g. 'Young professionals who drive, enjoy dining out')",
    "not_ideal_for": "string — who should look elsewhere (e.g. 'Families with school-age kids, transit-dependent commuters')",
}


def build_neighborhood_intel_prompt(
    nearby_places: dict,
    listing_title: str,
    listing_address: str,
    walk_scores: dict | None = None,
    airport_distance: dict | None = None,
    reviews_summary: dict | None = None,
) -> str:
    """Build prompt for LLM to curate raw nearby places into neighborhood intel."""

    # Format nearby places by category
    categories_text = []
    categories = nearby_places.get("categories") or {}
    for category_key, category_data in categories.items():
        places = category_data.get("places") or []
        if not places:
            continue
        place_lines = []
        for place in places[:8]:
            rating_text = f" (⭐{place['rating']})" if place.get("rating") else ""
            reviews_text = f" [{place['total_ratings']} reviews]" if place.get("total_ratings") else ""
            distance_text = f" — {place['distance_miles']}mi" if place.get("distance_miles") else ""
            place_line = f"  - {place['name']}{rating_text}{reviews_text}{distance_text}"

            # Include customer review excerpts — this is what makes the intel real
            customer_reviews = place.get("customer_reviews") or []
            if customer_reviews:
                review_excerpts = [f'    "{review[:150]}"' for review in customer_reviews[:3]]
                place_line += "\n" + "\n".join(review_excerpts)

            place_lines.append(place_line)
        categories_text.append(f"{category_data['label']} ({len(places)} found):\n" + "\n".join(place_lines))

    nearby_block = "\n\n".join(categories_text) if categories_text else "No nearby places data available."

    # Additional context
    context_parts = [f"Property: {listing_title}", f"Address: {listing_address}"]

    if walk_scores:
        walk = walk_scores.get("walk_score")
        transit = walk_scores.get("transit_score")
        bike = walk_scores.get("bike_score")
        context_parts.append(f"Walk Score: {walk}, Transit Score: {transit}, Bike Score: {bike}")

    if airport_distance:
        context_parts.append(f"Airport: {airport_distance.get('airport_distance_text')} ({airport_distance.get('airport_drive_text')})")

    if reviews_summary:
        sentiment = reviews_summary.get("sentiment") or {}
        recommendation = sentiment.get("recommendation")
        if recommendation:
            context_parts.append(f"Resident feedback: {recommendation}")

    context_block = "\n".join(context_parts)

    return f"""Analyze this neighborhood for someone considering this apartment.

{context_block}

Raw nearby places data:
{nearby_block}

Provide a curated neighborhood report. For each category:
- Pick the TOP 3-5 places (not all 20) — the ones a resident would actually use
- For restaurants: show DIVERSITY of cuisines (Indian, Asian, Mexican, Italian, etc.) — not just American chains
- For grocery: list ALL types — mainstream (H-E-B, Walmart) AND specialty/international stores (Indian, Asian, Middle Eastern, Mexican, etc.) if any exist nearby. This matters to many residents
- For schools: include any available rating or reputation note
- Also mention: farmers markets, libraries, community centers, co-working spaces if notable ones exist
- Flag what's MISSING (no pharmacy nearby? no specialty grocery? no diverse dining? no good transit? no parks?)
- Be honest about problems — highway noise, food deserts, weak transit, thin walls, safety concerns
- Don't assume what the user cares about — present all options and let them decide

Return JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}"""
