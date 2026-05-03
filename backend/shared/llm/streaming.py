"""SSE (Server-Sent Events) streaming helpers for LLM responses.

Converts LLM streaming generators into SSE-formatted responses
that the frontend can consume via EventSource or fetch with streaming.

SSE format:
  data: {"type": "chunk", "text": "Hello"}
  data: {"type": "chunk", "text": " world"}
  data: {"type": "done", "full_text": "Hello world"}
  data: {"type": "error", "message": "Budget exceeded"}

Usage in FastAPI route:
  from starlette.responses import StreamingResponse

  @router.get("/analyze/{listing_id}/stream")
  async def stream_analysis(listing_id: int):
      generator = llm_provider.complete_stream(prompt, system=system_prompt)
      return StreamingResponse(
          format_sse_stream(generator),
          media_type="text/event-stream",
      )
"""

import json
from typing import Iterator

from shared.app_logger import get_logger

logger = get_logger("llm.streaming")


def format_sse_stream(
    text_chunks: Iterator[str],
    metadata: dict | None = None,
) -> Iterator[str]:
    """Convert a text chunk generator into SSE-formatted events.

    Yields SSE-formatted strings for each chunk, plus a final 'done' event.
    If the generator raises an exception, yields an error event.

    Args:
        text_chunks: Iterator of text strings from LLM streaming.
        metadata: Optional dict to include in the 'done' event (e.g., token count, cost).
    """
    full_response_parts = []

    try:
        for chunk in text_chunks:
            if chunk:
                full_response_parts.append(chunk)
                event_data = json.dumps({"type": "chunk", "text": chunk})
                yield f"data: {event_data}\n\n"

    except Exception as streaming_error:
        logger.error("Streaming error: %s", streaming_error)
        error_data = json.dumps({
            "type": "error",
            "message": str(streaming_error),
        })
        yield f"data: {error_data}\n\n"
        return

    # Final event with complete text
    full_text = "".join(full_response_parts)
    done_event = {"type": "done", "full_text": full_text}
    if metadata:
        done_event["metadata"] = metadata
    yield f"data: {json.dumps(done_event)}\n\n"


def format_sse_progress(step_name: str, status: str, detail: str = "") -> str:
    """Format a pipeline progress event as SSE.

    Used to send intermediate progress updates during multi-step analysis:
      "Gathering neighborhood data..."
      "Analyzing floor plan..."
      "Generating price verdict..."
    """
    event_data = json.dumps({
        "type": "progress",
        "step": step_name,
        "status": status,
        "detail": detail,
    })
    return f"data: {event_data}\n\n"


def format_sse_error(message: str) -> str:
    """Format an error event as SSE."""
    event_data = json.dumps({"type": "error", "message": message})
    return f"data: {event_data}\n\n"
