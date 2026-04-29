"""Workflow 1: Import resume → KB populated, template created.

Happy paths:
- DOCX import populates experiences, skills, education, projects.
- A resume_template entry is created and marked default.
- Repeating the import merges new bullets into existing experiences.

Error paths:
- Unsupported file extensions are rejected with HTTP 400.
- Empty/garbled file content does not crash the endpoint.
"""

from __future__ import annotations


def test_docx_import_populates_knowledge_bank(client, docx_resume_bytes):
    payload = docx_resume_bytes()

    response = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    counts = response.json()
    assert counts["experiences"] >= 1
    assert counts.get("skills", 0) >= 1

    entries = client.get("/api/knowledge/entries").json()
    assert len(entries["experiences"]) >= 1
    assert any("Acme" in (e.get("company") or "") for e in entries["experiences"])
    assert len(entries["skills"]) >= 1
    assert any("Python" == s["name"] for s in entries["skills"])
    assert len(entries["education"]) >= 1


def test_docx_import_creates_default_template(client, docx_resume_bytes):
    client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", docx_resume_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    templates = client.get("/api/resume-templates").json()
    assert isinstance(templates, list)
    assert len(templates) >= 1
    defaults = [t for t in templates if t.get("is_default")]
    assert len(defaults) == 1, "Exactly one template should be default after first import"


def test_repeat_import_merges_new_bullets(client, docx_resume_bytes):
    first = docx_resume_bytes()
    client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", first, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    initial_exp_count = len(client.get("/api/knowledge/entries").json()["experiences"])

    second = docx_resume_bytes(
        experiences=[
            ("Acme Corp", "Senior Engineer", "Jan 2020 – Present",
             ["Built REST APIs in Python", "Shipped checkout flow used by 10k users"]),
        ]
    )
    response = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", second, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200

    after = client.get("/api/knowledge/entries").json()["experiences"]
    assert len(after) == initial_exp_count, "Same role should not duplicate"

    matching = [e for e in after if e.get("company") == "Acme Corp"]
    assert matching, "Expected the merged Acme Corp experience"
    description = matching[0].get("description") or ""
    assert "Shipped checkout flow used by 10k users" in description
    assert "Built REST APIs in Python" in description


def test_txt_import_succeeds(client, txt_resume_bytes):
    response = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.txt", txt_resume_bytes, "text/plain")},
    )
    assert response.status_code == 200


def test_unsupported_extension_rejected(client):
    response = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.jpg", b"not a real image", "image/jpeg")},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    code = detail.get("error", {}).get("code") if isinstance(detail, dict) else None
    assert code == "VALIDATION_ERROR"


def test_garbled_docx_does_not_crash(client):
    response = client.post(
        "/api/knowledge/import",
        files={"file": ("resume.docx", b"\x00\x01garbage", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code in (200, 400)
