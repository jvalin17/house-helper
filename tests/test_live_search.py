"""Live search tests — hits real APIs. Run manually, not in CI.

Usage: python -m pytest tests/test_live_search.py -v -m live
These tests use real API calls and should NOT be in regression.
"""

import os
import sqlite3
from pathlib import Path

import pytest

from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.job_matcher import JobMatcherService
from agents.job.services.auto_search import AutoSearchService

has_rapidapi = bool(os.environ.get("RAPIDAPI_KEY"))

skip_no_api = pytest.mark.skipif(
    not has_rapidapi,
    reason="RAPIDAPI_KEY not set — skipping live search tests",
)


@pytest.fixture
def search_service(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    jr = JobRepository(conn)
    kr = KnowledgeRepository(conn)
    matcher = JobMatcherService(knowledge_repo=kr, job_repo=jr, llm_provider=None)
    svc = AutoSearchService(job_repo=jr, knowledge_repo=kr, matcher=matcher)
    yield svc
    conn.close()


@pytest.mark.live
@skip_no_api
class TestLiveJSearchSearch:
    """Real API calls to JSearch. Max 2 tests to conserve quota."""

    def test_search_returns_results(self, search_service):
        results = search_service.search({"title": "Software Engineer", "location": "San Francisco"})
        assert len(results) > 0, "JSearch should return at least 1 job for 'Software Engineer in San Francisco'"
        # Verify result structure
        first = results[0]
        assert "title" in first
        assert "company" in first
        assert "id" in first

    def test_search_results_have_match_scores(self, search_service):
        # Add a skill first so matching has something to work with
        from agents.job.repositories.knowledge_repo import KnowledgeRepository
        kr = search_service._knowledge_repo
        kr.save_skill(name="Python", category="language")

        results = search_service.search({"title": "Python Developer"})
        assert len(results) > 0
        # At least one should have a match score (from skill overlap)
        scores = [r.get("match_score") for r in results if r.get("match_score") is not None]
        assert len(scores) > 0, "At least one job should have a match score"
