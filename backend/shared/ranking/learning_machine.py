"""Smart Ranking Learning Machine — learns user preferences from behavior.

Extends the calibration/scorer.py weight-learning pattern with:
- Implicit feedback (clicks, saves, skips — not just explicit ratings)
- Temporal decay (7-day half-life — old interactions matter less)
- Dampening (no single term can dominate)
- Weight bounds (0.05 min, 0.40 max after normalization)
- Encrypted storage (terms and weights encrypted at rest)

Agent-agnostic: works for jobs, apartments, or any future agent.
"""

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from shared.app_logger import get_logger
from shared.ranking.ranking_encryption import (
    encrypt_terms,
    decrypt_terms,
    encrypt_weights,
    decrypt_weights,
)

logger = get_logger("ranking.learning_machine")

# ── Engagement scoring ────────────────────────────────

ENGAGEMENT_WEIGHTS = {
    "apply": 1.0,
    "save": 0.7,
    "click": 0.3,
    "rate_good": 1.0,
    "rate_partial": 0.3,
    "rate_poor": -0.5,
    "skip": -0.15,
}

DECAY_HALF_LIFE_DAYS = 7
MINIMUM_INTERACTIONS_FOR_LEARNING = 5
MAXIMUM_TERM_WEIGHT = 10.0
RECALCULATION_INTERVAL = 10  # recalculate after every N new interactions


def compute_click_engagement(duration_seconds: int | None) -> float:
    """Score a click interaction based on reading duration.

    Longer reading = more interest. Caps at 0.8 for 60+ seconds.
    """
    if duration_seconds is None:
        return ENGAGEMENT_WEIGHTS["click"]
    return min(0.8, 0.3 + (duration_seconds / 120))


# ── Interaction storage ───────────────────────────────

def record_interaction(
    connection: sqlite3.Connection,
    profile_id: int | None,
    agent: str,
    entity_id: int,
    interaction_type: str,
    terms: list[str],
    duration_seconds: int | None = None,
) -> int:
    """Record a user interaction with encrypted terms.

    Returns the interaction ID. Triggers weight recalculation
    after every RECALCULATION_INTERVAL interactions.
    """
    encrypted_term_blob = encrypt_terms(terms)

    cursor = connection.execute(
        """INSERT INTO ranking_interactions
           (profile_id, agent, entity_id, interaction_type, duration_seconds,
            encrypted_terms, created_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
        (profile_id, agent, entity_id, interaction_type,
         duration_seconds, encrypted_term_blob),
    )
    connection.commit()
    interaction_id = cursor.lastrowid

    # Check if we should recalculate weights
    interaction_count = _count_meaningful_interactions(connection, profile_id, agent)
    if interaction_count >= MINIMUM_INTERACTIONS_FOR_LEARNING and interaction_count % RECALCULATION_INTERVAL == 0:
        recalculate_and_store_weights(connection, profile_id, agent)

    return interaction_id


def _count_meaningful_interactions(
    connection: sqlite3.Connection,
    profile_id: int | None,
    agent: str,
) -> int:
    """Count interactions that count toward learning (not just skips)."""
    meaningful_types = ("click", "save", "apply", "rate_good", "rate_partial", "rate_poor")
    placeholders = ",".join("?" for _ in meaningful_types)
    row = connection.execute(
        f"SELECT COUNT(*) as count FROM ranking_interactions "
        f"WHERE agent = ? AND (profile_id = ? OR ? IS NULL) "
        f"AND interaction_type IN ({placeholders})",
        (agent, profile_id, profile_id, *meaningful_types),
    ).fetchone()
    return row["count"]


# ── Weight recalculation ──────────────────────────────

def recalculate_and_store_weights(
    connection: sqlite3.Connection,
    profile_id: int | None,
    agent: str,
) -> dict[str, float]:
    """Recalculate term weights from all interactions and store encrypted.

    Uses temporal decay + engagement scoring + dampening.
    """
    interactions = _load_interactions(connection, profile_id, agent)

    # If no interactions loaded (possibly due to decryption failure), don't overwrite existing weights
    if not interactions:
        logger.warning("No interactions loaded for %s — keeping existing weights", agent)
        return get_learned_weights(connection, profile_id, agent)

    term_weights = _compute_term_weights_from_interactions(interactions)

    # Store encrypted in settings table
    settings_key = f"ranking_terms_{agent}_{profile_id or 'default'}"
    encrypted_value = encrypt_weights(term_weights)
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (settings_key, encrypted_value),
    )
    connection.commit()

    logger.info(
        "Recalculated %d term weights for %s (profile %s) from %d interactions",
        len(term_weights), agent, profile_id, len(interactions),
    )
    return term_weights


def get_learned_weights(
    connection: sqlite3.Connection,
    profile_id: int | None,
    agent: str,
) -> dict[str, float]:
    """Load learned term weights for a profile + agent. Returns empty if none."""
    settings_key = f"ranking_terms_{agent}_{profile_id or 'default'}"
    row = connection.execute(
        "SELECT value FROM settings WHERE key = ?",
        (settings_key,),
    ).fetchone()

    if not row or not row["value"]:
        return {}

    return decrypt_weights(row["value"])


def _load_interactions(
    connection: sqlite3.Connection,
    profile_id: int | None,
    agent: str,
) -> list[dict]:
    """Load all interactions for a profile + agent with decrypted terms."""
    rows = connection.execute(
        """SELECT interaction_type, duration_seconds, encrypted_terms, created_at
           FROM ranking_interactions
           WHERE agent = ? AND (profile_id = ? OR ? IS NULL)
           ORDER BY created_at""",
        (agent, profile_id, profile_id),
    ).fetchall()

    interactions = []
    decryption_failures = 0
    for row in rows:
        decrypted_terms = decrypt_terms(row["encrypted_terms"])
        if decrypted_terms:
            interactions.append({
                "interaction_type": row["interaction_type"],
                "duration_seconds": row["duration_seconds"],
                "terms": decrypted_terms,
                "created_at": row["created_at"],
            })
        else:
            decryption_failures += 1

    # Abort if too many decryption failures — likely key changed
    total_rows = len(rows)
    if total_rows > 0 and decryption_failures > total_rows * 0.5:
        logger.error(
            "Aborting interaction load: %d/%d decryption failures (likely key changed)",
            decryption_failures, total_rows,
        )
        return []

    return interactions


def _compute_term_weights_from_interactions(
    interactions: list[dict],
) -> dict[str, float]:
    """Compute term weights using engagement + temporal decay + dampening.

    Same pattern as calibration/scorer.py recalculate_weights() but with:
    - Implicit feedback types (click/save/skip, not just good/poor)
    - Temporal decay (7-day half-life)
    - Dampening (cap at ±MAXIMUM_TERM_WEIGHT)
    """
    if not interactions:
        return {}

    now = datetime.now(timezone.utc)
    term_weighted_scores = defaultdict(float)
    term_interaction_counts = defaultdict(int)

    for interaction in interactions:
        # Engagement score for this interaction type
        interaction_type = interaction["interaction_type"]
        if interaction_type == "click":
            engagement_score = compute_click_engagement(interaction.get("duration_seconds"))
        else:
            engagement_score = ENGAGEMENT_WEIGHTS.get(interaction_type, 0)

        # Temporal decay
        try:
            interaction_time = datetime.fromisoformat(interaction["created_at"])
            if interaction_time.tzinfo is None:
                interaction_time = interaction_time.replace(tzinfo=timezone.utc)
            days_since_interaction = max(0, (now - interaction_time).total_seconds() / 86400)
        except (ValueError, TypeError):
            days_since_interaction = 0

        decay_factor = math.pow(0.5, days_since_interaction / DECAY_HALF_LIFE_DAYS)
        effective_engagement = engagement_score * decay_factor

        # Apply to each term in this interaction
        for term in interaction["terms"]:
            term_weighted_scores[term] += effective_engagement
            term_interaction_counts[term] += 1

    # Dampening: cap any single term's weight
    if term_weighted_scores:
        maximum_absolute_weight = max(abs(score) for score in term_weighted_scores.values())
        if maximum_absolute_weight > MAXIMUM_TERM_WEIGHT:
            dampening_factor = MAXIMUM_TERM_WEIGHT / maximum_absolute_weight
            term_weighted_scores = {
                term: score * dampening_factor
                for term, score in term_weighted_scores.items()
            }

    return dict(term_weighted_scores)
