"""NestScout apartment agent — API routes.

All routes prefixed /api/apartments/.
Follows same factory pattern as job agent.
"""

import sqlite3

from fastapi import APIRouter, HTTPException

from agents.apartment.models import (
    ApartmentSearchQuery,
    ListingCreate,
    NoteCreate,
    CostUpdate,
    PreferencesUpdate,
)
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.preferences_repo import ApartmentPreferencesRepository


def _store_qa_discoveries(listing_id: int, question: str, answer: str, connection: sqlite3.Connection) -> None:
    """Store useful details from Q&A answers as listing enrichment.

    When users ask about nearby places, the LLM's answer contains
    valuable data (store names, distances) that should be saved
    so it appears on future visits without re-asking.
    """
    import json as json_module

    # Get existing discoveries or create new
    existing_row = connection.execute(
        "SELECT raw_data FROM apartment_neighborhood WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()

    existing_data = {}
    if existing_row and existing_row["raw_data"]:
        try:
            existing_data = json_module.loads(existing_row["raw_data"])
        except (json_module.JSONDecodeError, TypeError):
            pass

    # Append this Q&A to discoveries
    discoveries = existing_data.get("qa_discoveries") or []
    discoveries.append({"question": question, "answer_summary": answer[:500]})
    existing_data["qa_discoveries"] = discoveries[-10:]  # Keep last 10

    # Upsert into neighborhood table
    if existing_row:
        connection.execute(
            "UPDATE apartment_neighborhood SET raw_data = ? WHERE listing_id = ?",
            (json_module.dumps(existing_data), listing_id),
        )
    else:
        connection.execute(
            "INSERT INTO apartment_neighborhood (listing_id, raw_data) VALUES (?, ?)",
            (listing_id, json_module.dumps(existing_data)),
        )
    connection.commit()


def create_router(connection: sqlite3.Connection, llm_provider=None) -> APIRouter:
    """Create apartment agent router with all endpoints."""
    router = APIRouter(prefix="/api/apartments")

    listing_repo = ApartmentListingRepository(connection)
    preferences_repo = ApartmentPreferencesRepository(connection)

    from agents.apartment.repositories.feature_preferences_repo import FeaturePreferencesRepository
    from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository
    feature_preferences_repo = FeaturePreferencesRepository(connection)
    lab_analysis_repo = LabAnalysisRepository(connection)

    # ==================== Search ====================

    @router.post("/search")
    def search_apartments(data: dict):
        """Search apartments across all connected sources.

        Uses Strategy pattern — each API source is a provider class.
        The orchestrator runs all configured providers, handles failures
        per-provider, and merges results.
        """
        from agents.apartment.services.base_provider import SearchCriteria
        from agents.apartment.services.provider_registry import get_all_providers
        from agents.apartment.services.search_orchestrator import run_search

        city = data.get("city")
        zip_code = data.get("zip_code")

        if not city and not zip_code:
            raise HTTPException(400, detail="City or zip code is required")

        criteria = SearchCriteria(
            city=city,
            zip_code=zip_code,
            bedrooms=data.get("bedrooms"),
            max_rent=data.get("max_rent"),
            bathrooms=data.get("min_bathrooms"),
        )

        providers = get_all_providers(connection)
        search_result = run_search(providers, criteria)

        if not search_result.listings:
            if search_result.sources_failed:
                failed_names = ", ".join(search_result.sources_failed)
                return {"results": [], "sources_failed": search_result.sources_failed,
                        "message": f"{failed_names} failed. Check API keys in Settings."}
            return {"results": [], "message": "No apartments found. Check your API keys in Settings."}

        # Save results to DB, strip parsed_data from response (too large for frontend)
        saved_listings = []
        for listing in search_result.listings:
            listing_id = listing_repo.save_listing(**listing)
            lightweight_listing = {key: value for key, value in listing.items() if key != "parsed_data"}
            lightweight_listing["id"] = listing_id
            saved_listings.append(lightweight_listing)

        response = {
            "results": saved_listings,
            "count": len(saved_listings),
            "sources": search_result.sources_searched,
        }
        if search_result.sources_failed:
            response["sources_failed"] = search_result.sources_failed
        return response

    # ==================== Listings CRUD ====================

    @router.get("/listings")
    def list_apartments(saved_only: bool = False):
        return listing_repo.list_listings(saved_only=saved_only)

    @router.get("/listings/{listing_id}")
    def get_apartment(listing_id: int):
        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")
        return listing

    @router.post("/listings")
    def create_listing(listing: ListingCreate):
        listing_id = listing_repo.save_listing(**listing.model_dump())
        return {"id": listing_id, **listing.model_dump()}

    @router.post("/listings/{listing_id}/save")
    def save_to_shortlist(listing_id: int):
        listing_repo.save_to_shortlist(listing_id)
        return {"saved": listing_id}

    @router.post("/listings/{listing_id}/unsave")
    def remove_from_shortlist(listing_id: int):
        listing_repo.remove_from_shortlist(listing_id)
        return {"unsaved": listing_id}

    @router.delete("/listings/{listing_id}")
    def delete_listing(listing_id: int):
        listing_repo.delete_listing(listing_id)
        return {"deleted": listing_id}

    # ==================== Paste URL ====================

    @router.post("/listings/from-url")
    def create_from_url(data: dict):
        """Paste a listing URL → fetch page → extract apartment data → save."""
        from shared.scraping.extractors import detect_input_type
        from shared.url_fetcher import fetch_page, FetchError, SSRFError
        from agents.apartment.services.url_extractor import extract_apartment_data_from_html

        source_url = (data.get("url") or "").strip()
        if not source_url or detect_input_type(source_url) != "url":
            raise HTTPException(400, detail="Please provide a valid URL")

        try:
            page_html = fetch_page(source_url)
        except SSRFError as ssrf_error:
            raise HTTPException(400, detail=str(ssrf_error))
        except FetchError as fetch_error:
            raise HTTPException(400, detail=str(fetch_error))

        extracted_data = extract_apartment_data_from_html(page_html)

        # Save as listing
        listing_id = listing_repo.save_listing(
            title=extracted_data.get("title") or "Untitled Listing",
            address=extracted_data.get("address"),
            price=extracted_data.get("price"),
            bedrooms=extracted_data.get("bedrooms"),
            bathrooms=extracted_data.get("bathrooms"),
            sqft=extracted_data.get("sqft"),
            source="url",
            source_url=source_url,
            amenities=extracted_data.get("amenities", []),
            parsed_data=extracted_data,
        )

        return {"id": listing_id, "source_url": source_url, **extracted_data}

    # ==================== Notes ====================

    @router.post("/notes")
    def add_note(note: NoteCreate):
        """Add visit notes for a listing."""
        # Phase 3: implement notes CRUD
        return {"message": "Notes coming in Phase 3"}

    # ==================== Neighborhood ====================

    @router.get("/neighborhood/{listing_id}")
    def get_neighborhood(listing_id: int):
        """Get neighborhood intelligence for a listing."""
        # Phase 4: implement Google Places/Maps integration
        return {"message": "Neighborhood intel coming in Phase 4", "listing_id": listing_id}

    # ==================== Cost ====================

    # ==================== Cost ====================

    from agents.apartment.repositories.cost_repo import CostRepository
    cost_repo = CostRepository(connection)

    @router.get("/cost/{listing_id}")
    def get_cost(listing_id: int):
        """Get cost breakdown for a listing."""
        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")
        cost = cost_repo.get_cost(listing_id)
        if not cost:
            # Return template pre-filled with listing price
            return {
                "listing_id": listing_id,
                "base_rent": listing.get("price") or 0,
                "parking_fee": 0,
                "pet_fee": 0,
                "utilities_estimate": 0,
                "lease_months": 12,
                "special_discount": 0,
                "special_description": "",
                "effective_monthly": listing.get("price") or 0,
                "total_monthly": listing.get("price") or 0,
            }
        return cost

    @router.put("/cost/{listing_id}")
    def save_cost(listing_id: int, cost_data: CostUpdate):
        """Save cost breakdown — validates fields, calculates totals."""
        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")
        cost_repo.save_cost(listing_id, **cost_data.model_dump(exclude_none=True))
        return cost_repo.get_cost(listing_id)

    @router.get("/price-context/{listing_id}")
    def get_price_context_endpoint(listing_id: int):
        """Get price comparison context — median, percentile, comparables."""
        from agents.apartment.services.price_analyzer import get_price_context
        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")
        return get_price_context(listing_id, listing_repo)

    # ==================== Notifications ====================

    @router.get("/notifications")
    def get_notifications():
        """Get unread auto-search results."""
        # Phase 6: implement notification queue
        return {"unread": [], "count": 0}

    # ==================== Preferences ====================

    @router.get("/preferences")
    def get_preferences():
        """Get saved search preferences."""
        return preferences_repo.get_preferences()

    @router.put("/preferences")
    def update_preferences(preferences: PreferencesUpdate):
        """Save search preferences."""
        preference_id = preferences_repo.save_preferences(**preferences.model_dump())
        return {"updated": preference_id}

    # ==================== Feature Preferences (3-state tags) ====================

    @router.get("/preferences/features")
    def get_feature_preferences():
        """Get all feature preferences (must_have, deal_breaker)."""
        return feature_preferences_repo.get_all_preferences()

    @router.put("/preferences/features/{feature_name}")
    def set_feature_preference(feature_name: str, data: dict):
        """Set a feature preference. Body: {"category": "unit", "preference": "must_have"}"""
        category = data.get("category", "general")
        preference = data.get("preference", "neutral")
        try:
            feature_preferences_repo.set_preference(feature_name, category, preference)
        except ValueError as validation_error:
            raise HTTPException(400, detail=str(validation_error))
        return {"feature": feature_name, "category": category, "preference": preference}

    @router.delete("/preferences/features/{feature_name}")
    def reset_feature_preference(feature_name: str):
        """Reset a feature preference back to neutral."""
        feature_preferences_repo.reset_preference(feature_name)
        return {"feature": feature_name, "preference": "neutral"}

    # ==================== Nest Lab ====================

    from agents.apartment.repositories.qa_history_repo import QaHistoryRepository
    qa_history_repo = QaHistoryRepository(connection)

    from agents.apartment.services.lab_analyzer import LabAnalyzerService
    lab_analyzer = LabAnalyzerService(
        listing_repo=listing_repo,
        feature_preferences_repo=feature_preferences_repo,
        lab_analysis_repo=lab_analysis_repo,
        llm_provider=llm_provider,
    )

    @router.get("/lab/analyzed-ids")
    def get_analyzed_listing_ids():
        """Return IDs of listings that have cached analysis — for badge display."""
        rows = connection.execute(
            "SELECT DISTINCT listing_id FROM apartment_lab_analysis"
        ).fetchall()
        return [row["listing_id"] for row in rows]

    @router.get("/lab/{listing_id}")
    def get_lab_data(listing_id: int, run_analysis: bool = False):
        """Get full lab data for a listing.

        Default: returns gathered data + cached analysis (no new LLM call).
        With ?run_analysis=true: triggers fresh LLM analysis if not cached.
        """
        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")

        if run_analysis:
            return lab_analyzer.analyze(listing_id)
        return lab_analyzer.get_lab_data(listing_id)

    @router.get("/lab/{listing_id}/stream")
    async def stream_lab_analysis(listing_id: int):
        """SSE stream: progress events + LLM analysis chunks + done event.

        Frontend connects via EventSource. Events:
          data: {"type": "progress", "step": "gathering_data", "status": "running"}
          data: {"type": "chunk", "text": "Alexan Braker..."}
          data: {"type": "done", "full_text": "..."}
          data: {"type": "error", "message": "..."}
        """
        from starlette.responses import StreamingResponse
        from shared.llm.streaming import format_sse_stream, format_sse_progress, format_sse_error

        listing = listing_repo.get_listing(listing_id)
        if not listing:
            async def error_stream():
                yield format_sse_error("Listing not found")
            return StreamingResponse(error_stream(), media_type="text/event-stream")

        def generate_analysis_events():
            # Progress: gathering data
            yield format_sse_progress("gathering_data", "running", "Loading listing and preferences...")
            yield format_sse_progress("gathering_data", "complete")

            # Progress: analyzing
            yield format_sse_progress("analyzing", "running", "Generating AI analysis...")

            # Stream LLM response
            try:
                analysis_chunks = lab_analyzer.analyze_stream(listing_id)
                yield from format_sse_stream(analysis_chunks)
            except Exception as analysis_error:
                yield format_sse_error(str(analysis_error))

        return StreamingResponse(
            generate_analysis_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/lab/{listing_id}/neighborhood")
    def get_neighborhood_data(listing_id: int, refresh: bool = False):
        """Fetch neighborhood intel — Walk Score + airport distance + commute.

        Default: returns cached data if available.
        With ?refresh=true: forces re-fetch from APIs.
        Triggered by "Get more info" button in Lab.
        """
        from agents.apartment.services.neighborhood_service import (
            fetch_and_cache_neighborhood,
            get_cached_neighborhood,
        )

        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")

        if not refresh:
            cached = get_cached_neighborhood(listing_id, connection)
            if cached:
                return cached

        return fetch_and_cache_neighborhood(listing_id, connection)

    # ==================== Lab Q&A ====================

    @router.post("/lab/{listing_id}/ask")
    def ask_about_listing(listing_id: int, data: dict):
        """Ask a question about a listing. LLM answers with full context."""
        from agents.apartment.prompts.qa_response import build_qa_prompt, SYSTEM_PROMPT

        listing = listing_repo.get_listing(listing_id)
        if not listing:
            raise HTTPException(404, detail="Listing not found")

        question = (data.get("question") or "").strip()
        if not question:
            raise HTTPException(400, detail="Question is required")

        if not llm_provider or not llm_provider.is_configured():
            raise HTTPException(503, detail="No AI provider configured. Set one in Settings.")

        # Build context
        previous_qa = qa_history_repo.get_history(listing_id, limit=5)
        cached_analysis = lab_analysis_repo.get_all_for_listing(listing_id)
        overview_analysis = cached_analysis.get("overview")
        preferences = {
            "must_haves": feature_preferences_repo.get_must_haves(),
            "deal_breakers": feature_preferences_repo.get_deal_breakers(),
        }

        prompt = build_qa_prompt(
            listing=listing,
            question=question,
            previous_qa=previous_qa,
            analysis=overview_analysis,
            user_preferences=preferences,
        )

        answer = llm_provider.complete(prompt, system=SYSTEM_PROMPT, feature="lab_qa")

        # Save to history
        qa_history_repo.save_qa(listing_id, question, answer)

        # Enrich neighborhood data — save Q&A discoveries to listing's knowledge
        _store_qa_discoveries(listing_id, question, answer, connection)

        return {"question": question, "answer": answer}

    @router.get("/lab/{listing_id}/qa-history")
    def get_qa_history(listing_id: int):
        """Get Q&A history for a listing."""
        return qa_history_repo.get_history(listing_id)

    # ==================== Compare ====================

    @router.post("/compare")
    def compare_listings(data: dict):
        """Compare 2-3 listings side-by-side with preference-weighted scoring.

        Body: {"listing_ids": [1, 2, 3]}
        """
        listing_ids = data.get("listing_ids") or []
        if len(listing_ids) < 2:
            raise HTTPException(400, detail="Need at least 2 listings to compare")
        if len(listing_ids) > 3:
            raise HTTPException(400, detail="Maximum 3 listings for comparison")

        must_haves = set(feature_preferences_repo.get_must_haves())
        deal_breakers = set(feature_preferences_repo.get_deal_breakers())

        compared_listings = []
        for listing_id in listing_ids:
            listing = listing_repo.get_listing(listing_id)
            if not listing:
                continue
            # Strip parsed_data from compare response (can be megabytes)
            listing.pop("parsed_data", None)

            amenities = set(listing.get("amenities") or [])
            matched_must_haves = list(must_haves & amenities)
            matched_deal_breakers = list(deal_breakers & amenities)

            # Get cached analysis if available
            cached_analysis = lab_analysis_repo.get_all_for_listing(listing_id)
            overview = cached_analysis.get("overview") or {}
            llm_score = overview.get("match_score")

            # Score calculation
            has_preferences = len(must_haves) > 0 or len(deal_breakers) > 0

            if llm_score is not None and has_preferences:
                # Best case: LLM score adjusted by preference matches
                preference_adjustment = len(matched_must_haves) * 5 - len(matched_deal_breakers) * 10
                score = max(0, min(100, llm_score + preference_adjustment))
            elif llm_score is not None:
                # LLM score only (no preferences set)
                score = llm_score
            elif has_preferences:
                # Preferences only (no LLM analysis)
                total_preferences = len(must_haves) + len(deal_breakers)
                match_ratio = len(matched_must_haves) / max(len(must_haves), 1)
                penalty_ratio = len(matched_deal_breakers) / max(len(deal_breakers), 1)
                score = round(70 + match_ratio * 20 - penalty_ratio * 30)
                score = max(0, min(100, score))
            else:
                # No data — show as null (frontend shows "Set preferences")
                score = None

            compared_listings.append({
                "listing": listing,
                "score": score,
                "matched_must_haves": matched_must_haves,
                "matched_deal_breakers": matched_deal_breakers,
                "must_have_count": len(matched_must_haves),
                "deal_breaker_count": len(matched_deal_breakers),
                "analysis_summary": overview.get("overview"),
                "price_verdict": overview.get("price_verdict"),
                "price_reasoning": overview.get("price_reasoning"),
                "red_flags": overview.get("red_flags") or [],
                "green_lights": overview.get("green_lights") or [],
                "neighborhood_summary": (overview.get("neighborhood") or {}).get("summary") if isinstance(overview.get("neighborhood"), dict) else None,
                "questions_to_ask": overview.get("questions_to_ask") or [],
                "is_analyzed": bool(overview),
                "qa_summary": [
                    {"question": qa_entry["question"], "answer": qa_entry["answer"]}
                    for qa_entry in qa_history_repo.get_history(listing_id, limit=3)
                ],
            })

        # Sort by score descending (None scores last)
        compared_listings.sort(key=lambda entry: entry["score"] if entry["score"] is not None else -1, reverse=True)

        return {
            "listings": compared_listings,
            "must_haves": list(must_haves),
            "deal_breakers": list(deal_breakers),
        }

    # ==================== Custom Apartment Sources ====================

    @router.get("/sources")
    def list_apartment_sources():
        """List all apartment API sources (built-in + custom)."""
        import json as json_module
        # Check if RentCast key is saved
        rentcast_key_row = connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
        ).fetchone()
        saved_keys = {}
        if rentcast_key_row:
            try:
                saved_keys = json_module.loads(rentcast_key_row["value"])
            except (json_module.JSONDecodeError, TypeError):
                pass

        has_rentcast_key = bool(saved_keys.get("rentcast"))
        has_realtyapi_key = bool(saved_keys.get("realtyapi"))
        has_walkscore_key = bool(saved_keys.get("walkscore"))
        has_google_maps_key = bool(saved_keys.get("google_maps"))

        built_in_sources = [
            {
                "id": "realtyapi", "name": "RealtyAPI",
                "signup": "https://www.realtyapi.io", "free_tier": "250 requests/month · images included",
                "is_custom": False, "enabled": True, "requires_api_key": True,
                "is_connected": has_realtyapi_key,
            },
            {
                "id": "rentcast", "name": "RentCast",
                "signup": "https://www.rentcast.io/api", "free_tier": "50 requests/month · market data",
                "is_custom": False, "enabled": True, "requires_api_key": True,
                "is_connected": has_rentcast_key,
            },
            {
                "id": "walkscore", "name": "Walk Score",
                "signup": "https://www.walkscore.com/professional/api.php",
                "free_tier": "5,000 calls/day · walk/transit/bike scores",
                "is_custom": False, "enabled": True, "requires_api_key": True,
                "is_connected": has_walkscore_key,
            },
            {
                "id": "google_maps", "name": "Google Maps",
                "signup": "https://console.cloud.google.com/apis",
                "free_tier": "$200/month credit · distance + commute",
                "is_custom": False, "enabled": True, "requires_api_key": True,
                "is_connected": has_google_maps_key,
            },
        ]
        custom_sources = preferences_repo.list_custom_sources()
        for source in custom_sources:
            source["is_custom"] = True
        return built_in_sources + custom_sources

    @router.put("/sources/{source_id}/api-key")
    def save_source_api_key(source_id: str, data: dict):
        """Save API key for a built-in source."""
        import json as json_module
        row = connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
        ).fetchone()
        saved_keys = {}
        if row:
            try:
                saved_keys = json_module.loads(row["value"])
            except (json_module.JSONDecodeError, TypeError):
                pass
        saved_keys[source_id] = data.get("api_key", "")
        connection.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
            [json_module.dumps(saved_keys)],
        )
        connection.commit()
        return {"saved": source_id, "connected": bool(data.get("api_key"))}

    @router.post("/sources/custom")
    def add_apartment_source(data: dict):
        """Add a custom apartment API source."""
        try:
            return preferences_repo.add_custom_source(
                name=data.get("name", ""),
                api_url=data.get("api_url", ""),
                api_key=data.get("api_key"),
            )
        except ValueError as error:
            raise HTTPException(400, detail=str(error))

    @router.delete("/sources/custom/{source_id}")
    def delete_apartment_source(source_id: str):
        preferences_repo.delete_custom_source(source_id)
        return {"deleted": source_id}

    @router.put("/sources/custom/{source_id}/toggle")
    def toggle_apartment_source(source_id: str, data: dict):
        enabled = data.get("enabled", True)
        preferences_repo.toggle_custom_source(source_id, enabled)
        return {"id": source_id, "enabled": enabled}

    # ==================== Health ====================

    @router.get("/health")
    def apartment_health():
        return {"agent": "nestscout", "status": "ok"}

    return router
