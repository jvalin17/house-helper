"""Workflow 18: Application tracker — status changes captured as timeline.

Happy paths:
- Initial application is recorded with the default 'applied' status in history.
- Each status update appends a row to application_status_history, in order.
- Listing applications by status reflects the current state.

Error paths:
- Updating a nonexistent application returns a sensible 200/404 with no crash.
- History on a nonexistent application returns an empty list.
"""

from __future__ import annotations

import json


def _seed_job(db) -> int:
    cur = db.execute(
        "INSERT INTO jobs (title, company, parsed_data, source_text) VALUES (?, ?, ?, ?)",
        ("Backend Engineer", "Acme", json.dumps({"required_skills": ["Python"]}), "x"),
    )
    db.commit()
    return cur.lastrowid


def test_initial_application_records_default_status(client, db):
    job_id = _seed_job(db)
    app = client.post("/api/applications", json={"job_id": job_id}).json()

    history = client.get(f"/api/applications/{app['id']}/history").json()
    assert len(history) == 1
    assert history[0]["status"] == "applied"


def test_status_timeline_orders_oldest_first(client, db):
    job_id = _seed_job(db)
    app = client.post("/api/applications", json={"job_id": job_id}).json()

    for status in ("submitted", "interview", "offer"):
        r = client.put(f"/api/applications/{app['id']}", json={"status": status})
        assert r.status_code == 200

    history = client.get(f"/api/applications/{app['id']}/history").json()
    assert [h["status"] for h in history] == ["applied", "submitted", "interview", "offer"]


def test_listing_filtered_by_status(client, db):
    j1 = _seed_job(db)
    j2 = _seed_job(db)
    a1 = client.post("/api/applications", json={"job_id": j1}).json()
    a2 = client.post("/api/applications", json={"job_id": j2}).json()
    client.put(f"/api/applications/{a1['id']}", json={"status": "interview"})

    interviews = client.get("/api/applications?status=interview").json()
    applied = client.get("/api/applications?status=applied").json()
    assert {a["id"] for a in interviews} == {a1["id"]}
    assert {a["id"] for a in applied} == {a2["id"]}


def test_history_for_unknown_app_is_empty(client):
    assert client.get("/api/applications/999999/history").json() == []
