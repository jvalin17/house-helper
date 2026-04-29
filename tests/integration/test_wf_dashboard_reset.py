"""Workflow 5: Dashboard reset — clears jobs/apps, preserves KB/templates/saved.

Happy paths:
- Reset zeroes out jobs and applications.
- Knowledge bank entries (experiences, skills, education, projects) survive.
- Resume templates survive.
- Saved resumes (is_saved=1) survive but are detached from deleted jobs.

Error paths:
- Reset on an empty DB returns zero counts and HTTP 200.
- Reset called twice in a row is idempotent.
"""

from __future__ import annotations


def _seed_full(client) -> dict:
    """Populate KB + jobs + applications + saved resume + ephemeral resume + template."""
    client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme",
        "description": "Built APIs",
    })
    client.post("/api/knowledge/skills", json={"name": "Python", "category": "language"})
    job_id = client.post(
        "/api/jobs/parse", json={"inputs": ["SWE at BigTech\n- Python"]}
    ).json()["jobs"][0]["id"]
    saved_resume_id = client.post(
        "/api/resumes/generate", json={"job_id": job_id, "preferences": {}}
    ).json()["id"]
    client.post(f"/api/resumes/{saved_resume_id}/save", json={"name": "keep-me"})

    ephemeral_resume_id = client.post(
        "/api/resumes/generate", json={"job_id": job_id, "preferences": {}}
    ).json()["id"]

    app_id = client.post("/api/applications", json={
        "job_id": job_id, "resume_id": saved_resume_id,
    }).json()["id"]
    client.put(f"/api/applications/{app_id}", json={"status": "interview"})

    return {
        "job_id": job_id,
        "saved_resume_id": saved_resume_id,
        "ephemeral_resume_id": ephemeral_resume_id,
        "app_id": app_id,
    }


def test_reset_clears_jobs_and_applications(client_no_llm):
    _seed_full(client_no_llm)
    assert len(client_no_llm.get("/api/jobs").json()) == 1
    assert len(client_no_llm.get("/api/applications").json()) == 1

    response = client_no_llm.post("/api/dashboard/reset")
    assert response.status_code == 200
    counts = response.json()
    assert counts["jobs_deleted"] == 1
    assert counts["applications_deleted"] == 1
    assert counts["resumes_deleted"] >= 1

    assert client_no_llm.get("/api/jobs").json() == []
    assert client_no_llm.get("/api/applications").json() == []


def test_reset_preserves_knowledge_bank(client_no_llm):
    seeded = _seed_full(client_no_llm)
    before = client_no_llm.get("/api/knowledge/entries").json()
    skills_before = client_no_llm.get("/api/knowledge/skills").json()

    client_no_llm.post("/api/dashboard/reset")

    after = client_no_llm.get("/api/knowledge/entries").json()
    assert len(after["experiences"]) == len(before["experiences"])
    skills_after = client_no_llm.get("/api/knowledge/skills").json()
    assert len(skills_after) == len(skills_before)
    _ = seeded


def test_reset_preserves_saved_resumes(client_no_llm):
    seeded = _seed_full(client_no_llm)

    client_no_llm.post("/api/dashboard/reset")

    saved = client_no_llm.get("/api/resumes/saved").json()
    saved_ids = {r["id"] for r in saved}
    assert seeded["saved_resume_id"] in saved_ids
    assert seeded["ephemeral_resume_id"] not in saved_ids


def test_reset_preserves_resume_templates(client_no_llm, docx_resume_bytes):
    client_no_llm.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    templates_before = client_no_llm.get("/api/resume-templates").json()
    assert len(templates_before) >= 1

    client_no_llm.post("/api/dashboard/reset")

    templates_after = client_no_llm.get("/api/resume-templates").json()
    assert len(templates_after) == len(templates_before)


def test_reset_on_empty_db_returns_zero_counts(client_no_llm):
    response = client_no_llm.post("/api/dashboard/reset")
    assert response.status_code == 200
    counts = response.json()
    assert counts["jobs_deleted"] == 0
    assert counts["applications_deleted"] == 0
    assert counts["resumes_deleted"] == 0


def test_reset_is_idempotent(client_no_llm):
    _seed_full(client_no_llm)
    client_no_llm.post("/api/dashboard/reset")
    response = client_no_llm.post("/api/dashboard/reset")
    assert response.status_code == 200
    assert response.json()["jobs_deleted"] == 0
