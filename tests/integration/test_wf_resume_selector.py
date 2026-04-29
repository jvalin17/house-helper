"""Workflow 11: Resume selector for matching.

When a user picks a saved resume to match against, its content text drives
TF-IDF/semantic features instead of the knowledge bank's experiences.

Happy paths:
- Posting {resume_id: N} to /api/jobs/{id}/match uses the resume's text.
- Posting {resume_id: N} to /api/jobs/match-batch uses the resume's text.
- A resume that mentions the job's required skill scores higher than a
  resume that doesn't.

Error paths:
- Unknown resume_id → falls back to KB matching (no crash, no 5xx).
- Unknown job_id in match-batch returns an error entry per job, not a 500.
"""

from __future__ import annotations

import io

from .conftest import _build_docx_resume


def _import_kb_resume(client, *, skills, experiences=None):
    docx = _build_docx_resume(
        skills=skills,
        experiences=experiences or [
            ("KB Co", "KB Engineer", "Jan 2018 – Present", ["KB summary work."])
        ],
    )
    response = client.post(
        "/api/knowledge/import",
        files={"file": ("kb.docx", io.BytesIO(docx), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200


def _seed_job(db, *, title="Backend Engineer", skills=None, description="Python required"):
    """Seed a job directly with required_skills + description in parsed_data."""
    import json as _json

    parsed = {
        "required_skills": skills or [],
        "description": description,
    }
    cursor = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text) VALUES (?, ?, ?, ?)",
        (title, "MatchCo", _json.dumps(parsed), description),
    )
    db.commit()
    return cursor.lastrowid


def _create_resume(client, db, content: str, job_id: int) -> int:
    """Generate a resume for `job_id`, then overwrite its content text directly."""
    gen = client.post("/api/resumes/generate", json={"job_id": job_id}).json()
    resume_id = gen.get("id") or gen.get("resume_id")
    assert resume_id, gen
    db.execute("UPDATE resumes SET content = ? WHERE id = ?", (content, resume_id))
    db.commit()
    return resume_id


def test_resume_id_steers_match_score(client, db):
    _import_kb_resume(client, skills=["Java"])
    job_id = _seed_job(db, skills=["Python", "FastAPI"], description="Python FastAPI REST APIs scalable backend services")

    weak = _create_resume(client, db, "I primarily use Java and Spring Boot enterprise applications.", job_id)
    strong = _create_resume(client, db, "Built Python FastAPI REST APIs with PostgreSQL backend services.", job_id)

    weak_score = client.post(f"/api/jobs/{job_id}/match", json={"resume_id": weak}).json()["score"]
    strong_score = client.post(f"/api/jobs/{job_id}/match", json={"resume_id": strong}).json()["score"]

    assert strong_score > weak_score, (weak_score, strong_score)


def test_resume_id_in_batch(client, db):
    _import_kb_resume(client, skills=["Python"])
    job_id = _seed_job(db, skills=["Kubernetes"], description="Kubernetes operator development")
    resume_id = _create_resume(
        client, db, "Operated Kubernetes clusters, wrote custom controllers.", job_id
    )

    response = client.post(
        "/api/jobs/match-batch",
        json={"job_ids": [job_id], "resume_id": resume_id},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["job_id"] == job_id
    assert results[0]["score"] > 0


def test_unknown_resume_id_falls_back(client, db):
    _import_kb_resume(client, skills=["Python"])
    job_id = _seed_job(db, skills=["Python"], description="Python work")

    response = client.post(f"/api/jobs/{job_id}/match", json={"resume_id": 999999})
    assert response.status_code == 200
    body = response.json()
    assert "score" in body


def test_unknown_job_in_batch_returns_error_entry(client):
    response = client.post(
        "/api/jobs/match-batch",
        json={"job_ids": [424242], "resume_id": None},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["job_id"] == 424242
    assert "error" in results[0]
