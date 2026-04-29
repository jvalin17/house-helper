"""Workflow 15: Apply & Track — application records, status changes, history.

Happy paths:
- POST /api/applications creates a record tied to a job + resume + cover letter.
- GET /api/applications lists it.
- PUT /api/applications/{id} updates status and history captures the transition.

Error paths:
- GET on unknown application returns 404.
"""

from __future__ import annotations

import json


def _seed_job(db, *, title="Backend Engineer"):
    parsed = {"required_skills": ["Python"], "description": "Backend role"}
    cur = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text) VALUES (?, ?, ?, ?)",
        (title, "Acme", json.dumps(parsed), "Backend role"),
    )
    db.commit()
    return cur.lastrowid


def _seed_resume(db, job_id: int) -> int:
    cur = db.execute(
        "INSERT INTO resumes (job_id, content, preferences) VALUES (?, ?, ?)",
        (job_id, "Resume content", "{}"),
    )
    db.commit()
    return cur.lastrowid


def _seed_cover_letter(db, job_id: int) -> int:
    cur = db.execute(
        "INSERT INTO cover_letters (job_id, content) VALUES (?, ?)",
        (job_id, "Dear Hiring Manager..."),
    )
    db.commit()
    return cur.lastrowid


def test_create_application_links_resume_and_cover_letter(client, db):
    job_id = _seed_job(db)
    resume_id = _seed_resume(db, job_id)
    cl_id = _seed_cover_letter(db, job_id)

    response = client.post("/api/applications", json={
        "job_id": job_id,
        "resume_id": resume_id,
        "cover_letter_id": cl_id,
    })
    assert response.status_code == 200
    app = response.json()
    assert app["job_id"] == job_id
    assert app["resume_id"] == resume_id
    assert app["cover_letter_id"] == cl_id

    listed = client.get("/api/applications").json()
    assert any(a["id"] == app["id"] for a in listed)


def test_status_update_creates_history(client, db):
    job_id = _seed_job(db)
    app = client.post("/api/applications", json={"job_id": job_id}).json()

    client.put(f"/api/applications/{app['id']}", json={"status": "submitted"})
    client.put(f"/api/applications/{app['id']}", json={"status": "interview"})

    refreshed = client.get(f"/api/applications/{app['id']}").json()
    assert refreshed["status"] == "interview"

    history = client.get(f"/api/applications/{app['id']}/history").json()
    statuses = [h["status"] for h in history]
    assert "submitted" in statuses
    assert "interview" in statuses


def test_filter_applications_by_status(client, db):
    j1 = _seed_job(db, title="Job A")
    j2 = _seed_job(db, title="Job B")
    a1 = client.post("/api/applications", json={"job_id": j1}).json()
    a2 = client.post("/api/applications", json={"job_id": j2}).json()

    client.put(f"/api/applications/{a1['id']}", json={"status": "rejected"})
    client.put(f"/api/applications/{a2['id']}", json={"status": "interview"})

    interviews = client.get("/api/applications?status=interview").json()
    assert {app["id"] for app in interviews} == {a2["id"]}


def test_unknown_application_returns_404(client):
    response = client.get("/api/applications/999999")
    assert response.status_code == 404
