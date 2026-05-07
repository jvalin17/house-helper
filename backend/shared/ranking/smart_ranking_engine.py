"""Smart Ranking Engine — scores and sorts results by learned term overlap.

Agent-agnostic: works for jobs, apartments, or any future agent.
Combines three scoring components:
  1. Learned weights: accumulated from user behavior (clicks/saves/skips)
  2. Search intent boost: terms from current search query get extra weight
  3. Normalization: raw scores mapped to 0-100 for display

Zero-opinion cold start: returns results unsorted until enough interactions.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Callable

from shared.app_logger import get_logger
from shared.ranking.learning_machine import get_learned_weights
from shared.ranking.term_extractor import extract_search_terms

logger = get_logger("ranking.engine")

SEARCH_TERM_BOOST = 0.5  # Each matching search term adds this to raw score
MINIMUM_WEIGHT_COUNT_FOR_RANKING = 3  # Need at least 3 learned terms to rank


@dataclass
class RankingResult:
    """Score breakdown for a single result."""
    composite_score: int | None        # 0-100, None = not enough data
    raw_score: float                   # unnormalized weighted sum
    matched_learned_terms: dict[str, float]  # term → weight for matched terms
    matched_search_terms: list[str]    # terms that matched the current search
    result_terms: list[str]            # all terms extracted from this result


def score_single_result(
    result_terms: list[str],
    learned_term_weights: dict[str, float],
    search_terms: list[str],
) -> RankingResult:
    """Score one result by term overlap with learned weights + search boost.

    Returns RankingResult with composite_score=None if not enough learned data.
    """
    # Learned weight component: sum weights of terms present in this result
    matched_learned = {}
    learned_score = 0.0
    for term in result_terms:
        if term in learned_term_weights:
            matched_learned[term] = learned_term_weights[term]
            learned_score += learned_term_weights[term]

    # Search intent boost: each matching search term adds SEARCH_TERM_BOOST
    matched_search = [term for term in result_terms if term in search_terms]
    search_boost = len(matched_search) * SEARCH_TERM_BOOST

    raw_score = learned_score + search_boost

    # Only produce a composite score if we have enough learned data
    has_enough_learned_data = len(learned_term_weights) >= MINIMUM_WEIGHT_COUNT_FOR_RANKING
    composite_score = None
    if has_enough_learned_data or search_terms:
        composite_score = 0  # placeholder, normalized after all results scored

    return RankingResult(
        composite_score=composite_score,
        raw_score=raw_score,
        matched_learned_terms=matched_learned,
        matched_search_terms=matched_search,
        result_terms=result_terms,
    )


def score_and_sort_results(
    results: list[dict],
    term_extractor: Callable[[dict], list[str]],
    agent: str,
    search_filters: dict,
    connection: sqlite3.Connection,
    profile_id: int | None = None,
) -> list[dict]:
    """Score and sort a list of results using learned weights + search intent.

    This is the main entry point. Called by both Jobsmith and NestScout after
    fetching raw results.

    Args:
        results: list of result dicts (jobs or listings)
        term_extractor: function that extracts terms from a single result
        agent: "job" or "apartment"
        search_filters: the current search query/filters (for intent boost)
        connection: DB connection for reading learned weights
        profile_id: user profile (for per-profile learning)

    Returns:
        Same results list, sorted by ranking score (highest first).
        Each result gets 'ranking_score' and 'ranking_breakdown' fields added.
    """
    if not results:
        return results

    # Load learned weights for this profile + agent
    learned_term_weights = get_learned_weights(connection, profile_id, agent)

    # Extract search terms for session-scoped boost
    search_terms = extract_search_terms(search_filters)

    # Score each result
    scored_results = []
    for result in results:
        result_terms = term_extractor(result)
        ranking = score_single_result(result_terms, learned_term_weights, search_terms)
        scored_results.append((result, ranking))

    # Normalize raw scores to 0-100 range
    _normalize_scores(scored_results)

    # Attach scores to results and sort
    for result, ranking in scored_results:
        result["ranking_score"] = ranking.composite_score
        result["ranking_breakdown"] = {
            "matched_learned": ranking.matched_learned_terms,
            "matched_search": ranking.matched_search_terms,
            "term_count": len(ranking.result_terms),
        }

    # Sort: scored results first (by score desc), then unscored in original order
    scored_items = [(result, ranking) for result, ranking in scored_results if ranking.composite_score is not None]
    unscored_items = [(result, ranking) for result, ranking in scored_results if ranking.composite_score is None]

    scored_items.sort(key=lambda pair: pair[1].composite_score, reverse=True)

    sorted_results = [result for result, _ in scored_items] + [result for result, _ in unscored_items]
    return sorted_results


def _normalize_scores(scored_results: list[tuple[dict, RankingResult]]) -> None:
    """Normalize raw scores to 0-100 range across all results.

    Uses min-max normalization. If all scores are equal, everyone gets 50.
    """
    scoreable_rankings = [ranking for _, ranking in scored_results if ranking.composite_score is not None]
    if not scoreable_rankings:
        return

    raw_scores = [ranking.raw_score for ranking in scoreable_rankings]
    minimum_raw_score = min(raw_scores)
    maximum_raw_score = max(raw_scores)
    score_range = maximum_raw_score - minimum_raw_score

    for ranking in scoreable_rankings:
        if score_range > 0:
            normalized = (ranking.raw_score - minimum_raw_score) / score_range
            ranking.composite_score = max(1, min(100, round(normalized * 80 + 20)))
            # 20-100 range: even the worst match gets 20, not 0
        else:
            ranking.composite_score = 50  # all equal → everyone gets 50
