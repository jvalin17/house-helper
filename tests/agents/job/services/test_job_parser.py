"""Tests for job_parser service — parse job postings from URL or text."""

import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository
from agents.job.services.job_parser import JobParserService


SAMPLE_JOB_TEXT = """
Software Engineer at BigTech

Location: San Francisco, CA (Remote OK)
Salary: $150,000 - $200,000

Requirements:
- 3+ years of Python experience
- Experience with React and TypeScript
- Docker and Kubernetes
"""

SNOWFLAKE_URL = "https://careers.snowflake.com/us/en/job/SNCOUSDD524B932E4E4E3B84B44684A46E9148EXTERNALENUS3EB872AF0AB149868F72E7321FCD1538/Software-Engineer-Backend"
META_URL = "https://www.metacareers.com/profile/job_details/860406887033740"


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def service(db_conn):
    job_repo = JobRepository(db_conn)
    return JobParserService(job_repo=job_repo, llm_provider=None)


class TestParseText:
    def test_parse_text_saves_job(self, service):
        job = service.parse_input(SAMPLE_JOB_TEXT)
        assert job["id"] > 0
        assert job["title"] is not None

    def test_parse_text_extracts_skills(self, service):
        job = service.parse_input(SAMPLE_JOB_TEXT)
        skills = job.get("extracted_skills", [])
        assert "Python" in skills

    def test_parse_text_extracts_location(self, service):
        job = service.parse_input(SAMPLE_JOB_TEXT)
        assert "San Francisco" in job.get("location", "")

    def test_parse_text_extracts_salary(self, service):
        job = service.parse_input(SAMPLE_JOB_TEXT)
        assert "$150,000" in job.get("salary_range", "")

    def test_parse_empty_text(self, service):
        job = service.parse_input("")
        assert job["title"] == "(untitled)" or job["title"] is None

    def test_detects_url_vs_text(self, service):
        text_result = service.parse_input("Python developer at Acme")
        assert text_result["id"] > 0
        # URL would be detected differently
        assert "Acme" in (text_result.get("company") or text_result.get("title") or "")


class TestParseURL:
    @pytest.mark.network
    def test_parse_snowflake_url(self, service):
        job = service.parse_input(SNOWFLAKE_URL)
        assert job["id"] > 0
        assert "Snowflake" in (job.get("company") or "")
        assert job.get("title") is not None
        assert len(job.get("extracted_skills", [])) > 0

    @pytest.mark.network
    def test_parse_meta_url(self, service):
        job = service.parse_input(META_URL)
        assert job["id"] > 0
        assert "Meta" in (job.get("company") or "")
        assert job.get("title") is not None

    @pytest.mark.network
    def test_parse_invalid_url_doesnt_crash(self, service):
        job = service.parse_input("https://example.com/nonexistent-job-12345")
        assert job["id"] > 0
        # Should still save something, even if fetch fails or no job data found


class TestParseBatch:
    def test_parse_multiple_texts(self, service):
        texts = [
            "Engineer at Company A\nRequirements:\n- Python",
            "Designer at Company B\nRequirements:\n- Figma",
        ]
        jobs = service.parse_batch(texts)
        assert len(jobs) == 2

    @pytest.mark.network
    def test_parse_mixed_urls_and_text(self, service):
        inputs = [
            META_URL,
            "Backend Engineer at Startup\n- Python\n- PostgreSQL",
        ]
        jobs = service.parse_batch(inputs)
        assert len(jobs) == 2
        # First should be Meta (URL), second should be text
        companies = [j.get("company") or "" for j in jobs]
        assert any("Meta" in c for c in companies)
