"""Concession and fee extraction prompt — extracts structured fee data from listing page text.

Sends page text to LLM, returns: concessions, application fee, admin fee,
pet deposit, parking cost, move-in total.
"""

import json

SYSTEM_PROMPT = (
    "You are a real estate data extraction specialist. "
    "Extract move-in specials, concession details, and fee information from the listing page text below. "
    "Only extract information that is explicitly stated — do not guess or infer. "
    "If a field is not mentioned in the text, use null. "
    "Return your extraction as JSON."
)

RESPONSE_SCHEMA = {
    "concessions": [
        {
            "description": "string — e.g. '2 months free on 14-month lease'",
            "lease_months": "integer or null — required lease length",
            "monthly_discount": "float or null — monthly savings from the concession",
        }
    ],
    "application_fee": "float or null",
    "admin_fee": "float or null",
    "pet_deposit": "float or null",
    "pet_monthly": "float or null",
    "parking_monthly": "float or null",
    "move_in_total": "float or null — estimated first month total if stated",
    "lease_terms_available": ["list of available lease lengths — e.g. '12 months', '14 months'"],
}


def build_concession_prompt(page_text: str, listing_title: str) -> str:
    """Build the extraction prompt with page content.

    Truncates page_text to ~8000 chars to stay within token budget.
    """
    # Truncate very long pages — concession info is usually near the top
    max_text_length = 8000
    truncated_text = page_text[:max_text_length]
    if len(page_text) > max_text_length:
        truncated_text += "\n[...page truncated]"

    return f"""Extract all concession, fee, and move-in cost information from this listing page for "{listing_title}".

Page content:
---
{truncated_text}
---

Return JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}

Important:
- Only extract fees/concessions that are explicitly mentioned
- Use null for any field not found in the text
- For concessions, calculate the monthly_discount if possible (e.g., 2 months free on 14-month lease = total_discount / 14)
- Convert all prices to numbers (no $ signs or commas in the JSON values)"""
