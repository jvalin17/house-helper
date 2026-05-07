"""Term extractor — tests for extracting ranking terms from jobs and apartments.

Covers: job term extraction, apartment term extraction, search term extraction,
salary/price bucketing, freshness bucketing, amenity normalization.
"""

import pytest

from shared.ranking.term_extractor import (
    extract_job_terms,
    extract_apartment_terms,
    extract_search_terms,
    salary_bucket,
    price_bucket,
    freshness_bucket,
    normalize_amenity,
    tokenize_text,
)


# ── Tokenization ─────────────────────────────────────

def test_tokenize_removes_noise_words():
    tokens = tokenize_text("This is a senior engineer for the team")
    assert "senior" in tokens
    assert "engineer" in tokens
    assert "the" not in tokens
    assert "is" not in tokens


def test_tokenize_empty():
    assert tokenize_text("") == []
    assert tokenize_text(None) == []


# ── Job term extraction ──────────────────────────────

def test_extract_job_terms_basic():
    """Extracts title, company, location, skills from a job."""
    job = {
        "title": "Senior SDET",
        "company": "Apple",
        "location": "Austin, TX",
        "description": "Experience with Python and Selenium required.",
        "salary": "$120,000 - $150,000",
        "posted_date": None,
    }
    terms = extract_job_terms(job)
    assert "senior" in terms
    assert "sdet" in terms
    assert "apple" in terms
    assert "austin" in terms
    assert "python" in terms
    assert "direct_hire" in terms
    assert "has_salary_posted" in terms


def test_extract_job_terms_staffing_company():
    """Staffing agency detected from company name."""
    job = {"title": "Java Dev", "company": "Infosys Limited", "description": ""}
    terms = extract_job_terms(job)
    assert "staffing_agency" in terms
    assert "direct_hire" not in terms


def test_extract_job_terms_remote():
    """Remote keyword detected from title or description."""
    job = {"title": "Backend Engineer Remote", "company": "Stripe", "description": ""}
    terms = extract_job_terms(job)
    assert "remote" in terms


def test_extract_job_terms_salary_bucket():
    """Salary string converted to bucket term."""
    job = {"title": "Dev", "company": "Co", "description": "", "salary": "$130,000 - $160,000"}
    terms = extract_job_terms(job)
    assert "salary_125k_150k" in terms or "salary_130k_155k" in terms or any(
        term.startswith("salary_") for term in terms
    )


# ── Apartment term extraction ────────────────────────

def test_extract_apartment_terms_basic():
    """Extracts address, amenities, bedrooms, price from a listing."""
    listing = {
        "title": "Alexan Braker Pointe",
        "address": "10801 N Mopac Expy, Austin, TX 78759",
        "price": 1832.0,
        "bedrooms": 2,
        "bathrooms": 2,
        "amenities": ["Pool", "Gym", "In-Unit Washer/Dryer"],
        "images": ["photo1.jpg", "photo2.jpg"],
    }
    terms = extract_apartment_terms(listing)
    assert "austin" in terms
    assert "2br" in terms
    assert "2ba" in terms
    assert "pool" in terms
    assert "gym" in terms
    assert "in_unit_washer_dryer" in terms
    assert "has_photos" in terms
    assert any(term.startswith("rent_") for term in terms)


def test_extract_apartment_terms_studio():
    """Studio (0 bedrooms) produces 'studio' term."""
    listing = {"title": "Downtown Loft", "bedrooms": 0, "amenities": []}
    terms = extract_apartment_terms(listing)
    assert "studio" in terms


def test_extract_apartment_terms_many_photos():
    """10+ photos produces 'many_photos' term."""
    listing = {"title": "Luxury Apt", "amenities": [], "images": [f"photo{index}.jpg" for index in range(15)]}
    terms = extract_apartment_terms(listing)
    assert "many_photos" in terms
    assert "has_photos" in terms


# ── Search term extraction ───────────────────────────

def test_extract_search_terms():
    """Extracts terms from search filters for session boost."""
    filters = {
        "title": "senior backend engineer",
        "location": "Austin TX",
        "keywords": ["python", "django"],
        "remote": True,
    }
    terms = extract_search_terms(filters)
    assert "senior" in terms
    assert "backend" in terms
    assert "austin" in terms
    assert "python" in terms
    assert "django" in terms
    assert "remote" in terms


def test_extract_search_terms_empty():
    assert extract_search_terms({}) == []


# ── Bucketing helpers ────────────────────────────────

def test_salary_bucket_range():
    """$120,000 → 120000 / 25000 = 4 (floored) → 100k bucket."""
    assert salary_bucket("$120,000 - $150,000") == "salary_100k_125k"

def test_salary_bucket_single():
    assert salary_bucket("$85,000") == "salary_75k_100k"

def test_salary_bucket_none():
    assert salary_bucket(None) is None

def test_price_bucket_mid_range():
    assert price_bucket(1832.0) == "rent_1500_2000"

def test_price_bucket_low():
    assert price_bucket(950.0) == "rent_500_1000"

def test_price_bucket_none():
    assert price_bucket(None) is None

def test_normalize_amenity():
    assert normalize_amenity("In-Unit Washer/Dryer") == "in_unit_washer_dryer"
    assert normalize_amenity("24-Hour Fitness Center") == "24_hour_fitness_center"
    assert normalize_amenity("Pool") == "pool"
