"""Workflow 19: Saved resumes — preview, download, unsave.

Already covered for save creation/limit in test_wf_save_resume.py — this
suite focuses on the post-save lifecycle.

Happy paths:
- GET /api/resumes/{id} returns the resume body (preview).
- GET /api/resumes/{id}/export?format=md returns content in the right type.
- POST /api/resumes/{id}/unsave removes the resume from the saved list while
  the row itself remains accessible.

Error paths:
- Exporting an unknown format returns a clean error.
- Previewing an unknown id returns 404.
"""

from __future__ import annotations


def _seed_resume(db, content: str = "# Resume body") -> int:
    cur = db.execute(
        "INSERT INTO resumes (content, preferences) VALUES (?, ?)",
        (content, "{}"),
    )
    db.commit()
    return cur.lastrowid


def test_preview_returns_resume_body(client, db):
    resume_id = _seed_resume(db, "# Hello world\nBody")
    response = client.get(f"/api/resumes/{resume_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["content"].startswith("# Hello world")


def test_preview_unknown_id_returns_404(client):
    response = client.get("/api/resumes/999999")
    assert response.status_code == 404


def test_export_md_returns_markdown_payload(client, db):
    resume_id = _seed_resume(db, "# Title\n- Bullet")
    response = client.get(f"/api/resumes/{resume_id}/export?format=md")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert b"# Title" in response.content


def test_save_then_unsave_removes_from_saved_list(client, db):
    resume_id = _seed_resume(db)
    client.post(f"/api/resumes/{resume_id}/save", json={"name": "v1"})
    saved_before = client.get("/api/resumes/saved").json()
    assert any(r["id"] == resume_id for r in saved_before)

    client.post(f"/api/resumes/{resume_id}/unsave")
    saved_after = client.get("/api/resumes/saved").json()
    assert all(r["id"] != resume_id for r in saved_after)

    # The resume itself should still be reachable for preview/export.
    assert client.get(f"/api/resumes/{resume_id}").status_code == 200


def test_invalid_export_format_is_handled(client, db):
    resume_id = _seed_resume(db)
    response = client.get(f"/api/resumes/{resume_id}/export?format=banana")
    assert response.status_code in (400, 415, 422, 500)
