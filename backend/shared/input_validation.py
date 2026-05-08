"""Shared input validation — guardrails for all user input across agents.

Every endpoint that accepts user input should validate through these helpers.
Prevents: SSRF, XSS storage, data corruption, resource exhaustion.

Usage:
    from shared.input_validation import validate_url, validate_text, validate_numeric

    validated_url = validate_url(user_url)  # raises ValueError if bad
    clean_text = validate_text(user_text, max_length=200)  # truncates + sanitizes
    valid_price = validate_numeric(price, min_value=0, max_value=999999)  # bounds check
"""

import re
from urllib.parse import urlparse

from shared.url_fetcher import validate_url_safety, SSRFError

MAX_URL_LENGTH = 2048
MAX_TEXT_LENGTH_DEFAULT = 500
MAX_DESCRIPTION_LENGTH = 50_000

# File extensions that are NOT web pages
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"})
DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"})
BINARY_EXTENSIONS = frozenset({".zip", ".tar", ".gz", ".exe", ".dmg", ".msi", ".deb", ".rpm"})

# Control characters and dangerous patterns to strip from stored text
DANGEROUS_PATTERNS = re.compile(r"<script[^>]*>.*?</script>|javascript:|data:text/html|on\w+=", re.IGNORECASE | re.DOTALL)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# ZIP code pattern
ZIP_CODE_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")


class InputValidationError(ValueError):
    """Raised when input fails validation. Message is safe to show to user."""
    pass


# ── URL validation ────────────────────────────────────

def validate_url(url: str, allow_images: bool = False, label: str = "URL") -> str:
    """Validate and sanitize a URL. Raises InputValidationError if invalid.

    Checks: length, SSRF, file type, protocol.
    Returns the cleaned URL.
    """
    url = url.strip()

    if not url:
        raise InputValidationError(f"{label} is required")

    if len(url) > MAX_URL_LENGTH:
        raise InputValidationError(f"{label} is too long (max {MAX_URL_LENGTH} characters)")

    # Protocol check
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InputValidationError(f"{label} must use http:// or https://")

    if not parsed.hostname:
        raise InputValidationError(f"Invalid {label} — no hostname")

    # File type check BEFORE SSRF (catches bad types without network call)
    url_path_lower = parsed.path.lower()
    extension = _get_extension(url_path_lower)

    if extension in BINARY_EXTENSIONS:
        raise InputValidationError(f"Binary files are not supported. Please provide a webpage URL.")

    if extension in DOCUMENT_EXTENSIONS:
        raise InputValidationError(f"Document URLs are not supported. Please provide a webpage URL.")

    if extension in IMAGE_EXTENSIONS and not allow_images:
        raise InputValidationError(
            f"This looks like an image URL, not a listing page. "
            f"To add a floor plan image, use the floor plan upload option."
        )

    # SSRF protection (after type checks — avoids network call for obviously bad URLs)
    try:
        validate_url_safety(url)
    except SSRFError as ssrf_error:
        raise InputValidationError(str(ssrf_error))

    return url


def validate_image_url(url: str) -> str:
    """Validate a URL specifically for image resources. Must be image extension or generic."""
    url = validate_url(url, allow_images=True, label="Image URL")
    return url


# ── Text validation ───────────────────────────────────

def validate_text(
    text: str | None,
    max_length: int = MAX_TEXT_LENGTH_DEFAULT,
    field_name: str = "text",
    required: bool = False,
    sanitize: bool = True,
) -> str | None:
    """Validate and sanitize a text field.

    Strips whitespace, removes control characters, truncates to max_length.
    Optionally removes dangerous HTML/JS patterns.
    """
    if text is None:
        if required:
            raise InputValidationError(f"{field_name} is required")
        return None

    cleaned = text.strip()
    if not cleaned:
        if required:
            raise InputValidationError(f"{field_name} is required")
        return None

    # Remove control characters
    cleaned = CONTROL_CHARS.sub("", cleaned)

    # Remove dangerous patterns (XSS prevention for stored text)
    if sanitize:
        cleaned = DANGEROUS_PATTERNS.sub("", cleaned)

    # Truncate
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


# ── Numeric validation ────────────────────────────────

def validate_numeric(
    value: float | int | None,
    min_value: float | None = None,
    max_value: float | None = None,
    field_name: str = "value",
    required: bool = False,
) -> float | int | None:
    """Validate a numeric field within bounds."""
    if value is None:
        if required:
            raise InputValidationError(f"{field_name} is required")
        return None

    if not isinstance(value, (int, float)):
        raise InputValidationError(f"{field_name} must be a number")

    if min_value is not None and value < min_value:
        raise InputValidationError(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        raise InputValidationError(f"{field_name} must be at most {max_value}")

    return value


# ── Specialized validators ────────────────────────────

def validate_zip_code(zip_code: str | None) -> str | None:
    """Validate US ZIP code format (5 digits or 5+4)."""
    if not zip_code:
        return None
    cleaned = zip_code.strip()
    if not ZIP_CODE_PATTERN.match(cleaned):
        return cleaned  # Allow non-standard formats (city names sometimes passed as zip)
    return cleaned


def validate_listing_data(extracted_data: dict) -> dict:
    """Validate extracted listing data has minimum quality.

    Raises InputValidationError if the data is garbage (no title AND no address).
    Sanitizes all text fields.
    """
    title = validate_text(extracted_data.get("title"), max_length=200, field_name="title")
    address = validate_text(extracted_data.get("address"), max_length=300, field_name="address")

    if not title and not address:
        raise InputValidationError(
            "Could not extract apartment data from this page. "
            "The page may not be a listing, or the site blocks automated access."
        )

    price = validate_numeric(extracted_data.get("price"), min_value=0, max_value=999999, field_name="price")
    bedrooms = validate_numeric(extracted_data.get("bedrooms"), min_value=0, max_value=20, field_name="bedrooms")
    bathrooms = validate_numeric(extracted_data.get("bathrooms"), min_value=0, max_value=20, field_name="bathrooms")
    sqft = validate_numeric(extracted_data.get("sqft"), min_value=0, max_value=100000, field_name="sqft")

    amenities = extracted_data.get("amenities") or []
    safe_amenities = [
        validate_text(amenity, max_length=100, field_name="amenity")
        for amenity in amenities[:50]
        if amenity
    ]

    return {
        **extracted_data,
        "title": title,
        "address": address,
        "price": price,
        "bedrooms": int(bedrooms) if bedrooms is not None else None,
        "bathrooms": bathrooms,
        "sqft": int(sqft) if sqft is not None else None,
        "amenities": [amenity for amenity in safe_amenities if amenity],
    }


def _get_extension(url_path: str) -> str:
    """Extract file extension from URL path, handling query params."""
    # Remove query string
    path_without_query = url_path.split("?")[0].split("#")[0]
    last_dot = path_without_query.rfind(".")
    if last_dot == -1:
        return ""
    return path_without_query[last_dot:]
