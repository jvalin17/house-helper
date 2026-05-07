"""Job filter — tests for post-fetch filtering by preferences.

Covers: clearance, citizenship, sponsorship, internship, consultancy filters.
Uses realistic job data with actual company names and description patterns.
"""

import pytest

from agents.job.services.job_filter import (
    filter_jobs_by_preferences,
    _is_staffing_company,
)


# ── Realistic job fixtures ────────────────────────────

DIRECT_HIRE_JOB = {
    "title": "Senior SDET",
    "company": "Apple",
    "description": "We are looking for a Senior SDET to join our team. "
                   "Experience with Python, Java, and CI/CD pipelines required. "
                   "Competitive salary and benefits.",
}

CLEARANCE_JOB = {
    "title": "Software Engineer - Defense Systems",
    "company": "Raytheon",
    "description": "Active TS/SCI security clearance required. "
                   "Must have experience with embedded systems.",
}

CITIZENSHIP_JOB = {
    "title": "Backend Engineer",
    "company": "Palantir",
    "description": "This position requires US citizenship. "
                   "Must be a US citizen due to government contract requirements.",
}

NO_SPONSOR_JOB = {
    "title": "Full Stack Developer",
    "company": "Startup Corp",
    "description": "Candidates must be authorized to work in the US. "
                   "We cannot sponsor visas at this time.",
}

INTERNSHIP_JOB = {
    "title": "Software Engineering Intern - Summer 2026",
    "company": "Google",
    "description": "Join us for a 12-week summer program. "
                   "This internship is for students pursuing a CS degree.",
}

CONSULTANCY_JOB_INFOSYS = {
    "title": "Java Developer",
    "company": "Infosys Limited",
    "description": "Infosys is looking for a Java Developer to work on client projects.",
}

CONSULTANCY_JOB_WIPRO = {
    "title": "QA Engineer",
    "company": "Wipro Technologies",
    "description": "Join Wipro's quality engineering practice.",
}

CONSULTANCY_JOB_TCS = {
    "title": "Python Developer",
    "company": "TCS (Tata Consultancy Services)",
    "description": "TCS is hiring Python developers for a banking client.",
}

STAFFING_AGENCY_JOB = {
    "title": "React Developer",
    "company": "Creative Solutions LLC",
    "description": "We are a staffing agency looking for a React developer "
                   "on behalf of our client, a Fortune 500 company. Contract to hire.",
}

STAFFING_DESCRIPTION_JOB = {
    "title": "DevOps Engineer",
    "company": "TechBridge Inc",
    "description": "C2C or W2 contract available. Our client is seeking "
                   "a DevOps engineer for a 12-month consulting engagement.",
}

ALL_JOBS = [
    DIRECT_HIRE_JOB, CLEARANCE_JOB, CITIZENSHIP_JOB, NO_SPONSOR_JOB,
    INTERNSHIP_JOB, CONSULTANCY_JOB_INFOSYS, CONSULTANCY_JOB_WIPRO,
    CONSULTANCY_JOB_TCS, STAFFING_AGENCY_JOB, STAFFING_DESCRIPTION_JOB,
]


# ── No filters = all jobs pass ────────────────────────

def test_no_preferences_returns_all_jobs():
    """With empty preferences, all jobs pass through."""
    result = filter_jobs_by_preferences(ALL_JOBS, {})
    assert len(result) == len(ALL_JOBS)


def test_none_preferences_returns_all_jobs():
    """With None preferences, all jobs pass through."""
    result = filter_jobs_by_preferences(ALL_JOBS, None)
    assert len(result) == len(ALL_JOBS)


# ── Clearance filter ─────────────────────────────────

def test_exclude_clearance_removes_clearance_jobs():
    """Clearance filter removes TS/SCI and 'clearance required' jobs."""
    result = filter_jobs_by_preferences(ALL_JOBS, {"exclude_clearance": True})
    company_names = [job["company"] for job in result]
    assert "Raytheon" not in company_names
    assert "Apple" in company_names


def test_exclude_clearance_keeps_non_clearance_jobs():
    """Clearance filter keeps regular jobs untouched."""
    result = filter_jobs_by_preferences(
        [DIRECT_HIRE_JOB, CITIZENSHIP_JOB],
        {"exclude_clearance": True},
    )
    assert len(result) == 2


# ── Citizenship filter ───────────────────────────────

def test_exclude_citizenship_removes_us_citizen_required():
    """Citizenship filter removes 'US citizenship required' jobs."""
    result = filter_jobs_by_preferences(ALL_JOBS, {"exclude_citizenship": True})
    company_names = [job["company"] for job in result]
    assert "Palantir" not in company_names
    assert "Apple" in company_names


# ── Sponsorship filter ───────────────────────────────

def test_exclude_sponsorship_removes_no_sponsor_jobs():
    """Sponsorship filter removes 'cannot sponsor' jobs."""
    result = filter_jobs_by_preferences(ALL_JOBS, {"exclude_sponsorship": True})
    company_names = [job["company"] for job in result]
    assert "Startup Corp" not in company_names
    assert "Apple" in company_names


# ── Internship filter ────────────────────────────────

def test_exclude_internship_removes_intern_positions():
    """Internship filter removes intern/co-op jobs by title and description."""
    result = filter_jobs_by_preferences(ALL_JOBS, {"exclude_internship": True})
    titles = [job["title"] for job in result]
    assert not any("Intern" in title for title in titles)
    assert "Senior SDET" in titles


# ── Consultancy filter ───────────────────────────────

def test_exclude_consultancy_removes_known_staffing_companies():
    """Consultancy filter removes Infosys, Wipro, TCS by company name."""
    result = filter_jobs_by_preferences(ALL_JOBS, {"exclude_consultancy": True})
    company_names = [job["company"] for job in result]
    assert "Infosys Limited" not in company_names
    assert "Wipro Technologies" not in company_names
    assert "TCS (Tata Consultancy Services)" not in company_names
    assert "Apple" in company_names


def test_exclude_consultancy_catches_staffing_description():
    """Consultancy filter catches 'staffing agency' and 'C2C' in description."""
    result = filter_jobs_by_preferences(
        [DIRECT_HIRE_JOB, STAFFING_AGENCY_JOB, STAFFING_DESCRIPTION_JOB],
        {"exclude_consultancy": True},
    )
    assert len(result) == 1
    assert result[0]["company"] == "Apple"


def test_exclude_consultancy_keeps_direct_hire():
    """Consultancy filter preserves direct-hire jobs from real companies."""
    result = filter_jobs_by_preferences(
        [DIRECT_HIRE_JOB, {"title": "ML Engineer", "company": "Netflix", "description": "Join our ML team."}],
        {"exclude_consultancy": True},
    )
    assert len(result) == 2


# ── Multiple filters combined ────────────────────────

def test_all_filters_combined():
    """All filters active removes clearance + citizenship + sponsorship + intern + consultancy."""
    result = filter_jobs_by_preferences(ALL_JOBS, {
        "exclude_clearance": True,
        "exclude_citizenship": True,
        "exclude_sponsorship": True,
        "exclude_internship": True,
        "exclude_consultancy": True,
    })
    # Only Apple direct-hire should survive
    assert len(result) == 1
    assert result[0]["company"] == "Apple"


# ── _is_staffing_company helper ──────────────────────

def test_is_staffing_infosys():
    assert _is_staffing_company("infosys limited", "") is True

def test_is_staffing_wipro():
    assert _is_staffing_company("wipro technologies", "") is True

def test_is_staffing_apple():
    assert _is_staffing_company("apple", "") is False

def test_is_staffing_description_pattern():
    assert _is_staffing_company("unknown corp", "we are a staffing agency recruiting for...") is True

def test_is_staffing_c2c_pattern():
    assert _is_staffing_company("techbridge", "C2C or W2 contract available for this role") is True

def test_is_staffing_empty_company():
    assert _is_staffing_company("", "some description") is False
