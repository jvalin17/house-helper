"""Tests for scraping/parsers — regex/pattern-based job field extraction (no LLM)."""

from shared.scraping.parsers import parse_job_text


SAMPLE_JOB_TEXT = """
Software Engineer at BigTech

Location: San Francisco, CA (Remote OK)
Salary: $150,000 - $200,000

About the role:
We are looking for a Software Engineer to build scalable backend services.

Requirements:
- 3+ years of Python experience
- Experience with React and TypeScript
- Strong understanding of distributed systems
- BS in Computer Science or equivalent

Nice to have:
- Kubernetes experience
- AWS certification
"""


class TestParseJobText:
    """Extract structured fields from job posting text using patterns."""

    def test_returns_dict(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        assert isinstance(result, dict)

    def test_extracts_title(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        # Title extraction is best-effort from first line
        assert result.get("title") is not None

    def test_extracts_company(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        assert result.get("company") is not None

    def test_extracts_location(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        location = result.get("location", "")
        assert "San Francisco" in location or "Remote" in location

    def test_extracts_salary(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        salary = result.get("salary_range", "")
        assert "150" in salary or "$" in salary

    def test_extracts_skills(self):
        result = parse_job_text(SAMPLE_JOB_TEXT)
        skills = result.get("extracted_skills", [])
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_empty_text_returns_empty_fields(self):
        result = parse_job_text("")
        assert isinstance(result, dict)
        assert result.get("title") is None or result.get("title") == ""

    def test_minimal_text(self):
        result = parse_job_text("Python developer needed")
        assert isinstance(result, dict)
