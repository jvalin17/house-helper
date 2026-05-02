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


def create_router(connection: sqlite3.Connection, llm_provider=None) -> APIRouter:
    """Create apartment agent router with all endpoints."""
    router = APIRouter(prefix="/api/apartments")

    listing_repo = ApartmentListingRepository(connection)
    preferences_repo = ApartmentPreferencesRepository(connection)

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

        # Save results to DB
        saved_listings = []
        for listing in search_result.listings:
            listing_id = listing_repo.save_listing(**listing)
            saved_listings.append({"id": listing_id, **listing})

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

    @router.get("/cost/{listing_id}")
    def get_cost(listing_id: int):
        """Get cost breakdown for a listing."""
        # Phase 3: implement cost calculator
        return {"message": "Cost calculator coming in Phase 3", "listing_id": listing_id}

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
