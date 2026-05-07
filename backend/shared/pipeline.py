"""Data processing pipeline — gather, process, feed LLM, restructure, present.

A reusable pipeline pattern for any agent that needs to:
1. GATHER — collect data from multiple sources (DB, APIs, scraped pages)
2. PROCESS — normalize, clean, validate, enrich
3. BUILD CONTEXT — assemble a token-aware data package for LLM
4. ANALYZE — send to LLM with structured prompt
5. RESTRUCTURE — parse LLM output into usable data
6. PRESENT — format for frontend consumption

Each step is a function that transforms data. Steps are composable
and independently testable. The pipeline handles errors per-step
so partial results are still usable.

Used by:
  - NestScout: listing analysis, floor plan analysis, neighborhood intelligence
  - Jobsmith: resume generation, job matching, cover letter generation
"""

import json
from dataclasses import dataclass, field

from shared.app_logger import get_logger
from shared.llm.token_counter import count_text_tokens, fits_in_context

logger = get_logger("pipeline")


@dataclass
class PipelineContext:
    """Data flowing through the pipeline.

    Each step reads from and writes to this context.
    Steps that fail set their error — downstream steps can check and skip.
    """
    # Input
    source_data: dict = field(default_factory=dict)

    # Gathered data from various sources
    gathered: dict = field(default_factory=dict)

    # Processed/normalized data
    processed: dict = field(default_factory=dict)

    # LLM context package (text parts + images)
    context_text_parts: list[str] = field(default_factory=list)
    context_images: list[dict] = field(default_factory=list)
    context_token_estimate: int = 0

    # LLM output (raw)
    llm_raw_response: str = ""

    # Structured result (parsed LLM output)
    result: dict = field(default_factory=dict)

    # Errors per step
    errors: dict[str, str] = field(default_factory=dict)

    # Metadata
    steps_completed: list[str] = field(default_factory=list)
    llm_used: bool = False


def build_context_package(
    data_sections: dict[str, str],
    max_tokens: int = 150_000,
    reserve_for_output: int = 4_096,
    priority_order: list[str] | None = None,
) -> list[str]:
    """Assemble text sections into a context package that fits the token budget.

    Sections are added in priority order. If adding a section would exceed
    the budget, it's truncated or skipped.

    Args:
        data_sections: {"section_name": "section_text"}
        max_tokens: model's context window
        reserve_for_output: tokens reserved for the LLM's response
        priority_order: which sections to include first. Sections not in
                       the list are added after priority sections.

    Returns:
        List of text parts that fit within the token budget.
    """
    available_tokens = max_tokens - reserve_for_output
    text_parts = []
    tokens_used = 0

    # Determine order
    if priority_order:
        ordered_keys = list(priority_order)
        remaining_keys = [key for key in data_sections if key not in ordered_keys]
        ordered_keys.extend(remaining_keys)
    else:
        ordered_keys = list(data_sections.keys())

    for section_key in ordered_keys:
        section_text = data_sections.get(section_key)
        if not section_text:
            continue

        section_tokens = count_text_tokens(section_text)

        if tokens_used + section_tokens <= available_tokens:
            text_parts.append(section_text)
            tokens_used += section_tokens
        else:
            # Truncate to fit remaining budget
            remaining_tokens = available_tokens - tokens_used
            if remaining_tokens > 100:  # Only include if meaningful
                # Rough truncation: 4 bytes per token
                max_bytes = remaining_tokens * 4
                truncated = section_text[:max_bytes]
                truncated += "\n[...truncated due to context limit]"
                text_parts.append(truncated)
                tokens_used = available_tokens
            break  # No more room

    return text_parts


def parse_llm_json_response(response: str) -> dict | None:
    """Parse LLM response that contains JSON, handling markdown fences.

    LLMs often wrap JSON in ```json...``` blocks. This handles that
    plus common formatting quirks.
    """
    if not response:
        return None

    cleaned = response.strip()

    # Remove markdown code fences
    if cleaned.startswith("```"):
        # Remove first line (```json or ```)
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        else:
            cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object or array within the text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_index = cleaned.find(start_char)
            end_index = cleaned.rfind(end_char)
            if start_index != -1 and end_index > start_index:
                try:
                    return json.loads(cleaned[start_index:end_index + 1])
                except json.JSONDecodeError:
                    continue
        return None


def run_pipeline(
    context: PipelineContext,
    steps: list[tuple[str, callable]],
) -> PipelineContext:
    """Execute pipeline steps in order.

    Each step is a (name, function) tuple. The function receives
    the PipelineContext and modifies it in place.

    If a step raises an exception, the error is recorded and
    subsequent steps continue (they can check context.errors).
    """
    for step_name, step_function in steps:
        try:
            step_function(context)
            context.steps_completed.append(step_name)
        except Exception as step_error:
            context.errors[step_name] = str(step_error)
            logger.error("Pipeline step '%s' failed: %s", step_name, step_error)

    return context
