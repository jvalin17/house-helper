"""Input validation — tests for shared guardrails.

Covers: URL validation (SSRF, file type, length, protocol),
text sanitization, numeric bounds, listing data quality check.
"""

import pytest

from shared.input_validation import (
    validate_url,
    validate_image_url,
    validate_text,
    validate_numeric,
    validate_listing_data,
    InputValidationError,
)


# ── URL validation ────────────────────────────────────

class TestValidateUrl:

    def test_valid_listing_url(self):
        result = validate_url("https://www.apartments.com/alexan-braker-pointe/")
        assert result == "https://www.apartments.com/alexan-braker-pointe/"

    def test_rejects_empty(self):
        with pytest.raises(InputValidationError, match="required"):
            validate_url("")

    def test_rejects_too_long(self):
        with pytest.raises(InputValidationError, match="too long"):
            validate_url("https://example.com/" + "a" * 3000)

    def test_rejects_ftp_protocol(self):
        with pytest.raises(InputValidationError, match="http"):
            validate_url("ftp://files.example.com/listing.html")

    def test_rejects_file_protocol(self):
        with pytest.raises(InputValidationError, match="http"):
            validate_url("file:///etc/passwd")

    def test_rejects_localhost(self):
        with pytest.raises(InputValidationError, match="localhost"):
            validate_url("http://localhost:8040/health")

    def test_rejects_private_ip(self):
        with pytest.raises(InputValidationError):
            validate_url("http://192.168.1.1/admin")

    def test_rejects_png_image(self):
        """Image URLs rejected before SSRF check (no network call needed)."""
        with pytest.raises(InputValidationError, match="image URL"):
            validate_url("https://cdn.somesite.com/floor-plan.png")

    def test_rejects_jpg_with_query_params(self):
        with pytest.raises(InputValidationError, match="image URL"):
            validate_url("https://cdn.somesite.com/photo.jpg?w=800")

    def test_rejects_pdf(self):
        with pytest.raises(InputValidationError, match="Document"):
            validate_url("https://somesite.com/lease.pdf")

    def test_rejects_zip(self):
        with pytest.raises(InputValidationError, match="Binary"):
            validate_url("https://somesite.com/data.zip")

    def test_allows_image_when_flag_set(self):
        """Image URLs pass type check when allow_images=True (SSRF still runs)."""
        # Use localhost to verify SSRF still catches it even with allow_images
        with pytest.raises(InputValidationError, match="localhost"):
            validate_url("http://localhost/floor-plan.png", allow_images=True)


class TestValidateImageUrl:

    def test_still_rejects_localhost(self):
        with pytest.raises(InputValidationError):
            validate_image_url("http://localhost:8040/secret.png")


# ── Text validation ───────────────────────────────────

class TestValidateText:

    def test_strips_whitespace(self):
        assert validate_text("  hello  ") == "hello"

    def test_truncates_long_text(self):
        result = validate_text("a" * 1000, max_length=100)
        assert len(result) == 100

    def test_removes_script_tags(self):
        result = validate_text('<script>alert("xss")</script>Safe text')
        assert "<script>" not in result
        assert "Safe text" in result

    def test_removes_javascript_protocol(self):
        result = validate_text('Click javascript:alert(1) here')
        assert "javascript:" not in result

    def test_removes_control_characters(self):
        result = validate_text("hello\x00\x01\x02world")
        assert result == "helloworld"

    def test_none_returns_none(self):
        assert validate_text(None) is None

    def test_none_required_raises(self):
        with pytest.raises(InputValidationError, match="required"):
            validate_text(None, required=True, field_name="title")

    def test_empty_returns_none(self):
        assert validate_text("   ") is None


# ── Numeric validation ────────────────────────────────

class TestValidateNumeric:

    def test_valid_price(self):
        assert validate_numeric(1500.0, min_value=0, max_value=999999) == 1500.0

    def test_rejects_negative_price(self):
        with pytest.raises(InputValidationError, match="at least"):
            validate_numeric(-100, min_value=0, field_name="price")

    def test_rejects_too_high(self):
        with pytest.raises(InputValidationError, match="at most"):
            validate_numeric(5000000, max_value=999999, field_name="rent")

    def test_none_returns_none(self):
        assert validate_numeric(None) is None

    def test_none_required_raises(self):
        with pytest.raises(InputValidationError, match="required"):
            validate_numeric(None, required=True, field_name="price")


# ── Listing data validation ───────────────────────────

class TestValidateListingData:

    def test_valid_listing(self):
        result = validate_listing_data({
            "title": "Alexan Braker Pointe",
            "address": "10801 N Mopac, Austin TX",
            "price": 1445.0,
            "bedrooms": 1,
            "amenities": ["Pool", "Gym"],
        })
        assert result["title"] == "Alexan Braker Pointe"
        assert result["price"] == 1445.0

    def test_rejects_no_title_no_address(self):
        with pytest.raises(InputValidationError, match="Could not extract"):
            validate_listing_data({"title": "", "address": None})

    def test_accepts_address_only(self):
        result = validate_listing_data({"title": "", "address": "Austin, TX"})
        assert result["address"] == "Austin, TX"

    def test_caps_bedroom_count(self):
        with pytest.raises(InputValidationError, match="at most"):
            validate_listing_data({"title": "Test", "bedrooms": 999})

    def test_rejects_negative_price(self):
        with pytest.raises(InputValidationError, match="at least"):
            validate_listing_data({"title": "Test", "price": -500})

    def test_caps_amenities_list(self):
        result = validate_listing_data({
            "title": "Test",
            "amenities": [f"amenity_{index}" for index in range(100)],
        })
        assert len(result["amenities"]) <= 50

    def test_sanitizes_xss_in_title(self):
        result = validate_listing_data({
            "title": '<script>alert("xss")</script>Real Apartment',
            "address": "Austin",
        })
        assert "<script>" not in result["title"]
        assert "Real Apartment" in result["title"]
