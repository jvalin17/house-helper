"""Nest Intel service — orchestrates the premium intelligence pipeline.

Manages cost estimation, budget enforcement, and multi-step data gathering.
Each step is independent — partial failures return partial results.

Three-tier architecture:
  Search Cards → free, instant, from DB
  Nest Lab     → LLM tokens only
  Nest Intel   → $$ APIs + LLM vision + concession extraction
"""

import json
import sqlite3

from shared.app_logger import get_logger
from shared.credentials import CredentialStore
from shared.pipeline import PipelineContext, run_pipeline
from agents.apartment.repositories.intel_repo import IntelRepository
from agents.apartment.repositories.listing_repo import ApartmentListingRepository

logger = get_logger("apartment.intel")

# Cost estimates per API call (in USD)
COST_ESTIMATES = {
    "unit_details": 0.001,       # RealtyAPI: 1 of 250 free/mo
    "verified_scores": 0.0,      # Walk Score: free tier
    "distances": 0.01,           # Google Distance Matrix × 2
    "floor_plan_analysis": 0.03, # Vision LLM (Claude/GPT-4o)
    "concessions": 0.01,         # Text LLM extraction
}

PER_LISTING_COST_CAP = 5.00
DEFAULT_DAILY_BUDGET = 1.00


class IntelService:
    """Orchestrates Nest Intel — premium property intelligence."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        llm_provider=None,
    ):
        self._connection = connection
        self._llm_provider = llm_provider
        self._credential_store = CredentialStore(connection)
        self._intel_repo = IntelRepository(connection)
        self._listing_repo = ApartmentListingRepository(connection)

    def estimate_cost(self, listing_id: int) -> dict:
        """Check which sources are configured and estimate total cost.

        Returns available/unavailable sources, estimated cost, budget status.
        Called BEFORE user clicks "Get Intel" — shows what they'll get and what it costs.
        """
        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            return {"error": "Listing not found"}

        available_sources, unavailable_sources = self._check_source_availability(listing_id, listing)
        total_estimated_cost = sum(source["estimated_cost"] for source in available_sources)

        # Budget check
        listing_spend = self._intel_repo.get_total_cost_for_listing(listing_id)
        daily_spend = self._intel_repo.get_daily_spend()
        daily_budget = self._get_daily_budget()
        per_listing_remaining = PER_LISTING_COST_CAP - listing_spend
        daily_remaining = daily_budget - daily_spend

        budget_warning = None
        if total_estimated_cost > per_listing_remaining:
            budget_warning = f"Per-listing cap reached (${listing_spend:.2f} of ${PER_LISTING_COST_CAP:.2f} spent)"
        elif total_estimated_cost > daily_remaining:
            budget_warning = f"Daily budget low (${daily_spend:.2f} of ${daily_budget:.2f} used)"

        existing_intel = self._intel_repo.get_all_intel(listing_id)

        return {
            "listing_id": listing_id,
            "available_sources": available_sources,
            "unavailable_sources": unavailable_sources,
            "estimated_cost": round(total_estimated_cost, 4),
            "per_listing_spent": round(listing_spend, 4),
            "per_listing_remaining": round(per_listing_remaining, 4),
            "daily_spent": round(daily_spend, 4),
            "daily_remaining": round(daily_remaining, 4),
            "daily_budget": daily_budget,
            "can_proceed": (
                total_estimated_cost <= per_listing_remaining
                and total_estimated_cost <= daily_remaining
                and len(available_sources) > 0
            ),
            "budget_warning": budget_warning,
            "already_gathered": len(existing_intel) > 0,
            "gathered_types": list(existing_intel.keys()),
        }

    def _check_source_availability(self, listing_id: int, listing: dict) -> tuple[list[dict], list[dict]]:
        """Check which Intel sources are configured and available.

        Returns (available_sources, unavailable_sources) with labels and costs.
        """
        available = []
        unavailable = []

        # Simple API-key-gated sources
        api_key_sources = [
            ("unit_details", "Unit Availability", "realtyapi", "RealtyAPI not configured"),
            ("verified_scores", "Walk / Transit / Bike Scores", "walkscore", "Walk Score not configured"),
            ("distances", "Airport + Commute Distance", "google_maps", "Google Maps not configured"),
        ]
        for source_name, label, credential_key, unavailable_reason in api_key_sources:
            if self._credential_store.is_configured(credential_key):
                available.append({"name": source_name, "label": label, "estimated_cost": COST_ESTIMATES[source_name]})
            else:
                unavailable.append({"name": source_name, "label": label, "reason": unavailable_reason})

        # Floor plan analysis — requires vision LLM + floor plan image
        has_vision_llm = (
            self._llm_provider
            and self._llm_provider.is_configured()
            and hasattr(self._llm_provider, "supports_vision")
            and self._llm_provider.supports_vision
        )
        has_floor_plan = self._has_floor_plan(listing_id)
        if has_vision_llm and has_floor_plan:
            available.append({"name": "floor_plan_analysis", "label": "Floor Plan Analysis (Vision AI)", "estimated_cost": COST_ESTIMATES["floor_plan_analysis"]})
        else:
            reasons = []
            if not has_vision_llm:
                reasons.append("No vision-capable AI provider")
            if not has_floor_plan:
                reasons.append("No floor plan image available")
            unavailable.append({"name": "floor_plan_analysis", "label": "Floor Plan Analysis (Vision AI)", "reason": "; ".join(reasons)})

        # Concession extraction — requires LLM + listing URL
        has_llm = self._llm_provider and self._llm_provider.is_configured()
        if has_llm and listing.get("source_url"):
            available.append({"name": "concessions", "label": "Concessions + Fee Extraction", "estimated_cost": COST_ESTIMATES["concessions"]})
        else:
            reasons = []
            if not has_llm:
                reasons.append("No AI provider configured")
            if not listing.get("source_url"):
                reasons.append("No listing URL available")
            unavailable.append({"name": "concessions", "label": "Concessions + Fee Extraction", "reason": "; ".join(reasons)})

        return available, unavailable

    def gather(self, listing_id: int) -> dict:
        """Run the full Intel pipeline — gather from all configured sources.

        Each step is independent. If one fails, others continue.
        Results are cached per-step in apartment_intel.
        """
        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            return {"error": "Listing not found"}

        # Budget check
        estimate = self.estimate_cost(listing_id)
        has_budget_issue = bool(estimate.get("budget_warning"))
        if has_budget_issue and not estimate.get("can_proceed"):
            return {
                "error": "Budget exceeded",
                "budget_warning": estimate.get("budget_warning"),
                "per_listing_remaining": estimate.get("per_listing_remaining"),
                "daily_remaining": estimate.get("daily_remaining"),
            }

        context = PipelineContext(source_data={
            "listing_id": listing_id,
            "listing": listing,
        })

        steps = []

        # Step 1: Unit details (RealtyAPI)
        if self._credential_store.is_configured("realtyapi"):
            steps.append(("unit_details", self._gather_unit_details))

        # Step 2: Verified scores (Walk Score)
        if self._credential_store.is_configured("walkscore"):
            steps.append(("verified_scores", self._gather_verified_scores))

        # Step 3: Distances (Google Maps)
        if self._credential_store.is_configured("google_maps"):
            steps.append(("distances", self._gather_distances))

        # Step 4: Floor plan analysis (Vision LLM)
        has_vision_llm = (
            self._llm_provider
            and self._llm_provider.is_configured()
            and hasattr(self._llm_provider, "supports_vision")
            and self._llm_provider.supports_vision
        )
        if has_vision_llm and self._has_floor_plan(listing_id):
            steps.append(("floor_plan_analysis", self._gather_floor_plan_analysis))

        # Step 5: Concession extraction (LLM + URL)
        has_llm = self._llm_provider and self._llm_provider.is_configured()
        has_source_url = bool(listing.get("source_url"))
        if has_llm and has_source_url:
            steps.append(("concessions", self._gather_concessions))

        # Run all configured steps
        run_pipeline(context, steps)

        return {
            "listing_id": listing_id,
            "intel": self._intel_repo.get_all_intel(listing_id),
            "total_cost": self._intel_repo.get_total_cost_for_listing(listing_id),
            "steps_completed": context.steps_completed,
            "steps_failed": context.errors,
        }

    def gather_stream(self, listing_id: int):
        """SSE streaming variant — yields progress events per step.

        Each step emits: running → complete/error. Final event includes full Intel.
        """
        import json as json_module
        from shared.llm.streaming import format_sse_progress, format_sse_error

        listing = self._listing_repo.get_listing(listing_id)
        if not listing:
            yield format_sse_error("Listing not found")
            return

        # Budget check
        estimate = self.estimate_cost(listing_id)
        has_budget_issue = bool(estimate.get("budget_warning"))
        if has_budget_issue and not estimate.get("can_proceed"):
            yield format_sse_error(estimate.get("budget_warning", "Budget exceeded"))
            return

        context = PipelineContext(source_data={
            "listing_id": listing_id,
            "listing": listing,
        })

        step_labels = {
            "unit_details": "Fetching unit availability",
            "verified_scores": "Getting Walk / Transit / Bike scores",
            "distances": "Calculating airport + commute distances",
            "floor_plan_analysis": "Analyzing floor plan with Vision AI",
            "concessions": "Extracting concessions + fees",
        }

        # Build step list (same logic as gather)
        steps = []
        if self._credential_store.is_configured("realtyapi"):
            steps.append(("unit_details", self._gather_unit_details))
        if self._credential_store.is_configured("walkscore"):
            steps.append(("verified_scores", self._gather_verified_scores))
        if self._credential_store.is_configured("google_maps"):
            steps.append(("distances", self._gather_distances))

        has_vision_llm = (
            self._llm_provider
            and self._llm_provider.is_configured()
            and hasattr(self._llm_provider, "supports_vision")
            and self._llm_provider.supports_vision
        )
        if has_vision_llm and self._has_floor_plan(listing_id):
            steps.append(("floor_plan_analysis", self._gather_floor_plan_analysis))

        has_llm = self._llm_provider and self._llm_provider.is_configured()
        has_source_url = bool(listing.get("source_url"))
        if has_llm and has_source_url:
            steps.append(("concessions", self._gather_concessions))

        if not steps:
            yield format_sse_error("No Intel sources configured")
            return

        # Run each step with SSE progress
        for step_name, step_function in steps:
            label = step_labels.get(step_name, step_name)
            yield format_sse_progress(step_name, "running", label)

            try:
                step_function(context)
                context.steps_completed.append(step_name)
                yield format_sse_progress(step_name, "complete", label)
            except Exception as step_error:
                context.errors[step_name] = str(step_error)
                logger.error("Intel step '%s' failed: %s", step_name, step_error)
                yield format_sse_progress(step_name, "error", str(step_error))

        # Done — emit final result
        final_data = {
            "type": "done",
            "intel": {
                intel_type: {
                    "result": intel_entry["result"],
                    "source_api": intel_entry.get("source_api"),
                    "actual_cost": intel_entry.get("actual_cost"),
                    "created_at": intel_entry.get("created_at"),
                }
                for intel_type, intel_entry in self._intel_repo.get_all_intel(listing_id).items()
            },
            "total_cost": self._intel_repo.get_total_cost_for_listing(listing_id),
            "steps_completed": context.steps_completed,
            "steps_failed": context.errors,
        }
        yield f"data: {json_module.dumps(final_data)}\n\n"

    # ── Pipeline steps ─────────────────────────────────────

    def _gather_unit_details(self, context: PipelineContext) -> None:
        """Fetch unit-level details from RealtyAPI /apartment_details."""
        from agents.apartment.services.unit_details_service import fetch_unit_details

        listing_id = context.source_data["listing_id"]
        result = fetch_unit_details(listing_id, self._connection)

        if result and result.get("total_available", 0) > 0:
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="unit_details",
                result=result,
                source_api="realtyapi",
                estimated_cost=COST_ESTIMATES["unit_details"],
                actual_cost=COST_ESTIMATES["unit_details"],
            )
            context.gathered["unit_details"] = result
            logger.info("Gathered %d units for listing %d", result["total_available"], listing_id)
        else:
            logger.info("No unit details available for listing %d", listing_id)

    def _gather_verified_scores(self, context: PipelineContext) -> None:
        """Fetch Walk Score / Transit Score / Bike Score."""
        from agents.apartment.services.neighborhood_service import get_walk_scores

        listing = context.source_data["listing"]
        listing_id = context.source_data["listing_id"]
        latitude = listing.get("latitude")
        longitude = listing.get("longitude")
        address = listing.get("address") or ""

        if not latitude or not longitude:
            logger.info("No coordinates for listing %d — skipping scores", listing_id)
            return

        scores = get_walk_scores(latitude, longitude, address, self._connection)
        if scores:
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="verified_scores",
                result=scores,
                source_api="walkscore",
                estimated_cost=COST_ESTIMATES["verified_scores"],
                actual_cost=0.0,
            )
            context.gathered["verified_scores"] = scores
            logger.info(
                "Gathered scores for listing %d: walk=%s, transit=%s, bike=%s",
                listing_id, scores.get("walk_score"), scores.get("transit_score"), scores.get("bike_score"),
            )

    def _gather_distances(self, context: PipelineContext) -> None:
        """Fetch airport distance + commute time via Google Distance Matrix."""
        from agents.apartment.services.neighborhood_service import (
            get_distance_to_airport,
            get_commute_time,
        )

        listing = context.source_data["listing"]
        listing_id = context.source_data["listing_id"]
        latitude = listing.get("latitude")
        longitude = listing.get("longitude")

        if not latitude or not longitude:
            logger.info("No coordinates for listing %d — skipping distances", listing_id)
            return

        distance_result = {}

        # Airport distance
        airport_data = get_distance_to_airport(latitude, longitude, self._connection)
        if airport_data:
            distance_result["airport"] = airport_data

        # Commute time (if user has workplace set)
        workplace_row = self._connection.execute(
            "SELECT location FROM apartment_preferences LIMIT 1"
        ).fetchone()
        workplace_address = workplace_row["location"] if workplace_row else None

        if workplace_address:
            commute_data = get_commute_time(
                latitude, longitude, workplace_address, self._connection
            )
            if commute_data:
                distance_result["commute"] = commute_data

        if distance_result:
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="distances",
                result=distance_result,
                source_api="google_maps",
                estimated_cost=COST_ESTIMATES["distances"],
                actual_cost=COST_ESTIMATES["distances"],
            )
            context.gathered["distances"] = distance_result
            logger.info("Gathered distances for listing %d", listing_id)

    def _gather_floor_plan_analysis(self, context: PipelineContext) -> None:
        """Analyze floor plan image(s) using vision LLM."""
        from agents.apartment.services.floor_plan_analyzer import analyze_floor_plan

        listing_id = context.source_data["listing_id"]
        result = analyze_floor_plan(
            listing_id, self._connection, self._llm_provider
        )

        if result and not result.get("parse_error"):
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="floor_plan_analysis",
                result=result,
                source_api="vision_llm",
                estimated_cost=COST_ESTIMATES["floor_plan_analysis"],
                actual_cost=COST_ESTIMATES["floor_plan_analysis"],
            )
            context.gathered["floor_plan_analysis"] = result
            logger.info(
                "Floor plan analysis complete for listing %d: livability=%s",
                listing_id, result.get("livability_score"),
            )

    def _gather_concessions(self, context: PipelineContext) -> None:
        """Extract concessions and fees from listing URL via LLM."""
        from agents.apartment.services.concession_extractor import extract_concessions

        listing_id = context.source_data["listing_id"]
        result = extract_concessions(
            listing_id, self._connection, self._llm_provider
        )

        if result and not result.get("error") and not result.get("parse_error"):
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="concessions",
                result=result,
                source_api="llm_extraction",
                estimated_cost=COST_ESTIMATES["concessions"],
                actual_cost=COST_ESTIMATES["concessions"],
            )
            context.gathered["concessions"] = result
            logger.info("Concession extraction complete for listing %d", listing_id)

    def get_cached_intel(self, listing_id: int) -> dict | None:
        """Return cached Intel data if it exists."""
        all_intel = self._intel_repo.get_all_intel(listing_id)
        if not all_intel:
            return None
        return {
            "listing_id": listing_id,
            "intel": all_intel,
            "total_cost": self._intel_repo.get_total_cost_for_listing(listing_id),
        }

    def _has_floor_plan(self, listing_id: int) -> bool:
        """Check if listing has any floor plan images."""
        row = self._connection.execute(
            "SELECT 1 FROM apartment_floor_plans WHERE listing_id = ? LIMIT 1",
            (listing_id,),
        ).fetchone()
        return row is not None

    def _get_daily_budget(self) -> float:
        """Read daily Intel budget from settings, or use default."""
        row = self._connection.execute(
            "SELECT value FROM settings WHERE key = 'intel_budget'"
        ).fetchone()
        if row:
            try:
                config = json.loads(row["value"])
                return float(config.get("daily_limit", DEFAULT_DAILY_BUDGET))
            except (json.JSONDecodeError, TypeError, ValueError) as parse_error:
                logger.warning("Failed to parse intel_budget setting: %s", parse_error)
        return DEFAULT_DAILY_BUDGET
