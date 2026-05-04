"""Lab analyzer service — orchestrates property analysis using the data pipeline.

Gathers listing data + preferences + comparables → builds context → LLM → cache.
Works without LLM (returns gathered data only).
"""

import json

from shared.address_utils import extract_city_from_address
from shared.app_logger import get_logger
from shared.pipeline import PipelineContext, build_context_package, parse_llm_json_response, run_pipeline
from agents.apartment.prompts.property_overview import build_overview_prompt, SYSTEM_PROMPT

logger = get_logger("apartment.lab_analyzer")


class LabAnalyzerService:
    """Orchestrates full property analysis for Nest Lab."""

    def __init__(self, listing_repo, feature_preferences_repo, lab_analysis_repo, llm_provider=None):
        self._listing_repo = listing_repo
        self._feature_preferences_repo = feature_preferences_repo
        self._lab_analysis_repo = lab_analysis_repo
        self._llm_provider = llm_provider

    def analyze(self, listing_id: int) -> dict:
        """Run full analysis pipeline. Returns gathered data + LLM analysis (if available)."""
        context = PipelineContext(source_data={"listing_id": listing_id})

        steps = [
            ("gather_listing", self._gather_listing),
            ("gather_preferences", self._gather_preferences),
            ("gather_comparables", self._gather_comparables),
            ("check_cache", self._check_cache),
        ]

        # Only add LLM steps if provider is configured and cache missed
        run_pipeline(context, steps)

        # If cache hit, return cached result
        if context.result.get("analysis"):
            return self._build_response(context)

        # If LLM available and no cache, run analysis
        if self._llm_provider and self._llm_provider.is_configured():
            llm_steps = [
                ("build_context", self._build_context),
                ("run_llm_analysis", self._run_llm_analysis),
                ("cache_result", self._cache_result),
            ]
            run_pipeline(context, llm_steps)

        return self._build_response(context)

    def analyze_stream(self, listing_id: int):
        """Stream analysis — yields text chunks for SSE.

        Gathers data first (non-streamed), then streams LLM response.
        """
        context = PipelineContext(source_data={"listing_id": listing_id})

        # Gather data (non-streamed)
        gather_steps = [
            ("gather_listing", self._gather_listing),
            ("gather_preferences", self._gather_preferences),
            ("gather_comparables", self._gather_comparables),
            ("check_cache", self._check_cache),
        ]
        run_pipeline(context, gather_steps)

        # If cache hit, yield cached result as one chunk
        cached_analysis = context.result.get("analysis")
        if cached_analysis:
            yield json.dumps(cached_analysis)
            return

        # If no LLM, nothing to stream
        if not self._llm_provider or not self._llm_provider.is_configured():
            return

        # Build context
        self._build_context(context)

        # Stream LLM response
        prompt = context.processed.get("prompt", "")
        if not prompt:
            return

        full_response_chunks = []
        for chunk in self._llm_provider.complete_stream(
            prompt, system=SYSTEM_PROMPT, feature="lab_overview"
        ):
            full_response_chunks.append(chunk)
            yield chunk

        # After streaming, parse and cache
        full_response = "".join(full_response_chunks)
        parsed_result = parse_llm_json_response(full_response)
        if parsed_result:
            listing_id = context.source_data["listing_id"]
            self._lab_analysis_repo.save_analysis(listing_id, "overview", parsed_result)

    def get_lab_data(self, listing_id: int) -> dict:
        """Get all gathered data WITHOUT running LLM — for no-LLM mode."""
        context = PipelineContext(source_data={"listing_id": listing_id})
        steps = [
            ("gather_listing", self._gather_listing),
            ("gather_preferences", self._gather_preferences),
            ("gather_comparables", self._gather_comparables),
            ("check_cache", self._check_cache),
        ]
        run_pipeline(context, steps)
        return self._build_response(context)

    # ── Pipeline steps ────────────────────────────────────

    def _gather_listing(self, context: PipelineContext) -> None:
        listing_id = context.source_data["listing_id"]
        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found")
        context.gathered["listing"] = listing

    def _gather_preferences(self, context: PipelineContext) -> None:
        must_haves = self._feature_preferences_repo.get_must_haves()
        deal_breakers = self._feature_preferences_repo.get_deal_breakers()
        all_preferences = self._feature_preferences_repo.get_all_preferences()
        context.gathered["preferences"] = {
            "must_haves": must_haves,
            "deal_breakers": deal_breakers,
            "all": all_preferences,
        }

    def _gather_comparables(self, context: PipelineContext) -> None:
        listing = context.gathered.get("listing") or {}
        city = extract_city_from_address(listing.get("address") or "")
        listing_id = context.source_data["listing_id"]

        if city:
            context.gathered["comparables"] = self._listing_repo.find_comparables(
                city=city, exclude_listing_id=listing_id, limit=10,
            )
        else:
            context.gathered["comparables"] = []

    def _check_cache(self, context: PipelineContext) -> None:
        listing_id = context.source_data["listing_id"]
        cached = self._lab_analysis_repo.get_cached_analysis(listing_id, "overview")
        if cached:
            context.result["analysis"] = cached
            logger.info("Using cached analysis for listing %d", listing_id)

    def _build_context(self, context: PipelineContext) -> None:
        listing = context.gathered.get("listing") or {}
        preferences = context.gathered.get("preferences") or {}
        comparables = context.gathered.get("comparables") or []

        prompt = build_overview_prompt(
            listing=listing,
            user_preferences=preferences,
            comparable_listings=comparables,
        )
        context.processed["prompt"] = prompt
        context.context_text_parts = [prompt]

    def _run_llm_analysis(self, context: PipelineContext) -> None:
        prompt = context.processed.get("prompt", "")
        if not prompt:
            return

        response = self._llm_provider.complete(
            prompt, system=SYSTEM_PROMPT, feature="lab_overview"
        )
        context.llm_raw_response = response
        context.llm_used = True

        parsed = parse_llm_json_response(response)
        if parsed:
            context.result["analysis"] = parsed
        else:
            # LLM returned non-JSON — store raw text as overview
            context.result["analysis"] = {"overview": response, "parse_error": True}
            logger.warning("LLM returned non-JSON response for lab analysis")

    def _cache_result(self, context: PipelineContext) -> None:
        analysis = context.result.get("analysis")
        if not analysis:
            return
        listing_id = context.source_data["listing_id"]
        self._lab_analysis_repo.save_analysis(listing_id, "overview", analysis)

    # ── Response assembly ─────────────────────────────────

    def _build_response(self, context: PipelineContext) -> dict:
        listing = context.gathered.get("listing") or {}
        preferences = context.gathered.get("preferences") or {}
        comparables = context.gathered.get("comparables") or []
        analysis = context.result.get("analysis")

        response = {
            "listing": listing,
            "feature_preferences": preferences.get("all") or [],
            "must_haves": preferences.get("must_haves") or [],
            "deal_breakers": preferences.get("deal_breakers") or [],
            "comparable_count": len(comparables),
            "analyses": {},
            "pipeline_steps": context.steps_completed,
            "pipeline_errors": context.errors,
        }

        if analysis:
            response["analyses"]["overview"] = analysis

        # Also include any other cached analyses
        listing_id = context.source_data.get("listing_id")
        if listing_id:
            all_cached = self._lab_analysis_repo.get_all_for_listing(listing_id)
            for analysis_type, cached_result in all_cached.items():
                if analysis_type not in response["analyses"]:
                    response["analyses"][analysis_type] = cached_result

        return response
