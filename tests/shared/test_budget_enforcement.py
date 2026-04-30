"""Budget enforcement — blocks LLM calls when daily limit is exceeded.

Tests the budget check in LazyLLMProvider.complete():
- Allows calls when under budget
- Raises BudgetExceededError when over budget
- Allows calls when no limit is set
- Returns remaining budget info in the error
- Allows calls with force_override=True even when over budget
"""

import json
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from shared.db import migrate
from shared.llm.lazy_provider import LazyLLMProvider, BudgetExceededError
from agents.job.repositories.token_repo import TokenRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    migrate(c)
    # Set up a fake LLM provider config
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('llm', ?)",
        [json.dumps({"provider": "claude", "model": "claude-sonnet-4-20250514", "api_key": "sk-test"})],
    )
    c.commit()
    yield c
    c.close()


@pytest.fixture
def token_repo(conn):
    return TokenRepository(conn)


@pytest.fixture
def provider(conn):
    return LazyLLMProvider(conn)


class TestBudgetEnforcement:
    def test_allows_call_when_no_limit_set(self, conn, token_repo):
        """No daily limit = always allow."""
        token_repo.set_budget(daily_limit_cost=None)
        provider = LazyLLMProvider(conn)

        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "response"
            mock_llm.provider_name.return_value = "claude"
            mock_llm.model_name.return_value = "claude-sonnet-4-20250514"
            mock_get.return_value = mock_llm

            result = provider.complete("hello", feature="test")
            assert result == "response"
            mock_llm.complete.assert_called_once()

    def test_allows_call_when_under_budget(self, conn, token_repo):
        """Under daily limit = allow."""
        token_repo.set_budget(daily_limit_cost=1.00)
        # Log $0.10 of usage today
        token_repo.log_usage("test", "claude", 100, 0.10)

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "response"
            mock_llm.provider_name.return_value = "claude"
            mock_llm.model_name.return_value = "claude-sonnet-4-20250514"
            mock_get.return_value = mock_llm

            result = provider.complete("hello", feature="test")
            assert result == "response"

    def test_blocks_call_when_over_budget(self, conn, token_repo):
        """Over daily limit = raise BudgetExceededError."""
        token_repo.set_budget(daily_limit_cost=0.50)
        # Log $0.60 of usage today (over the $0.50 limit)
        token_repo.log_usage("test", "claude", 1000, 0.60)

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.provider_name.return_value = "claude"
            mock_llm.model_name.return_value = "claude-sonnet-4-20250514"
            mock_get.return_value = mock_llm

            with pytest.raises(BudgetExceededError) as exc_info:
                provider.complete("hello", feature="test")

            assert exc_info.value.spent >= 0.60
            assert exc_info.value.limit == 0.50
            # LLM should NOT have been called
            mock_llm.complete.assert_not_called()

    def test_blocks_call_when_exactly_at_limit(self, conn, token_repo):
        """Exactly at limit = block (no room for another call)."""
        token_repo.set_budget(daily_limit_cost=0.50)
        token_repo.log_usage("test", "claude", 1000, 0.50)

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.provider_name.return_value = "claude"
            mock_get.return_value = mock_llm

            with pytest.raises(BudgetExceededError):
                provider.complete("hello", feature="test")

    def test_force_override_allows_over_budget(self, conn, token_repo):
        """force_override=True bypasses budget check."""
        token_repo.set_budget(daily_limit_cost=0.50)
        token_repo.log_usage("test", "claude", 1000, 0.60)

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "forced response"
            mock_llm.provider_name.return_value = "claude"
            mock_llm.model_name.return_value = "claude-sonnet-4-20250514"
            mock_get.return_value = mock_llm

            result = provider.complete("hello", feature="test", force_override=True)
            assert result == "forced response"

    def test_budget_error_contains_details(self, conn, token_repo):
        """BudgetExceededError includes spent, limit, and remaining."""
        token_repo.set_budget(daily_limit_cost=0.50)
        token_repo.log_usage("test", "claude", 1000, 0.35)
        token_repo.log_usage("test2", "claude", 500, 0.20)

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.provider_name.return_value = "claude"
            mock_get.return_value = mock_llm

            with pytest.raises(BudgetExceededError) as exc_info:
                provider.complete("hello", feature="test")

            err = exc_info.value
            assert err.limit == 0.50
            assert err.spent == pytest.approx(0.55, abs=0.01)
            assert "budget" in str(err).lower() or "limit" in str(err).lower()

    def test_budget_check_only_counts_today(self, conn, token_repo):
        """Yesterday's usage doesn't count against today's budget."""
        token_repo.set_budget(daily_limit_cost=0.50)
        # Insert yesterday's usage directly
        conn.execute(
            "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost, created_at) "
            "VALUES (?, ?, ?, ?, datetime('now', '-1 day'))",
            ("test", "claude", 10000, 5.00),
        )
        conn.commit()

        provider = LazyLLMProvider(conn)
        with patch.object(provider, "_get_provider") as mock_get:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "response"
            mock_llm.provider_name.return_value = "claude"
            mock_llm.model_name.return_value = "claude-sonnet-4-20250514"
            mock_get.return_value = mock_llm

            # Should succeed — yesterday's $5 doesn't count
            result = provider.complete("hello", feature="test")
            assert result == "response"


class TestBudgetErrorHTTP:
    """Test that BudgetExceededError is handled in API routes."""

    def test_error_has_http_friendly_message(self):
        err = BudgetExceededError(spent=0.55, limit=0.50)
        msg = str(err)
        assert "0.50" in msg
        assert "0.55" in msg

    def test_error_to_dict(self):
        err = BudgetExceededError(spent=0.55, limit=0.50)
        d = err.to_dict()
        assert d["error"] == "budget_exceeded"
        assert d["spent"] == 0.55
        assert d["limit"] == 0.50
        assert "remaining" in d
