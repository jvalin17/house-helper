"""Filter LLM suggestions against user-rejected ones.

Matching strategy:
- Check if the rejected original_bullet text appears in the new suggestion
- Check if key phrases from the rejection appear in the new suggestion
- Both use case-insensitive substring matching
"""


def filter_suggestions(
    suggestions: list[dict],
    rejections: list[dict],
) -> list[dict]:
    """Remove suggestions that match previously rejected ones."""
    if not rejections:
        return suggestions

    # Build rejection matchers: key phrases from suggestion_text + original_bullet
    rejection_phrases: list[set[str]] = []
    for rej in rejections:
        phrases = set()
        # Extract meaningful phrases from the rejected suggestion
        for text in [rej.get("suggestion_text", ""), rej.get("original_bullet", "")]:
            if text:
                phrases.update(_extract_key_phrases(text.lower()))
        if phrases:
            rejection_phrases.append(phrases)

    result = []
    for suggestion in suggestions:
        desc = (suggestion.get("description") or "").lower()
        if not _matches_any_rejection(desc, rejection_phrases):
            result.append(suggestion)

    return result


def _matches_any_rejection(description: str, rejection_phrases: list[set[str]]) -> bool:
    """Check if a suggestion description matches any rejection."""
    for phrases in rejection_phrases:
        # If 2+ key phrases from the rejection appear in this suggestion, it's a match
        match_count = sum(1 for phrase in phrases if phrase in description)
        if match_count >= 2:
            return True
    return False


def _extract_key_phrases(text: str) -> list[str]:
    """Extract meaningful multi-word phrases from text for matching."""
    phrases = []

    # Domain-specific phrases that indicate the same suggestion
    keyword_groups = [
        "llm sentiment",
        "gen ai",
        "sentiment analysis",
        "ml model integration",
        "ai-driven",
        "ml inference",
        "feedback system",
        "email feedback",
        "notification pipeline",
    ]

    for kw in keyword_groups:
        if kw in text:
            phrases.append(kw)

    # Also extract 3-word sequences from the text for generic matching
    words = text.split()
    for i in range(len(words) - 2):
        trigram = " ".join(words[i:i + 3])
        if len(trigram) > 10:  # skip short trigrams
            phrases.append(trigram)

    return phrases
