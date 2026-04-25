"""Exact + fuzzy skill matching using RapidFuzz.

Matches job-required skills against a user's skill list.
Handles common variations: "React.js" ≈ "ReactJS", case differences, etc.
"""

from rapidfuzz import fuzz

FUZZY_MATCH_THRESHOLD = 75  # minimum RapidFuzz score (0-100) to consider a match


def find_best_match(
    skill: str, candidates: list[str]
) -> tuple[float, str | None]:
    """Find the best matching skill from a list of candidates.

    Returns (confidence 0.0-1.0, matched_skill or None).
    """
    if not candidates:
        return 0.0, None

    skill_lower = skill.lower()

    # Try exact match first (case-insensitive)
    for candidate in candidates:
        if candidate.lower() == skill_lower:
            return 1.0, candidate

    # Fuzzy match using token_sort_ratio (handles word reordering)
    best_score = 0.0
    best_match = None

    for candidate in candidates:
        score = fuzz.token_sort_ratio(skill_lower, candidate.lower())
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_score / 100.0, best_match

    return best_score / 100.0, None


def compute_skill_overlap(
    required_skills: list[str], user_skills: list[str]
) -> dict:
    """Score how well required skills overlap with user skills.

    Returns dict with score (0.0-1.0), matched details, and missing skills.
    """
    if not required_skills:
        return {"score": 1.0, "matched": [], "missing": []}

    if not user_skills:
        return {"score": 0.0, "matched": [], "missing": list(required_skills)}

    matched = []
    missing = []

    for required in required_skills:
        confidence, matched_skill = find_best_match(required, user_skills)

        if matched_skill is not None:
            matched.append({
                "required": required,
                "matched_with": matched_skill,
                "confidence": confidence,
            })
        else:
            missing.append(required)

    score = len(matched) / len(required_skills)

    return {"score": score, "matched": matched, "missing": missing}
