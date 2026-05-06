"""Unit details service — tests for normalizing RealtyAPI /apartment_details responses.

Covers: floor plan extraction from various response shapes, price/sqft range parsing,
bedroom normalization, individual unit parsing, summary generation.
"""

import pytest

from agents.apartment.services.unit_details_service import (
    normalize_unit_details,
    _parse_price_range,
    _parse_sqft_range,
    _parse_bedrooms,
    _get_zpid_for_listing,
)


# ── Normalize floor plans ─────────────────────────────

class TestNormalizeUnitDetails:
    """Tests for normalizing various RealtyAPI apartment_details response shapes."""

    def test_standard_floor_plans_response(self):
        """Typical response: top-level floorPlans array with units."""
        raw_response = {
            "floorPlans": [
                {
                    "name": "Studio A",
                    "beds": "Studio",
                    "baths": 1,
                    "sqft": "450-520",
                    "price": "$1,445 - $1,595",
                    "units": [
                        {"unit": "101", "sqft": 450, "price": 1445, "available": "2026-06-01"},
                        {"unit": "205", "sqft": 520, "price": 1595, "available": "2026-07-15"},
                    ],
                },
                {
                    "name": "1BR Deluxe",
                    "beds": 1,
                    "baths": 1,
                    "sqft": "720",
                    "price": "$1,832",
                    "units": [
                        {"unit": "302", "sqft": 720, "price": 1832, "available": "2026-06-01"},
                    ],
                },
            ],
        }

        result = normalize_unit_details(raw_response)

        assert result["total_available"] == 3
        assert len(result["floor_plans"]) == 2

        studio = result["floor_plans"][0]
        assert studio["name"] == "Studio A"
        assert studio["bedrooms"] == 0
        assert studio["min_price"] == 1445.0
        assert studio["max_price"] == 1595.0
        assert studio["min_sqft"] == 450
        assert studio["max_sqft"] == 520
        assert len(studio["units"]) == 2
        assert studio["units"][0]["unit_number"] == "101"

        one_bed = result["floor_plans"][1]
        assert one_bed["bedrooms"] == 1
        assert one_bed["min_price"] == 1832.0
        assert len(one_bed["units"]) == 1

    def test_summary_groups_by_bedroom_count(self):
        """Summary aggregates floor plans by bedroom type."""
        raw_response = {
            "floorPlans": [
                {"name": "Plan A", "beds": 1, "baths": 1, "price": "$1,800", "units": [{"unit": "1A", "price": 1800}]},
                {"name": "Plan B", "beds": 1, "baths": 1, "price": "$2,100", "units": [{"unit": "2B", "price": 2100}]},
                {"name": "Plan C", "beds": 2, "baths": 2, "price": "$2,500", "units": [{"unit": "3C", "price": 2500}]},
            ],
        }

        result = normalize_unit_details(raw_response)

        assert 1 in result["summary"]
        assert 2 in result["summary"]
        assert result["summary"][1]["label"] == "1BR"
        assert result["summary"][1]["min_price"] == 1800.0
        assert result["summary"][1]["max_price"] == 2100.0
        assert result["summary"][1]["total_available"] == 2
        assert result["summary"][2]["label"] == "2BR"
        assert result["summary"][2]["total_available"] == 1

    def test_nested_building_response_shape(self):
        """Response with floor plans nested under 'building' key."""
        raw_response = {
            "building": {
                "floorPlans": [
                    {"name": "Penthouse", "beds": 2, "baths": 2, "price": 3200,
                     "units": [{"unit": "PH1", "price": 3200}]},
                ],
            },
        }

        result = normalize_unit_details(raw_response)
        assert result["total_available"] == 1
        assert result["floor_plans"][0]["name"] == "Penthouse"

    def test_flat_list_response_shape(self):
        """Response is a flat list of floor plan objects (no wrapping)."""
        raw_response = [
            {"name": "Classic", "beds": 1, "baths": 1, "price": 1650,
             "units": [{"unit": "A1", "price": 1650}]},
        ]

        result = normalize_unit_details(raw_response)
        assert result["total_available"] == 1
        assert result["floor_plans"][0]["bedrooms"] == 1

    def test_empty_response(self):
        """Empty or missing floor plans returns zero totals."""
        assert normalize_unit_details({})["total_available"] == 0
        assert normalize_unit_details({"floorPlans": []})["total_available"] == 0
        assert normalize_unit_details([])["total_available"] == 0

    def test_plan_without_individual_units(self):
        """Floor plan with availability count but no individual unit data."""
        raw_response = {
            "floorPlans": [
                {"name": "Urban Loft", "beds": 0, "baths": 1, "price": "$1,445 - $1,595",
                 "sqft": "450-520", "availableCount": 8},
            ],
        }

        result = normalize_unit_details(raw_response)
        assert result["total_available"] == 8
        assert result["floor_plans"][0]["available_count"] == 8
        assert result["floor_plans"][0]["units"] == []


# ── Price/sqft parsing ────────────────────────────────

class TestParsing:
    """Tests for parsing price ranges, sqft, and bedroom formats."""

    def test_price_range_with_dollars_and_commas(self):
        """Parse '$1,445 - $1,595' to (1445.0, 1595.0)."""
        assert _parse_price_range("$1,445 - $1,595") == (1445.0, 1595.0)

    def test_price_single_value(self):
        """Parse '$1,832' to (1832.0, 1832.0)."""
        assert _parse_price_range("$1,832") == (1832.0, 1832.0)

    def test_price_numeric(self):
        """Parse numeric 1445 to (1445.0, 1445.0)."""
        assert _parse_price_range(1445) == (1445.0, 1445.0)

    def test_price_none(self):
        """Parse None to (None, None)."""
        assert _parse_price_range(None) == (None, None)

    def test_sqft_range_string(self):
        """Parse '450-520' to (450, 520)."""
        assert _parse_sqft_range("450-520") == (450, 520)

    def test_sqft_single_number(self):
        """Parse '720' to (720, 720)."""
        assert _parse_sqft_range("720") == (720, 720)

    def test_sqft_numeric(self):
        """Parse numeric 850 to (850, 850)."""
        assert _parse_sqft_range(850) == (850, 850)

    def test_bedrooms_studio_string(self):
        """Parse 'Studio' as 0 bedrooms."""
        assert _parse_bedrooms({"beds": "Studio"}) == 0

    def test_bedrooms_numeric(self):
        """Parse numeric bedroom count."""
        assert _parse_bedrooms({"beds": 2}) == 2

    def test_bedrooms_string_number(self):
        """Parse string bedroom count like '1'."""
        assert _parse_bedrooms({"beds": "1"}) == 1


# ── ZPID extraction ──────────────────────────────────

class TestZpidExtraction:
    """Tests for extracting zpid from listing data."""

    def test_zpid_from_source_url(self, database_connection_with_listing):
        """Extracts zpid from Zillow URL pattern."""
        connection, listing_id = database_connection_with_listing
        zpid = _get_zpid_for_listing(listing_id, connection)
        assert zpid == "12345"

    def test_zpid_from_parsed_data(self, database_connection_with_parsed_zpid):
        """Extracts zpid from stored parsed_data JSON."""
        connection, listing_id = database_connection_with_parsed_zpid
        zpid = _get_zpid_for_listing(listing_id, connection)
        assert zpid == "98765"

    def test_zpid_missing_returns_none(self, database_connection_without_zpid):
        """Returns None when no zpid is available."""
        connection, listing_id = database_connection_without_zpid
        zpid = _get_zpid_for_listing(listing_id, connection)
        assert zpid is None


# ── Fixtures ──────────────────────────────────────────

import json
import sqlite3
from shared.db import migrate


@pytest.fixture
def database_connection_with_listing():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    cursor = connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url, parsed_data)
           VALUES (?, ?, ?, ?, ?)""",
        ("Alexan Braker Pointe", "10801 N Mopac Expy, Austin, TX 78759", 1445.0,
         "https://www.zillow.com/homedetails/12345_zpid/", "{}"),
    )
    connection.commit()
    yield connection, cursor.lastrowid
    connection.close()


@pytest.fixture
def database_connection_with_parsed_zpid():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    cursor = connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url, parsed_data)
           VALUES (?, ?, ?, ?, ?)""",
        ("Windsor Ridge", "500 E Riverside, Austin, TX", 1200.0,
         "https://apartments.com/windsor-ridge", json.dumps({"property": {"zpid": 98765}})),
    )
    connection.commit()
    yield connection, cursor.lastrowid
    connection.close()


@pytest.fixture
def database_connection_without_zpid():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    cursor = connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url)
           VALUES (?, ?, ?, ?)""",
        ("Manual Entry Apt", "123 Oak St", 1000.0, "https://craigslist.org/apt/abc123"),
    )
    connection.commit()
    yield connection, cursor.lastrowid
    connection.close()
