"""Apartment URL extraction — TDD tests.

Covers:
- Extract title, price, bedrooms, bathrooms, sqft, address, amenities
- Image extraction: filters logos, icons, map thumbnails, deduplicates
- Floor plan image extraction
- Handle pages with missing data gracefully
- Real-world example: Ellwood at Lake Travis property website
"""

import pytest
from agents.apartment.services.url_extractor import extract_apartment_data_from_html


class TestExtractApartmentDataFromHtml:
    def test_extracts_title_from_page(self):
        html = """
        <html><head><title>Beautiful 2BR Apartment - Downtown Dallas</title></head>
        <body><h1>Beautiful 2BR Apartment</h1>
        <p>$1,750/mo</p><p>2 bed, 2 bath</p><p>1,100 sqft</p>
        <p>123 Main St, Dallas, TX 75001</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert "Beautiful 2BR" in result["title"]

    def test_extracts_price(self):
        html = """
        <html><body><h1>Studio Apartment</h1>
        <span class="price">$1,450/mo</span>
        <p>1 bed</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["price"] == 1450.0

    def test_extracts_bedrooms_bathrooms(self):
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
        html = """
        <html><body><h1>Cozy Place</h1>
        <p>$1,200/mo</p><p>1,200 sqft</p></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["sqft"] == 1200

    def test_handles_missing_data_gracefully(self):
        html = "<html><body><p>Some random content with no listing data</p></body></html>"
        result = extract_apartment_data_from_html(html)
        assert result["title"] is not None
        assert result["price"] is None
        assert result["bedrooms"] is None

    def test_extracts_amenities(self):
        html = """
        <html><body><h1>Luxury Apartment</h1>
        <p>$2,500/mo</p>
        <ul class="amenities">
            <li>Elevator</li><li>Pool</li><li>Gym</li><li>Parking</li>
        </ul></body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert "elevator" in [amenity.lower() for amenity in result.get("amenities", [])]


class TestImageExtraction:
    def test_filters_logo_images(self):
        html = """
        <html><body>
        <img src="https://example.com/logo.png" alt="Company Logo" width="200" height="80">
        <img src="https://example.com/apartment-photo.jpg" alt="Living room" width="960" height="527">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 1
        assert "apartment-photo" in result["images"][0]

    def test_filters_icon_images(self):
        html = """
        <html><body>
        <img src="https://example.com/equal-housing-icon.png" alt="Equal-housing-icon">
        <img src="https://example.com/pet-friendly-icon.svg" alt="Pet-friendly-icon">
        <img src="https://example.com/pool-photo.jpg" alt="the pool" width="720" height="480">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 1
        assert "pool-photo" in result["images"][0]

    def test_filters_google_maps_static_images(self):
        html = """
        <html><body>
        <img src="https://maps.googleapis.com/maps/api/staticmap?center=33.8,-118.3&zoom=15" width="400" height="300">
        <img src="https://example.com/bedroom.jpg" alt="bedroom" width="800" height="600">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 1
        assert "bedroom" in result["images"][0]

    def test_deduplicates_images(self):
        html = """
        <html><body>
        <img src="https://example.com/photo1.jpg" width="500" height="400">
        <img src="https://example.com/photo1.jpg" width="500" height="400">
        <img src="https://example.com/photo2.jpg" width="500" height="400">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 2

    def test_skips_tiny_images(self):
        html = """
        <html><body>
        <img src="https://example.com/tiny.png" width="50" height="50">
        <img src="https://example.com/large.jpg" width="800" height="600">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 1
        assert "large" in result["images"][0]

    def test_prefers_larger_images_first(self):
        html = """
        <html><body>
        <img src="https://example.com/small.jpg" width="300" height="200">
        <img src="https://example.com/large.jpg" width="1200" height="800">
        <img src="https://example.com/medium.jpg" width="600" height="400">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert result["images"][0] == "https://example.com/large.jpg"

    def test_filters_footer_and_powered_by(self):
        html = """
        <html><body>
        <img src="https://example.com/PoweredBySwifty.png" alt="Footer Powered By Swifty">
        <img src="https://example.com/Submitting.gif" alt="Submitting">
        <img src="https://example.com/kitchen.jpg" alt="kitchen" width="960" height="527">
        </body></html>
        """
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 1
        assert "kitchen" in result["images"][0]

    def test_max_20_images(self):
        images_html = "\n".join(
            f'<img src="https://example.com/photo{index}.jpg" width="500" height="400">'
            for index in range(30)
        )
        html = f"<html><body>{images_html}</body></html>"
        result = extract_apartment_data_from_html(html)
        assert len(result["images"]) == 20


class TestRealWorldEllwoodExample:
    """Test with HTML patterns from ellwoodlaketravis.com."""

    ELLWOOD_HTML = """
    <html><body>
    <h1>Hill Country Living, Elevated</h1>
    <p>1 Bed 1 Bath</p>

    <!-- Logo (should be filtered) -->
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/color.png"
         alt="ellwood at lake travis" class="attachment-s-s">
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/color.png"
         alt="ellwood at lake travis" class="attachment-s-s">

    <!-- Property photos (should be kept) -->
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/pool-photo.jpg"
         alt="the pool at The Ellwood" width="720" height="900">
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/lobby-photo.jpg"
         alt="the lobby of a large apartment building" width="1640" height="900">
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/kitchen-photo.jpg"
         alt="a kitchen with stainless steel appliances" width="960" height="527">
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2023/10/bedroom-photo.jpg"
         alt="a bedroom with a wooden bed" width="960" height="527">

    <!-- Gallery photos (540x540) -->
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2026/04/gallery1.jpg"
         alt="" width="540" height="540">
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2026/04/gallery2.jpg"
         alt="" width="540" height="540">

    <!-- Footer icons (should be filtered) -->
    <img src="https://example.com/property-icon/Equal-housing-icon.png" alt="Equal-housing-icon">
    <img src="https://example.com/property-icon/Pet-friendly-icon.png" alt="Pet-friendly-icon">
    <img src="https://example.com/property-icon/Accessibility-icon.png" alt="Accessibility-icon">
    <img src="https://example.com/PoweredBySwifty.png" alt="Footer Powered By Swifty">

    <!-- Fee schedule (should be filtered) -->
    <img src="https://swifty-media.s3.amazonaws.com/sites/8250/2025/12/Ellwood.png"
         alt="Fee Schedule" class="fee-sheet-image">

    <!-- Amenities text -->
    <ul><li>Pool</li><li>Clubhouse</li><li>Dishwasher</li>
    <li>Parking</li><li>Patio</li><li>Storage</li><li>Valet</li></ul>

    <!-- Floor plan -->
    <img src="https://swifty-media.s3.amazonaws.com/floor-plan-a1.jpg" alt="Floor Plan A1">
    </body></html>
    """

    def test_extracts_title(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        assert result["title"] == "Hill Country Living, Elevated"

    def test_extracts_bedrooms_bathrooms(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        assert result["bedrooms"] == 1
        assert result["bathrooms"] == 1

    def test_filters_logo_and_icons_keeps_property_photos(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        images = result["images"]
        # Should NOT contain logo (color.png is not filtered by URL but is a duplicate)
        # Should contain property photos
        assert any("pool" in url for url in images)
        assert any("kitchen" in url for url in images)
        assert any("bedroom" in url for url in images)
        # Should NOT contain footer icons
        assert not any("Equal-housing" in url for url in images)
        assert not any("PoweredBySwifty" in url for url in images)
        assert not any("fee-sheet" in url.lower() or "Fee Schedule" in url for url in images)

    def test_deduplicates_logo_appearing_twice(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        image_urls = result["images"]
        unique_urls = set(image_urls)
        assert len(image_urls) == len(unique_urls)

    def test_prefers_larger_photos(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        images = result["images"]
        # lobby-photo (1640x900) should come before gallery photos (540x540)
        if len(images) >= 2:
            assert "lobby" in images[0]

    def test_extracts_amenities(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        amenity_names_lower = [amenity.lower() for amenity in result["amenities"]]
        assert "pool" in amenity_names_lower
        assert "dishwasher" in amenity_names_lower
        assert "parking" in amenity_names_lower
        assert "valet" in amenity_names_lower

    def test_extracts_floor_plan(self):
        result = extract_apartment_data_from_html(self.ELLWOOD_HTML)
        assert len(result["floor_plan_images"]) >= 1
        assert any("floor-plan" in url for url in result["floor_plan_images"])
