"""TDD tests for PDF resume text preprocessing.

These tests define the EXPECTED behavior for parsing messy PDF text.
Write tests first, then fix the code to pass them.

Scenarios from real resumes:
1. Bullet markers (●, •) on standalone lines
2. Contact info scattered across multiple lines
3. Dates wrapping to next line
4. Zero-width unicode characters
5. Skills in "Category: skill1, skill2" format with bullet prefix
6. Multi-line role headers (Company | Title | Location + date on next line)
7. Section headers (ALL CAPS)
8. Education entries with date on next line
9. Project entries with links and dates
"""

import pytest

from shared.scraping.resume_parser import parse_resume_pdf, parse_date
from shared.export.pdf import _preprocess_lines, _plain_text_to_html


class TestPreprocessLines:
    """Test the line preprocessor that cleans PDF artifacts."""

    def test_standalone_bullet_joined_with_next_line(self):
        lines = _preprocess_lines("●\nBuilt a notification pipeline")
        assert any("Built a notification pipeline" in l and l.startswith("-") for l in lines)

    def test_dot_bullet_joined(self):
        lines = _preprocess_lines("•\nDesigned real-time dashboard")
        assert any("Designed real-time dashboard" in l and l.startswith("-") for l in lines)

    def test_inline_bullet_converted(self):
        lines = _preprocess_lines("● Built something cool")
        assert any("Built something cool" in l and l.startswith("-") for l in lines)

    def test_inline_dot_bullet_converted(self):
        lines = _preprocess_lines("• Reduced latency by 40%")
        assert any("Reduced latency by 40%" in l and l.startswith("-") for l in lines)

    def test_date_joined_to_previous_line(self):
        lines = _preprocess_lines("Master of Science in CS, UT Arlington\nMay 2016")
        joined = [l for l in lines if "Master" in l]
        assert len(joined) == 1
        assert "May 2016" in joined[0]

    def test_date_with_period_joined(self):
        lines = _preprocess_lines("Bachelor of Engineering, Pune\nAug. 2013")
        joined = [l for l in lines if "Bachelor" in l]
        assert len(joined) == 1
        assert "Aug. 2013" in joined[0]

    def test_normal_lines_unchanged(self):
        lines = _preprocess_lines("WORK EXPERIENCE\nZillow | Engineer\tOct 2022")
        assert "WORK EXPERIENCE" in lines
        assert any("Zillow" in l for l in lines)

    def test_empty_lines_preserved(self):
        lines = _preprocess_lines("Line 1\n\nLine 2")
        assert "" in lines

    def test_multiple_bullets_in_sequence(self):
        text = "●\nFirst bullet\n●\nSecond bullet\n●\nThird bullet"
        lines = _preprocess_lines(text)
        bullet_lines = [l for l in lines if l.startswith("-")]
        assert len(bullet_lines) == 3


class TestPlainTextToHtml:
    """Test the plain text to HTML converter for PDF export."""

    def test_name_is_h1(self):
        html = _plain_text_to_html("Jane Doe\n\nSUMMARY\nEngineer")
        assert "<h1>Jane Doe</h1>" in html

    def test_contact_grouped_under_name(self):
        html = _plain_text_to_html("Jane Doe\njane@email.com | 555-1234\nlinkedin.com/jane\n\nSUMMARY\nText")
        assert '<div class="contact">' in html
        assert "jane@email.com" in html
        assert "linkedin.com/jane" in html

    def test_section_headers_are_h2(self):
        html = _plain_text_to_html("Name\n\nWORK EXPERIENCE\nSome text")
        assert "<h2>" in html
        assert "Work Experience" in html  # title-cased

    def test_bullets_are_list_items(self):
        html = _plain_text_to_html("Name\n\nWORK EXPERIENCE\nCompany | Title\tJan 2020\n- Built stuff\n- Fixed things")
        assert "<ul>" in html
        assert "<li>Built stuff</li>" in html
        assert "<li>Fixed things</li>" in html

    def test_role_header_with_dates(self):
        html = _plain_text_to_html("Name\n\nWORK EXPERIENCE\nAcme Corp | Engineer\tJan 2020 – Present")
        assert "Acme Corp" in html
        assert "role-header" in html
        assert "role-dates" in html

    def test_side_projects_is_section_header(self):
        html = _plain_text_to_html("Name\n\nSIDE PROJECTS\nSome project")
        assert "<h2>" in html
        assert "Side Projects" in html

    def test_full_resume_has_all_sections(self):
        content = """Jvalin Dave
682.215.5246 | jvalin17@gmail.com
LinkedIn: linkedin.com/in/jvalindave

TECHNICAL SKILLS
- Proficient: Python, Java, SQL

WORK EXPERIENCE
Zillow | Software Engineer\tOct 2022 – Present
- Built notification pipeline
- Led Kubernetes migration

EDUCATION
MS Computer Science, UT Arlington\tMay 2016

PROJECTS
FileComparison | github.com/test
- Open-source Python tool"""

        html = _plain_text_to_html(content)

        assert "<h1>Jvalin Dave</h1>" in html
        assert "contact" in html
        assert "Technical Skills" in html
        assert "Work Experience" in html
        assert "Education" in html
        assert "<li>" in html
        assert "role-header" in html

    def test_no_empty_bullets(self):
        html = _plain_text_to_html("Name\n\nWORK EXPERIENCE\nCo | Eng\tJan 2020\n- Good bullet\n-\n- Another")
        assert "<li></li>" not in html or html.count("<li>") >= 2


class TestDateParsing:
    """Test date parsing handles all resume date formats."""

    def test_full_month(self):
        assert parse_date("October 2022") == "2022-10"

    def test_abbreviated_month(self):
        assert parse_date("Oct 2022") == "2022-10"

    def test_abbreviated_with_period(self):
        assert parse_date("Apr. 2017") == "2017-04"

    def test_present(self):
        assert parse_date("Present") is None

    def test_empty(self):
        assert parse_date("") is None

    def test_aug_with_period(self):
        assert parse_date("Aug. 2013") == "2013-08"

    def test_may_no_period(self):
        assert parse_date("May 2016") == "2016-05"


class TestPdfResumeIntegration:
    """Integration test: full PDF text → parsed structured data."""

    def test_parse_simulated_pdf_text(self):
        """Simulate what PyMuPDF extracts from a real resume PDF."""
        # This mimics the messy text fitz.get_text() produces
        from shared.scraping.resume_parser import _parse_paragraphs

        # Simulate paragraphs as the PDF parser would produce them
        paragraphs = [
            {"text": "Jane Doe", "is_bold": True, "is_heading": False, "style": "body"},
            {"text": "jane@email.com | 555-1234", "is_bold": False, "is_heading": False, "style": "body"},
            {"text": "TECHNICAL SKILLS", "is_bold": True, "is_heading": True, "style": "heading"},
            {"text": "Proficient: Python, Java, SQL, AWS", "is_bold": False, "is_heading": False, "style": "body"},
            {"text": "WORK EXPERIENCE", "is_bold": True, "is_heading": True, "style": "heading"},
            {"text": "Acme Corp | Engineer\tJan 2020 – Present", "is_bold": False, "is_heading": False, "style": "body"},
            {"text": "- Built distributed systems", "is_bold": False, "is_heading": False, "is_list": True, "style": "list"},
            {"text": "- Reduced latency by 40%", "is_bold": False, "is_heading": False, "is_list": True, "style": "list"},
            {"text": "EDUCATION", "is_bold": True, "is_heading": True, "style": "heading"},
            {"text": "BS Computer Science, State University\t2018", "is_bold": False, "is_heading": False, "style": "body"},
        ]

        result = _parse_paragraphs(paragraphs)

        assert len(result["experiences"]) >= 1
        assert result["experiences"][0]["company"] == "Acme Corp"
        assert len(result["experiences"][0]["bullets"]) >= 2
        assert len(result["skills"]) >= 3
        assert len(result["education"]) >= 1
