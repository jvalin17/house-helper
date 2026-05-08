"""Photo analysis prompt — AI vision analysis of apartment visit photos.

Sends photos from an apartment tour to a vision-capable LLM and returns
structured analysis: room-by-room observations, condition scores,
natural light assessment, questions for landlord, move-in readiness.
"""

import json

SYSTEM_PROMPT = (
    "You are a property inspector analyzing photos from an apartment visit. "
    "The user took these photos during a tour. Analyze them for livability, condition, and practical concerns. "
    "Be honest and specific — mention visible wear, cleanliness, fixtures, and anything a renter should know. "
    "Return your analysis as JSON."
)

RESPONSE_SCHEMA = {
    "rooms": [
        {
            "room_type": "string — kitchen/bedroom/bathroom/living/exterior/other",
            "observations": "string — detailed description of what you see",
            "condition_score": "integer 1-10",
            "positives": ["list of good things noticed"],
            "concerns": ["list of issues or potential problems"],
        }
    ],
    "overall_condition": {
        "score": "integer 1-10",
        "explanation": "string — brief justification of the overall score",
    },
    "natural_light": "string — assessment of natural light quality across rooms",
    "storage_adequacy": "string — assessment of closets, cabinets, and storage space",
    "questions_for_landlord": ["list of questions to ask based on what the photos reveal"],
    "move_in_readiness": "ready | needs_work | needs_discussion",
    "summary": "string — 2-3 sentence overall summary of the apartment condition",
}


def build_photo_analysis_prompt(
    listing_title: str,
    address: str | None = None,
    room_tags: list[str] | None = None,
) -> str:
    """Build the user prompt for apartment photo vision analysis.

    Args:
        listing_title: Property name for context.
        address: Property address for context.
        room_tags: List of room tags assigned to the photos being analyzed.
    """
    context_lines = [
        f"Property: {listing_title}",
    ]
    if address:
        context_lines.append(f"Address: {address}")

    if room_tags:
        unique_tags = sorted(set(room_tags))
        context_lines.append(f"Photos tagged as: {', '.join(unique_tags)}")

    context_block = "\n".join(context_lines)

    return f"""Analyze these apartment visit photos for the following property:

{context_block}

Evaluate each photo and provide:
1. Room-by-room observations with condition scores (1-10)
2. Positives and concerns for each room
3. Overall condition score (1-10) with explanation
4. Natural light assessment across all rooms
5. Storage adequacy (closets, cabinets, shelving)
6. Questions to ask the landlord based on what you see
7. Move-in readiness: "ready" (looks good), "needs_work" (visible issues), or "needs_discussion" (unclear items to clarify)
8. A 2-3 sentence summary

Return your analysis as JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}"""
