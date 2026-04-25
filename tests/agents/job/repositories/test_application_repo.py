"""Tests for application_repo — application tracking + status history."""

import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.application_repo import ApplicationRepository


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def job_id(db_conn):
    repo = JobRepository(db_conn)
    return repo.save_job(title="SWE", company="Co", parsed_data={})


@pytest.fixture
def repo(db_conn):
    return ApplicationRepository(db_conn)


class TestApplicationCrud:
    def test_create_application(self, repo, job_id):
        app_id = repo.create_application(job_id=job_id)
        assert app_id > 0
        app = repo.get_application(app_id)
        assert app["status"] == "applied"
        assert app["job_id"] == job_id

    def test_list_applications(self, repo, job_id):
        repo.create_application(job_id=job_id)
        apps = repo.list_applications()
        assert len(apps) == 1

    def test_filter_by_status(self, repo, job_id):
        repo.create_application(job_id=job_id)
        apps = repo.list_applications(status="applied")
        assert len(apps) == 1
        apps = repo.list_applications(status="interview")
        assert len(apps) == 0

    def test_update_status(self, repo, job_id):
        app_id = repo.create_application(job_id=job_id)
        repo.update_status(app_id, "interview")
        app = repo.get_application(app_id)
        assert app["status"] == "interview"

    def test_status_history_tracked(self, repo, job_id):
        app_id = repo.create_application(job_id=job_id)
        repo.update_status(app_id, "interview")
        repo.update_status(app_id, "offer")
        history = repo.get_status_history(app_id)
        statuses = [h["status"] for h in history]
        assert "applied" in statuses
        assert "interview" in statuses
        assert "offer" in statuses

    def test_link_resume_and_cover_letter(self, repo, job_id):
        app_id = repo.create_application(
            job_id=job_id, resume_id=10, cover_letter_id=20
        )
        app = repo.get_application(app_id)
        assert app["resume_id"] == 10
        assert app["cover_letter_id"] == 20
