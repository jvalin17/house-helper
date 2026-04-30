"""Local ML matcher — learns from LLM match decisions to reduce API costs.

Strategy: LLM as teacher, local model as student.
1. Collect LLM match scores + feature vectors (calibration_judgements table)
2. After enough data (~50 matches), train a local regression model
3. Local model handles routine matching, LLM only for edge cases

Uses pure Python + our TF-IDF — no sklearn/scipy needed.
"""

import json
import math
import sqlite3


def get_training_data(conn: sqlite3.Connection) -> list[dict]:
    """Get all LLM match decisions stored in calibration_judgements."""
    rows = conn.execute(
        "SELECT match_features, match_score FROM calibration_judgements"
    ).fetchall()
    return [
        {"features": json.loads(row["match_features"]), "score": row["match_score"]}
        for row in rows
    ]


def train_local_weights(conn: sqlite3.Connection) -> dict | None:
    """Learn optimal weights from accumulated LLM match data.

    Returns weights dict or None if not enough data.
    Minimum 20 data points needed for meaningful training.
    """
    data = get_training_data(conn)
    if len(data) < 20:
        return None

    # Collect all feature names
    all_features = set()
    for d in data:
        all_features.update(d["features"].keys())

    if not all_features:
        return None

    # Simple approach: for each feature, compute correlation with target score
    # Higher correlation = higher weight
    feature_correlations = {}
    for feature in all_features:
        values = [(d["features"].get(feature, 0.0), d["score"]) for d in data]
        correlation = _pearson_correlation(
            [v[0] for v in values],
            [v[1] for v in values],
        )
        feature_correlations[feature] = max(0, correlation)  # only positive correlations

    # Normalize to sum to 1
    total = sum(feature_correlations.values())
    if total == 0:
        return None

    weights = {feature_name: correlation_value / total for feature_name, correlation_value in feature_correlations.items()}
    return weights


def predict_score(features: dict, weights: dict) -> float:
    """Predict match score using learned weights."""
    score = 0.0
    for feature, weight in weights.items():
        score += weight * features.get(feature, 0.0)
    return min(1.0, max(0.0, score))


def should_use_llm(features: dict, weights: dict | None, threshold: float = 0.15) -> bool:
    """Decide if LLM is needed for this match.

    If local prediction is confident (far from decision boundary), skip LLM.
    If uncertain (close to 50% or features are unusual), use LLM.
    """
    if weights is None:
        return True  # no local model yet, always use LLM

    predicted = predict_score(features, weights)
    # If clearly good (>70%) or clearly bad (<30%), local is confident enough
    if predicted > 0.70 or predicted < 0.30:
        return False
    return True  # uncertain zone — LLM adds value


def get_local_model_stats(conn: sqlite3.Connection) -> dict:
    """Report on local model readiness."""
    data = get_training_data(conn)
    count = len(data)
    weights = train_local_weights(conn)
    return {
        "data_points": count,
        "min_required": 20,
        "is_ready": weights is not None,
        "weights": weights,
        "savings_estimate": f"~{min(90, count * 2)}% of LLM calls" if weights else "Not enough data yet",
    }


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient between two lists."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if denom_x == 0 or denom_y == 0:
        return 0.0

    return numerator / (denom_x * denom_y)
