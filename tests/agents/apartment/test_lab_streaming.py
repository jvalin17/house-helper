"""Lab SSE streaming endpoint — tests for progress events + LLM chunks.

Tests the full HTTP streaming response, verifying SSE format compliance
and event ordering: progress → chunks → done.
"""

import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from agents.apartment.routes import create_router as create_apartment_router


MOCK_ANALYSIS_JSON = json.dumps({
    "overview": "Great apartment in North Austin.",
    "price_verdict": "fair",
    "match_score": 78,
})


class FakeStreamingLLM(LLMProviderBase):
    """Mock LLM that yields chunks for streaming tests."""

    def complete(self, prompt, system=None, feature="unknown", force_override=False):
        return MOCK_ANALYSIS_JSON

    def complete_stream(self, prompt, system=None, feature="unknown", force_override=False):
        yield '{"overview": "Great '
        yield 'apartment in North '
        yield 'Austin.", "price_verdict": '
        yield '"fair", "match_score": 78}'

    def is_configured(self):
        return True

    def provider_name(self):
        return "fake"

    def model_name(self):
        return "fake-stream"


class FakeNoLLM(LLMProviderBase):
    def complete(self, prompt, system=None):
        raise RuntimeError("Not configured")
    def is_configured(self):
        return False
    def provider_name(self):
        return "none"
    def model_name(self):
        return "none"


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def streaming_test_client(database_connection):
    """Test client with a fake streaming LLM provider."""
    application = FastAPI()
    application.include_router(create_apartment_router(database_connection, llm_provider=FakeStreamingLLM()))
    return TestClient(application)


@pytest.fixture
def no_llm_test_client(database_connection):
    """Test client without LLM configured."""
    application = FastAPI()
    application.include_router(create_apartment_router(database_connection, llm_provider=FakeNoLLM()))
    return TestClient(application)


@pytest.fixture
def sample_listing_id(database_connection):
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, address, price, bedrooms) VALUES (?, ?, ?, ?)",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX, 78759", 1445, 1),
    )
    database_connection.commit()
    return cursor.lastrowid


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response into list of event dicts."""
    events = []
    for line in response_text.strip().split("\n\n"):
        for subline in line.strip().split("\n"):
            if subline.startswith("data: "):
                payload = subline[6:]
                events.append(json.loads(payload))
    return events


class TestLabStreamingEndpoint:
    def test_stream_returns_event_stream_content_type(self, streaming_test_client, sample_listing_id):
        response = streaming_test_client.get(f"/api/apartments/lab/{sample_listing_id}/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_yields_progress_then_chunks_then_done(self, streaming_test_client, sample_listing_id):
        response = streaming_test_client.get(f"/api/apartments/lab/{sample_listing_id}/stream")
        events = parse_sse_events(response.text)

        event_types = [event["type"] for event in events]

        # Should have: progress, progress, progress, chunk(s), done
        assert "progress" in event_types
        assert "chunk" in event_types
        assert event_types[-1] == "done"

    def test_stream_progress_events_have_step_info(self, streaming_test_client, sample_listing_id):
        response = streaming_test_client.get(f"/api/apartments/lab/{sample_listing_id}/stream")
        events = parse_sse_events(response.text)

        progress_events = [event for event in events if event["type"] == "progress"]
        assert len(progress_events) >= 2
        step_names = [event["step"] for event in progress_events]
        assert "gathering_data" in step_names
        assert "analyzing" in step_names

    def test_stream_done_event_contains_full_text(self, streaming_test_client, sample_listing_id):
        response = streaming_test_client.get(f"/api/apartments/lab/{sample_listing_id}/stream")
        events = parse_sse_events(response.text)

        done_event = next(event for event in events if event["type"] == "done")
        assert "Great apartment" in done_event["full_text"]
        assert "North Austin" in done_event["full_text"]

    def test_stream_returns_error_for_nonexistent_listing(self, streaming_test_client):
        response = streaming_test_client.get("/api/apartments/lab/99999/stream")
        events = parse_sse_events(response.text)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "not found" in events[0]["message"].lower()

    def test_stream_without_llm_yields_empty_done(self, no_llm_test_client, database_connection):
        """Without LLM, stream should yield progress + empty done (no chunks)."""
        cursor = database_connection.execute(
            "INSERT INTO apartment_listings (title, price) VALUES (?, ?)",
            ("Test Listing", 1200),
        )
        database_connection.commit()
        listing_id = cursor.lastrowid

        response = no_llm_test_client.get(f"/api/apartments/lab/{listing_id}/stream")
        events = parse_sse_events(response.text)

        event_types = [event["type"] for event in events]
        assert "progress" in event_types
        # Should have done with empty text (no LLM output)
        done_event = next(event for event in events if event["type"] == "done")
        assert done_event["full_text"] == ""
