"""Workflow 17: View AI usage — token_usage table → /api/budget/usage.

Happy paths:
- /api/budget/usage returns today + alltime totals computed from token_usage.
- After logging usage rows, totals reflect them.

Error paths:
- Empty token_usage table returns zeroed totals.
"""

from __future__ import annotations


def _log_usage(db, *, feature: str, provider: str, tokens: int, cost: float) -> None:
    db.execute(
        "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost) VALUES (?, ?, ?, ?)",
        (feature, provider, tokens, cost),
    )
    db.commit()


def test_usage_starts_at_zero(client):
    response = client.get("/api/budget/usage")
    assert response.status_code == 200
    body = response.json()
    assert body["total_cost"] in (0, 0.0)
    assert body["total_tokens"] in (0, 0.0)
    assert body["alltime"]["total_cost"] in (None, 0, 0.0)


def test_usage_aggregates_logged_rows(client, db):
    _log_usage(db, feature="resume_gen", provider="openai", tokens=1000, cost=0.012)
    _log_usage(db, feature="resume_analyze", provider="openai", tokens=500, cost=0.006)

    body = client.get("/api/budget/usage").json()
    assert body["total_tokens"] == 1500
    assert round(body["total_cost"], 4) == round(0.018, 4)

    breakdown = body.get("breakdown", {})
    assert "resume_gen" in breakdown
    assert breakdown["resume_gen"]["tokens"] == 1000


def test_alltime_independent_of_today(client, db):
    db.execute(
        "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost, created_at)"
        " VALUES ('resume_gen','openai', 9000, 0.5, datetime('now','-2 days'))"
    )
    db.commit()

    body = client.get("/api/budget/usage").json()
    assert (body["total_tokens"] or 0) == 0
    assert body["alltime"]["total_tokens"] == 9000
    assert round(body["alltime"]["total_cost"], 4) == 0.5
