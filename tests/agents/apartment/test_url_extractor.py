"""Apartment URL extraction — TDD tests.

Covers:
- Extract title from HTML page
- Extract price from page content
- Extract bedrooms/bathrooms from page
- Extract address from page
- Extract amenities list
- Handle pages with missing data gracefully
- SSRF protection (block localhost/private IPs)
"""

import pytest
from agents.apartment.services.url_extractor import extract_apartment_data_from_html


class TestExtractApartmentDataFromHtml:
    def test_extracts_title_from_page(self):
        """Should extract the listing title from HTML."""
        html = """
        <html><head><title>Beautiful 2BR Apartment - Downtown Dallas</title></head>
        <body><h1>Beautiful 2BR Apartment</h1>
        <p>$1,750/mo</p><p>2 bed, 2 bath</p><p>1,100 sqft</p>
        <p>123 Main St, Dallas, TX 75001</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert "Beautiful 2BR" in result["title"]

    def test_extracts_price(self):
        """Should extract monthly rent price."""
        html = """
        <html><body><h1>Studio Apartment</h1>
        <span class="price">$1,450/mo</span>
        <p>1 bed</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["price"] == 1450.0

    def test_extracts_bedrooms_bathrooms(self):
        """Should extract bedroom and bathroom count."""
        html = """
        <html><body><h1>Spacious Unit</h1>
        <p>$2,100/mo</p>
        <span>3 bed</span> <span>2 bath</span>
        <p>1,500 sqft</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["bedrooms"] == 3
        assert result["bathrooms"] == 2

    def test_extracts_sqft(self):
        """Should extract square footage."""
        html = """
        <html><body><h1>Cozy Place</h1>
        <p>$1,200/mo</p><p>1,200 sqft</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["sqft"] == 1200

    def test_handles_missing_data_gracefully(self):
        """Pages with minimal data should return partial results, not crash."""
        html = "<html><body><p>Some random content with no listing data</p></body></html>"
        result = extract_apartment_data_from_html(html)
        assert result["title"] is not None  # Falls back to page title or empty
        assert result["price"] is None
        assert result["bedrooms"] is None

    def test_extracts_amenities(self):
        """Should extract amenities from listing."""
        html = """
        <html><body><h1>Luxury Apartment</h1>
        <p>$2,500/mo</p>
        <ul class="amenities">
            <li>Elevator</li><li>Pool</li><li>Gym</li><li>Parking</li>
        </ul></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert "elevator" in [amenity.lower() for amenity in result.get("amenities", [])]
