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
        job = service.parse_text(SAMPLE_JOB_TEXT)
        assert job["id"] > 0
        assert job["title"] is not None

    def test_parse_text_extracts_skills(self, service):
        job = service.parse_text(SAMPLE_JOB_TEXT)
        skills = job.get("extracted_skills", [])
        assert "Python" in skills

    def test_parse_text_extracts_location(self, service):
        job = service.parse_text(SAMPLE_JOB_TEXT)
        assert "San Francisco" in job.get("location", "")

    def test_parse_text_extracts_salary(self, service):
        job = service.parse_text(SAMPLE_JOB_TEXT)
        assert "$150,000" in job.get("salary_range", "")

    def test_parse_empty_text(self, service):
        job = service.parse_text("")
        assert job["title"] is None or job["title"] == ""


class TestParseBatch:
    def test_parse_multiple_texts(self, service):
        texts = [
            "Engineer at Company A\nRequirements:\n- Python",
            "Designer at Company B\nRequirements:\n- Figma",
        ]
        jobs = service.parse_batch(texts)
        assert len(jobs) == 2
