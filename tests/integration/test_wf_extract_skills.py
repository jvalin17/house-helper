"""Workflow 6: Extract skills from text/link → save accepted skills.

Happy paths:
- Plain text input returns extracted_skills via algorithmic path.
- URL input fetches via httpx (mocked), extracts text, returns skills.
- Saving a returned skill via /api/knowledge/skills persists and lists it.

Error paths:
- Localhost / private-IP URLs are blocked (SSRF guard) with HTTP 400.
- A failing httpx request returns 400 FETCH_FAILED.
"""

from __future__ import annotations


def test_extract_from_text_returns_skills(client):
    response = client.post("/api/knowledge/extract", json={
        "text": "Experienced engineer with Python, FastAPI, React, and Docker"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "text"
    assert isinstance(body["extracted_skills"], list)
    skills_lower = [s.lower() for s in body["extracted_skills"]]
    assert "python" in skills_lower
    assert "react" in skills_lower


def test_save_extracted_skills_persists(client):
    extracted = client.post("/api/knowledge/extract", json={
        "text": "Python and React engineer"
    }).json()["extracted_skills"]
    assert extracted

    for name in extracted[:2]:
        client.post("/api/knowledge/skills", json={"name": name, "category": "extracted"})

    listing = client.get("/api/knowledge/skills").json()
    saved_names = {s["name"].lower() for s in listing}
    assert any(s.lower() in saved_names for s in extracted[:2])


def test_extract_from_url_uses_fetched_html(client, monkeypatch):
    """Patch httpx.get so the route doesn't hit the network."""
    import httpx

    captured: dict = {}

    class _FakeResponse:
        status_code = 200
        text = (
            "<html><head><title>Job</title></head><body>"
            "<p>We need someone strong in Python, FastAPI and Kubernetes.</p>"
            "</body></html>"
        )

        def raise_for_status(self) -> None: ...

    def fake_get(url, *_, **kwargs):
        captured["url"] = url
        captured["follow_redirects"] = kwargs.get("follow_redirects", False)
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    response = client.post("/api/knowledge/extract", json={"text": "https://example.com/job"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "url"
    assert captured["url"] == "https://example.com/job"
    assert captured["follow_redirects"] is True
    assert isinstance(body["extracted_skills"], list)


def test_extract_blocks_localhost_url(client):
    response = client.post("/api/knowledge/extract", json={"text": "http://localhost:8080/admin"})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    code = detail.get("error", {}).get("code")
    assert code == "BLOCKED"


def test_extract_blocks_private_ip(client):
    response = client.post("/api/knowledge/extract", json={"text": "http://10.0.0.1/secret"})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "BLOCKED"


def test_extract_handles_http_error(client, monkeypatch):
    import httpx

    def fake_get(url, *_, **__):
        raise httpx.ConnectError("DNS failure")

    monkeypatch.setattr(httpx, "get", fake_get)

    response = client.post("/api/knowledge/extract", json={"text": "https://invalid.example/job"})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "FETCH_FAILED"
