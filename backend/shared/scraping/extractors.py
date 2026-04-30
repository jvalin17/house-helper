"""HTML content extraction for job postings.

Uses JSON-LD structured data first (most reliable for job boards),
then trafilatura, then BeautifulSoup as fallback.
"""

import json

from bs4 import BeautifulSoup
import trafilatura


def extract_text_from_html(html: str) -> str:
    """Extract main text content from HTML.

    Priority: JSON-LD → trafilatura → BeautifulSoup.
    """
    if not html.strip():
        return ""

    # Try JSON-LD first — many job boards embed structured data
    jsonld_text = _extract_from_jsonld(html)
    if jsonld_text:
        return jsonld_text

    # Try trafilatura — best at stripping nav/footer/ads
    extracted = trafilatura.extract(html)
    if extracted:
        return extracted

    # Fallback: BeautifulSoup strips tags, returns all text
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def extract_job_from_jsonld(html: str) -> dict | None:
    """Extract structured job data from JSON-LD script tags.

    Returns dict with title, company, description, location, or None.
    """
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        # Look for JobPosting schema
        if data.get("@type") == "JobPosting" or data.get("title"):
            desc_html = data.get("description", "")
            description_soup = BeautifulSoup(desc_html, "html.parser")
            description = description_soup.get_text("\n", strip=True)

            company = ""
            hiring_org = data.get("hiringOrganization", {})
            if isinstance(hiring_org, dict):
                company = hiring_org.get("name", "")

            locations = []
            job_location = data.get("jobLocation", [])
            if isinstance(job_location, dict):
                job_location = [job_location]
            for loc in job_location:
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    parts = [addr.get("addressLocality", ""), addr.get("addressRegion", "")]
                    locations.append(", ".join(p for p in parts if p))

            return {
                "title": data.get("title", ""),
                "company": company,
                "description": description,
                "locations": locations,
            }

    return None


def _extract_from_jsonld(html: str) -> str | None:
    """Extract text description from JSON-LD if available."""
    result = extract_job_from_jsonld(html)
    if result and result.get("description"):
        parts = []
        if result["title"]:
            parts.append(result["title"])
        if result["company"]:
            parts.append(f"at {result['company']}")
        if result["locations"]:
            parts.append(f"Location: {'; '.join(result['locations'])}")
        parts.append("")
        parts.append(result["description"])
        return "\n".join(parts)
    return None


def detect_input_type(user_input: str) -> str:
    """Detect whether user input is a URL or raw text.

    Returns 'url' or 'text'.
    """
    trimmed = user_input.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return "url"
    return "text"
