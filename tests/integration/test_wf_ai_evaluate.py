"""Workflow 12: Evaluate selected (AI) — LLM-driven match scoring.

Happy paths:
- POST /api/jobs/{id}/match {use_llm: True} forwards to the LLM and returns
  the LLM's overall_score plus the LLM's analysis.
- POST /api/jobs/match-batch-ai runs LLM scoring on every job and sorts
  by score descending.

Error paths:
- LLM returning malformed JSON falls back to algorithmic score with
  llm_error captured (no 5xx).
- Without an LLM provider configured, /match {use_llm: True} returns the
  algorithmic score (graceful degradation).
"""

from __future__ import annotations

import json


def _seed_job(db, *, title="AI Engineer", skills=None, description="ML systems"):
    parsed = {"required_skills": skills or [], "description": description}
    cursor = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text) VALUES (?, ?, ?, ?)",
        (title, "AICo", json.dumps(parsed), description),
    )
    db.commit()
    return cursor.lastrowid


def _seed_kb_experience(client):
    response = client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Senior ML Engineer", "company": "Acme",
        "start_date": "2020-01-01",
        "description": "Built ML pipelines, recommender systems, RAG features.",
    })
    assert response.status_code == 200


def test_ai_match_uses_llm_score(client, llm, db):
    _seed_kb_experience(client)
    job_id = _seed_job(db, skills=["Python", "ML"], description="ML platform engineering")

    llm.set_response("job_match", json.dumps({
        "overall_score": 0.91,
        "strengths": ["Python", "ML"],
        "gaps": ["Kubernetes"],
        "summary": "Strong ML fit.",
    }))

    response = client.post(f"/api/jobs/{job_id}/match", json={"use_llm": True})
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0.91
    assert body["breakdown"]["llm_analysis"]["summary"] == "Strong ML fit."
    assert any(call["feature"] == "job_match" for call in llm.calls)


def test_ai_batch_match_sorted_by_score(client, llm, db):
    _seed_kb_experience(client)
    a = _seed_job(db, title="Job A", skills=["Python"], description="A description")
    b = _seed_job(db, title="Job B", skills=["Python"], description="B description")

    scores = iter([0.42, 0.95])

    def respond(*_args, **_kwargs):
        return json.dumps({
            "overall_score": next(scores),
            "strengths": [],
            "gaps": [],
            "summary": "ok",
        })

    llm.complete = respond  # type: ignore[method-assign]

    response = client.post("/api/jobs/match-batch-ai", json={"job_ids": [a, b]})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["score"] for r in results] == sorted([r["score"] for r in results], reverse=True)
    assert results[0]["score"] == 0.95


def test_ai_match_with_malformed_llm_response_falls_back(client, llm, db):
    _seed_kb_experience(client)
    job_id = _seed_job(db, skills=["Python"], description="Backend role")
    llm.set_response("job_match", "this is not json {{")

    response = client.post(f"/api/jobs/{job_id}/match", json={"use_llm": True})
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert "llm_error" in body["breakdown"]


def test_ai_match_without_llm_provider_returns_algo_score(client_no_llm, db):
    """When no LLM is wired, use_llm=True must still return a non-error response."""
    job_id = _seed_job(db, skills=["Python"], description="Backend role")
    client_no_llm.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "X",
        "start_date": "2020-01-01", "description": "Built things in Python.",
    })

    response = client_no_llm.post(f"/api/jobs/{job_id}/match", json={"use_llm": True})
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert body["breakdown"].get("llm_score") is None
