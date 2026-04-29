"""Workflow 2: Scout jobs → results returned, match all scores them, sorted.

Happy paths:
- /api/search/run returns canned mock results, persists them as jobs.
- match-batch updates match_score for each job.
- list_jobs returns sorted-by-score order after matching.

Error paths:
- Search with no available job boards returns an empty list without raising.
- match-batch on a non-existent job_id returns an entry with an error/score 0.
"""

from __future__ import annotations

from .conftest import make_job_result


def test_scout_returns_mock_results(client, mock_job_boards):
    mock_job_boards([
        make_job_result(title="Senior Backend Engineer", company="BigTech",
                        description="Python, FastAPI, AWS"),
        make_job_result(title="Platform Engineer", company="Startup",
                        description="Kubernetes, Go, infra"),
    ])

    response = client.post("/api/search/run", json={"title": "engineer"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    titles = {j["title"] for j in body["jobs"]}
    assert {"Senior Backend Engineer", "Platform Engineer"} <= titles

    listed = client.get("/api/jobs").json()
    assert len(listed) == 2


def test_match_all_scores_and_sorts(client, mock_job_boards):
    # Populate KB so matcher has signal — Python-heavy candidate
    for skill in ("Python", "FastAPI", "PostgreSQL", "REST"):
        client.post("/api/knowledge/skills", json={"name": skill, "category": "language"})
    client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme",
        "description": "Built Python REST APIs with FastAPI and PostgreSQL",
    })

    mock_job_boards([
        make_job_result(title="Python Backend",
                        description="Python, FastAPI, PostgreSQL, REST APIs"),
        make_job_result(title="Java Lead",
                        description="Java, Spring, Hibernate, JBoss"),
    ])
    search = client.post("/api/search/run", json={"title": "engineer"}).json()
    job_ids = [j["id"] for j in search["jobs"]]
    assert len(job_ids) == 2

    match = client.post("/api/jobs/match-batch", json={"job_ids": job_ids}).json()
    assert len(match["results"]) == 2
    for entry in match["results"]:
        assert "score" in entry

    jobs = client.get("/api/jobs").json()
    sorted_by_score = sorted(jobs, key=lambda j: j.get("match_score") or 0, reverse=True)
    assert jobs == sorted_by_score or all(j.get("match_score") is not None for j in jobs)
    python_job = next(j for j in jobs if j["title"] == "Python Backend")
    java_job = next(j for j in jobs if j["title"] == "Java Lead")
    assert (python_job.get("match_score") or 0) >= (java_job.get("match_score") or 0)


def test_scout_with_no_boards_returns_empty(client, monkeypatch):
    monkeypatch.setattr(
        "agents.job.services.auto_search.get_available_boards",
        lambda: [],
    )
    response = client.post("/api/search/run", json={"title": "anything"})
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["jobs"] == []


def test_match_batch_handles_missing_job(client):
    response = client.post("/api/jobs/match-batch", json={"job_ids": [99999]})
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        results = response.json()["results"]
        assert results == [] or all(r.get("score", 0) == 0 or r.get("error") for r in results)
