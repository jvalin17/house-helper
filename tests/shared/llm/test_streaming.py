"""SSE streaming — tests for LLM response streaming and SSE formatting.

Tests cover:
- SSE event format compliance (data: JSON\n\n)
- Chunk-by-chunk streaming
- Error handling mid-stream
- Progress events for multi-step pipelines
- Done event with full text assembly
"""

import json

from shared.llm.streaming import (
    format_sse_stream,
    format_sse_progress,
    format_sse_error,
)


# ── SSE stream formatting ─────────────────────────────────

class TestFormatSseStream:
    def test_yields_chunk_events_for_each_text_piece(self):
        """Each text chunk becomes a separate SSE data event."""
        chunks = iter(["Hello", " world", "!"])
        events = list(format_sse_stream(chunks))

        # 3 chunk events + 1 done event
        assert len(events) == 4

        # First chunk
        first_event = json.loads(events[0].replace("data: ", "").strip())
        assert first_event["type"] == "chunk"
        assert first_event["text"] == "Hello"

        # Second chunk
        second_event = json.loads(events[1].replace("data: ", "").strip())
        assert second_event["text"] == " world"

    def test_done_event_contains_full_assembled_text(self):
        chunks = iter(["The apartment ", "scores 85/100 ", "for livability."])
        events = list(format_sse_stream(chunks))

        done_event = json.loads(events[-1].replace("data: ", "").strip())
        assert done_event["type"] == "done"
        assert done_event["full_text"] == "The apartment scores 85/100 for livability."

    def test_done_event_includes_metadata_when_provided(self):
        chunks = iter(["Analysis complete."])
        metadata = {"tokens_used": 1_500, "estimated_cost": 0.0045}
        events = list(format_sse_stream(chunks, metadata=metadata))

        done_event = json.loads(events[-1].replace("data: ", "").strip())
        assert done_event["metadata"]["tokens_used"] == 1_500
        assert done_event["metadata"]["estimated_cost"] == 0.0045

    def test_handles_error_mid_stream(self):
        """If the generator raises, yield an error event instead of crashing."""
        def failing_generator():
            yield "Starting analysis..."
            raise RuntimeError("Budget exceeded: $0.50 spent of $0.50 limit")

        events = list(format_sse_stream(failing_generator()))

        # Should have 1 chunk + 1 error (no done event)
        assert len(events) == 2

        chunk_event = json.loads(events[0].replace("data: ", "").strip())
        assert chunk_event["type"] == "chunk"
        assert chunk_event["text"] == "Starting analysis..."

        error_event = json.loads(events[1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Budget exceeded" in error_event["message"]

    def test_empty_generator_yields_only_done(self):
        events = list(format_sse_stream(iter([])))
        assert len(events) == 1
        done_event = json.loads(events[0].replace("data: ", "").strip())
        assert done_event["type"] == "done"
        assert done_event["full_text"] == ""

    def test_skips_empty_chunks(self):
        chunks = iter(["Hello", "", None, " world"])
        events = list(format_sse_stream(chunks))

        # Only "Hello" and " world" should produce chunk events
        chunk_events = [
            json.loads(event.replace("data: ", "").strip())
            for event in events
            if "chunk" in event
        ]
        assert len(chunk_events) == 2

    def test_sse_format_compliance(self):
        """Every event must follow SSE spec: 'data: ...\n\n'"""
        chunks = iter(["test chunk"])
        events = list(format_sse_stream(chunks))

        for event in events:
            assert event.startswith("data: ")
            assert event.endswith("\n\n")

    def test_json_parseable_events(self):
        """All event payloads must be valid JSON."""
        chunks = iter(["Apartment has pool", " and gym."])
        events = list(format_sse_stream(chunks))

        for event in events:
            payload = event.replace("data: ", "").strip()
            parsed = json.loads(payload)  # Should not raise
            assert "type" in parsed


# ── Progress events ───────────────────────────────────────

class TestFormatSseProgress:
    def test_formats_progress_event(self):
        event = format_sse_progress(
            "neighborhood_analysis",
            "running",
            "Fetching Walk Score data...",
        )
        parsed = json.loads(event.replace("data: ", "").strip())
        assert parsed["type"] == "progress"
        assert parsed["step"] == "neighborhood_analysis"
        assert parsed["status"] == "running"
        assert parsed["detail"] == "Fetching Walk Score data..."

    def test_progress_without_detail(self):
        event = format_sse_progress("floor_plan", "complete")
        parsed = json.loads(event.replace("data: ", "").strip())
        assert parsed["step"] == "floor_plan"
        assert parsed["detail"] == ""

    def test_sse_format_compliance(self):
        event = format_sse_progress("step", "running")
        assert event.startswith("data: ")
        assert event.endswith("\n\n")


# ── Error events ──────────────────────────────────────────

class TestFormatSseError:
    def test_formats_error_event(self):
        event = format_sse_error("No LLM provider configured. Set one in Settings.")
        parsed = json.loads(event.replace("data: ", "").strip())
        assert parsed["type"] == "error"
        assert "No LLM provider" in parsed["message"]

    def test_sse_format_compliance(self):
        event = format_sse_error("test error")
        assert event.startswith("data: ")
        assert event.endswith("\n\n")


# ── Integration: Simulated LLM streaming ──────────────────

class TestStreamingIntegration:
    def test_simulates_property_analysis_stream(self):
        """Simulate what a real Nest Lab analysis stream would look like."""
        def simulated_analysis_generator():
            yield "## Property Overview\n\n"
            yield "Alexan Braker Pointe is a modern apartment complex "
            yield "located in North Austin near the Mopac corridor. "
            yield "Priced at $1,445/mo for a 1BR, this is "
            yield "**below the area median of $1,600** — a good deal.\n\n"
            yield "## Key Strengths\n"
            yield "- 24 units available (good selection)\n"
            yield "- Lounge amenity (only 17% of Austin complexes)\n"

        events = list(format_sse_stream(simulated_analysis_generator()))

        # Should have 8 chunks + 1 done
        chunk_count = sum(1 for event in events if '"chunk"' in event)
        assert chunk_count == 8

        done_event = json.loads(events[-1].replace("data: ", "").strip())
        assert "Alexan Braker Pointe" in done_event["full_text"]
        assert "below the area median" in done_event["full_text"]
        assert done_event["full_text"].startswith("## Property Overview")

    def test_pipeline_with_progress_and_streaming(self):
        """Simulate a full pipeline: progress events → streamed analysis → done."""
        all_events = []

        # Progress events from pipeline steps
        all_events.append(format_sse_progress("data_gathering", "running", "Loading listing data..."))
        all_events.append(format_sse_progress("data_gathering", "complete"))
        all_events.append(format_sse_progress("llm_analysis", "running", "Generating analysis..."))

        # Streamed LLM response
        llm_chunks = iter(["This apartment ", "is a great value."])
        all_events.extend(format_sse_stream(llm_chunks))

        # Verify event order
        parsed_events = [json.loads(event.replace("data: ", "").strip()) for event in all_events]
        event_types = [event["type"] for event in parsed_events]
        assert event_types == ["progress", "progress", "progress", "chunk", "chunk", "done"]
