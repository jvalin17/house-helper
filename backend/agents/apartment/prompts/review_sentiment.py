"""Review sentiment analysis prompt — extracts themes from resident reviews.

Takes raw Google Places reviews and returns structured sentiment analysis:
themes with counts, key quotes, overall rating, recommendation.
"""

import json

SYSTEM_PROMPT = (
    "You are a real estate analyst specializing in resident satisfaction. "
    "Analyze these property reviews and extract key themes that would matter "
    "to someone deciding whether to live here. Be objective — highlight both "
    "positives and negatives. Return your analysis as JSON."
)

RESPONSE_SCHEMA = {
    "themes": [
        {
            "topic": "string — e.g. 'Maintenance', 'Noise', 'Management', 'Amenities'",
            "sentiment": "'positive' | 'negative' | 'mixed'",
            "mention_count": "integer — how many reviews mention this topic",
            "summary": "string — one-sentence summary of what reviewers say",
        }
    ],
    "key_quotes": [
        {
            "text": "string — direct quote from a review",
            "sentiment": "'positive' | 'negative'",
            "topic": "string — which theme this relates to",
        }
    ],
    "overall_sentiment": "'positive' | 'negative' | 'mixed'",
    "average_rating": "float — average star rating if available",
    "recommendation": "string — one-sentence recommendation for apartment hunters",
}


def build_review_sentiment_prompt(
    reviews: list[dict],
    property_name: str,
    review_count: int | None = None,
) -> str:
    """Build prompt for LLM sentiment analysis of reviews.

    Args:
        reviews: List of review dicts with text, rating, author_name, time
        property_name: The apartment complex name
        review_count: Total number of reviews (may be more than provided)
    """
    # Format reviews for the prompt — limit to 20 most useful
    max_reviews_for_prompt = 20
    formatted_reviews = []
    for review in reviews[:max_reviews_for_prompt]:
        lines = []
        if review.get("author_name"):
            lines.append(f"Author: {review['author_name']}")
        if review.get("rating"):
            lines.append(f"Rating: {review['rating']}/5")
        if review.get("text"):
            lines.append(f"Review: {review['text']}")
        if review.get("relative_time_description"):
            lines.append(f"Posted: {review['relative_time_description']}")
        formatted_reviews.append("\n".join(lines))

    reviews_block = "\n---\n".join(formatted_reviews)

    count_note = ""
    displayed_count = min(len(reviews), max_reviews_for_prompt)
    if review_count and review_count > displayed_count:
        count_note = f"\n(Showing {displayed_count} of {review_count} total reviews)"

    return f"""Analyze these resident reviews for "{property_name}".{count_note}

Reviews:
{reviews_block}

Extract:
1. Key themes (maintenance, noise, management, amenities, parking, pests, etc.)
2. For each theme: sentiment (positive/negative/mixed) and how many reviews mention it
3. 3-5 most impactful direct quotes
4. Overall sentiment and recommendation

Return JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA, indent=2)}"""
