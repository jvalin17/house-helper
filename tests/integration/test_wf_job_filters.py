"""Workflow 10: Post-fetch job filters (sponsorship / clearance / internship).

Happy paths:
- exclude_sponsorship strips jobs whose description says "no sponsorship".
- exclude_clearance strips jobs requiring security clearance.
- exclude_internship strips internship/co-op postings.
- Without preferences, all jobs are returned.

Error paths:
- Malformed resume_preferences JSON is tolerated (no crash, all jobs returned).
"""

from __future__ import annotations

import json

from .conftest import make_job_result


def _set_filters(client, **prefs) -> int:
    profile = client.get("/api/profiles/active").json()
    client.put(
        f"/api/profiles/{profile['id']}",
        json={"resume_preferences": json.dumps(prefs)},
    )
    return profile["id"]


def test_filters_strip_sponsorship_required(client, mock_job_boards):
    _set_filters(client, exclude_sponsorship=True)
    mock_job_boards([
        make_job_result(title="Backend Eng", description="Python, FastAPI"),
        make_job_result(title="Backend Eng", company="StrictCo",
                        description="Must be authorized to work — no visa sponsorship",
                        url="https://jobs.example.com/strictco"),
    ])

    response = client.post("/api/search/run", json={"title": "engineer"}).json()
    titles = {j["title"] for j in response["jobs"]}
    companies = {j.get("company") for j in response["jobs"]}
    assert "StrictCo" not in companies, f"Sponsorship-required job not filtered: {response['jobs']}"
    assert response["count"] == 1
    assert "Backend Eng" in titles


def test_filters_strip_clearance(client, mock_job_boards):
    _set_filters(client, exclude_clearance=True)
    mock_job_boards([
        make_job_result(title="SDE I", description="Python work"),
        make_job_result(title="DoD SDE", company="GovCo",
                        description="Must hold active TS/SCI clearance",
                        url="https://jobs.example.com/govco"),
    ])
    response = client.post("/api/search/run", json={"title": "engineer"}).json()
    companies = {j.get("company") for j in response["jobs"]}
    assert "GovCo" not in companies
    assert response["count"] == 1


def test_filters_strip_internship(client, mock_job_boards):
    _set_filters(client, exclude_internship=True)
    mock_job_boards([
        make_job_result(title="Backend Engineer", description="Full-time SWE"),
        make_job_result(title="Software Engineering Intern", company="Internlandia",
                        description="Summer internship for college students",
                        url="https://jobs.example.com/intern"),
    ])
    response = client.post("/api/search/run", json={"title": "engineer"}).json()
    companies = {j.get("company") for j in response["jobs"]}
    assert "Internlandia" not in companies


def test_no_filters_returns_all_jobs(client, mock_job_boards):
    mock_job_boards([
        make_job_result(title="Job A", description="No restrictions"),
        make_job_result(title="Internship", description="Summer internship",
                        url="https://jobs.example.com/internship"),
        make_job_result(title="Cleared role", description="TS/SCI required",
                        url="https://jobs.example.com/cleared"),
    ])
    response = client.post("/api/search/run", json={"title": "any"}).json()
    assert response["count"] == 3


def test_malformed_preferences_does_not_crash(client, mock_job_boards):
    profile = client.get("/api/profiles/active").json()
    client.put(
        f"/api/profiles/{profile['id']}",
        json={"resume_preferences": "{not valid json"},
    )
    mock_job_boards([make_job_result(title="Eng", description="generic")])

    response = client.post("/api/search/run", json={"title": "any"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
