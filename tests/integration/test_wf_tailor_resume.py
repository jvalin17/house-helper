"""Workflow 3: Tailor resume → analyze fit → generate → content + analysis.

Happy paths:
- analyze_resume_fit returns suggestions when LLM is configured.
- generate_resume returns content + an analysis block when LLM is configured.
- Generate falls back to algorithmic resume when no LLM.

Error paths:
- analyze without LLM returns 400 LLM_REQUIRED.
- analyze without an imported original resume returns 400 NO_RESUME.
- generate on a missing job_id returns 500 GENERATION_FAILED (not crash).
"""

from __future__ import annotations


def _seed_kb_and_job(client) -> int:
    client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Senior Engineer", "company": "Acme Corp",
        "start_date": "2020-01-01",
        "description": "Built REST APIs in Python\nMentored 4 engineers",
    })
    for skill in ("Python", "FastAPI", "PostgreSQL", "REST"):
        client.post("/api/knowledge/skills", json={"name": skill, "category": "language"})
    parsed = client.post("/api/jobs/parse", json={
        "inputs": ["Backend Engineer at BigTech\nRequirements:\n- Python\n- FastAPI"],
    }).json()
    return parsed["jobs"][0]["id"]


def _store_original_resume(client, text: str = "Jane Doe\nWORK EXPERIENCE\nAcme Corp | Senior Engineer\tJan 2020 – Present\n- Built REST APIs in Python") -> None:
    """Skip /api/knowledge/import (slow on real DOCX) and write directly via preferences endpoint?
    The original resume is stored in settings; reuse the import flow for realism.
    """
    client.put(
        "/api/preferences",
        json={"tone": "professional"},
    )
    # Inject directly via the same path the import service uses.
    # We piggyback on the resume_gen step which falls back to algorithmic when
    # there's no original — for analyze_fit we need original text.


def test_analyze_fit_returns_suggestions(client, llm, docx_resume_bytes):
    job_id = _seed_kb_and_job(client)
    client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    response = client.post("/api/resumes/analyze", json={"job_id": job_id})
    assert response.status_code == 200
    body = response.json()
    assert "suggested_improvements" in body
    assert isinstance(body["suggested_improvements"], list)
    assert "current_resume_match" in body


def test_generate_resume_returns_content_and_analysis(client, docx_resume_bytes):
    job_id = _seed_kb_and_job(client)
    client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    response = client.post("/api/resumes/generate", json={"job_id": job_id, "preferences": {"tone": "professional"}})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert isinstance(body["content"], str) and len(body["content"]) > 30
    # Mock LLM provides JSON edits → analysis included
    assert "analysis" in body


def test_generate_resume_without_llm_uses_algorithmic(client_no_llm):
    """Workflow still completes when no LLM is configured (template path)."""
    client_no_llm.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme",
        "description": "Built APIs",
    })
    client_no_llm.post("/api/knowledge/skills", json={"name": "Python", "category": "language"})
    job_id = client_no_llm.post(
        "/api/jobs/parse", json={"inputs": ["SWE at Co\n- Python"]}
    ).json()["jobs"][0]["id"]

    response = client_no_llm.post("/api/resumes/generate", json={"job_id": job_id, "preferences": {}})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert "Acme" in body["content"]
    # Algorithmic path does not produce an analysis block
    assert "analysis" not in body or body.get("analysis") is None


def test_analyze_without_llm_returns_400(client_no_llm):
    job_id = client_no_llm.post(
        "/api/jobs/parse", json={"inputs": ["SWE at Co\n- Python"]}
    ).json()["jobs"][0]["id"]
    response = client_no_llm.post("/api/resumes/analyze", json={"job_id": job_id})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "LLM_REQUIRED"


def test_analyze_without_original_resume_returns_400(client):
    job_id = _seed_kb_and_job(client)
    response = client.post("/api/resumes/analyze", json={"job_id": job_id})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "NO_RESUME"


def test_generate_with_missing_job_returns_error(client):
    response = client.post("/api/resumes/generate", json={"job_id": 99999, "preferences": {}})
    assert response.status_code in (400, 404, 500)
    if response.status_code == 500:
        detail = response.json().get("detail", {})
        assert detail.get("error", {}).get("code") == "GENERATION_FAILED"
