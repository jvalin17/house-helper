"""Weighted match scoring with user calibration.

Computes match scores using feature weights that adjust over time
based on user judgements (which features predicted good matches).
"""

DEFAULT_WEIGHTS = {
    "skills_overlap": 0.3,
    "semantic_sim": 0.3,
    "tfidf": 0.2,
    "experience_years": 0.2,
}

# Maps user ratings to numeric values for weight calculation
RATING_SCORES = {"good": 1.0, "partial": 0.5, "poor": 0.0}


def compute_weighted_score(features: dict, weights: dict) -> float:
    """Compute a weighted match score from feature scores and calibration weights.

    features: {"skills_overlap": 0.8, "semantic_sim": 0.6, ...}
    weights: {"skills_overlap": 0.3, "semantic_sim": 0.3, ...}
    Returns float 0.0-1.0.
    """
    score = 0.0
    for feature_name, weight in weights.items():
        feature_value = features.get(feature_name, 0.0)
        score += weight * feature_value
    return score


def recalculate_weights(judgements: list[dict]) -> dict:
    """Adjust weights based on accumulated user judgements.

    Each judgement has match_features and user_rating.
    Features that correlate with "good" ratings get higher weights.
    """
    if not judgements:
        return dict(DEFAULT_WEIGHTS)

    # Collect all feature names
    all_features = set()
    for judgement in judgements:
        all_features.update(judgement.get("match_features", {}).keys())

    if not all_features:
        return dict(DEFAULT_WEIGHTS)

    # For each feature, compute correlation with positive ratings
    feature_importance = {}
    for feature in all_features:
        weighted_sum = 0.0
        count = 0
        for judgement in judgements:
            feature_value = judgement.get("match_features", {}).get(feature, 0.0)
            rating_score = RATING_SCORES.get(judgement.get("user_rating", "partial"), 0.5)
            # High feature value + good rating = important feature
            weighted_sum += feature_value * rating_score
            count += 1

        feature_importance[feature] = weighted_sum / count if count > 0 else 0.0

    # Normalize so weights sum to 1.0
    total = sum(feature_importance.values())
    if total == 0:
        return dict(DEFAULT_WEIGHTS)

    return {
        feature: importance / total
        for feature, importance in feature_importance.items()
    }
