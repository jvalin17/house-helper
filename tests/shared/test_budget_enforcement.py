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
def db_connection():
    """In-memory SQLite DB with full schema and a fake LLM provider configured."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('llm', ?)",
        [json.dumps({"provider": "claude", "model": "claude-sonnet-4-20250514", "api_key": "sk-test"})],
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def token_repository(db_connection):
    return TokenRepository(db_connection)


def _make_mock_llm(response_text: str = "response") -> MagicMock:
    """Create a mock LLM provider with standard return values."""
    mock_provider = MagicMock()
    mock_provider.complete.return_value = response_text
    mock_provider.provider_name.return_value = "claude"
    mock_provider.model_name.return_value = "claude-sonnet-4-20250514"
    return mock_provider


def _create_lazy_provider_with_mock(db_connection, mock_llm: MagicMock) -> LazyLLMProvider:
    """Create a LazyLLMProvider that returns the given mock instead of a real provider."""
    lazy_provider = LazyLLMProvider(db_connection)
    # Patch _get_provider to return our mock
    lazy_provider._get_provider = lambda: mock_llm  # type: ignore[assignment]
    return lazy_provider


class TestBudgetEnforcement:
    def test_allows_call_when_no_limit_set(self, db_connection, token_repository):
        """No daily limit = always allow."""
        token_repository.set_budget(daily_limit_cost=None)
        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        result = lazy_provider.complete("hello", feature="test")
        assert result == "response"
        mock_llm.complete.assert_called_once()

    def test_allows_call_when_under_budget(self, db_connection, token_repository):
        """Under daily limit = allow."""
        token_repository.set_budget(daily_limit_cost=1.00)
        token_repository.log_usage("test", "claude", 100, 0.10)

        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        result = lazy_provider.complete("hello", feature="test")
        assert result == "response"

    def test_blocks_call_when_over_budget(self, db_connection, token_repository):
        """Over daily limit = raise BudgetExceededError."""
        token_repository.set_budget(daily_limit_cost=0.50)
        token_repository.log_usage("resume_gen", "claude", 1000, 0.60)

        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        with pytest.raises(BudgetExceededError) as raised:
            lazy_provider.complete("hello", feature="test")

        assert raised.value.spent >= 0.60
        assert raised.value.limit == 0.50
        mock_llm.complete.assert_not_called()

    def test_blocks_call_when_exactly_at_limit(self, db_connection, token_repository):
        """Exactly at limit = block (no room for another call)."""
        token_repository.set_budget(daily_limit_cost=0.50)
        token_repository.log_usage("resume_gen", "claude", 1000, 0.50)

        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        with pytest.raises(BudgetExceededError):
            lazy_provider.complete("hello", feature="test")

    def test_force_override_allows_over_budget(self, db_connection, token_repository):
        """force_override=True bypasses budget check."""
        token_repository.set_budget(daily_limit_cost=0.50)
        token_repository.log_usage("resume_gen", "claude", 1000, 0.60)

        mock_llm = _make_mock_llm(response_text="forced response")
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        result = lazy_provider.complete("hello", feature="test", force_override=True)
        assert result == "forced response"
        mock_llm.complete.assert_called_once()

    def test_budget_error_contains_details(self, db_connection, token_repository):
        """BudgetExceededError includes spent, limit, and remaining."""
        token_repository.set_budget(daily_limit_cost=0.50)
        token_repository.log_usage("resume_gen", "claude", 1000, 0.35)
        token_repository.log_usage("cover_letter", "claude", 500, 0.20)

        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        with pytest.raises(BudgetExceededError) as raised:
            lazy_provider.complete("hello", feature="test")

        budget_error = raised.value
        assert budget_error.limit == 0.50
        assert budget_error.spent == pytest.approx(0.55, abs=0.01)
        assert "budget" in str(budget_error).lower() or "limit" in str(budget_error).lower()

    def test_budget_check_only_counts_today(self, db_connection, token_repository):
        """Yesterday's usage doesn't count against today's budget."""
        token_repository.set_budget(daily_limit_cost=0.50)
        # Insert yesterday's usage directly
        db_connection.execute(
            "INSERT INTO token_usage (feature, provider, tokens_used, estimated_cost, created_at) "
            "VALUES (?, ?, ?, ?, datetime('now', '-1 day'))",
            ("resume_gen", "claude", 10000, 5.00),
        )
        db_connection.commit()

        mock_llm = _make_mock_llm()
        lazy_provider = _create_lazy_provider_with_mock(db_connection, mock_llm)

        result = lazy_provider.complete("hello", feature="test")
        assert result == "response"


class TestBudgetExceededErrorFormat:
    """Test that BudgetExceededError produces useful messages and dicts for the API."""

    def test_error_message_includes_spent_and_limit(self):
        budget_error = BudgetExceededError(spent=0.55, limit=0.50)
        error_message = str(budget_error)
        assert "0.50" in error_message
        assert "0.55" in error_message

    def test_to_dict_has_all_required_fields(self):
        budget_error = BudgetExceededError(spent=0.55, limit=0.50)
        error_dict = budget_error.to_dict()
        assert error_dict["error"] == "budget_exceeded"
        assert error_dict["spent"] == 0.55
        assert error_dict["limit"] == 0.50
        assert error_dict["remaining"] == 0

    def test_to_dict_remaining_is_zero_when_over(self):
        budget_error = BudgetExceededError(spent=1.00, limit=0.50)
        assert budget_error.to_dict()["remaining"] == 0

    def test_to_dict_remaining_when_at_limit(self):
        budget_error = BudgetExceededError(spent=0.50, limit=0.50)
        assert budget_error.to_dict()["remaining"] == 0
