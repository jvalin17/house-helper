"""Workflow 20: Match calibration — user ratings → recalculated feature weights.

Happy paths:
- Calibration weights default to DEFAULT_WEIGHTS when no judgements exist.
- Submitting a judgement persists it on calibration_judgements.
- /api/calibration/recalculate returns new weights summing to ~1.0 once
  judgements exist.

Error paths:
- Submitting a judgement for an unknown job returns 404, not 5xx.
"""

from __future__ import annotations

import json


def _seed_job_with_score(db, *, score: float = 0.7) -> int:
    parsed = {"required_skills": ["Python"], "description": "Backend role"}
    breakdown = {
        "skills_overlap": 0.8,
        "semantic_sim": 0.7,
        "tfidf": 0.6,
        "experience_years": 0.5,
        "weighted_score": score,
    }
    cur = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text, match_score, match_breakdown)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("Backend Engineer", "Acme", json.dumps(parsed), "x", score, json.dumps(breakdown)),
    )
    db.commit()
    return cur.lastrowid


def test_default_weights_when_empty(client):
    body = client.get("/api/calibration/weights").json()
    assert set(body) >= {"skills_overlap", "semantic_sim", "tfidf", "experience_years"}
    assert abs(sum(body.values()) - 1.0) < 1e-6


def test_judgement_is_persisted(client, db):
    job_id = _seed_job_with_score(db)
    response = client.post("/api/calibration/judge", json={"job_id": job_id, "rating": "good"})
    assert response.status_code == 200

    rows = db.execute("SELECT * FROM calibration_judgements WHERE job_id = ?", (job_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["user_rating"] == "good"


def test_recalculate_returns_normalized_weights(client, db):
    job_a = _seed_job_with_score(db, score=0.8)
    job_b = _seed_job_with_score(db, score=0.4)
    client.post("/api/calibration/judge", json={"job_id": job_a, "rating": "good"})
    client.post("/api/calibration/judge", json={"job_id": job_b, "rating": "poor"})

    weights = client.post("/api/calibration/recalculate").json()
    assert set(weights) >= {"skills_overlap", "semantic_sim", "tfidf", "experience_years"}
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_judgement_for_unknown_job_returns_404(client):
    response = client.post(
        "/api/calibration/judge", json={"job_id": 999999, "rating": "good"}
    )
    assert response.status_code == 404
