"""Policy extraction prompt — extracts lease policies from listing page text.

Extracts: pet policy (breeds, weight), subletting rules, guest policy,
lease break penalty, parking rules, noise policy.
"""

import json

SYSTEM_PROMPT = (
    "You are a real estate policy analyst. Extract lease and community policies "
    "from the listing page text below. Only extract information that is explicitly stated. "
    "If a policy is not mentioned, use null. Return your extraction as JSON."
)

RESPONSE_SCHEMA = {
    "pet_policy": {
        "allowed": "boolean or null",
        "breed_restrictions": "string or null — e.g. 'No aggressive breeds'",
        "weight_limit_lbs": "integer or null",
        "max_pets": "integer or null",
        "monthly_pet_rent": "float or null",
        "one_time_deposit": "float or null",
    },
    "lease_terms": {
        "minimum_months": "integer or null",
        "maximum_months": "integer or null",
        "early_termination_fee": "string or null — e.g. '2 months rent'",
        "month_to_month_available": "boolean or null",
        "month_to_month_premium": "float or null — extra per month",
    },
    "subletting": {
        "allowed": "boolean or null",
        "conditions": "string or null",
    },
    "guest_policy": {
        "max_consecutive_days": "integer or null",
        "requires_registration": "boolean or null",
        "notes": "string or null",
    },
    "parking": {
        "included": "boolean or null",
        "covered_monthly": "float or null",
        "uncovered_monthly": "float or null",
        "garage_monthly": "float or null",
        "ev_charging": "boolean or null",
    },
    "utilities": {
        "included": ["list of included utilities — e.g. 'water', 'trash', 'internet'"],
        "tenant_responsible": ["list of tenant-paid utilities"],
        "estimated_monthly": "float or null",
    },
    "move_in_requirements": {
        "credit_score_minimum": "integer or null",
        "income_requirement": "string or null — e.g. '3x monthly rent'",
        "background_check": "boolean or null",
    },
}


def build_policy_prompt(page_text: str, property_name: str) -> str:
    """Build extraction prompt for lease policies."""
    max_text_length = 10000
    truncated_text = page_text[:max_text_length]
    if len(page_text) > max_text_length:
        truncated_text += "\n[...page truncated]"

    return f"""Extract all lease policies and community rules from this listing page for "{property_name}".

Page content:
---
{truncated_text}
---

Return JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}

Important:
- Only extract policies explicitly mentioned in the text
- Use null for any field not found
- Convert monetary values to numbers (no $ signs)
- For breed restrictions, quote the exact language used"""
