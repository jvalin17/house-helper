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
    "reviews": 0.02,             # Google Places ($0.003) + LLM sentiment (~$0.017)
    "policies": 0.01,            # Text LLM extraction (reuses concession page text)
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
        if has_vision_llm:
            has_floor_plan = self._has_floor_plan(listing_id)
            floor_plan_label = "Floor Plan Analysis (Vision AI)"
            if has_floor_plan:
                floor_plan_label += " — image found"
            else:
                floor_plan_label += " — will search for images"
            available.append({"name": "floor_plan_analysis", "label": floor_plan_label, "estimated_cost": COST_ESTIMATES["floor_plan_analysis"]})
        else:
            unavailable.append({"name": "floor_plan_analysis", "label": "Floor Plan Analysis (Vision AI)", "reason": "No vision-capable AI provider"})

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

        # Reviews — requires Google Maps key (Places API) + LLM for sentiment
        has_google = self._credential_store.is_configured("google_maps")
        if has_google:
            available.append({"name": "reviews", "label": "Resident Reviews + Sentiment", "estimated_cost": COST_ESTIMATES["reviews"]})
        else:
            unavailable.append({"name": "reviews", "label": "Resident Reviews + Sentiment", "reason": "Google Maps not configured"})

        # Policies — requires LLM + listing URL (same prereqs as concessions)
        if has_llm and listing.get("source_url"):
            available.append({"name": "policies", "label": "Lease Policies + Rules", "estimated_cost": COST_ESTIMATES["policies"]})
        else:
            reasons = []
            if not has_llm:
                reasons.append("No AI provider configured")
            if not listing.get("source_url"):
                reasons.append("No listing URL available")
            unavailable.append({"name": "policies", "label": "Lease Policies + Rules", "reason": "; ".join(reasons)})

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

        steps = self._build_step_list(listing_id, listing)
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
            "discover_floor_plans": "Searching for floor plan images",
            "floor_plan_analysis": "Analyzing floor plan with Vision AI",
            "concessions": "Extracting concessions + fees",
            "reviews": "Mining resident reviews + sentiment",
            "policies": "Extracting lease policies + rules",
        }

        steps = self._build_step_list(listing_id, listing)

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

    def _build_step_list(self, listing_id: int, listing: dict) -> list[tuple[str, callable]]:
        """Build the list of Intel pipeline steps based on configured sources.

        Single source of truth — used by gather(), gather_stream(), and step labels.
        """
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
        if has_vision_llm:
            # Try to discover floor plans if none in DB, then analyze
            if not self._has_floor_plan(listing_id):
                steps.append(("discover_floor_plans", self._discover_floor_plans))
            steps.append(("floor_plan_analysis", self._gather_floor_plan_analysis))

        has_llm = self._llm_provider and self._llm_provider.is_configured()
        has_source_url = bool(listing.get("source_url"))
        if has_llm and has_source_url:
            # Pre-fetch page once, shared by concessions + policies
            steps.append(("fetch_page", self._prefetch_listing_page))
            steps.append(("concessions", self._gather_concessions))
        if self._credential_store.is_configured("google_maps"):
            steps.append(("reviews", self._gather_reviews))
        if has_llm and has_source_url:
            steps.append(("policies", self._gather_policies))

        return steps

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

    def _discover_floor_plans(self, context: PipelineContext) -> None:
        """Try to find floor plan images from listing data and save to DB.

        Sources checked (in priority order):
        1. parsed_data.floor_plan_images (from previous URL extraction)
        2. Listing images with floor-plan keywords in URL
        3. Live page scrape — fetch listing URL and extract floor plan images
        """
        listing_id = context.source_data["listing_id"]
        listing = context.source_data["listing"]
        discovered_urls: list[str] = []

        # Source 1: parsed_data may have floor plan URLs from URL extraction
        parsed_data = listing.get("parsed_data") or {}
        if isinstance(parsed_data, str):
            import json as json_module
            try:
                parsed_data = json_module.loads(parsed_data)
            except Exception:
                parsed_data = {}

        floor_plan_images = parsed_data.get("floor_plan_images") or []
        discovered_urls.extend(floor_plan_images)

        # Source 2: listing images with floor-plan-like filenames
        all_images = listing.get("images") or parsed_data.get("images") or []
        floor_plan_keywords = ("floor", "floorplan", "floor-plan", "layout", "plan", "blueprint")
        for image_url in all_images:
            if isinstance(image_url, str):
                image_url_lower = image_url.lower()
                if any(keyword in image_url_lower for keyword in floor_plan_keywords):
                    if image_url not in discovered_urls:
                        discovered_urls.append(image_url)

        # Source 3: live page scrape (if no floor plans found yet and we have a URL)
        if not discovered_urls and listing.get("source_url"):
            try:
                from shared.url_fetcher import fetch_page, FetchError, SSRFError
                from agents.apartment.services.url_extractor import extract_apartment_data_from_html

                page_html = context.gathered.get("page_html")
                if not page_html:
                    page_html = fetch_page(listing["source_url"])
                    context.gathered["page_html"] = page_html

                page_data = extract_apartment_data_from_html(page_html)
                scraped_floor_plans = page_data.get("floor_plan_images") or []
                discovered_urls.extend(scraped_floor_plans)
                logger.info("Scraped %d floor plan images from listing page", len(scraped_floor_plans))
            except (FetchError, SSRFError) as fetch_error:
                logger.warning("Could not fetch listing page for floor plans: %s", fetch_error)
            except Exception as scrape_error:
                logger.warning("Floor plan scraping failed: %s", scrape_error)

        # Save discovered floor plans to DB
        if discovered_urls:
            saved_count = 0
            for floor_plan_url in discovered_urls[:5]:  # Max 5 floor plans
                self._connection.execute(
                    """INSERT OR IGNORE INTO apartment_floor_plans
                       (listing_id, image_url, unit_type)
                       VALUES (?, ?, ?)""",
                    (listing_id, floor_plan_url, "discovered"),
                )
                saved_count += 1
            self._connection.commit()
            logger.info("Discovered %d floor plan images for listing %d", saved_count, listing_id)
        else:
            logger.info("No floor plan images found for listing %d", listing_id)

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

    def _prefetch_listing_page(self, context: PipelineContext) -> None:
        """Pre-fetch the listing page text once — shared by concessions + policies."""
        from shared.url_fetcher import fetch_page, extract_text_from_page, FetchError, SSRFError

        listing = context.source_data["listing"]
        source_url = listing.get("source_url")
        if not source_url:
            return

        try:
            page_html = fetch_page(source_url)
            page_text = extract_text_from_page(page_html)
            context.gathered["page_text"] = page_text
            logger.info("Pre-fetched listing page: %d chars", len(page_text))
        except (FetchError, SSRFError) as fetch_error:
            logger.warning("Page pre-fetch failed: %s", fetch_error)
            context.gathered["page_fetch_error"] = str(fetch_error)

    def _gather_concessions(self, context: PipelineContext) -> None:
        """Extract concessions and fees from listing URL via LLM."""
        from agents.apartment.services.concession_extractor import extract_concessions

        listing_id = context.source_data["listing_id"]

        # Use pre-fetched page text if available
        page_text = context.gathered.get("page_text")
        if context.gathered.get("page_fetch_error"):
            logger.info("Skipping concessions — page fetch failed earlier")
            return

        result = extract_concessions(
            listing_id, self._connection, self._llm_provider,
            prefetched_page_text=page_text,
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

    def _gather_reviews(self, context: PipelineContext) -> None:
        """Fetch Google Places reviews and run LLM sentiment analysis."""
        from agents.apartment.services.review_mining_service import fetch_and_analyze_reviews

        listing_id = context.source_data["listing_id"]
        result = fetch_and_analyze_reviews(
            listing_id, self._connection, self._llm_provider
        )

        if result and not result.get("place_not_found") and not result.get("no_reviews"):
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="reviews",
                result=result,
                source_api="google_places",
                estimated_cost=COST_ESTIMATES["reviews"],
                actual_cost=COST_ESTIMATES["reviews"],
            )
            context.gathered["reviews"] = result
            review_count = result.get("review_count", 0)
            logger.info("Review mining complete for listing %d: %d reviews", listing_id, review_count)

    def _gather_policies(self, context: PipelineContext) -> None:
        """Extract lease policies from listing URL via LLM."""
        from agents.apartment.services.policy_extractor import extract_policies

        listing_id = context.source_data["listing_id"]

        page_text = context.gathered.get("page_text")
        if context.gathered.get("page_fetch_error"):
            logger.info("Skipping policies — page fetch failed earlier")
            return

        result = extract_policies(
            listing_id, self._connection, self._llm_provider,
            prefetched_page_text=page_text,
        )

        if result and not result.get("error") and not result.get("parse_error"):
            self._intel_repo.save_intel(
                listing_id=listing_id,
                intel_type="policies",
                result=result,
                source_api="llm_extraction",
                estimated_cost=COST_ESTIMATES["policies"],
                actual_cost=COST_ESTIMATES["policies"],
            )
            context.gathered["policies"] = result
            logger.info("Policy extraction complete for listing %d", listing_id)

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
