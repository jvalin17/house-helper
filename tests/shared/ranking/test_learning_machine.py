"""Learning machine — tests for behavioral weight learning.

Covers: interaction recording, weight recalculation with decay/dampening,
encrypted storage, cold start, click duration scoring.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from shared.db import migrate
from shared.ranking.learning_machine import (
    record_interaction,
    get_learned_weights,
    recalculate_and_store_weights,
    compute_click_engagement,
    _compute_term_weights_from_interactions,
    MINIMUM_INTERACTIONS_FOR_LEARNING,
)
from shared.ranking.ranking_encryption import encrypt_terms, decrypt_terms


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


# ── Click engagement scoring ─────────────────────────

def test_click_engagement_no_duration():
    """Click without duration gets base score 0.3."""
    assert compute_click_engagement(None) == 0.3


def test_click_engagement_short_read():
    """5-second click gets slightly more than base."""
    score = compute_click_engagement(5)
    assert 0.3 < score < 0.4


def test_click_engagement_long_read():
    """60-second click caps at 0.8."""
    score = compute_click_engagement(60)
    assert score == 0.8


def test_click_engagement_very_long():
    """120+ seconds still caps at 0.8."""
    score = compute_click_engagement(300)
    assert score == 0.8


# ── Interaction recording ────────────────────────────

def test_record_interaction_stores_encrypted(database_connection):
    """Interaction terms are stored encrypted in the DB."""
    terms = ["python", "remote", "senior", "austin"]
    interaction_id = record_interaction(
        database_connection,
        profile_id=1,
        agent="job",
        entity_id=42,
        interaction_type="click",
        terms=terms,
    )
    assert interaction_id > 0

    # Verify stored data
    row = database_connection.execute(
        "SELECT * FROM ranking_interactions WHERE id = ?", (interaction_id,)
    ).fetchone()
    assert row["agent"] == "job"
    assert row["entity_id"] == 42
    assert row["interaction_type"] == "click"

    # Terms are encrypted — raw blob is NOT the original JSON
    raw_blob = row["encrypted_terms"]
    assert isinstance(raw_blob, bytes)
    assert b"python" not in raw_blob  # encrypted, not plaintext

    # But decryption works
    decrypted = decrypt_terms(raw_blob)
    assert "python" in decrypted
    assert "remote" in decrypted


def test_record_save_interaction(database_connection):
    """Save interaction recorded correctly."""
    record_interaction(
        database_connection, profile_id=1, agent="apartment",
        entity_id=100, interaction_type="save",
        terms=["pool", "2br", "austin", "walkable"],
    )
    row = database_connection.execute(
        "SELECT COUNT(*) as count FROM ranking_interactions WHERE agent = 'apartment'"
    ).fetchone()
    assert row["count"] == 1


# ── Weight computation from interactions ──────────────

def test_empty_interactions_returns_empty_weights():
    """No interactions → no learned weights."""
    assert _compute_term_weights_from_interactions([]) == {}


def test_single_click_produces_positive_weights():
    """One click → all terms get positive weight."""
    interactions = [{
        "interaction_type": "click",
        "duration_seconds": None,
        "terms": ["python", "remote", "startup"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }]
    weights = _compute_term_weights_from_interactions(interactions)
    assert weights["python"] > 0
    assert weights["remote"] > 0
    assert weights["startup"] > 0


def test_skip_produces_negative_weights():
    """Skip interaction → terms get negative weight."""
    interactions = [{
        "interaction_type": "skip",
        "duration_seconds": None,
        "terms": ["staffing_agency", "onsite", "clearance"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }]
    weights = _compute_term_weights_from_interactions(interactions)
    assert weights["staffing_agency"] < 0
    assert weights["onsite"] < 0


def test_save_outweighs_skip():
    """Save (+0.7) has stronger signal than skip (-0.15)."""
    interactions = [
        {"interaction_type": "save", "duration_seconds": None,
         "terms": ["python"], "created_at": datetime.now(timezone.utc).isoformat()},
        {"interaction_type": "skip", "duration_seconds": None,
         "terms": ["python"], "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    weights = _compute_term_weights_from_interactions(interactions)
    assert weights["python"] > 0  # net positive


def test_temporal_decay_reduces_old_interactions():
    """Interactions from 14 days ago have ~25% the weight of today's."""
    now = datetime.now(timezone.utc)
    two_weeks_ago = (now - timedelta(days=14)).isoformat()
    today = now.isoformat()

    old_interactions = [{
        "interaction_type": "click", "duration_seconds": 30,
        "terms": ["old_term"], "created_at": two_weeks_ago,
    }]
    new_interactions = [{
        "interaction_type": "click", "duration_seconds": 30,
        "terms": ["new_term"], "created_at": today,
    }]

    old_weights = _compute_term_weights_from_interactions(old_interactions)
    new_weights = _compute_term_weights_from_interactions(new_interactions)

    # Old term should be roughly 25% of new term (2 half-lives = 0.25)
    assert old_weights["old_term"] < new_weights["new_term"] * 0.35


def test_dampening_caps_extreme_weights():
    """Terms with many interactions get capped at MAXIMUM_TERM_WEIGHT."""
    now = datetime.now(timezone.utc).isoformat()
    interactions = [
        {"interaction_type": "apply", "duration_seconds": None,
         "terms": ["hot_term"], "created_at": now}
        for _ in range(50)  # 50 applies to same term
    ]
    weights = _compute_term_weights_from_interactions(interactions)
    assert weights["hot_term"] <= 10.0  # MAXIMUM_TERM_WEIGHT


# ── End-to-end: record + learn + retrieve ────────────

def test_cold_start_returns_empty_weights(database_connection):
    """Before any interactions, learned weights are empty."""
    weights = get_learned_weights(database_connection, profile_id=1, agent="job")
    assert weights == {}


def test_learning_after_enough_interactions(database_connection):
    """Weights recalculated after MINIMUM_INTERACTIONS_FOR_LEARNING interactions."""
    terms_to_click = ["python", "remote", "senior", "backend"]

    for entity_index in range(MINIMUM_INTERACTIONS_FOR_LEARNING + 1):
        record_interaction(
            database_connection, profile_id=1, agent="job",
            entity_id=entity_index + 1, interaction_type="click",
            terms=terms_to_click,
        )

    # Force recalculation
    recalculate_and_store_weights(database_connection, profile_id=1, agent="job")
    weights = get_learned_weights(database_connection, profile_id=1, agent="job")

    assert len(weights) > 0
    assert weights.get("python", 0) > 0
    assert weights.get("remote", 0) > 0


def test_weights_are_profile_specific(database_connection):
    """Different profiles have independent learned weights."""
    record_interaction(database_connection, profile_id=1, agent="job",
                       entity_id=1, interaction_type="save", terms=["python", "remote"])
    record_interaction(database_connection, profile_id=2, agent="job",
                       entity_id=2, interaction_type="save", terms=["java", "onsite"])

    recalculate_and_store_weights(database_connection, profile_id=1, agent="job")
    recalculate_and_store_weights(database_connection, profile_id=2, agent="job")

    weights_profile_1 = get_learned_weights(database_connection, profile_id=1, agent="job")
    weights_profile_2 = get_learned_weights(database_connection, profile_id=2, agent="job")

    assert weights_profile_1.get("python", 0) > 0
    assert weights_profile_1.get("java", 0) == 0
    assert weights_profile_2.get("java", 0) > 0
    assert weights_profile_2.get("python", 0) == 0


def test_weights_encrypted_in_settings(database_connection):
    """Stored weights in settings table are encrypted, not plaintext."""
    record_interaction(database_connection, profile_id=1, agent="job",
                       entity_id=1, interaction_type="click", terms=["python", "secret_term"])
    recalculate_and_store_weights(database_connection, profile_id=1, agent="job")

    row = database_connection.execute(
        "SELECT value FROM settings WHERE key = 'ranking_terms_job_1'"
    ).fetchone()
    assert row is not None
    # Value should be encrypted — not readable as JSON
    raw_value = row["value"]
    assert "python" not in raw_value
    assert "secret_term" not in raw_value


# ── Encryption round-trip ────────────────────────────

def test_encrypt_decrypt_terms_roundtrip():
    """Terms survive encrypt → decrypt round-trip."""
    original_terms = ["python", "remote", "senior", "salary_150k_175k"]
    encrypted = encrypt_terms(original_terms)
    decrypted = decrypt_terms(encrypted)
    assert decrypted == original_terms
