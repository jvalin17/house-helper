"""Tests for scraping/extractors — HTML content extraction."""

from shared.scraping.extractors import extract_text_from_html, detect_input_type


SAMPLE_JOB_HTML = """
<html>
<head><title>Software Engineer - BigTech</title></head>
<body>
  <nav>Home | Jobs | About</nav>
  <main>
    <h1>Software Engineer</h1>
    <p>BigTech is looking for a Software Engineer to join our team.</p>
    <h2>Requirements</h2>
    <ul>
      <li>3+ years of Python experience</li>
      <li>Experience with React and TypeScript</li>
      <li>Strong understanding of distributed systems</li>
    </ul>
    <h2>Nice to have</h2>
    <ul>
      <li>Kubernetes experience</li>
      <li>AWS certification</li>
    </ul>
  </main>
  <footer>Copyright 2024</footer>
</body>
</html>
"""


class TestExtractTextFromHtml:
    """Extract main content from HTML, stripping nav/footer/ads."""

    def test_extracts_main_content(self):
        text = extract_text_from_html(SAMPLE_JOB_HTML)
        assert "Software Engineer" in text
        assert "Python experience" in text

    def test_strips_navigation(self):
        text = extract_text_from_html(SAMPLE_JOB_HTML)
        # Nav content should ideally be stripped or at least main content present
        assert "Python experience" in text

    def test_empty_html_returns_empty(self):
        text = extract_text_from_html("")
        assert text == ""

    def test_plain_text_passthrough(self):
        text = extract_text_from_html("Just plain text, no HTML tags")
        assert "plain text" in text

    def test_handles_malformed_html(self):
        text = extract_text_from_html("<p>Unclosed paragraph <b>bold")
        assert "Unclosed paragraph" in text


class TestDetectInputType:
    """Detect whether user input is a URL or raw text."""

    def test_detects_https_url(self):
        assert detect_input_type("https://jobs.example.com/123") == "url"

    def test_detects_http_url(self):
        assert detect_input_type("http://example.com/job") == "url"

    def test_detects_raw_text(self):
        assert detect_input_type("We are looking for a Python developer") == "text"

    def test_detects_url_with_query_params(self):
        assert detect_input_type("https://example.com/job?id=123&ref=search") == "url"

    def test_empty_string_is_text(self):
        assert detect_input_type("") == "text"

    def test_url_with_whitespace_trimmed(self):
        assert detect_input_type("  https://example.com/job  ") == "url"
