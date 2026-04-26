"""ATS resume optimizer — applies ATS rules to generated resumes.

Reads rules from ats_rules.json (updatable offline file).
Validates and scores resumes against ATS best practices.
"""

import json
from pathlib import Path

RULES_PATH = Path(__file__).parent / "ats_rules.json"


def load_rules() -> dict:
    """Load ATS rules from the local JSON file."""
    if RULES_PATH.exists():
        return json.loads(RULES_PATH.read_text())
    return {}


def get_section_order(seniority: str = "mid") -> list[str]:
    """Get recommended section order for a seniority level."""
    rules = load_rules()
    orders = rules.get("section_order", {})
    return orders.get(seniority, orders.get("mid", []))


def get_action_verbs() -> dict:
    """Get strong and weak action verbs."""
    rules = load_rules()
    return rules.get("section_rules", {}).get("experience", {}).get("action_verbs", {})


def validate_resume(content: str, seniority: str = "mid") -> dict:
    """Score a resume against ATS rules.

    Returns dict with score, issues found, and suggestions.
    """
    rules = load_rules()
    issues = []
    suggestions = []

    lines = content.split("\n")
    total_lines = len([l for l in lines if l.strip()])

    # Check length
    length_rules = rules.get("length_guidelines", {})
    if seniority in ("junior", "0-5_years") and total_lines > 60:
        issues.append("Resume may be too long for junior level (aim for 1 page)")

    # Check for weak action verbs
    weak_verbs = rules.get("section_rules", {}).get("experience", {}).get("action_verbs", {}).get("weak_avoid", [])
    for verb in weak_verbs:
        if verb.lower() in content.lower():
            issues.append(f"Weak action verb detected: '{verb}' — replace with a stronger verb")

    # Check for metrics in bullets
    bullet_lines = [l for l in lines if l.strip().startswith("-") or l.strip().startswith("*")]
    bullets_with_numbers = [l for l in bullet_lines if any(c.isdigit() for c in l)]
    if bullet_lines and len(bullets_with_numbers) < len(bullet_lines) * 0.3:
        suggestions.append("Add more quantified metrics — less than 30% of bullets have numbers")

    # Check sections exist
    required_sections = ["experience", "skills", "education"]
    content_lower = content.lower()
    for section in required_sections:
        if section not in content_lower:
            issues.append(f"Missing section: {section}")

    # Check contact info
    has_email = "@" in content
    has_phone = any(c.isdigit() for c in content[:200])
    if not has_email:
        issues.append("No email address found in resume")
    if not has_phone:
        suggestions.append("Consider adding phone number")

    # Score
    max_score = 100
    score = max_score - (len(issues) * 15) - (len(suggestions) * 5)
    score = max(0, min(100, score))

    return {
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "seniority": seniority,
        "rules_version": rules.get("_version", "unknown"),
    }


def get_formatting_tips() -> dict:
    """Get formatting recommendations."""
    rules = load_rules()
    return rules.get("formatting", {})
