"""LazyLLMProvider streaming — tests for complete_stream() and supports_streaming().

Tests use mock providers to avoid real API calls.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from shared.llm.lazy_provider import LazyLLMProvider


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class FakeStreamingProvider:
    """Mock provider that supports streaming."""

    def complete(self, prompt, system=None):
        return "Full response text"

    def complete_stream(self, prompt, system=None):
        yield "Hello "
        yield "from "
        yield "streaming."

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "fake-stream-v1"


class FakeNonStreamingProvider:
    """Mock provider that does NOT support streaming."""

    def complete(self, prompt, system=None):
        return "Non-streaming full response"

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "fake-nostream-v1"


class TestLazyProviderStreaming:
    def _configure_provider(self, database_connection, provider_instance, monkeypatch):
        """Configure a fake provider in the lazy wrapper."""
        database_connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('llm', ?, datetime('now'))",
            [json.dumps({"provider": "fake", "model": "fake-v1"})],
        )
        database_connection.commit()

        lazy_provider = LazyLLMProvider(database_connection)
        # Monkey-patch the provider lookup
        monkeypatch.setattr(lazy_provider, "_get_provider", lambda: provider_instance)
        return lazy_provider

    def test_streams_chunks_from_provider(self, database_connection, monkeypatch):
        lazy_provider = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)

        chunks = list(lazy_provider.complete_stream("Analyze this apartment", feature="test"))
        assert chunks == ["Hello ", "from ", "streaming."]

    def test_fallback_to_complete_when_no_stream_support(self, database_connection, monkeypatch):
        """Provider without complete_stream() should yield full response as single chunk."""
        lazy_provider = self._configure_provider(database_connection, FakeNonStreamingProvider(), monkeypatch)

        chunks = list(lazy_provider.complete_stream("Analyze this", feature="test"))
        assert chunks == ["Non-streaming full response"]

    def test_supports_streaming_returns_true(self, database_connection, monkeypatch):
        lazy_provider = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)
        assert lazy_provider.supports_streaming() is True

    def test_supports_streaming_returns_false(self, database_connection, monkeypatch):
        lazy_provider = self._configure_provider(database_connection, FakeNonStreamingProvider(), monkeypatch)
        assert lazy_provider.supports_streaming() is False

    def test_streaming_logs_usage_after_completion(self, database_connection, monkeypatch):
        lazy_provider = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)

        # Consume the stream
        list(lazy_provider.complete_stream("Test prompt", feature="floor_plan_analysis"))

        # Check usage was logged
        usage_row = database_connection.execute(
            "SELECT feature, provider, tokens_used, estimated_cost FROM token_usage ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert usage_row is not None
        assert usage_row["feature"] == "floor_plan_analysis"
        assert usage_row["provider"] == "fake"
        assert usage_row["tokens_used"] > 0

    def test_streaming_raises_when_no_provider(self, database_connection):
        lazy_provider = LazyLLMProvider(database_connection)
        with pytest.raises(RuntimeError, match="No LLM provider configured"):
            list(lazy_provider.complete_stream("test"))
