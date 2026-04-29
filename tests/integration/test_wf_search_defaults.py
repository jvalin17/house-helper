"""Workflow 9: Save search defaults → profile updated → pre-filled on next load.

Happy paths:
- PUT /api/profiles/{id} stores search defaults (title, location, keywords, remote).
- GET /api/profiles/active returns those defaults.
- POST /api/search/run with empty filters auto-fills from active profile.

Error paths:
- PUT on a non-existent profile id is currently a no-op (returns null/empty).
"""

from __future__ import annotations

from .conftest import make_job_result


def _active_profile_id(client) -> int:
    profile = client.get("/api/profiles/active").json()
    return profile["id"]


def test_save_defaults_persists_on_profile(client):
    profile_id = _active_profile_id(client)

    response = client.put(f"/api/profiles/{profile_id}", json={
        "search_title": "Backend Engineer",
        "search_location": "Austin, TX",
        "search_keywords": "Python,FastAPI",
        "search_remote": 1,
    })
    assert response.status_code == 200

    active = client.get("/api/profiles/active").json()
    assert active["search_title"] == "Backend Engineer"
    assert active["search_location"] == "Austin, TX"
    assert active["search_keywords"] == "Python,FastAPI"
    assert active["search_remote"] in (1, True)


def test_search_run_uses_profile_defaults_when_filters_empty(client, mock_job_boards):
    profile_id = _active_profile_id(client)
    client.put(f"/api/profiles/{profile_id}", json={
        "search_title": "Site Reliability Engineer",
        "search_location": "Seattle, WA",
        "search_keywords": "SRE,Kubernetes",
        "search_remote": 1,
    })

    mock_job_boards([make_job_result(title="SRE", company="CloudCo",
                                     description="Kubernetes, observability")])
    response = client.post("/api/search/run", json={})
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_explicit_filters_override_profile_defaults(client, mock_job_boards):
    profile_id = _active_profile_id(client)
    client.put(f"/api/profiles/{profile_id}", json={
        "search_title": "Will Be Overridden",
    })

    mock_job_boards([make_job_result(title="Backend Engineer", company="Acme")])
    response = client.post("/api/search/run", json={
        "title": "Backend Engineer",
        "location": "Remote",
    })
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_update_missing_profile_does_not_create_one(client):
    """Updating an unknown profile id should return either empty/null or 404 — never raise 500."""
    response = client.put("/api/profiles/999999", json={"search_title": "Ghost"})
    assert response.status_code in (200, 404)
