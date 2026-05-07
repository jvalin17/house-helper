"""Post-fetch job filtering based on user preferences.

Scans job descriptions and company names for keywords related to:
- Visa sponsorship requirements
- Security clearance requirements
- Internship positions
- Consultancy / staffing agencies
"""

import json
import re

# Jobs that WON'T sponsor — filter these out when user requires sponsorship
NO_SPONSORSHIP_KEYWORDS = re.compile(
    r"authorized\s+to\s+work|US\s+citizen(s)?\s+required|"
    r"work\s+authorization\s+required|must\s+be\s+authorized|"
    r"permanent\s+resident\s+required|cannot\s+sponsor|"
    r"no\s+visa\s+sponsor|not\s+sponsor|without\s+sponsor|"
    r"eligibility\s+to\s+work\s+in\s+the\s+US|"
    r"US\s+work\s+authorization\s+required",
    re.IGNORECASE,
)

CLEARANCE_KEYWORDS = re.compile(
    r"security\s+clearance|clearance\s+required|TS/SCI|"
    r"secret\s+clearance|top\s+secret|DoD\s+clearance|"
    r"must\s+have\s+clearance|active\s+clearance|"
    r"public\s+trust\s+clearance|SCI\s+eligible",
    re.IGNORECASE,
)

CITIZENSHIP_KEYWORDS = re.compile(
    r"US\s+citizen(s)?\s+only|must\s+be\s+(a\s+)?US\s+citizen|"
    r"U\.?S\.?\s+citizenship\s+required|citizen(ship)?\s+required|"
    r"only\s+US\s+citizens|green\s+card\s+holder",
    re.IGNORECASE,
)

INTERNSHIP_KEYWORDS = re.compile(
    r"\bintern\b|\binternship\b|co-?op\s+program|summer\s+program",
    re.IGNORECASE,
)

# Staffing agencies / consultancies — matched against company name (case-insensitive)
STAFFING_COMPANY_NAMES = frozenset({
    "infosys", "wipro", "tcs", "tata consultancy", "cognizant",
    "accenture", "hcl", "hcltech", "tech mahindra", "capgemini",
    "randstad", "robert half", "teksystems", "insight global",
    "apex systems", "kforce", "manpower", "kelly services", "adecco",
    "cgi", "mindtree", "mphasis", "ltimindtree", "ust",
    "persistent systems", "hexaware", "cyient", "niit", "syntel",
    "collabera", "revature", "virtusa", "zensar", "birlasoft",
    "l&t infotech", "coforge", "mastech", "igate", "mphasis",
    "hays", "michael page", "spencer stuart", "aerotek",
    "staffing", "consulting group", "solutions inc", "solutions llc",
    "tek systems", "global solutions", "infotech",
})

STAFFING_DESCRIPTION_KEYWORDS = re.compile(
    r"(we\s+are\s+a\s+staffing|staffing\s+agency|staffing\s+company|"
    r"on\s+behalf\s+of\s+our\s+client|our\s+client\s+is\s+(looking|seeking)|"
    r"contract\s+to\s+hire|c2c|corp[\s-]to[\s-]corp|w2\s+contract|"
    r"third[\s-]party\s+vendor|consulting\s+engagement)",
    re.IGNORECASE,
)


def filter_jobs_by_preferences(jobs: list[dict], preferences: dict) -> list[dict]:
    """Filter out jobs based on user's exclusion preferences.

    Supported preferences:
      exclude_sponsorship — hide jobs that won't sponsor visa
      exclude_clearance   — hide jobs requiring security clearance
      exclude_citizenship — hide jobs requiring US citizenship
      exclude_internship  — hide internship/co-op positions
      exclude_consultancy — hide staffing agency / consultancy postings
    """
    if not preferences:
        return jobs

    exclude_sponsorship = preferences.get("exclude_sponsorship", False)
    exclude_clearance = preferences.get("exclude_clearance", False)
    exclude_citizenship = preferences.get("exclude_citizenship", False)
    exclude_internship = preferences.get("exclude_internship", False)
    exclude_consultancy = preferences.get("exclude_consultancy", False)

    active_filters = (
        exclude_sponsorship or exclude_clearance or exclude_citizenship
        or exclude_internship or exclude_consultancy
    )
    if not active_filters:
        return jobs

    result = []
    for job in jobs:
        description = _get_description(job)
        title = (job.get("title") or "").lower()
        company = (job.get("company") or "").lower().strip()

        if exclude_sponsorship and NO_SPONSORSHIP_KEYWORDS.search(description):
            continue
        if exclude_clearance and CLEARANCE_KEYWORDS.search(description):
            continue
        if exclude_citizenship and CITIZENSHIP_KEYWORDS.search(description):
            continue
        if exclude_internship and (INTERNSHIP_KEYWORDS.search(description) or INTERNSHIP_KEYWORDS.search(title)):
            continue
        if exclude_consultancy and _is_staffing_company(company, description):
            continue

        result.append(job)

    return result


def _is_staffing_company(company_name: str, description: str) -> bool:
    """Check if job is from a staffing agency / consultancy.

    Matches by company name (exact or substring) and description keywords.
    """
    if not company_name:
        return False

    # Check company name against known staffing firms
    for staffing_name in STAFFING_COMPANY_NAMES:
        if staffing_name in company_name:
            return True

    # Check description for staffing patterns
    if STAFFING_DESCRIPTION_KEYWORDS.search(description):
        return True

    return False


def _get_description(job: dict) -> str:
    """Extract description text from a job dict.

    Different code paths shape jobs differently:
    - DB rows expose ``parsed_data`` (a JSON string or dict with a ``description`` key).
    - In-flight search results may expose ``description`` directly.
    """
    direct = job.get("description")
    if isinstance(direct, str) and direct:
        return direct

    parsed = job.get("parsed_data", "{}")
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return parsed
    return parsed.get("description", "") if isinstance(parsed, dict) else ""
