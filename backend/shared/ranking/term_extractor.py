"""Term extraction — pulls ranking-relevant terms from any result.

Reuses existing entity_extractor for tech skills, adds apartment-specific
term extraction. Every data field is a potential term.

Agent-agnostic: extractors are plain functions registered per agent.
"""

import re

from shared.algorithms.entity_extractor import extract_skills_from_text

# ── Shared normalizers ────────────────────────────────

def tokenize_text(text: str) -> list[str]:
    """Split text into lowercase tokens, removing noise words."""
    if not text:
        return []
    noise_words = frozenset({
        "the", "a", "an", "and", "or", "in", "at", "for", "of", "to",
        "is", "are", "was", "were", "be", "been", "being", "with", "by",
        "on", "as", "it", "its", "this", "that", "we", "our", "you",
        "your", "from", "will", "can", "all", "has", "have", "had",
    })
    words = re.findall(r"[a-zA-Z0-9#+.]+", text.lower())
    return [word for word in words if word not in noise_words and len(word) > 1]


def normalize_amenity(amenity_text: str) -> str:
    """Normalize an amenity string to a consistent term format."""
    normalized = amenity_text.lower().strip()
    # Replace hyphens and slashes with spaces first (keep word boundaries)
    normalized = re.sub(r"[-/]", " ", normalized)
    # Remove remaining special chars
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    # Collapse whitespace to underscores
    normalized = re.sub(r"\s+", "_", normalized.strip())
    return normalized


def salary_bucket(salary_text: str | None) -> str | None:
    """Convert salary string to bucket term: 'salary_100k_150k'."""
    if not salary_text:
        return None
    numbers = re.findall(r"[\d,]+", salary_text.replace(",", ""))
    if not numbers:
        return None
    try:
        first_value = int(numbers[0])
        bucket_lower = (first_value // 25000) * 25
        bucket_upper = bucket_lower + 25
        return f"salary_{bucket_lower}k_{bucket_upper}k"
    except (ValueError, IndexError):
        return None


def price_bucket(price: float | None) -> str | None:
    """Convert rent price to bucket term: 'rent_1500_2000'."""
    if not price or price <= 0:
        return None
    bucket_lower = (int(price) // 500) * 500
    bucket_upper = bucket_lower + 500
    return f"rent_{bucket_lower}_{bucket_upper}"


def freshness_bucket(posted_date: str | None) -> str:
    """Convert posted date to freshness term."""
    if not posted_date:
        return "posted_unknown"
    from datetime import datetime, timezone
    try:
        if "T" in posted_date:
            posted = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
        else:
            posted = datetime.strptime(posted_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - posted).days
        if days_old <= 1:
            return "posted_today"
        if days_old <= 3:
            return "posted_this_week"
        if days_old <= 7:
            return "posted_this_week"
        if days_old <= 14:
            return "posted_two_weeks"
        if days_old <= 30:
            return "posted_this_month"
        return "posted_older"
    except (ValueError, TypeError):
        return "posted_unknown"


# ── Job term extraction ───────────────────────────────

STAFFING_COMPANY_TERMS = frozenset({
    "infosys", "wipro", "tcs", "cognizant", "accenture", "hcl",
    "capgemini", "randstad", "teksystems", "insight global",
})


def extract_job_terms(job: dict) -> list[str]:
    """Extract ranking terms from a job search result.

    Pulls from: title, company, location, skills, salary, structural signals.
    """
    terms = []

    # Title terms
    title = job.get("title") or ""
    terms.extend(tokenize_text(title))

    # Company
    company = (job.get("company") or "").lower().strip()
    if company:
        terms.append(company)
        if any(staffing_name in company for staffing_name in STAFFING_COMPANY_TERMS):
            terms.append("staffing_agency")
        else:
            terms.append("direct_hire")

    # Location
    location = job.get("location") or ""
    location_tokens = tokenize_text(location)
    terms.extend(location_tokens)

    # Tech skills from description (reuse existing extractor)
    description = job.get("description") or ""
    extracted_skills = job.get("extracted_skills") or extract_skills_from_text(description)
    terms.extend(skill.lower() for skill in extracted_skills)

    # Salary bucket
    salary_term = salary_bucket(job.get("salary"))
    if salary_term:
        terms.append(salary_term)
    if job.get("salary"):
        terms.append("has_salary_posted")

    # Remote detection
    combined_text = f"{title} {location} {description}".lower()
    if "remote" in combined_text or "work from home" in combined_text:
        terms.append("remote")
    if "hybrid" in combined_text:
        terms.append("hybrid")
    if "onsite" in combined_text or "on-site" in combined_text:
        terms.append("onsite")

    # Freshness
    terms.append(freshness_bucket(job.get("posted_date")))

    # Source
    source = job.get("source")
    if source:
        terms.append(f"source_{source}")

    return list(set(terms))  # deduplicate


# ── Apartment term extraction ─────────────────────────

def extract_apartment_terms(listing: dict) -> list[str]:
    """Extract ranking terms from an apartment listing.

    Pulls from: title, address, amenities, price, bedrooms, images, Intel data.
    """
    terms = []

    # Title terms (property name)
    terms.extend(tokenize_text(listing.get("title") or ""))

    # Address/location terms
    address = listing.get("address") or ""
    address_tokens = tokenize_text(address)
    terms.extend(address_tokens)

    # Amenities — each becomes its own term
    for amenity in (listing.get("amenities") or []):
        terms.append(normalize_amenity(amenity))

    # Bedroom type
    bedrooms = listing.get("bedrooms")
    if bedrooms is not None:
        terms.append(f"{bedrooms}br" if bedrooms > 0 else "studio")

    # Bathrooms
    bathrooms = listing.get("bathrooms")
    if bathrooms is not None:
        terms.append(f"{int(bathrooms)}ba")

    # Price bucket
    price_term = price_bucket(listing.get("price"))
    if price_term:
        terms.append(price_term)

    # Photo availability
    images = listing.get("images") or []
    if images:
        terms.append("has_photos")
        if len(images) >= 10:
            terms.append("many_photos")

    # Source
    source = listing.get("source")
    if source:
        terms.append(f"source_{source}")

    # Freshness (from created_at if available)
    terms.append(freshness_bucket(listing.get("created_at")))

    return list(set(terms))


# ── Search term extraction ────────────────────────────

def extract_search_terms(search_filters: dict) -> list[str]:
    """Extract terms from the user's search query/filters.

    These get session-scoped boost during scoring.
    """
    terms = []

    title = search_filters.get("title") or ""
    terms.extend(tokenize_text(title))

    keywords = search_filters.get("keywords") or []
    terms.extend(keyword.lower() for keyword in keywords if isinstance(keyword, str))

    location = search_filters.get("location") or ""
    terms.extend(tokenize_text(location))

    if search_filters.get("remote"):
        terms.append("remote")

    salary_min = search_filters.get("salary_min")
    if salary_min:
        terms.append(salary_bucket(f"${salary_min}") or f"salary_{salary_min // 1000}k")

    return list(set(terms))
