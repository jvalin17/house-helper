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


def create_router(connection: sqlite3.Connection, llm_provider=None) -> APIRouter:
    """Create apartment agent router with all endpoints."""
    router = APIRouter(prefix="/api/apartments")

    listing_repo = ApartmentListingRepository(connection)

    # ==================== Search ====================

    @router.post("/search")
    def search_apartments(query: ApartmentSearchQuery):
        """Search apartments across connected sources."""
        # Phase 2: implement multi-source search + NL parsing
        return {"results": [], "query": query.query, "message": "Search coming in Phase 2"}

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
        # Phase 3: implement preferences
        return {"location": None, "max_price": None, "min_bedrooms": None, "auto_search_active": False}

    @router.put("/preferences")
    def update_preferences(preferences: PreferencesUpdate):
        """Save search preferences."""
        # Phase 3: implement preferences
        return {"updated": True}

    # ==================== Health ====================

    @router.get("/health")
    def apartment_health():
        return {"agent": "nestscout", "status": "ok"}

    return router
