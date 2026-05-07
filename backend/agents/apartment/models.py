"""Pydantic models for NestScout apartment agent."""

from pydantic import BaseModel


class ApartmentSearchQuery(BaseModel):
    query: str  # Natural language: "2BR in 75001 with elevator under $1800"
    location: str | None = None
    max_price: float | None = None
    min_bedrooms: int | None = None
    amenities: list[str] | None = None


class ListingCreate(BaseModel):
    title: str
    address: str | None = None
    price: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    source_url: str | None = None
    amenities: list[str] | None = None


class NoteCreate(BaseModel):
    listing_id: int
    notes: str | None = None
    visit_date: str | None = None
    structured_data: dict | None = None
    specials: dict | None = None
    status: str | None = None


class CostUpdate(BaseModel):
    base_rent: float | None = None
    lease_months: int | None = None
    special_description: str | None = None
    special_discount: float | None = None
    parking_fee: float | None = None
    pet_fee: float | None = None
    utilities_estimate: float | None = None


class PreferencesUpdate(BaseModel):
    location: str | None = None
    max_price: float | None = None
    min_bedrooms: int | None = None
    must_haves: list[str] | None = None
    layout_requirements: list[str] | None = None
    auto_search_active: bool | None = None
