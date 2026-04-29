"""Workflow 7: Manual experience CRUD + bullet merge on second import.

Happy paths:
- POST /api/knowledge/entries creates an experience and returns its id.
- PUT updates the title/description.
- DELETE removes it.
- A second import of the same role merges new bullets without duplicating.

Error paths:
- PUT with empty body returns 400 VALIDATION_ERROR.
- DELETE on a non-existent id is idempotent (200 with deleted echo).
"""

from __future__ import annotations


def test_create_update_delete_experience(client):
    create = client.post("/api/knowledge/entries", json={
        "type": "job", "title": "SWE", "company": "Acme",
        "description": "Built APIs",
    }).json()
    entry_id = create["id"]
    assert entry_id > 0

    listing = client.get("/api/knowledge/entries").json()
    assert any(e["id"] == entry_id for e in listing["experiences"])

    updated = client.put(f"/api/knowledge/entries/{entry_id}", json={
        "title": "Senior SWE",
        "description": "Built scalable APIs",
    }).json()
    assert updated["title"] == "Senior SWE"

    deleted = client.delete(f"/api/knowledge/entries/{entry_id}").json()
    assert deleted == {"deleted": entry_id}
    after = client.get("/api/knowledge/entries").json()
    assert all(e["id"] != entry_id for e in after["experiences"])


def test_update_with_no_fields_returns_400(client):
    create = client.post("/api/knowledge/entries", json={
        "type": "job", "title": "SWE", "company": "Acme",
    }).json()
    response = client.put(f"/api/knowledge/entries/{create['id']}", json={})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "VALIDATION_ERROR"


def test_delete_missing_entry_is_idempotent(client):
    response = client.delete("/api/knowledge/entries/99999")
    assert response.status_code == 200
    assert response.json() == {"deleted": 99999}


def test_repeat_import_merges_unique_bullets(client, docx_resume_bytes):
    first = docx_resume_bytes(
        experiences=[("Acme", "Engineer", "Jan 2020 – Present", ["Bullet One"])],
    )
    client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", first,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    initial = client.get("/api/knowledge/entries").json()["experiences"]
    assert len(initial) == 1

    second = docx_resume_bytes(
        experiences=[("Acme", "Engineer", "Jan 2020 – Present",
                      ["Bullet One", "Bullet Two", "Bullet Three"])],
    )
    counts = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", second,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    assert counts.get("experiences_merged", 0) >= 1

    merged = client.get("/api/knowledge/entries").json()["experiences"]
    assert len(merged) == len(initial), "Same role should not duplicate"
    matching = next(e for e in merged if e["company"] == "Acme")
    description = matching.get("description") or ""
    assert "Bullet One" in description
    assert "Bullet Two" in description
    assert "Bullet Three" in description
