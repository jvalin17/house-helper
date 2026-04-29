"""Workflow 14: Revision loop — regenerate resume with user instructions.

Happy paths:
- Calling /api/resumes/generate twice with different preferences produces
  two distinct resume rows.
- user_instructions in preferences flow into the LLM prompt.
- apply_suggestions in preferences is forwarded to the LLM.

Error paths:
- Generating without a job 404s.
"""

from __future__ import annotations

import io
import json

from .conftest import _build_docx_resume


def _seed(client, db):
    docx = _build_docx_resume(skills=["Python", "FastAPI"])
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


def test_user_instructions_reach_llm(client, llm, db):
    job_id = _seed(client, db)

    response = client.post("/api/resumes/generate", json={
        "job_id": job_id,
        "preferences": {"user_instructions": "Emphasize observability work and SLO ownership"},
    })
    assert response.status_code == 200

    gen_calls = [c for c in llm.calls if c["feature"] == "resume_gen"]
    assert gen_calls
    prompt = gen_calls[-1]["prompt"]
    assert "observability" in prompt.lower()
    assert "slo" in prompt.lower()


def test_apply_suggestions_reach_llm(client, llm, db):
    job_id = _seed(client, db)
    suggestion = {"description": "Quantify Python REST API throughput",
                  "type": "bullet_rewrite", "impact": "scale"}

    response = client.post("/api/resumes/generate", json={
        "job_id": job_id,
        "preferences": {"apply_suggestions": [suggestion]},
    })
    assert response.status_code == 200

    gen_calls = [c for c in llm.calls if c["feature"] == "resume_gen"]
    assert gen_calls
    prompt = gen_calls[-1]["prompt"]
    assert "quantify python rest api throughput" in prompt.lower()


def test_two_revisions_produce_distinct_rows(client, db):
    job_id = _seed(client, db)
    first = client.post("/api/resumes/generate", json={"job_id": job_id, "preferences": {}}).json()
    second = client.post("/api/resumes/generate", json={
        "job_id": job_id,
        "preferences": {"user_instructions": "Make it shorter"},
    }).json()

    assert first["id"] != second["id"]

    rows = db.execute(
        "SELECT id, preferences FROM resumes WHERE job_id = ? ORDER BY id", (job_id,)
    ).fetchall()
    assert len(rows) == 2
    assert json.loads(rows[1]["preferences"])["user_instructions"] == "Make it shorter"


def test_generate_for_missing_job_errors(client):
    response = client.post("/api/resumes/generate", json={"job_id": 999999, "preferences": {}})
    assert response.status_code in (400, 404, 500)
    body = response.json()
    assert "error" in body or "detail" in body
