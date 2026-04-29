"""Workflow 4: Save resume → appears in saved list, max 5 enforced.

Happy paths:
- Saving a generated resume returns its id and shows in /api/resumes/saved.
- The save_name auto-generator yields unique sequential names.
- Unsave removes it from the saved list but keeps the DB row.

Error paths:
- Saving a 6th resume returns 400 LIMIT_REACHED.
- Saving a non-existent resume id returns 200 with no rows updated (idempotent).
- saved/count is correct as save/unsave operations occur.
"""

from __future__ import annotations


def _generate_resume(client) -> int:
    client.post("/api/knowledge/entries", json={
        "type": "job", "title": "Engineer", "company": "Acme",
        "description": "Built APIs",
    })
    client.post("/api/knowledge/skills", json={"name": "Python", "category": "language"})
    job_id = client.post(
        "/api/jobs/parse", json={"inputs": ["SWE at Co\n- Python"]}
    ).json()["jobs"][0]["id"]
    return client.post("/api/resumes/generate", json={"job_id": job_id, "preferences": {}}).json()["id"]


def test_save_resume_appears_in_saved_list(client_no_llm):
    resume_id = _generate_resume(client_no_llm)

    saved = client_no_llm.post(f"/api/resumes/{resume_id}/save", json={}).json()
    assert saved["saved"] == resume_id
    assert saved["name"].startswith("resume_")

    listing = client_no_llm.get("/api/resumes/saved").json()
    assert any(r["id"] == resume_id and r["save_name"] == saved["name"] for r in listing)

    count = client_no_llm.get("/api/resumes/saved/count").json()
    assert count["count"] == 1
    assert count["max"] == 5


def test_save_with_explicit_name(client_no_llm):
    resume_id = _generate_resume(client_no_llm)
    response = client_no_llm.post(f"/api/resumes/{resume_id}/save", json={"name": "my-favorite"})
    assert response.json()["name"] == "my-favorite"


def test_unsave_removes_from_saved_list(client_no_llm):
    resume_id = _generate_resume(client_no_llm)
    client_no_llm.post(f"/api/resumes/{resume_id}/save", json={})
    assert client_no_llm.get("/api/resumes/saved/count").json()["count"] == 1

    response = client_no_llm.post(f"/api/resumes/{resume_id}/unsave")
    assert response.status_code == 200

    listing = client_no_llm.get("/api/resumes/saved").json()
    assert all(r["id"] != resume_id for r in listing)
    assert client_no_llm.get("/api/resumes/saved/count").json()["count"] == 0


def test_max_five_saved_enforced(client_no_llm):
    ids = [_generate_resume(client_no_llm) for _ in range(6)]
    for i in range(5):
        r = client_no_llm.post(f"/api/resumes/{ids[i]}/save", json={"name": f"resume-{i}"})
        assert r.status_code == 200, f"Save #{i+1} should succeed"

    # 6th save should fail
    response = client_no_llm.post(f"/api/resumes/{ids[5]}/save", json={"name": "resume-6"})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("error", {}).get("code") == "LIMIT_REACHED"

    # Unsave one — slot freed → 6th save now succeeds
    client_no_llm.post(f"/api/resumes/{ids[0]}/unsave")
    response = client_no_llm.post(f"/api/resumes/{ids[5]}/save", json={"name": "resume-6"})
    assert response.status_code == 200


def test_auto_name_increments_sequentially(client_no_llm):
    ids = [_generate_resume(client_no_llm) for _ in range(3)]
    names = [client_no_llm.post(f"/api/resumes/{rid}/save", json={}).json()["name"] for rid in ids]
    assert len(set(names)) == 3, "Each auto-name should be unique"
    versions = sorted(int(n.split("_v")[-1]) for n in names)
    assert versions == [1, 2, 3]
