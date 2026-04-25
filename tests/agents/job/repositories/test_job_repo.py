"""Tests for job_repo — CRUD for job postings."""

import json
import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn):
    return JobRepository(db_conn)


class TestJobCrud:
    def test_save_and_get_job(self, repo):
        job_id = repo.save_job(
            title="SWE",
            company="BigTech",
            parsed_data={"required_skills": ["Python"]},
            source_url="https://example.com/job/1",
        )
        assert job_id > 0
        job = repo.get_job(job_id)
        assert job["title"] == "SWE"
        assert job["company"] == "BigTech"

    def test_list_jobs(self, repo):
        repo.save_job(title="SWE", company="A", parsed_data={})
        repo.save_job(title="PM", company="B", parsed_data={})
        jobs = repo.list_jobs()
        assert len(jobs) == 2

    def test_delete_job(self, repo):
        job_id = repo.save_job(title="Del", company="X", parsed_data={})
        repo.delete_job(job_id)
        assert repo.get_job(job_id) is None

    def test_update_match_score(self, repo):
        job_id = repo.save_job(title="SWE", company="Co", parsed_data={})
        repo.update_match_score(
            job_id,
            score=0.85,
            breakdown={"skills": 0.9, "semantic": 0.8},
        )
        job = repo.get_job(job_id)
        assert job["match_score"] == 0.85

    def test_parsed_data_stored_as_json(self, repo):
        data = {"required_skills": ["Python", "React"], "salary": "$150k"}
        job_id = repo.save_job(title="SWE", company="Co", parsed_data=data)
        job = repo.get_job(job_id)
        loaded = json.loads(job["parsed_data"])
        assert loaded["required_skills"] == ["Python", "React"]
