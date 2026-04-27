"""Repository for token usage tracking and budget.

Budget config stored in settings table (key='token_budget').
Usage stored in token_usage table (time-series log).
"""

import json
import sqlite3
from datetime import date


class TokenRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def log_usage(self, feature: str, provider: str, tokens: int, cost: float) -> None:
        self._conn.execute(
            "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost) VALUES (?, ?, ?, ?)",
            (feature, provider, tokens, cost),
        )
        self._conn.commit()

    def get_today_usage(self) -> dict:
        today = date.today().isoformat()
        rows = self._conn.execute(
            "SELECT feature, SUM(tokens_used) as tokens, SUM(estimated_cost) as cost "
            "FROM token_usage WHERE date(created_at) = ? GROUP BY feature",
            (today,),
        ).fetchall()
        total_tokens = sum(r["tokens"] for r in rows)
        total_cost = sum(r["cost"] or 0 for r in rows)
        breakdown = {r["feature"]: {"tokens": r["tokens"], "cost": r["cost"] or 0} for r in rows}
        return {"total_tokens": total_tokens, "total_cost": total_cost, "breakdown": breakdown}

    def get_budget(self) -> dict:
        row = self._conn.execute("SELECT value FROM settings WHERE key = 'token_budget'").fetchone()
        if not row:
            return {"daily_limit_tokens": None, "daily_limit_cost": None, "ask_threshold": "over_budget"}
        return json.loads(row["value"])

    def set_budget(self, daily_limit_cost: float | None = None, daily_limit_tokens: int | None = None,
                   ask_threshold: str = "over_budget") -> None:
        value = json.dumps({
            "daily_limit_tokens": daily_limit_tokens,
            "daily_limit_cost": daily_limit_cost,
            "ask_threshold": ask_threshold,
        })
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('token_budget', ?, datetime('now'))",
            (value,),
        )
        self._conn.commit()

    def get_remaining_today(self) -> dict:
        budget = self.get_budget()
        usage = self.get_today_usage()
        remaining_cost = None
        if budget.get("daily_limit_cost"):
            remaining_cost = max(0, budget["daily_limit_cost"] - usage["total_cost"])
        remaining_tokens = None
        if budget.get("daily_limit_tokens"):
            remaining_tokens = max(0, budget["daily_limit_tokens"] - usage["total_tokens"])
        return {"remaining_cost": remaining_cost, "remaining_tokens": remaining_tokens, "usage": usage, "budget": budget}
