"""HTML content extraction for job postings.

Uses trafilatura for main content extraction (strips nav, ads, footers)
with BeautifulSoup as fallback.
"""

from bs4 import BeautifulSoup
import trafilatura


def extract_text_from_html(html: str) -> str:
    """Extract main text content from HTML.

    Uses trafilatura first (best at isolating article/posting content),
    falls back to BeautifulSoup if trafilatura returns nothing.
    """
    if not html.strip():
        return ""

    # Try trafilatura first — best at stripping nav/footer/ads
    extracted = trafilatura.extract(html)
    if extracted:
        return extracted

    # Fallback: BeautifulSoup strips tags, returns all text
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def detect_input_type(user_input: str) -> str:
    """Detect whether user input is a URL or raw text.

    Returns 'url' or 'text'.
    """
    trimmed = user_input.strip()
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return "url"
    return "text"
