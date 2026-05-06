"""Floor plan vision analysis prompt — sends floor plan image to vision LLM.

Returns structured assessment: livability score, room-by-room analysis,
furniture fit, WFH suitability, red flags, green lights.
"""

import json

SYSTEM_PROMPT = (
    "You are an experienced architect and interior designer analyzing a floor plan image. "
    "Analyze for livability, furniture fit, and practical daily use. "
    "Be honest and specific — mention exact dimensions if visible, flag tight spaces, "
    "and note layout efficiency. Return your analysis as JSON."
)

RESPONSE_SCHEMA = {
    "livability_score": "integer 0-100",
    "room_assessment": {
        "bedroom": "string — size assessment, natural light, closet space",
        "kitchen": "string — counter space, appliance layout, workspace",
        "bathroom": "string — vanity space, shower vs tub, storage",
        "living": "string — shape, furniture arrangement potential",
    },
    "red_flags": ["list of concerns — tight spaces, awkward layouts, wasted space"],
    "green_lights": ["list of strengths — good flow, natural light, storage"],
    "furniture_fit": {
        "queen_bed": "boolean — fits a queen bed comfortably",
        "desk": "boolean — space for a work desk",
        "dining_table": "boolean — fits a 4-person dining table",
        "couch": "boolean — fits a standard sofa",
    },
    "wfh_suitability": "string — assessment of work-from-home potential",
    "efficiency_rating": "string — percentage of usable vs wasted space",
    "questions_to_ask": ["list of questions for leasing office based on the floor plan"],
}


def build_floor_plan_prompt(
    listing_title: str,
    address: str | None = None,
    unit_context: dict | None = None,
) -> str:
    """Build the user prompt for floor plan vision analysis.

    Args:
        listing_title: Property name
        address: Property address
        unit_context: Optional dict with unit_type, floor_number, direction
    """
    context_lines = [
        f"Property: {listing_title}",
    ]
    if address:
        context_lines.append(f"Address: {address}")

    if unit_context:
        unit_type = unit_context.get("unit_type", "Unknown")
        floor_number = unit_context.get("floor_number")
        direction = unit_context.get("direction")
        context_lines.append(f"Unit type: {unit_type}")
        if floor_number:
            context_lines.append(f"Floor: {floor_number}")
        if direction:
            context_lines.append(f"Facing: {direction}")

    context_block = "\n".join(context_lines)

    return f"""Analyze this floor plan image for the following property:

{context_block}

Evaluate:
1. Overall livability (score 0-100)
2. Room-by-room assessment (bedroom, kitchen, bathroom, living area)
3. Red flags (tight spaces, awkward layouts, wasted space, poor flow)
4. Green lights (good natural light, smart storage, efficient layout)
5. Furniture fit — can it comfortably hold: queen bed, work desk, dining table, couch?
6. Work-from-home suitability
7. Space efficiency rating
8. Questions to ask the leasing office about this layout

Return your analysis as JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}"""
