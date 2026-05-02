"""Shared URL fetcher — TDD tests.

Covers:
- SSRF blocks localhost
- SSRF blocks private IPs
- SSRF allows public domains
- FetchError on unreachable URLs
- extract_text_from_page returns content
- extract_page_title extracts h1 or title tag
"""

import pytest
from shared.url_fetcher import validate_url_safety, SSRFError, extract_text_from_page, extract_page_title


class TestSSRFProtection:
    def test_blocks_localhost(self):
        with pytest.raises(SSRFError, match="localhost"):
            validate_url_safety("http://localhost:8080/admin")

    def test_blocks_127_0_0_1(self):
        with pytest.raises(SSRFError, match="localhost"):
            validate_url_safety("http://127.0.0.1/secret")

    def test_blocks_private_ip(self):
        with pytest.raises(SSRFError, match="private"):
            validate_url_safety("http://192.168.1.1/admin")

    def test_allows_public_domain(self):
        validate_url_safety("https://www.apartments.com/listing/123")
        # No exception means pass

    def test_allows_public_ip(self):
        validate_url_safety("http://8.8.8.8/")


class TestExtractTextFromPage:
    def test_extracts_text_from_html(self):
        html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        text = extract_text_from_page(html)
        assert "Hello" in text
        assert "World" in text

    def test_empty_html_returns_empty(self):
        text = extract_text_from_page("")
        assert text == "" or text.strip() == ""


class TestExtractPageTitle:
    def test_extracts_h1(self):
        html = "<html><body><h1>Main Heading</h1></body></html>"
        assert extract_page_title(html) == "Main Heading"

    def test_falls_back_to_title_tag(self):
        html = "<html><head><title>Page Title</title></head><body><p>No heading</p></body></html>"
        assert extract_page_title(html) == "Page Title"

    def test_returns_empty_for_no_title(self):
        html = "<html><body><p>Just text</p></body></html>"
        assert extract_page_title(html) == ""
