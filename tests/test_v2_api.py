"""Integration tests for v2 features — auto search, auto apply, token budget."""

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.db import migrate
from coordinator import Coordinator


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    migrate(conn)

    test_app = FastAPI()
    coordinator = Coordinator(conn=conn, llm_provider=None)
    test_app.include_router(coordinator.get_router())
    yield test_app
    conn.close()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def seeded_client(client):
    """Client with knowledge bank data and a parsed job."""
    client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme", "description": "Built APIs with Python",
    })
    client.post("/api/knowledge/skills", json={"name": "Python", "category": "language"})
    client.post("/api/knowledge/skills", json={"name": "React", "category": "framework"})
    client.post("/api/jobs/parse", json={
        "inputs": ["Backend Engineer at BigTech\nRequirements:\n- Python\n- React"],
    })
    return client


class TestSearchFilters:
    def test_save_and_list_filters(self, client):
        r = client.post("/api/search/filters", json={
            "name": "My Backend Search",
            "title": "Backend Engineer",
            "location": "Austin, TX",
            "remote": True,
            "keywords": ["Python", "FastAPI"],
        })
        assert r.status_code == 200
        assert r.json()["id"] > 0

        r = client.get("/api/search/filters")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_delete_filter(self, client):
        r = client.post("/api/search/filters", json={"name": "Del", "title": "Test"})
        filter_id = r.json()["id"]
        client.delete(f"/api/search/filters/{filter_id}")
        r = client.get("/api/search/filters")
        assert len(r.json()) == 0


class TestAutoApply:
    def test_queue_batch(self, seeded_client):
        jobs = seeded_client.get("/api/jobs").json()
        job_ids = [j["id"] for j in jobs]

        r = seeded_client.post("/api/apply/batch", json={"job_ids": job_ids})
        assert r.status_code == 200
        assert len(r.json()["queue"]) == len(job_ids)

    def test_max_batch_size(self, seeded_client):
        r = seeded_client.post("/api/apply/batch", json={"job_ids": [1, 2, 3, 4, 5, 6]})
        assert r.status_code == 400

    def test_get_queue(self, seeded_client):
        jobs = seeded_client.get("/api/jobs").json()
        seeded_client.post("/api/apply/batch", json={"job_ids": [jobs[0]["id"]]})

        r = seeded_client.get("/api/apply/queue")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_generate_docs_for_queue_entry(self, seeded_client):
        jobs = seeded_client.get("/api/jobs").json()
        batch = seeded_client.post("/api/apply/batch", json={"job_ids": [jobs[0]["id"]]})
        entry_id = batch.json()["queue"][0]["id"]

        r = seeded_client.post(f"/api/apply/generate/{entry_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"
        assert "resume" in r.json()
        assert "cover_letter" in r.json()

    def test_confirm_and_skip(self, seeded_client):
        jobs = seeded_client.get("/api/jobs").json()
        batch = seeded_client.post("/api/apply/batch", json={"job_ids": [jobs[0]["id"]]})
        entry_id = batch.json()["queue"][0]["id"]

        seeded_client.post(f"/api/apply/generate/{entry_id}")

        r = seeded_client.post(f"/api/apply/confirm/{entry_id}")
        assert r.json()["status"] == "confirmed"

    def test_full_apply_flow(self, seeded_client):
        jobs = seeded_client.get("/api/jobs").json()
        batch = seeded_client.post("/api/apply/batch", json={"job_ids": [jobs[0]["id"]]})
        entry_id = batch.json()["queue"][0]["id"]

        # Generate
        seeded_client.post(f"/api/apply/generate/{entry_id}")
        # Confirm
        seeded_client.post(f"/api/apply/confirm/{entry_id}")
        # Execute (opens browser — will work in test since webbrowser.open is a no-op in test)
        r = seeded_client.post(f"/api/apply/execute/{entry_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "applied"
        assert "application_id" in r.json()

        # Verify tracked
        apps = seeded_client.get("/api/applications").json()
        assert len(apps) >= 1


class TestTokenBudget:
    def test_set_and_get_budget(self, client):
        r = client.put("/api/budget", json={"daily_limit_cost": 1.0, "ask_threshold": "over_budget"})
        assert r.status_code == 200

        r = client.get("/api/budget")
        assert r.status_code == 200
        assert r.json()["budget"]["daily_limit_cost"] == 1.0

    def test_usage_starts_at_zero(self, client):
        r = client.get("/api/budget/usage")
        assert r.status_code == 200
        assert r.json()["total_tokens"] == 0
        assert r.json()["total_cost"] == 0


class TestEvidence:
    def test_get_evidence_empty(self, client):
        r = client.get("/api/evidence/experience/1")
        assert r.status_code == 200
        assert r.json() == []
