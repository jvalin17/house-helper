"""API request quota tracker — counts outbound requests per source per period.

Append-only log in api_request_log table. Each API call records one row.
Quota limits come from the service registry (BUILT_IN_SERVICES).
AI providers are excluded — they use token_budget for cost-based tracking.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from shared.service_registry import BUILT_IN_SERVICES


def _get_quota_config(service_name: str) -> dict | None:
    """Look up quota_limit and quota_period from the service registry."""
    for service in BUILT_IN_SERVICES:
        if service["service_name"] == service_name:
            if service.get("quota_limit") is not None:
                return {
                    "limit": service["quota_limit"],
                    "period": service["quota_period"],
                    "display_name": service["display_name"],
                }
            return None
    return None


def _period_start(period: str) -> str:
    """Return the start of the current period as an ISO datetime string."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    # day
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _period_reset(period: str) -> str:
    """Return the start of the next period as an ISO datetime string."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if period == "month":
        if now.month == 12:
            return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    # day
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


class QuotaTracker:
    """Tracks API request counts per source and checks against quota limits."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def record_request(self, service_name: str) -> None:
        """Log one API request for the given source."""
        self._connection.execute(
            "INSERT INTO api_request_log (service_name) VALUES (?)",
            (service_name,),
        )
        self._connection.commit()

    def get_usage(self, service_name: str) -> dict | None:
        """Return usage data for a source. None if source has no quota limit."""
        config = _get_quota_config(service_name)
        if not config:
            return None

        period_start = _period_start(config["period"])
        row = self._connection.execute(
            "SELECT COUNT(*) as request_count FROM api_request_log "
            "WHERE service_name = ? AND requested_at >= ?",
            (service_name, period_start),
        ).fetchone()
        used = row["request_count"] if row else 0
        limit = config["limit"]
        remaining = max(0, limit - used)

        return {
            "service_name": service_name,
            "display_name": config["display_name"],
            "used": used,
            "limit": limit,
            "period": config["period"],
            "remaining": remaining,
            "exhausted": used >= limit,
            "percent_used": round((used / limit) * 100, 1) if limit > 0 else 0,
            "resets_at": _period_reset(config["period"]),
        }

    def get_all_usage(self) -> list[dict]:
        """Return usage for all sources that have quota limits."""
        results = []
        for service in BUILT_IN_SERVICES:
            if service.get("quota_limit") is not None:
                usage = self.get_usage(service["service_name"])
                if usage:
                    results.append(usage)
        return results

    def is_exhausted(self, service_name: str) -> bool:
        """True if the source has reached its quota limit for the current period."""
        usage = self.get_usage(service_name)
        if not usage:
            return False
        return usage["exhausted"]

    def cleanup(self, days: int = 90) -> int:
        """Delete log entries older than N days. Returns count deleted."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat()
        cursor = self._connection.execute(
            "DELETE FROM api_request_log WHERE requested_at < ?",
            (cutoff,),
        )
        self._connection.commit()
        return cursor.rowcount
