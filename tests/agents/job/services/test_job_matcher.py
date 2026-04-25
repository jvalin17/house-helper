"""Tests for job_matcher service — score jobs against knowledge bank."""

import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.job_matcher import JobMatcherService


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def repos(db_conn):
    knowledge_repo = KnowledgeRepository(db_conn)
    job_repo = JobRepository(db_conn)

    # Populate knowledge bank
    knowledge_repo.save_experience(type="job", title="Engineer", company="Acme")
    knowledge_repo.save_skill(name="Python", category="language")
    knowledge_repo.save_skill(name="React", category="framework")
    knowledge_repo.save_skill(name="Docker", category="tool")

    return knowledge_repo, job_repo


@pytest.fixture
def service(repos):
    knowledge_repo, job_repo = repos
    return JobMatcherService(
        knowledge_repo=knowledge_repo,
        job_repo=job_repo,
        llm_provider=None,
    )


class TestMatchSingleJob:
    def test_returns_score_and_breakdown(self, service, repos):
        _, job_repo = repos
        job_id = job_repo.save_job(
            title="SWE",
            company="Co",
            parsed_data={"required_skills": ["Python", "React", "Go"]},
        )
        result = service.match_job(job_id)
        assert "score" in result
        assert "breakdown" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_high_overlap_scores_higher_than_no_overlap(self, service, repos):
        _, job_repo = repos
        good_id = job_repo.save_job(
            title="SWE", company="Co",
            parsed_data={"required_skills": ["Python", "React", "Docker"]},
        )
        bad_id = job_repo.save_job(
            title="Chef", company="Restaurant",
            parsed_data={"required_skills": ["Cooking", "Baking"]},
        )
        good_result = service.match_job(good_id)
        bad_result = service.match_job(bad_id)
        assert good_result["score"] > bad_result["score"]

    def test_no_overlap_scores_low(self, service, repos):
        _, job_repo = repos
        job_id = job_repo.save_job(
            title="Chef",
            company="Restaurant",
            parsed_data={"required_skills": ["Cooking", "Baking", "Pastry"]},
        )
        result = service.match_job(job_id)
        assert result["score"] < 0.3

    def test_saves_score_to_db(self, service, repos):
        _, job_repo = repos
        job_id = job_repo.save_job(
            title="SWE",
            company="Co",
            parsed_data={"required_skills": ["Python"]},
        )
        service.match_job(job_id)
        job = job_repo.get_job(job_id)
        assert job["match_score"] is not None


class TestMatchBatch:
    def test_returns_sorted_results(self, service, repos):
        _, job_repo = repos
        id1 = job_repo.save_job(title="A", company="X", parsed_data={"required_skills": ["Python", "React"]})
        id2 = job_repo.save_job(title="B", company="Y", parsed_data={"required_skills": ["Cooking"]})
        results = service.match_batch([id1, id2])
        assert len(results) == 2
        # Better match should be first
        assert results[0]["score"] >= results[1]["score"]
