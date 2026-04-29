"""Post-fetch job filtering based on user preferences.

Scans job descriptions for keywords related to:
- Visa sponsorship
- Security clearance
- Internship positions
"""

import json
import re

SPONSORSHIP_KEYWORDS = re.compile(
    r"visa\s+sponsor|sponsorship|authorized\s+to\s+work|"
    r"US\s+citizen\s+required|work\s+authorization\s+required|"
    r"must\s+be\s+authorized|permanent\s+resident",
    re.IGNORECASE,
)

CLEARANCE_KEYWORDS = re.compile(
    r"security\s+clearance|clearance\s+required|TS/SCI|"
    r"secret\s+clearance|top\s+secret|DoD\s+clearance",
    re.IGNORECASE,
)

INTERNSHIP_KEYWORDS = re.compile(
    r"\bintern\b|\binternship\b|co-?op\s+program|summer\s+program",
    re.IGNORECASE,
)


def filter_jobs_by_preferences(jobs: list[dict], preferences: dict) -> list[dict]:
    """Filter out jobs based on user's exclusion preferences."""
    if not preferences:
        return jobs

    exclude_sponsorship = preferences.get("exclude_sponsorship", False)
    exclude_clearance = preferences.get("exclude_clearance", False)
    exclude_internship = preferences.get("exclude_internship", False)

    if not (exclude_sponsorship or exclude_clearance or exclude_internship):
        return jobs

    result = []
    for job in jobs:
        description = _get_description(job)
        title = (job.get("title") or "").lower()

        if exclude_sponsorship and SPONSORSHIP_KEYWORDS.search(description):
            continue
        if exclude_clearance and CLEARANCE_KEYWORDS.search(description):
            continue
        if exclude_internship and (INTERNSHIP_KEYWORDS.search(description) or INTERNSHIP_KEYWORDS.search(title)):
            continue

        result.append(job)

    return result


def _get_description(job: dict) -> str:
    """Extract description text from job's parsed_data."""
    parsed = job.get("parsed_data", "{}")
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return parsed
    return parsed.get("description", "") if isinstance(parsed, dict) else ""
