"""Natural language job search query parser — tests.

Covers: title extraction, location detection, salary parsing, remote flag,
exclusion patterns, tech skill keywords, combined queries.
"""

import pytest

from agents.job.services.query_parser import parse_job_search_query


# ── Simple title queries ─────────────────────────────

def test_simple_title():
    """Plain job title comes through as title."""
    result = parse_job_search_query("SDET")
    assert result["title"] == "SDET"


def test_multi_word_title():
    """Multi-word title preserved."""
    result = parse_job_search_query("senior backend engineer")
    assert result["title"] == "senior backend engineer"


def test_empty_query():
    """Empty query returns empty dict."""
    assert parse_job_search_query("") == {}
    assert parse_job_search_query("   ") == {}
    assert parse_job_search_query(None) == {}


# ── Location extraction ──────────────────────────────

def test_location_city_state():
    """Extracts 'Austin, TX' from query."""
    result = parse_job_search_query("SDET Austin, TX")
    assert result["location"] == "Austin, TX"
    assert "Austin" not in result.get("title", "")


def test_location_city_state_no_comma():
    """Extracts 'Austin TX' without comma."""
    result = parse_job_search_query("SDET Austin TX")
    assert result["location"] == "Austin, TX"


def test_location_in_prefix():
    """Extracts location from 'in Austin' pattern."""
    result = parse_job_search_query("backend engineer in Austin")
    assert result["location"] == "Austin"
    assert "in" not in result.get("title", "").lower().split()


def test_location_known_city():
    """Detects known city names without state."""
    result = parse_job_search_query("ML engineer Seattle")
    assert result["location"] == "Seattle"


def test_location_two_word_city():
    """Detects two-word cities like San Francisco."""
    result = parse_job_search_query("DevOps San Francisco")
    assert result["location"] == "San Francisco"


def test_location_new_york():
    """Detects New York."""
    result = parse_job_search_query("frontend developer New York")
    assert result["location"] == "New York"


# ── Remote flag ──────────────────────────────────────

def test_remote_keyword():
    """'remote' sets remote flag and is removed from title."""
    result = parse_job_search_query("backend engineer remote")
    assert result["remote"] is True
    assert "remote" not in result.get("title", "").lower()


def test_fully_remote():
    """'fully remote' detected."""
    result = parse_job_search_query("SDET fully remote")
    assert result["remote"] is True


# ── Salary extraction ────────────────────────────────

def test_salary_range_with_dollar():
    """'$120k-180k' → salary_min=120000, salary_max=180000."""
    result = parse_job_search_query("engineer $120k-180k")
    assert result["salary_min"] == 120000
    assert result["salary_max"] == 180000


def test_salary_min_only():
    """'$150k+' → salary_min=150000, no max."""
    result = parse_job_search_query("senior engineer $150k+")
    assert result["salary_min"] == 150000
    assert "salary_max" not in result


def test_salary_range_no_dollar():
    """'120k-180k' without $ sign."""
    result = parse_job_search_query("engineer 120k-180k")
    assert result["salary_min"] == 120000
    assert result["salary_max"] == 180000


# ── Tech skill keywords ─────────────────────────────

def test_extracts_python_as_keyword():
    """Python extracted as keyword, not part of title."""
    result = parse_job_search_query("senior engineer python")
    assert "python" in result.get("keywords", [])
    assert "python" not in result.get("title", "").lower()


def test_extracts_multiple_skills():
    """Multiple tech skills extracted."""
    result = parse_job_search_query("engineer python react aws")
    keywords = result.get("keywords", [])
    assert "python" in keywords
    assert "react" in keywords
    assert "aws" in keywords


def test_title_with_skills_separated():
    """Title words kept, skills extracted."""
    result = parse_job_search_query("senior backend engineer python java")
    assert "senior" in result.get("title", "")
    assert "backend" in result.get("title", "")
    assert "python" in result.get("keywords", [])
    assert "java" in result.get("keywords", [])


# ── Exclusion patterns ───────────────────────────────

def test_no_clearance_exclusion():
    """'no clearance' sets exclude_clearance."""
    result = parse_job_search_query("SDET no clearance")
    assert result["exclusions"]["exclude_clearance"] is True
    assert "clearance" not in result.get("title", "").lower()


def test_no_consultancy_exclusion():
    """'no consultancy' sets exclude_consultancy."""
    result = parse_job_search_query("backend engineer no consultancy")
    assert result["exclusions"]["exclude_consultancy"] is True


def test_direct_hire_exclusion():
    """'direct hire' sets exclude_consultancy."""
    result = parse_job_search_query("SDET direct hire")
    assert result["exclusions"]["exclude_consultancy"] is True


def test_need_sponsorship():
    """'need sponsorship' sets exclude_sponsorship."""
    result = parse_job_search_query("engineer need sponsorship")
    assert result["exclusions"]["exclude_sponsorship"] is True


def test_h1b_keyword():
    """'h1b' sets exclude_sponsorship (user needs H1B)."""
    result = parse_job_search_query("backend h1b")
    assert result["exclusions"]["exclude_sponsorship"] is True


# ── Combined queries ─────────────────────────────────

def test_full_combined_query():
    """Complete natural language query with all components."""
    result = parse_job_search_query("senior backend python Austin TX remote $150k+ no clearance")

    assert "senior" in result.get("title", "")
    assert "backend" in result.get("title", "")
    assert result["location"] == "Austin, TX"
    assert result["remote"] is True
    assert result["salary_min"] == 150000
    assert "python" in result.get("keywords", [])
    assert result["exclusions"]["exclude_clearance"] is True


def test_sdet_austin_query():
    """The user's actual use case: 'SDET in Austin TX'."""
    result = parse_job_search_query("SDET in Austin TX")
    assert result["title"] == "SDET"
    assert result["location"] == "Austin, TX"


def test_ml_engineer_remote_high_pay():
    """ML engineer remote with salary."""
    result = parse_job_search_query("ML engineer remote 120k-180k")
    assert result.get("title") is not None
    assert result["remote"] is True
    assert result["salary_min"] == 120000
    assert result["salary_max"] == 180000
