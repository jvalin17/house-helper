"""QuotaTracker — tests for API request quota tracking."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from shared.db import migrate
from shared.quota_tracker import QuotaTracker


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def tracker(database_connection):
    return QuotaTracker(database_connection)


class TestRecordRequest:
    def test_record_inserts_row(self, tracker, database_connection):
        tracker.record_request("realtyapi")
        count = database_connection.execute(
            "SELECT COUNT(*) as total FROM api_request_log WHERE service_name = 'realtyapi'"
        ).fetchone()["total"]
        assert count == 1

    def test_record_multiple_requests(self, tracker, database_connection):
        for _ in range(5):
            tracker.record_request("realtyapi")
        count = database_connection.execute(
            "SELECT COUNT(*) as total FROM api_request_log WHERE service_name = 'realtyapi'"
        ).fetchone()["total"]
        assert count == 5


class TestGetUsage:
    def test_returns_none_for_ai_provider(self, tracker):
        assert tracker.get_usage("claude") is None

    def test_returns_none_for_unknown_service(self, tracker):
        assert tracker.get_usage("nonexistent") is None

    def test_empty_usage_for_realtyapi(self, tracker):
        usage = tracker.get_usage("realtyapi")
        assert usage["used"] == 0
        assert usage["limit"] == 250
        assert usage["period"] == "month"
        assert usage["remaining"] == 250
        assert usage["exhausted"] is False
        assert usage["percent_used"] == 0.0

    def test_usage_after_recording(self, tracker):
        for _ in range(47):
            tracker.record_request("realtyapi")
        usage = tracker.get_usage("realtyapi")
        assert usage["used"] == 47
        assert usage["remaining"] == 203
        assert usage["percent_used"] == 18.8
        assert usage["exhausted"] is False

    def test_daily_quota_for_walkscore(self, tracker):
        usage = tracker.get_usage("walkscore")
        assert usage["limit"] == 5000
        assert usage["period"] == "day"

    def test_resets_at_is_future(self, tracker):
        usage = tracker.get_usage("realtyapi")
        resets_at = datetime.fromisoformat(usage["resets_at"])
        assert resets_at > datetime.now(timezone.utc).replace(tzinfo=None)

    def test_display_name_included(self, tracker):
        usage = tracker.get_usage("realtyapi")
        assert usage["display_name"] == "RealtyAPI"


class TestIsExhausted:
    def test_not_exhausted_when_empty(self, tracker):
        assert tracker.is_exhausted("realtyapi") is False

    def test_exhausted_at_limit(self, tracker):
        for _ in range(250):
            tracker.record_request("realtyapi")
        assert tracker.is_exhausted("realtyapi") is True

    def test_not_exhausted_for_unknown_service(self, tracker):
        assert tracker.is_exhausted("unknown_service") is False

    def test_not_exhausted_for_ai_provider(self, tracker):
        assert tracker.is_exhausted("claude") is False


class TestGetAllUsage:
    def test_returns_all_quota_tracked_sources(self, tracker):
        all_usage = tracker.get_all_usage()
        service_names = [usage["service_name"] for usage in all_usage]
        assert "realtyapi" in service_names
        assert "rentcast" in service_names
        assert "rapidapi" in service_names
        assert "walkscore" in service_names
        assert "adzuna_app_key" in service_names
        # AI providers should NOT appear
        assert "claude" not in service_names
        assert "openai" not in service_names

    def test_usage_reflects_recorded_requests(self, tracker):
        tracker.record_request("realtyapi")
        tracker.record_request("realtyapi")
        all_usage = tracker.get_all_usage()
        realtyapi = next(usage for usage in all_usage if usage["service_name"] == "realtyapi")
        assert realtyapi["used"] == 2


class TestCleanup:
    def test_cleanup_removes_old_entries(self, tracker, database_connection):
        # Insert an old entry (100 days ago)
        old_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=100)).isoformat()
        database_connection.execute(
            "INSERT INTO api_request_log (service_name, requested_at) VALUES (?, ?)",
            ("realtyapi", old_date),
        )
        database_connection.commit()

        # Insert a recent entry
        tracker.record_request("realtyapi")

        deleted_count = tracker.cleanup(days=90)
        assert deleted_count == 1

        # Recent entry should survive
        remaining = database_connection.execute(
            "SELECT COUNT(*) as total FROM api_request_log"
        ).fetchone()["total"]
        assert remaining == 1

    def test_cleanup_keeps_recent_entries(self, tracker):
        tracker.record_request("realtyapi")
        deleted_count = tracker.cleanup(days=90)
        assert deleted_count == 0


class TestPeriodBoundary:
    def test_old_month_requests_not_counted(self, tracker, database_connection):
        """Requests from last month should not count toward this month's quota."""
        last_month = (datetime.now(timezone.utc).replace(tzinfo=None).replace(day=1) - timedelta(days=1)).isoformat()
        database_connection.execute(
            "INSERT INTO api_request_log (service_name, requested_at) VALUES (?, ?)",
            ("realtyapi", last_month),
        )
        database_connection.commit()

        usage = tracker.get_usage("realtyapi")
        assert usage["used"] == 0

    def test_old_day_requests_not_counted(self, tracker, database_connection):
        """Requests from yesterday should not count toward today's daily quota."""
        yesterday = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).replace(hour=12).isoformat()
        database_connection.execute(
            "INSERT INTO api_request_log (service_name, requested_at) VALUES (?, ?)",
            ("walkscore", yesterday),
        )
        database_connection.commit()

        usage = tracker.get_usage("walkscore")
        assert usage["used"] == 0


class TestOrchestratorIntegration:
    """Integration test: orchestrator skips exhausted sources and records on success."""

    def test_orchestrator_skips_exhausted_source(self, tracker, database_connection):
        """When a source is exhausted, the orchestrator should skip it."""
        # Exhaust realtyapi
        for _ in range(250):
            tracker.record_request("realtyapi")
        assert tracker.is_exhausted("realtyapi") is True

        # Simulate orchestrator pre-call check
        sources_exhausted = []
        sources_searched = []
        providers = [("realtyapi", True), ("rentcast", False)]

        for service_name, is_exhausted_flag in providers:
            if tracker.is_exhausted(service_name):
                sources_exhausted.append(service_name)
            else:
                # Would call provider.search() here
                tracker.record_request(service_name)
                sources_searched.append(service_name)

        assert "realtyapi" in sources_exhausted
        assert "rentcast" in sources_searched
        assert tracker.get_usage("rentcast")["used"] == 1
