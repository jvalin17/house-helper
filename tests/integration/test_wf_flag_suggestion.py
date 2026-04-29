"""Workflow 13: Flag incorrect suggestion → stored, filtered from future analysis.

Happy paths:
- POST /api/feedback/suggestions stores a rejection.
- GET /api/feedback/suggestions returns it.
- analyze_resume_fit calls drop suggestions matching the rejection's
  key phrases.

Error paths:
- DELETE removes the rejection (so future suggestions return again).
- Empty/blank rejection payload still creates a row (current behavior).
"""

from __future__ import annotations

import io
import json

from .conftest import _build_docx_resume


def _import_resume_and_job(client, db):
    docx = _build_docx_resume(skills=["Python"])
    client.post(
        "/api/knowledge/import",
        files={"file": ("kb.docx", io.BytesIO(docx))},
    )
    parsed = {"required_skills": ["Python"], "description": "Backend role"}
    cur = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text) VALUES (?, ?, ?, ?)",
        ("Backend Engineer", "Acme", json.dumps(parsed), "Backend role"),
    )
    db.commit()
    return cur.lastrowid


def test_rejection_stored_and_listed(client):
    response = client.post("/api/feedback/suggestions", json={
        "suggestion_text": "Add LLM sentiment analysis to feedback system",
        "reason": "Already covered",
        "original_bullet": "Built feedback system",
    })
    assert response.status_code == 200

    listed = client.get("/api/feedback/suggestions").json()
    assert len(listed) == 1
    assert "sentiment" in listed[0]["suggestion_text"].lower()


def test_rejection_filters_future_suggestions(client, llm, db):
    job_id = _import_resume_and_job(client, db)

    client.post("/api/feedback/suggestions", json={
        "suggestion_text": "Add LLM sentiment analysis to email feedback system",
        "reason": "Out of scope",
        "original_bullet": "Built feedback system",
    })

    llm.set_response("resume_analyze", json.dumps({
        "current_resume_match": 0.7,
        "knowledge_bank_match": 0.8,
        "match_gap": "small",
        "strengths": [],
        "gaps": [],
        "summary": "ok",
        "suggested_improvements": [
            {
                "type": "bullet_rewrite",
                "description": "Add LLM sentiment analysis to email feedback system",
                "impact": "scale",
                "source": "experience",
            },
            {
                "type": "bullet_rewrite",
                "description": "Quantify Python REST API throughput",
                "impact": "scale",
                "source": "experience",
            },
        ],
    }))

    response = client.post("/api/resumes/analyze", json={"job_id": job_id})
    assert response.status_code == 200
    descs = [s["description"] for s in response.json()["suggested_improvements"]]
    assert all("sentiment" not in d.lower() for d in descs), descs
    assert any("python rest api" in d.lower() for d in descs)


def test_delete_rejection_restores_suggestion(client, llm, db):
    job_id = _import_resume_and_job(client, db)

    rej = client.post("/api/feedback/suggestions", json={
        "suggestion_text": "Add LLM sentiment analysis",
        "original_bullet": "Built feedback system",
    }).json()
    rejection_id = rej.get("id") or client.get("/api/feedback/suggestions").json()[0]["id"]

    client.delete(f"/api/feedback/suggestions/{rejection_id}")
    assert client.get("/api/feedback/suggestions").json() == []

    llm.set_response("resume_analyze", json.dumps({
        "current_resume_match": 0.7,
        "knowledge_bank_match": 0.8,
        "match_gap": "small",
        "strengths": [],
        "gaps": [],
        "summary": "ok",
        "suggested_improvements": [
            {
                "type": "bullet_rewrite",
                "description": "Add LLM sentiment analysis to email feedback system",
                "impact": "scale",
                "source": "experience",
            },
        ],
    }))

    response = client.post("/api/resumes/analyze", json={"job_id": job_id})
    assert response.status_code == 200
    assert len(response.json()["suggested_improvements"]) == 1


def test_empty_rejection_payload_does_not_crash(client):
    response = client.post("/api/feedback/suggestions", json={})
    assert response.status_code == 200
