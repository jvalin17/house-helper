"""Shared URL fetcher — fetch and extract content from any URL.

Reusable across agents. Includes SSRF protection, timeout, and
content extraction via trafilatura/BeautifulSoup.
"""

import ipaddress
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from shared.app_logger import get_logger

logger = get_logger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; Panini/1.0)"
FETCH_TIMEOUT = 15.0


class FetchError(Exception):
    """Raised when URL fetching fails."""
    pass


class SSRFError(Exception):
    """Raised when URL targets a private/internal address."""
    pass


def validate_url_safety(url: str) -> None:
    """Check URL for SSRF — block localhost and private IPs."""
    hostname = urlparse(url).hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise SSRFError("Cannot fetch localhost URLs")
    try:
        resolved_ip = ipaddress.ip_address(hostname)
        if resolved_ip.is_private:
            raise SSRFError("Cannot fetch private/internal URLs")
    except ValueError:
        pass  # Domain name, not IP — that's fine


def fetch_page(url: str) -> str:
    """Fetch a URL and return raw HTML. Raises FetchError on failure."""
    validate_url_safety(url)
    logger.info("Fetching URL: %s", url)
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return response.text
    except SSRFError:
        raise
    except Exception as error:
        raise FetchError(f"Could not fetch URL: {error}")


def extract_text_from_page(html: str) -> str:
    """Extract main text content from HTML. Uses trafilatura with BS4 fallback."""
    try:
        import trafilatura
        extracted_text = trafilatura.extract(html)
        if extracted_text and len(extracted_text) > 50:
            return extracted_text
    except ImportError:
        pass

    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def extract_page_title(html: str) -> str:
    """Extract the page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    if heading and heading.get_text(strip=True):
        return heading.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        return title_tag.get_text(strip=True)
    return ""
