"""Tests for resume_parser — extract structured data from DOCX resumes.

Uses the user's actual resume as a test fixture.
"""

import pytest
from pathlib import Path

from shared.scraping.resume_parser import parse_resume_docx, detect_sections, parse_experience_entry, parse_date

RESUME_PATH = Path(__file__).parent / "fixtures" / "test_resume.docx"

skip_no_resume = pytest.mark.skipif(
    not RESUME_PATH.exists(),
    reason="Test resume not available at expected path",
)


class TestParseDate:
    """Extract normalized dates from various formats."""

    def test_month_year(self):
        assert parse_date("Oct 2022") == "2022-10"

    def test_month_year_long(self):
        assert parse_date("October 2022") == "2022-10"

    def test_present(self):
        assert parse_date("Present") is None

    def test_month_year_short(self):
        assert parse_date("May 2016") == "2016-05"

    def test_aug_2013(self):
        assert parse_date("Aug 2013") == "2013-08"

    def test_empty(self):
        assert parse_date("") is None


class TestParseExperienceEntry:
    """Parse a 'Company | Title  Date – Date' line."""

    def test_zillow_line(self):
        result = parse_experience_entry("TechCorp | Software Engineer\tOct 2022 – Present")
        assert result["company"] == "TechCorp"
        assert result["title"] == "Software Engineer"
        assert result["start_date"] == "2022-10"
        assert result["end_date"] is None

    def test_dematic_line(self):
        result = parse_experience_entry("AutomationCo | Software Engineer\tAug 2018 – Oct 2022")
        assert result["company"] == "AutomationCo"
        assert result["title"] == "Software Engineer"
        assert result["start_date"] == "2018-08"
        assert result["end_date"] == "2022-10"

    def test_dash_separator(self):
        result = parse_experience_entry("Acme Corp — Senior Engineer\tJan 2020 – Dec 2023")
        assert result["company"] == "Acme Corp"
        assert result["title"] == "Senior Engineer"


class TestDetectSections:
    """Detect resume sections from paragraph text + formatting."""

    def test_detects_experience_header(self):
        paragraphs = [
            {"text": "WORK EXPERIENCE", "is_bold": True, "style": "None"},
            {"text": "TechCorp | Engineer\tOct 2022 – Present", "is_bold": True, "style": "None"},
        ]
        sections = detect_sections(paragraphs)
        assert "experience" in sections

    def test_detects_education_header(self):
        paragraphs = [
            {"text": "EDUCATION", "is_bold": True, "style": "None"},
            {"text": "MS Computer Science, MIT\tMay 2020", "is_bold": True, "style": "None"},
        ]
        sections = detect_sections(paragraphs)
        assert "education" in sections

    def test_detects_skills_header(self):
        paragraphs = [
            {"text": "TECHNICAL SKILLS", "is_bold": True, "style": "None"},
            {"text": "Languages: Python, Java", "is_bold": True, "style": "None"},
        ]
        sections = detect_sections(paragraphs)
        assert "skills" in sections

    def test_detects_projects_header(self):
        paragraphs = [
            {"text": "PROJECTS", "is_bold": True, "style": "None"},
            {"text": "MyApp | github.com/user/myapp", "is_bold": True, "style": "None"},
        ]
        sections = detect_sections(paragraphs)
        assert "projects" in sections


@skip_no_resume
class TestParseResumeDocx:
    """Full end-to-end parsing of the user's actual resume."""

    def test_returns_dict_with_all_sections(self):
        result = parse_resume_docx(RESUME_PATH)
        assert "contact" in result
        assert "experiences" in result
        assert "education" in result
        assert "skills" in result
        assert "projects" in result

    def test_extracts_contact_info(self):
        result = parse_resume_docx(RESUME_PATH)
        assert "Alex" in result["contact"].get("name", "")

    def test_extracts_experiences(self):
        result = parse_resume_docx(RESUME_PATH)
        exps = result["experiences"]
        assert len(exps) >= 2
        companies = [e["company"] for e in exps]
        assert "TechCorp" in companies
        assert "AutomationCo" in companies

    def test_experiences_have_bullets(self):
        result = parse_resume_docx(RESUME_PATH)
        zillow = [e for e in result["experiences"] if e["company"] == "TechCorp"][0]
        assert len(zillow["bullets"]) >= 5

    def test_experiences_have_dates(self):
        result = parse_resume_docx(RESUME_PATH)
        zillow = [e for e in result["experiences"] if e["company"] == "TechCorp"][0]
        assert zillow["start_date"] == "2022-10"
        assert zillow["end_date"] is None  # Present

    def test_extracts_education(self):
        result = parse_resume_docx(RESUME_PATH)
        edu = result["education"]
        assert len(edu) >= 2
        institutions = [e["institution"] for e in edu]
        assert any("Arlington" in i for i in institutions)
        assert any("Pune" in i for i in institutions)

    def test_extracts_skills(self):
        result = parse_resume_docx(RESUME_PATH)
        skills = result["skills"]
        assert len(skills) > 0
        all_skill_names = [s["name"] for s in skills]
        assert "Java" in all_skill_names
        assert "Python" in all_skill_names

    def test_extracts_projects(self):
        result = parse_resume_docx(RESUME_PATH)
        projects = result["projects"]
        assert len(projects) >= 1
        assert any("FileComparison" in p.get("name", "") for p in projects)

    def test_extracts_summary(self):
        result = parse_resume_docx(RESUME_PATH)
        assert "summary" in result
        assert "Backend" in result["summary"] or "Engineer" in result["summary"]
