"""Data processor — tests for deduplication and merging across sources.

Tests matching by zpid, address, location+price, and merge enrichment.
"""

from agents.apartment.services.data_processor import (
    deduplicate_listings,
    _normalize_address,
    _are_same_property,
    _merge_listings,
    _locations_match,
    _prices_match,
)


# ── Test data ─────────────────────────────────────────────

ZILLOW_LISTING = {
    "title": "Alexan Braker Pointe",
    "address": "10801 N Mopac Expy, Austin, TX, 78759",
    "price": 1445.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "sqft": 720,
    "source": "realtyapi",
    "source_url": "https://www.zillow.com/homedetails/12345_zpid/",
    "latitude": 30.4186,
    "longitude": -97.7404,
    "images": [
        "https://photos.zillowstatic.com/fp/photo1.jpg",
        "https://photos.zillowstatic.com/fp/photo2.jpg",
    ],
    "amenities": ["Pool", "Garage"],
    "parsed_data": {"property": {"zpid": 12345}},
}

APARTMENTS_COM_SAME_PROPERTY = {
    "title": "Alexan Braker Pointe Apartments",
    "address": "10801 N Mopac Expressway, Austin, TX 78759",
    "price": 1445.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "sqft": 720,
    "source": "realtyapi_apartments",
    "source_url": "https://www.apartments.com/alexan-braker-pointe/",
    "latitude": 30.4186,
    "longitude": -97.7404,
    "images": [
        "https://photos.apartments.com/photo_a.jpg",
        "https://photos.apartments.com/photo_b.jpg",
        "https://photos.apartments.com/photo_c.jpg",
    ],
    "amenities": ["Pool", "Fitness Center", "Dog Park"],
    "parsed_data": {"property": {"zpid": 12345}},
}

RENTCAST_SAME_PROPERTY = {
    "title": "1BR 1BA Apartment in Austin",
    "address": "10801 N Mopac Expy, Austin, TX",
    "price": 1500.0,
    "bedrooms": 1,
    "bathrooms": 1,
    "sqft": None,
    "source": "rentcast",
    "source_url": "",
    "latitude": 30.4187,
    "longitude": -97.7403,
    "images": [],
    "amenities": [],
    "parsed_data": {},
}

DIFFERENT_PROPERTY = {
    "title": "Downtown Dallas Loft",
    "address": "500 Elm St, Dallas, TX, 75201",
    "price": 1800.0,
    "bedrooms": 2,
    "bathrooms": 1,
    "sqft": 950,
    "source": "realtyapi",
    "latitude": 32.7831,
    "longitude": -96.7936,
    "images": ["https://photos.zillowstatic.com/fp/dallas.jpg"],
    "amenities": ["Doorman"],
    "parsed_data": {"property": {"zpid": 99999}},
}


# ── Address normalization ─────────────────────────────────

class TestNormalizeAddress:
    def test_normalizes_abbreviations(self):
        assert "elm street" in _normalize_address("500 Elm St")
        assert "oak drive" in _normalize_address("123 Oak Dr")
        assert "main avenue" in _normalize_address("789 Main Ave")

    def test_removes_apartment_numbers(self):
        normalized = _normalize_address("500 Elm St Apt 12, Dallas, TX")
        assert "apt" not in normalized
        assert "12" not in normalized.split()  # 12 removed as apt number

    def test_removes_zip_codes(self):
        normalized = _normalize_address("500 Elm St, Dallas, TX 75201")
        assert "75201" not in normalized

    def test_case_insensitive(self):
        assert _normalize_address("500 ELM ST") == _normalize_address("500 elm st")

    def test_empty_returns_empty(self):
        assert _normalize_address("") == ""

    def test_matches_mopac_expy_vs_expressway(self):
        address_a = _normalize_address("10801 N Mopac Expy, Austin, TX, 78759")
        address_b = _normalize_address("10801 N Mopac Expressway, Austin, TX 78759")
        assert address_a == address_b


# ── Property matching ─────────────────────────────────────

class TestAreSameProperty:
    def test_matches_by_zpid(self):
        assert _are_same_property(ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY) is True

    def test_matches_by_address_similarity(self):
        listing_a = {**ZILLOW_LISTING, "parsed_data": {}}
        listing_b = {**APARTMENTS_COM_SAME_PROPERTY, "parsed_data": {}}
        assert _are_same_property(listing_a, listing_b) is True

    def test_matches_by_location_and_price(self):
        listing_a = {**ZILLOW_LISTING, "parsed_data": {}, "address": ""}
        listing_b = {**RENTCAST_SAME_PROPERTY, "address": ""}
        assert _are_same_property(listing_a, listing_b) is True

    def test_rejects_different_property(self):
        assert _are_same_property(ZILLOW_LISTING, DIFFERENT_PROPERTY) is False

    def test_rejects_same_city_different_address(self):
        listing_a = {"address": "100 Oak St, Austin, TX", "price": 1500, "latitude": 30.27, "longitude": -97.74, "parsed_data": {}}
        listing_b = {"address": "200 Pine Dr, Austin, TX", "price": 1500, "latitude": 30.30, "longitude": -97.80, "parsed_data": {}}
        assert _are_same_property(listing_a, listing_b) is False


# ── Location matching ─────────────────────────────────────

class TestLocationsMatch:
    def test_same_coordinates(self):
        assert _locations_match(
            {"latitude": 30.4186, "longitude": -97.7404},
            {"latitude": 30.4186, "longitude": -97.7404},
        ) is True

    def test_within_100_meters(self):
        assert _locations_match(
            {"latitude": 30.4186, "longitude": -97.7404},
            {"latitude": 30.4187, "longitude": -97.7403},
        ) is True

    def test_far_apart(self):
        assert _locations_match(
            {"latitude": 30.4186, "longitude": -97.7404},
            {"latitude": 32.7831, "longitude": -96.7936},
        ) is False

    def test_missing_coordinates(self):
        assert _locations_match(
            {"latitude": None, "longitude": -97.7404},
            {"latitude": 30.4186, "longitude": -97.7404},
        ) is False


# ── Price matching ────────────────────────────────────────

class TestPricesMatch:
    def test_same_price(self):
        assert _prices_match({"price": 1445}, {"price": 1445}) is True

    def test_within_20_percent(self):
        assert _prices_match({"price": 1445}, {"price": 1500}) is True

    def test_beyond_20_percent(self):
        assert _prices_match({"price": 1000}, {"price": 1500}) is False

    def test_missing_price_matches(self):
        assert _prices_match({"price": None}, {"price": 1500}) is True


# ── Merge enrichment ─────────────────────────────────────

class TestMergeListings:
    def test_merges_images_from_both_sources(self):
        merged = _merge_listings([ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY])
        assert len(merged["images"]) == 5  # 2 from Zillow + 3 from Apartments.com

    def test_merges_amenities_without_duplicates(self):
        merged = _merge_listings([ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY])
        assert "Pool" in merged["amenities"]
        assert "Garage" in merged["amenities"]
        assert "Fitness Center" in merged["amenities"]
        assert "Dog Park" in merged["amenities"]
        assert merged["amenities"].count("Pool") == 1  # No duplicates

    def test_tracks_all_sources(self):
        merged = _merge_listings([ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY, RENTCAST_SAME_PROPERTY])
        assert "realtyapi" in merged["sources"]
        assert "realtyapi_apartments" in merged["sources"]
        assert "rentcast" in merged["sources"]

    def test_keeps_longer_title(self):
        merged = _merge_listings([ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY])
        assert merged["title"] == "Alexan Braker Pointe Apartments"  # Longer

    def test_fills_missing_sqft_from_other_source(self):
        listing_no_sqft = {**ZILLOW_LISTING, "sqft": None}
        listing_with_sqft = {**RENTCAST_SAME_PROPERTY, "sqft": 720}
        merged = _merge_listings([listing_no_sqft, listing_with_sqft])
        assert merged["sqft"] == 720

    def test_single_listing_adds_sources_field(self):
        merged = _merge_listings([ZILLOW_LISTING])
        assert merged["sources"] == ["realtyapi"]


# ── Full deduplication ────────────────────────────────────

class TestDeduplicateListings:
    def test_deduplicates_same_property_from_three_sources(self):
        all_listings = [ZILLOW_LISTING, APARTMENTS_COM_SAME_PROPERTY, RENTCAST_SAME_PROPERTY, DIFFERENT_PROPERTY]
        deduplicated = deduplicate_listings(all_listings)

        assert len(deduplicated) == 2  # One Austin property + one Dallas property

        austin_listing = next(listing for listing in deduplicated if "Braker" in listing["title"] or "Alexan" in listing["title"])
        dallas_listing = next(listing for listing in deduplicated if "Dallas" in listing["title"])

        assert len(austin_listing["sources"]) == 3
        assert len(austin_listing["images"]) == 5
        assert dallas_listing["sources"] == ["realtyapi"]

    def test_no_duplicates_returns_all(self):
        listings = [ZILLOW_LISTING, DIFFERENT_PROPERTY]
        deduplicated = deduplicate_listings(listings)
        assert len(deduplicated) == 2

    def test_empty_list_returns_empty(self):
        assert deduplicate_listings([]) == []

    def test_single_listing_returns_with_sources(self):
        deduplicated = deduplicate_listings([ZILLOW_LISTING])
        assert len(deduplicated) == 1
        assert deduplicated[0]["sources"] == ["realtyapi"]
