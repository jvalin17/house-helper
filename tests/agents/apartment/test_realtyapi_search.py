"""RealtyAPI search service — unit tests.

Tests normalization, image extraction, and error handling.
Uses REAL response data from the RealtyAPI live endpoint (verified 2026-05-02).
"""

import json
import sqlite3

import pytest
import httpx

from agents.apartment.services.realtyapi_search import (
    get_realtyapi_key,
    search_realtyapi,
    _normalize_listing,
    _extract_listings_from_response,
    _extract_images,
    _extract_address,
    _extract_price,
    _extract_bed_bath,
    _build_title,
    _is_age_restricted,
    _format_bathrooms_filter,
)
from shared.db import migrate


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def database_with_realtyapi_key(database_connection):
    """Database with a RealtyAPI key stored in settings."""
    database_connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
        [json.dumps({"realtyapi": "rt_test_key_abc123"})],
    )
    database_connection.commit()
    return database_connection


# ── Real API response samples (from live RealtyAPI, 2026-05-02) ──

SAMPLE_REALTYAPI_LISTING = {
    "property": {
        "zpid": 2054616655,
        "location": {
            "latitude": 30.205002,
            "longitude": -97.978966,
        },
        "address": {
            "streetAddress": "167 Hargraves Dr",
            "zipcode": "78737",
            "city": "Austin",
            "state": "TX",
            "buildingId": 2750952657,
        },
        "media": {
            "propertyPhotoLinks": {
                "mediumSizeLink": "https://photos.zillowstatic.com/fp/6c0c41ac-p_c.jpg",
                "highResolutionLink": "https://photos.zillowstatic.com/fp/6c0c41ac-p_f.jpg",
            },
            "allPropertyPhotos": {
                "medium": [
                    "https://photos.zillowstatic.com/fp/6c0c41ac-p_c.jpg",
                    "https://photos.zillowstatic.com/fp/b3be9542-p_c.jpg",
                    "https://photos.zillowstatic.com/fp/48ab8171-p_c.jpg",
                ],
                "highResolution": [
                    "https://photos.zillowstatic.com/fp/6c0c41ac-p_f.jpg",
                    "https://photos.zillowstatic.com/fp/b3be9542-p_f.jpg",
                    "https://photos.zillowstatic.com/fp/48ab8171-p_f.jpg",
                ],
            },
        },
        "title": "Jovie Belterra - 55+ Active Adult Apartment Home",
        "minPrice": 2728,
        "maxPrice": 3198,
        "unitsGroup": [
            {"bedrooms": 1, "minPrice": 2728, "isRoomForRent": False},
            {"bedrooms": 2, "minPrice": 3198, "isRoomForRent": False},
        ],
        "listingDateTimeOnZillow": 1735675200000,
        "listingStatus": "FOR_RENT",
    },
    "resultType": "propertyGroup",
}

SAMPLE_LISTING_SINGLE_PHOTO = {
    "property": {
        "zpid": 9988776655,
        "location": {"latitude": 32.7767, "longitude": -96.7970},
        "address": {
            "streetAddress": "500 Elm St Apt 12",
            "city": "Dallas",
            "state": "TX",
            "zipcode": "75201",
        },
        "media": {
            "propertyPhotoLinks": {
                "mediumSizeLink": "https://photos.zillowstatic.com/fp/single-p_c.jpg",
            },
            "allPropertyPhotos": {},
        },
        "title": "Downtown Dallas Loft",
        "minPrice": 1500,
        "maxPrice": 1500,
        "unitsGroup": [
            {"bedrooms": 0, "minPrice": 1500, "isRoomForRent": False},
        ],
    },
    "resultType": "propertyGroup",
}

SAMPLE_LISTING_NO_MEDIA = {
    "property": {
        "zpid": 1122334455,
        "location": {"latitude": 29.7604, "longitude": -95.3698},
        "address": {
            "streetAddress": "800 Main St",
            "city": "Houston",
            "state": "TX",
            "zipcode": "77002",
        },
        "media": {},
        "title": "Houston Heights Studio",
        "price": 1100,
        "bedrooms": 0,
        "bathrooms": 1,
    },
    "resultType": "propertyGroup",
}


# ── API Key retrieval ─────────────────────────────────────

class TestGetRealtyapiKey:
    def test_returns_key_when_stored(self, database_with_realtyapi_key):
        key = get_realtyapi_key(database_with_realtyapi_key)
        assert key == "rt_test_key_abc123"

    def test_returns_none_when_no_settings(self, database_connection):
        key = get_realtyapi_key(database_connection)
        assert key is None

    def test_returns_none_when_other_keys_stored(self, database_connection):
        database_connection.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('apartment_api_keys', ?, datetime('now'))",
            [json.dumps({"rentcast": "rc_key_only"})],
        )
        database_connection.commit()
        key = get_realtyapi_key(database_connection)
        assert key is None


# ── Image extraction (from property.media) ────────────────

class TestExtractImages:
    def test_extracts_high_resolution_photos(self):
        property_data = SAMPLE_REALTYAPI_LISTING["property"]
        images = _extract_images(property_data)
        assert len(images) == 3
        assert images[0] == "https://photos.zillowstatic.com/fp/6c0c41ac-p_f.jpg"
        assert images[1] == "https://photos.zillowstatic.com/fp/b3be9542-p_f.jpg"
        assert images[2] == "https://photos.zillowstatic.com/fp/48ab8171-p_f.jpg"

    def test_falls_back_to_single_photo_link(self):
        property_data = SAMPLE_LISTING_SINGLE_PHOTO["property"]
        images = _extract_images(property_data)
        assert len(images) == 1
        assert images[0] == "https://photos.zillowstatic.com/fp/single-p_c.jpg"

    def test_returns_empty_when_no_media(self):
        property_data = SAMPLE_LISTING_NO_MEDIA["property"]
        images = _extract_images(property_data)
        assert images == []

    def test_returns_empty_for_missing_media_key(self):
        images = _extract_images({"zpid": 123})
        assert images == []


# ── Address extraction ────────────────────────────────────

class TestExtractAddress:
    def test_extracts_from_address_object(self):
        property_data = SAMPLE_REALTYAPI_LISTING["property"]
        address = _extract_address(property_data)
        assert "167 Hargraves Dr" in address
        assert "Austin" in address
        assert "TX" in address
        assert "78737" in address

    def test_extracts_dallas_address(self):
        property_data = SAMPLE_LISTING_SINGLE_PHOTO["property"]
        address = _extract_address(property_data)
        assert "500 Elm St Apt 12" in address
        assert "Dallas" in address

    def test_extracts_houston_address(self):
        property_data = SAMPLE_LISTING_NO_MEDIA["property"]
        address = _extract_address(property_data)
        assert "800 Main St" in address
        assert "Houston" in address


# ── Price extraction ──────────────────────────────────────

class TestExtractPrice:
    def test_extracts_min_price_from_range(self):
        property_data = SAMPLE_REALTYAPI_LISTING["property"]
        price = _extract_price(property_data)
        assert price == 2728.0

    def test_extracts_direct_price(self):
        property_data = SAMPLE_LISTING_NO_MEDIA["property"]
        price = _extract_price(property_data)
        assert price == 1100.0

    def test_extracts_price_from_dict_format(self):
        """Some listings have price as {"value": 1593, "changedDate": ...}."""
        property_data = {"price": {"value": 1593, "changedDate": 1777611600000, "priceChange": 11}}
        price = _extract_price(property_data)
        assert price == 1593.0

    def test_returns_none_when_no_price(self):
        price = _extract_price({"zpid": 123})
        assert price is None


# ── Bed/bath extraction ──────────────────────────────────

class TestExtractBedBath:
    def test_extracts_from_units_group(self):
        property_data = SAMPLE_REALTYAPI_LISTING["property"]
        bedrooms, bathrooms = _extract_bed_bath(property_data)
        assert bedrooms == 1  # First unit in group
        assert bathrooms is None  # Not in this response

    def test_extracts_direct_bedrooms(self):
        property_data = SAMPLE_LISTING_NO_MEDIA["property"]
        bedrooms, bathrooms = _extract_bed_bath(property_data)
        assert bedrooms == 0  # Studio
        assert bathrooms == 1

    def test_extracts_studio_from_units_group(self):
        property_data = SAMPLE_LISTING_SINGLE_PHOTO["property"]
        bedrooms, bathrooms = _extract_bed_bath(property_data)
        assert bedrooms == 0  # Studio


# ── Title ─────────────────────────────────────────────────

class TestBuildTitle:
    def test_uses_property_title_when_available(self):
        normalized = _normalize_listing(SAMPLE_REALTYAPI_LISTING)
        assert normalized["title"] == "Jovie Belterra - 55+ Active Adult Apartment Home"

    def test_builds_title_when_no_property_title(self):
        listing_no_title = {
            "property": {
                "zpid": 999,
                "address": {"streetAddress": "100 Oak St", "city": "Austin", "state": "TX", "zipcode": "78701"},
                "media": {},
                "minPrice": 1500,
                "unitsGroup": [{"bedrooms": 2, "minPrice": 1500}],
            },
            "resultType": "propertyGroup",
        }
        normalized = _normalize_listing(listing_no_title)
        assert "2BR" in normalized["title"]
        assert "Austin" in normalized["title"]


# ── Bathrooms filter format ───────────────────────────────

class TestFormatBathroomsFilter:
    def test_one_bathroom(self):
        assert _format_bathrooms_filter(1) == "OnePlus"

    def test_two_bathrooms(self):
        assert _format_bathrooms_filter(2) == "TwoPlus"

    def test_unknown_defaults_to_any(self):
        assert _format_bathrooms_filter(5) == "Any"


# ── Age-restricted filter ─────────────────────────────────

class TestAgeRestrictedFilter:
    def test_filters_55_plus_community(self):
        assert _is_age_restricted({"title": "Jovie Belterra - 55+ Active Adult Apartment Home"}) is True

    def test_filters_senior_living(self):
        assert _is_age_restricted({"title": "Senior Living at Oak Park"}) is True

    def test_filters_active_adult(self):
        assert _is_age_restricted({"title": "Sunrise Active Adult Community"}) is True

    def test_allows_regular_apartment(self):
        assert _is_age_restricted({"title": "Alexan Braker Pointe"}) is False

    def test_allows_empty_title(self):
        assert _is_age_restricted({"title": ""}) is False
        assert _is_age_restricted({}) is False

    def test_search_excludes_55_plus(self, database_with_realtyapi_key, monkeypatch):
        """55+ listings should not appear in search results."""
        mock_response = {
            "searchResults": [
                SAMPLE_REALTYAPI_LISTING,  # "Jovie Belterra - 55+ Active Adult"
                SAMPLE_LISTING_SINGLE_PHOTO,  # "Downtown Dallas Loft"
            ],
        }

        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200, json=mock_response,
                request=httpx.Request("GET", args[0] if args else ""),
            )

        monkeypatch.setattr(httpx, "get", mock_get)
        results = search_realtyapi(database_with_realtyapi_key, city="Austin, TX")
        assert len(results) == 1
        assert results[0]["title"] == "Downtown Dallas Loft"


# ── Response envelope extraction ──────────────────────────

class TestExtractListingsFromResponse:
    def test_extracts_from_dict_with_search_results(self):
        response = {
            "message": "200",
            "searchResults": [SAMPLE_REALTYAPI_LISTING, SAMPLE_LISTING_SINGLE_PHOTO],
            "resultsCount": {"totalMatchingCount": 2},
        }
        listings = _extract_listings_from_response(response)
        assert len(listings) == 2
        assert listings[0]["property"]["zpid"] == 2054616655

    def test_extracts_from_direct_list(self):
        response = [SAMPLE_REALTYAPI_LISTING]
        listings = _extract_listings_from_response(response)
        assert len(listings) == 1

    def test_returns_empty_for_unexpected_format(self):
        assert _extract_listings_from_response({"error": "bad request"}) == []
        assert _extract_listings_from_response({}) == []


# ── Full normalization ────────────────────────────────────

class TestNormalizeListing:
    def test_normalizes_real_listing_with_images(self):
        normalized = _normalize_listing(SAMPLE_REALTYAPI_LISTING)
        assert normalized is not None
        assert normalized["title"] == "Jovie Belterra - 55+ Active Adult Apartment Home"
        assert normalized["price"] == 2728.0
        assert normalized["bedrooms"] == 1
        assert normalized["source"] == "realtyapi"
        assert "167 Hargraves Dr" in normalized["address"]
        assert "Austin" in normalized["address"]
        assert len(normalized["images"]) == 3
        assert "zillowstatic.com" in normalized["images"][0]
        assert normalized["latitude"] == 30.205002
        assert normalized["longitude"] == -97.978966
        assert "zillow.com" in normalized["source_url"]
        assert "2054616655" in normalized["source_url"]

    def test_normalizes_single_photo_listing(self):
        normalized = _normalize_listing(SAMPLE_LISTING_SINGLE_PHOTO)
        assert normalized is not None
        assert normalized["title"] == "Downtown Dallas Loft"
        assert normalized["price"] == 1500.0
        assert normalized["bedrooms"] == 0  # Studio
        assert len(normalized["images"]) == 1
        assert "Dallas" in normalized["address"]

    def test_normalizes_listing_without_photos(self):
        normalized = _normalize_listing(SAMPLE_LISTING_NO_MEDIA)
        assert normalized is not None
        assert normalized["images"] == []
        assert normalized["price"] == 1100.0
        assert normalized["bedrooms"] == 0
        assert normalized["bathrooms"] == 1
        assert "Houston" in normalized["address"]

    def test_returns_none_for_non_dict(self):
        assert _normalize_listing("not a dict") is None
        assert _normalize_listing(None) is None

    def test_extracts_features_from_property_data(self):
        """Features mined from unitsGroup, matchingHomeCount, zovInsight, etc."""
        normalized = _normalize_listing(SAMPLE_REALTYAPI_LISTING)
        amenities = normalized["amenities"]
        # unitsGroup has 1BR and 2BR
        assert any("1BR" in feature and "2BR" in feature for feature in amenities)

    def test_extracts_special_offer(self):
        """Listings with flexFieldRecommendations show Special Offer."""
        listing_with_offer = {
            "property": {
                **SAMPLE_LISTING_SINGLE_PHOTO["property"],
                "listCardRecommendation": {
                    "flexFieldRecommendations": [
                        {"displayString": "Special Offer", "contentType": "frSpecialOffer"},
                    ],
                },
            },
            "resultType": "propertyGroup",
        }
        normalized = _normalize_listing(listing_with_offer)
        assert "Special Offer" in normalized["amenities"]

    def test_extracts_rare_amenity_insight(self):
        """Zillow's zovInsight highlights rare amenities."""
        listing_with_insight = {
            "property": {
                **SAMPLE_LISTING_NO_MEDIA["property"],
                "listCardRecommendation": {
                    "zovInsight": {
                        "amenityType": "PetWashingStation",
                        "rarity": "7%",
                        "displayString": "Pet washing station",
                    },
                },
            },
            "resultType": "propertyGroup",
        }
        normalized = _normalize_listing(listing_with_insight)
        assert "Pet washing station (7%)" in normalized["amenities"]


# ── Search integration (mocked HTTP) ─────────────────────

class TestSearchRealtyapi:
    def test_returns_empty_when_no_api_key(self, database_connection):
        results = search_realtyapi(database_connection, city="Dallas")
        assert results == []

    def test_returns_empty_when_no_location(self, database_with_realtyapi_key):
        results = search_realtyapi(database_with_realtyapi_key)
        assert results == []

    def test_search_with_real_response_format(self, database_with_realtyapi_key, monkeypatch):
        """Mock returns the exact format RealtyAPI sends — dict with searchResults array."""
        mock_response_data = {
            "message": "200",
            "source": "test",
            "resultsCount": {"totalMatchingCount": 2, "ungroupedResultCount": 2},
            "pagesInfo": {"totalPages": 1, "currentPage": 1, "resultsPerPage": 200},
            "searchResults": [
                SAMPLE_LISTING_SINGLE_PHOTO,
                SAMPLE_LISTING_NO_MEDIA,
            ],
        }

        def mock_get(*args, **kwargs):
            return httpx.Response(
                status_code=200,
                json=mock_response_data,
                request=httpx.Request("GET", args[0] if args else kwargs.get("url", "")),
            )

        monkeypatch.setattr(httpx, "get", mock_get)

        results = search_realtyapi(database_with_realtyapi_key, city="Austin, TX")
        assert len(results) == 2
        assert results[0]["title"] == "Downtown Dallas Loft"
        assert results[0]["price"] == 1500.0
        assert results[0]["source"] == "realtyapi"
        assert len(results[0]["images"]) == 1
        assert "zillowstatic.com" in results[0]["images"][0]
        assert results[1]["title"] == "Houston Heights Studio"
        assert results[1]["price"] == 1100.0

    def test_handles_api_error_gracefully(self, database_with_realtyapi_key, monkeypatch):
        def mock_get_error(*args, **kwargs):
            response = httpx.Response(
                status_code=401,
                text="Unauthorized",
                request=httpx.Request("GET", args[0] if args else ""),
            )
            raise httpx.HTTPStatusError(
                message="401 Unauthorized",
                request=response.request,
                response=response,
            )

        monkeypatch.setattr(httpx, "get", mock_get_error)

        results = search_realtyapi(database_with_realtyapi_key, city="Dallas")
        assert results == []

    def test_handles_empty_response(self, database_with_realtyapi_key, monkeypatch):
        def mock_get_empty(*args, **kwargs):
            return httpx.Response(
                status_code=200,
                json=[],
                request=httpx.Request("GET", args[0] if args else ""),
            )

        monkeypatch.setattr(httpx, "get", mock_get_empty)

        results = search_realtyapi(database_with_realtyapi_key, city="Nowhere, TX")
        assert results == []
