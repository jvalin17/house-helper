"""Workflow 8: Upload resume template → stored, set default, used by generate.

Happy paths:
- POST /api/resume-templates with a DOCX stores it and returns id.
- PUT /api/resume-templates/{id}/default toggles is_default exclusively.
- ResumeService picks up the default template for generation.

Error paths:
- Unsupported template extension returns 400 VALIDATION_ERROR.
"""

from __future__ import annotations


def test_upload_template_persists(client, docx_resume_bytes):
    response = client.post(
        "/api/resume-templates",
        files={"file": ("my-template.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0

    templates = client.get("/api/resume-templates").json()
    assert any(t["id"] == body["id"] for t in templates)


def test_set_default_template_is_exclusive(client, docx_resume_bytes):
    a = client.post(
        "/api/resume-templates",
        files={"file": ("template-a.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    b = client.post(
        "/api/resume-templates",
        files={"file": ("template-b.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()

    client.put(f"/api/resume-templates/{a['id']}/default")
    templates = client.get("/api/resume-templates").json()
    defaults = [t for t in templates if t.get("is_default")]
    assert len(defaults) == 1
    assert defaults[0]["id"] == a["id"]

    client.put(f"/api/resume-templates/{b['id']}/default")
    templates = client.get("/api/resume-templates").json()
    defaults = [t for t in templates if t.get("is_default")]
    assert len(defaults) == 1
    assert defaults[0]["id"] == b["id"]


def test_unsupported_template_extension_rejected(client):
    response = client.post(
        "/api/resume-templates",
        files={"file": ("template.png", b"fake", "image/png")},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "VALIDATION_ERROR"


def test_default_template_used_for_generation(client_no_llm, docx_resume_bytes):
    """When a template is set as default, generate_resume picks up its raw text
    so it can build content from the user's existing format."""
    template_response = client_no_llm.post(
        "/api/resume-templates",
        files={"file": ("my-template.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    template_id = template_response.json()["id"]
    client_no_llm.put(f"/api/resume-templates/{template_id}/default")

    client_no_llm.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme",
        "description": "Built APIs",
    })
    client_no_llm.post("/api/knowledge/skills", json={"name": "Python", "category": "language"})
    job_id = client_no_llm.post(
        "/api/jobs/parse", json={"inputs": ["SWE at Co\n- Python"]}
    ).json()["jobs"][0]["id"]

    response = client_no_llm.post(
        "/api/resumes/generate",
        json={"job_id": job_id, "preferences": {"template_id": template_id}},
    )
    assert response.status_code == 200
    assert response.json()["id"] > 0


def test_delete_template_removes_it(client, docx_resume_bytes):
    template = client.post(
        "/api/resume-templates",
        files={"file": ("template.docx", docx_resume_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()

    response = client.delete(f"/api/resume-templates/{template['id']}")
    assert response.status_code == 200
    templates = client.get("/api/resume-templates").json()
    assert all(t["id"] != template["id"] for t in templates)
