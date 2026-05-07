"""Natural language job search query parser.

Parses free-text queries like:
  "senior backend python Austin remote no clearance"
  "SDET in Austin TX"
  "ML engineer $150k+ remote"
  "react developer new york 120k-180k"

Into structured search filters:
  title, location, keywords, remote, salary_min, salary_max, exclusions

Algorithmic approach — no LLM needed. Pattern matching + keyword extraction.
"""

import re

# ── Location patterns ─────────────────────────────────

# US state abbreviations (uppercase)
US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
})

# Common US cities (for detection without state)
KNOWN_CITIES = frozenset({
    "austin", "dallas", "houston", "san antonio", "san francisco",
    "los angeles", "new york", "chicago", "seattle", "denver",
    "boston", "atlanta", "miami", "portland", "phoenix",
    "san diego", "san jose", "raleigh", "charlotte", "nashville",
    "minneapolis", "detroit", "philadelphia", "pittsburgh",
    "tampa", "orlando", "columbus", "indianapolis", "salt lake city",
    "boulder", "ann arbor", "palo alto", "mountain view", "cupertino",
    "redmond", "bellevue", "brooklyn", "manhattan",
})

# Pattern: "City, ST" or "City ST" or "in City"
LOCATION_PATTERN = re.compile(
    r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,?\s*[A-Z]{2})?)\b|"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b",
)

# ── Salary patterns ───────────────────────────────────

SALARY_PATTERN = re.compile(
    r"\$(\d{2,3})k?\s*[-–to]+\s*\$?(\d{2,3})k|"      # $120k-180k or $120-180k
    r"\$(\d{2,3})k?\+|"                                  # $150k+
    r"(\d{2,3})k\s*[-–to]+\s*(\d{2,3})k|"              # 120k-180k
    r"(\d{2,3})k\+",                                     # 150k+
    re.IGNORECASE,
)

# ── Remote patterns ───────────────────────────────────

REMOTE_KEYWORDS = frozenset({"remote", "wfh", "work from home", "fully remote", "100% remote"})
HYBRID_KEYWORDS = frozenset({"hybrid", "onsite", "on-site", "in-office", "in office"})

# ── Exclusion patterns ────────────────────────────────

EXCLUSION_PATTERNS = {
    "exclude_clearance": re.compile(r"\bno\s+clearance\b|\bwithout\s+clearance\b|\bno\s+security\b", re.IGNORECASE),
    "exclude_citizenship": re.compile(r"\bno\s+citizenship\b|\bno\s+us\s+citizen\b", re.IGNORECASE),
    "exclude_consultancy": re.compile(r"\bno\s+consult\w*\b|\bno\s+staffing\b|\bdirect\s+hire\b|\bno\s+agencies?\b", re.IGNORECASE),
    "exclude_internship": re.compile(r"\bno\s+intern\w*\b|\bfull[\s-]?time\s+only\b", re.IGNORECASE),
    "exclude_sponsorship": re.compile(r"\bneed\s+sponsor\w*\b|\bvisa\s+sponsor\w*\b|\bh1b\b", re.IGNORECASE),
}

# ── Seniority keywords (kept in title) ────────────────

SENIORITY_KEYWORDS = frozenset({
    "senior", "sr", "junior", "jr", "lead", "principal", "staff",
    "mid", "mid-level", "entry", "entry-level", "architect",
    "manager", "director", "vp", "head",
})

# ── Tech skills (extracted as keywords) ───────────────

TECH_SKILLS = frozenset({
    "python", "java", "javascript", "typescript", "react", "angular",
    "vue", "node", "nodejs", "go", "golang", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "aws", "azure", "gcp",
    "docker", "kubernetes", "k8s", "terraform", "jenkins", "ci/cd",
    "sql", "nosql", "mongodb", "postgres", "postgresql", "mysql",
    "redis", "kafka", "spark", "hadoop", "elasticsearch",
    "machine learning", "ml", "ai", "deep learning", "nlp",
    "data science", "data engineering", "devops", "sre",
    "microservices", "rest", "graphql", "grpc",
    "selenium", "cypress", "playwright", "appium", "jmeter",
    "pytest", "junit", "testng",
})


def parse_job_search_query(query: str) -> dict:
    """Parse a natural language job search query into structured filters.

    Returns a dict compatible with the search endpoint:
      title, location, keywords, remote, salary_min, salary_max, exclusions

    Examples:
      "senior backend python Austin TX remote" →
        {title: "senior backend", location: "Austin, TX", keywords: ["python"], remote: True}

      "SDET $120k+ no clearance" →
        {title: "SDET", salary_min: 120000, exclusions: {exclude_clearance: True}}
    """
    if not query or not query.strip():
        return {}

    original_query = query.strip()
    remaining_text = original_query
    result: dict = {}

    # 1. Extract exclusions (remove from text)
    exclusions = {}
    for exclusion_key, pattern in EXCLUSION_PATTERNS.items():
        match = pattern.search(remaining_text)
        if match:
            exclusions[exclusion_key] = True
            remaining_text = remaining_text[:match.start()] + remaining_text[match.end():]
    if exclusions:
        result["exclusions"] = exclusions

    # 2. Extract salary (remove from text)
    salary_match = SALARY_PATTERN.search(remaining_text)
    if salary_match:
        salary_min, salary_max = _extract_salary(salary_match)
        if salary_min:
            result["salary_min"] = salary_min
        if salary_max:
            result["salary_max"] = salary_max
        remaining_text = remaining_text[:salary_match.start()] + remaining_text[salary_match.end():]

    # 3. Extract remote/hybrid (remove from text)
    remaining_lower = remaining_text.lower()
    for remote_keyword in REMOTE_KEYWORDS:
        if remote_keyword in remaining_lower:
            result["remote"] = True
            remaining_text = re.sub(re.escape(remote_keyword), "", remaining_text, flags=re.IGNORECASE).strip()
            break

    # 4. Extract location (remove from text)
    location = _extract_location(remaining_text)
    if location:
        result["location"] = location
        # Remove location from remaining text
        remaining_text = _remove_location_from_text(remaining_text, location)

    # 5. Split remaining into title vs keywords
    remaining_words = remaining_text.split()
    remaining_words = [word for word in remaining_words if word.strip() and word.lower() not in ("in", "at", "for", "the", "a", "an", "and", "or", "with")]

    title_parts = []
    keyword_parts = []

    for word in remaining_words:
        word_lower = word.lower().strip(".,;:")
        if word_lower in TECH_SKILLS or (len(word_lower) > 1 and word_lower in TECH_SKILLS):
            keyword_parts.append(word_lower)
        else:
            title_parts.append(word)

    if title_parts:
        result["title"] = " ".join(title_parts).strip()
    if keyword_parts:
        result["keywords"] = keyword_parts

    return result


def _extract_salary(match: re.Match) -> tuple[int | None, int | None]:
    """Extract salary range from regex match groups."""
    groups = match.groups()

    # $120k-180k pattern
    if groups[0] and groups[1]:
        return int(groups[0]) * 1000, int(groups[1]) * 1000
    # $150k+ pattern
    if groups[2]:
        return int(groups[2]) * 1000, None
    # 120k-180k pattern (no $)
    if groups[3] and groups[4]:
        return int(groups[3]) * 1000, int(groups[4]) * 1000
    # 150k+ pattern (no $)
    if groups[5]:
        return int(groups[5]) * 1000, None

    return None, None


def _extract_location(text: str) -> str | None:
    """Extract location from text using patterns and known cities."""
    # Try "City, ST" pattern first
    city_state_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z]{2})\b", text)
    if city_state_match:
        state_code = city_state_match.group(2)
        if state_code in US_STATES:
            return f"{city_state_match.group(1)}, {state_code}"

    # Try "in City" pattern
    in_city_match = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
    if in_city_match:
        city_candidate = in_city_match.group(1)
        if city_candidate.lower() in KNOWN_CITIES:
            return city_candidate

    # Try known city names anywhere in text
    text_lower = text.lower()
    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        if city in text_lower:
            # Find the original case version
            start_index = text_lower.index(city)
            original_case = text[start_index:start_index + len(city)]
            return original_case.title()

    return None


def _remove_location_from_text(text: str, location: str) -> str:
    """Remove the detected location from the text, including 'in' prefix."""
    # Try removing "in Location"
    cleaned = re.sub(r"\bin\s+" + re.escape(location), "", text, flags=re.IGNORECASE)
    if cleaned != text:
        return cleaned.strip()

    # Try removing just the location
    cleaned = re.sub(re.escape(location), "", text, flags=re.IGNORECASE)

    # Also try removing individual location parts (city name, state code)
    for part in location.replace(",", "").split():
        if len(part) >= 2:
            cleaned = re.sub(r"\b" + re.escape(part) + r"\b", "", cleaned, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", cleaned).strip()
