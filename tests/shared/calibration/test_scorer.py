"""Tests for calibration/scorer — weighted match scoring with user calibration."""

from shared.calibration.scorer import compute_weighted_score, recalculate_weights

DEFAULT_WEIGHTS = {
    "skills_overlap": 0.3,
    "semantic_sim": 0.3,
    "tfidf": 0.2,
    "experience_years": 0.2,
}


class TestComputeWeightedScore:
    """Compute a weighted match score from feature scores + calibration weights."""

    def test_perfect_features_gives_perfect_score(self):
        features = {
            "skills_overlap": 1.0,
            "semantic_sim": 1.0,
            "tfidf": 1.0,
            "experience_years": 1.0,
        }
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)
        assert abs(score - 1.0) < 0.01

    def test_zero_features_gives_zero_score(self):
        features = {
            "skills_overlap": 0.0,
            "semantic_sim": 0.0,
            "tfidf": 0.0,
            "experience_years": 0.0,
        }
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)
        assert score == 0.0

    def test_mixed_features(self):
        features = {
            "skills_overlap": 0.8,
            "semantic_sim": 0.6,
            "tfidf": 0.5,
            "experience_years": 0.7,
        }
        # 0.3*0.8 + 0.3*0.6 + 0.2*0.5 + 0.2*0.7 = 0.24 + 0.18 + 0.10 + 0.14 = 0.66
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)
        assert abs(score - 0.66) < 0.01

    def test_missing_feature_treated_as_zero(self):
        features = {"skills_overlap": 1.0}
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)
        assert abs(score - 0.3) < 0.01

    def test_returns_float_in_range(self):
        features = {"skills_overlap": 0.5, "tfidf": 0.3}
        score = compute_weighted_score(features, DEFAULT_WEIGHTS)
        assert 0.0 <= score <= 1.0


class TestRecalculateWeights:
    """Adjust weights based on user judgements (which features predicted good matches)."""

    def test_returns_dict_of_weights(self):
        judgements = [
            {"match_features": {"skills_overlap": 0.9, "semantic_sim": 0.8}, "user_rating": "good"},
            {"match_features": {"skills_overlap": 0.2, "semantic_sim": 0.3}, "user_rating": "poor"},
        ]
        weights = recalculate_weights(judgements)
        assert isinstance(weights, dict)
        assert len(weights) > 0

    def test_weights_sum_to_one(self):
        judgements = [
            {"match_features": {"skills_overlap": 0.9, "semantic_sim": 0.8, "tfidf": 0.7}, "user_rating": "good"},
            {"match_features": {"skills_overlap": 0.1, "semantic_sim": 0.2, "tfidf": 0.9}, "user_rating": "poor"},
            {"match_features": {"skills_overlap": 0.5, "semantic_sim": 0.5, "tfidf": 0.5}, "user_rating": "partial"},
        ]
        weights = recalculate_weights(judgements)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_empty_judgements_returns_default(self):
        weights = recalculate_weights([])
        assert weights == DEFAULT_WEIGHTS

    def test_single_judgement_returns_weights(self):
        judgements = [
            {"match_features": {"skills_overlap": 0.9, "semantic_sim": 0.5}, "user_rating": "good"},
        ]
        weights = recalculate_weights(judgements)
        assert isinstance(weights, dict)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01
