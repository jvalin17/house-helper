"""LLMProviderManager streaming — tests for complete_stream() and supports_streaming.

Tests use mock providers extending LLMProviderBase.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from shared.llm.provider_manager import LLMProviderManager


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class FakeStreamingProvider(LLMProviderBase):
    """Mock provider with native streaming."""

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


class FakeBasicProvider(LLMProviderBase):
    """Mock provider with no streaming override — uses default fallback."""

    def complete(self, prompt, system=None):
        return "Non-streaming full response"

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "fake-basic-v1"


class TestProviderManagerStreaming:
    def _configure_provider(self, database_connection, provider_instance, monkeypatch):
        """Configure a fake provider in the manager."""
        database_connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('llm', ?, datetime('now'))",
            [json.dumps({"provider": "fake", "model": "fake-v1"})],
        )
        database_connection.commit()

        provider_manager = LLMProviderManager(database_connection)
        monkeypatch.setattr(provider_manager, "_get_provider", lambda: provider_instance)
        return provider_manager

    def test_streams_chunks_from_provider(self, database_connection, monkeypatch):
        provider_manager = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)
        chunks = list(provider_manager.complete_stream("Analyze this apartment", feature="test"))
        assert chunks == ["Hello ", "from ", "streaming."]

    def test_fallback_yields_complete_response_as_one_chunk(self, database_connection, monkeypatch):
        """Provider without streaming override uses base class fallback."""
        provider_manager = self._configure_provider(database_connection, FakeBasicProvider(), monkeypatch)
        chunks = list(provider_manager.complete_stream("Analyze this", feature="test"))
        assert chunks == ["Non-streaming full response"]

    def test_supports_streaming_always_true(self, database_connection, monkeypatch):
        """All providers support streaming (native or fallback)."""
        provider_manager = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)
        assert provider_manager.supports_streaming is True

    def test_basic_provider_also_supports_streaming(self, database_connection, monkeypatch):
        """Even providers without native streaming support it via fallback."""
        provider_manager = self._configure_provider(database_connection, FakeBasicProvider(), monkeypatch)
        assert provider_manager.supports_streaming is True

    def test_streaming_logs_usage_after_completion(self, database_connection, monkeypatch):
        provider_manager = self._configure_provider(database_connection, FakeStreamingProvider(), monkeypatch)

        list(provider_manager.complete_stream("Test prompt", feature="floor_plan_analysis"))

        usage_row = database_connection.execute(
            "SELECT feature, provider, tokens_used, estimated_cost FROM token_usage ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert usage_row is not None
        assert usage_row["feature"] == "floor_plan_analysis"
        assert usage_row["provider"] == "fake"
        assert usage_row["tokens_used"] > 0

    def test_streaming_raises_when_no_provider(self, database_connection):
        provider_manager = LLMProviderManager(database_connection)
        with pytest.raises(RuntimeError, match="No LLM provider configured"):
            list(provider_manager.complete_stream("test"))
