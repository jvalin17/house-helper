"""Regex/pattern-based job field extraction from plain text.

This is the no-LLM fallback for parsing job postings.
Extracts common fields using patterns found in typical job postings.
"""

import re

from shared.algorithms.entity_extractor import extract_skills_from_text

LOCATION_PATTERN = re.compile(
    r"(?:Location|Based in|Office)\s*[:]\s*(.+)",
    re.IGNORECASE,
)

SALARY_PATTERN = re.compile(
    r"\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?(?:\s*/\s*(?:year|yr|annually))?",
    re.IGNORECASE,
)

REMOTE_PATTERN = re.compile(
    r"\b(remote|hybrid|on-site|onsite)\b",
    re.IGNORECASE,
)

# "Title at Company" or "Title - Company" on the first non-empty line
TITLE_COMPANY_PATTERN = re.compile(
    r"^(.+?)\s+(?:at|[-–@])\s+(.+)$",
)


def parse_job_text(text: str) -> dict:
    """Extract structured fields from job posting text using regex patterns.

    Returns dict with: title, company, location, salary_range,
    remote_status, extracted_skills.
    """
    if not text.strip():
        return {
            "title": None,
            "company": None,
            "location": None,
            "salary_range": None,
            "remote_status": None,
            "extracted_skills": [],
        }

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    title, company = _extract_title_company(lines)
    location = _extract_location(text)
    salary_range = _extract_salary(text)
    remote_status = _extract_remote_status(text)
    skills = extract_skills_from_text(text)

    return {
        "title": title,
        "company": company,
        "location": location,
        "salary_range": salary_range,
        "remote_status": remote_status,
        "extracted_skills": skills,
    }


def _extract_title_company(lines: list[str]) -> tuple[str | None, str | None]:
    """Try to extract title and company from the first line."""
    if not lines:
        return None, None

    first_line = lines[0]
    match = TITLE_COMPANY_PATTERN.match(first_line)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # If no "at/- Company" pattern, first line is likely just the title
    return first_line, None


def _extract_location(text: str) -> str | None:
    match = LOCATION_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def _extract_salary(text: str) -> str | None:
    match = SALARY_PATTERN.search(text)
    if match:
        return match.group(0).strip()
    return None


def _extract_remote_status(text: str) -> str | None:
    match = REMOTE_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    return None
