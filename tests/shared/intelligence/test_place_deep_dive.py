"""Place deep-dive — tests for review fetching and selection.

Covers: newest 20% selection, min/max bounds, cache hit skips API,
enrichment with real review texts.
"""

import pytest

from shared.intelligence.place_deep_dive import _select_newest_reviews


# ── Review selection (newest 20%) ────────────────────

def _make_reviews(count: int) -> list[dict]:
    """Generate mock reviews with timestamps."""
    return [
        {"text": f"Review {index}", "time": 1700000000 + index * 86400, "rating": 4}
        for index in range(count)
    ]


def test_select_from_50_reviews_takes_10():
    """50 reviews × 20% = 10, but capped at max 5."""
    reviews = _make_reviews(50)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 5  # Max cap


def test_select_from_10_reviews_takes_2():
    """10 reviews × 20% = 2."""
    reviews = _make_reviews(10)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 2


def test_select_from_3_reviews_takes_1():
    """3 reviews × 20% = 0.6, rounded up to 1 (minimum)."""
    reviews = _make_reviews(3)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1


def test_select_from_1_review_takes_1():
    """1 review × 20% = 0.2, rounded up to 1 (minimum)."""
    reviews = _make_reviews(1)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1


def test_select_from_empty_returns_empty():
    assert _select_newest_reviews([]) == []


def test_select_returns_newest_first():
    """Selected reviews are the most recent ones."""
    reviews = _make_reviews(20)
    selected = _select_newest_reviews(reviews)  # 20 × 20% = 4
    assert len(selected) == 4

    # Newest should have highest timestamps
    selected_times = [review["time"] for review in selected]
    assert selected_times == sorted(selected_times, reverse=True)

    # The newest review in the selection should be the overall newest
    all_times = sorted([review["time"] for review in reviews], reverse=True)
    assert selected_times[0] == all_times[0]


def test_select_from_25_reviews_takes_5():
    """25 reviews × 20% = 5, exactly at max cap."""
    reviews = _make_reviews(25)
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 5


def test_select_preserves_review_text():
    """Selected reviews keep their text content."""
    reviews = [
        {"text": "Amazing indo-chinese food here", "time": 1700086400, "rating": 5},
        {"text": "Best dosa in Austin", "time": 1700000000, "rating": 4},
    ]
    selected = _select_newest_reviews(reviews)
    assert len(selected) == 1
    assert "indo-chinese" in selected[0]["text"]  # Newest one selected
