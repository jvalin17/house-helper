"""Extract apartment listing data from HTML page content.

Parses common patterns found on rental listing sites:
price ($X,XXX/mo), bedrooms, bathrooms, sqft, address, amenities.
"""

import re

from bs4 import BeautifulSoup


def extract_apartment_data_from_html(html: str) -> dict:
    """Extract structured apartment data from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(separator=" ", strip=True)

    return {
        "title": _extract_title(soup),
        "price": _extract_price(full_text),
        "bedrooms": _extract_bedrooms(full_text),
        "bathrooms": _extract_bathrooms(full_text),
        "sqft": _extract_sqft(full_text),
        "address": _extract_address(full_text),
        "amenities": _extract_amenities(soup),
        "floor_plan_images": _extract_floor_plan_images(soup),
    }


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract listing title from h1 or page title."""
    heading = soup.find("h1")
    if heading and heading.get_text(strip=True):
        return heading.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        return title_tag.get_text(strip=True)
    return ""


def _extract_price(text: str) -> float | None:
    """Extract monthly rent price from text like '$1,750/mo' or '$1750'."""
    price_patterns = [
        r"\$(\d{1,2},?\d{3})\s*/\s*mo",
        r"\$(\d{1,2},?\d{3})\s*/\s*month",
        r"\$(\d{1,2},?\d{3})",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_text = match.group(1).replace(",", "")
            return float(price_text)
    return None


def _extract_bedrooms(text: str) -> int | None:
    """Extract bedroom count from text like '2 bed' or '2 bedroom'."""
    match = re.search(r"(\d+)\s*(?:bed(?:room)?s?|br|BD)\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if re.search(r"\bstudio\b", text, re.IGNORECASE):
        return 0
    return None


def _extract_bathrooms(text: str) -> int | None:
    """Extract bathroom count from text like '2 bath' or '2.5 bathroom'."""
    match = re.search(r"(\d+(?:\.\d)?)\s*(?:bath(?:room)?s?|ba|BA)\b", text, re.IGNORECASE)
    if match:
        return int(float(match.group(1)))
    return None


def _extract_sqft(text: str) -> int | None:
    """Extract square footage from text like '1,100 sqft' or '1100 sq ft'."""
    match = re.search(r"(\d{1,2},?\d{3})\s*(?:sq\.?\s*ft|sqft|square\s*feet)", text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _extract_address(text: str) -> str | None:
    """Extract address — look for patterns with street number + city/state/zip."""
    match = re.search(
        r"(\d+\s+[\w\s]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl)\.?[,\s]+[\w\s]+,\s*[A-Z]{2}\s*\d{5})",
        text,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_amenities(soup: BeautifulSoup) -> list[str]:
    """Extract amenities from lists on the page."""
    amenity_keywords = {
        "elevator", "pool", "gym", "parking", "laundry", "dishwasher",
        "balcony", "patio", "fireplace", "storage", "pet friendly",
        "concierge", "rooftop", "clubhouse", "playground", "dog park",
        "ev charging", "package locker", "valet", "doorman",
    }
    found_amenities = []
    full_text_lower = soup.get_text(separator=" ", strip=True).lower()

    for amenity in amenity_keywords:
        if amenity in full_text_lower:
            found_amenities.append(amenity.title())

    return sorted(found_amenities)


def _extract_floor_plan_images(soup: BeautifulSoup) -> list[str]:
    """Extract floor plan image URLs from the page."""
    floor_plan_urls = []
    for image_tag in soup.find_all("img"):
        source_url = image_tag.get("src", "")
        alt_text = image_tag.get("alt", "").lower()
        if "floor" in alt_text or "plan" in alt_text or "layout" in alt_text:
            if source_url.startswith("http"):
                floor_plan_urls.append(source_url)
    return floor_plan_urls
