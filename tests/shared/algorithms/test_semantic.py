"""Tests for semantic — Sentence Transformers similarity scoring.

These tests require sentence-transformers + a downloaded model.
They are skipped if the dependency is not installed (e.g., Python 3.14).
"""

import pytest

try:
    from shared.algorithms.semantic import (
        compute_semantic_similarity,
        compute_batch_similarity,
        is_available,
    )
    HAS_SEMANTIC = is_available()
except ImportError:
    HAS_SEMANTIC = False

requires_semantic = pytest.mark.skipif(
    not HAS_SEMANTIC,
    reason="sentence-transformers not installed or model not available",
)


class TestIsAvailable:
    """Check if the semantic module reports availability correctly."""

    def test_reports_availability(self):
        from shared.algorithms.semantic import is_available

        result = is_available()
        assert isinstance(result, bool)


@requires_semantic
class TestComputeSemanticSimilarity:
    """Score similarity using sentence embeddings."""

    def test_identical_texts(self):
        score = compute_semantic_similarity(
            "Python developer with React experience",
            "Python developer with React experience",
        )
        assert score > 0.99

    def test_semantically_similar(self):
        score = compute_semantic_similarity(
            "experience with distributed systems",
            "worked on large-scale microservices architecture",
        )
        assert score > 0.4

    def test_semantically_unrelated(self):
        score = compute_semantic_similarity(
            "Python developer with machine learning experience",
            "Professional chef specializing in Italian cuisine",
        )
        assert score < 0.3

    def test_leadership_phrases(self):
        score = compute_semantic_similarity(
            "led a team of 5 engineers",
            "leadership and team management experience",
        )
        assert score > 0.4

    def test_empty_text_returns_zero(self):
        score = compute_semantic_similarity("", "Python developer")
        assert score == 0.0

    def test_both_empty_returns_zero(self):
        score = compute_semantic_similarity("", "")
        assert score == 0.0

    def test_returns_float_in_range(self):
        score = compute_semantic_similarity("Python", "Java")
        assert isinstance(score, float)
        assert -0.1 <= score <= 1.1  # small tolerance for floating point


@requires_semantic
class TestComputeBatchSimilarity:
    """Score one query against multiple candidates efficiently."""

    def test_batch_returns_scored_list(self):
        query = "Python backend developer"
        candidates = [
            "Senior Python engineer for API development",
            "React frontend developer",
            "Professional chef",
        ]
        results = compute_batch_similarity(query, candidates)
        assert len(results) == 3
        assert all("text" in r and "score" in r for r in results)

    def test_batch_sorted_by_score_descending(self):
        query = "Python backend developer"
        candidates = [
            "Professional chef",
            "Senior Python engineer for API development",
            "React frontend developer",
        ]
        results = compute_batch_similarity(query, candidates)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_batch_empty_candidates(self):
        results = compute_batch_similarity("Python", [])
        assert results == []

    def test_batch_empty_query(self):
        results = compute_batch_similarity("", ["Python", "Java"])
        assert all(r["score"] == 0.0 for r in results)
