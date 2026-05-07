"""Job search dedup — tests for cross-source deduplication.

Covers: URL-based dedup, title+company fuzzy dedup, DB-level dedup,
is_existing flag on duplicate results.
"""

import pytest

from shared.job_boards.base import JobResult
from agents.job.services.auto_search import AutoSearchService


# ── In-memory dedup (before DB) ──────────────────────

class TestDeduplicateResults:
    """Tests for AutoSearchService._deduplicate_results (static method)."""

    def test_dedup_by_exact_url(self):
        """Same URL from different boards → only first kept."""
        results = [
            JobResult(title="Senior SDET", company="Apple", url="https://linkedin.com/job/123", source="jsearch"),
            JobResult(title="Senior SDET", company="Apple", url="https://linkedin.com/job/123", source="adzuna"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        assert len(unique) == 1
        assert unique[0].source == "jsearch"

    def test_dedup_by_title_and_company(self):
        """Same title+company from LinkedIn vs Indeed (different URLs) → only first kept."""
        results = [
            JobResult(title="Backend Engineer", company="Netflix", url="https://linkedin.com/job/456", source="jsearch"),
            JobResult(title="Backend Engineer", company="Netflix", url="https://indeed.com/job/789", source="adzuna"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        assert len(unique) == 1

    def test_different_titles_same_company_not_deduped(self):
        """Different roles at same company are kept."""
        results = [
            JobResult(title="Frontend Engineer", company="Google", url="https://linkedin.com/job/1", source="jsearch"),
            JobResult(title="Backend Engineer", company="Google", url="https://linkedin.com/job/2", source="jsearch"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        assert len(unique) == 2

    def test_case_insensitive_title_company_dedup(self):
        """Title+company dedup is case-insensitive."""
        results = [
            JobResult(title="Senior SDET", company="APPLE INC", url="https://a.com/1", source="jsearch"),
            JobResult(title="senior sdet", company="apple inc", url="https://b.com/2", source="adzuna"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        assert len(unique) == 1

    def test_empty_company_not_false_dedup(self):
        """Two jobs with empty company names should NOT be deduped against each other."""
        results = [
            JobResult(title="QA Engineer", company="", url="https://a.com/1", source="jsearch"),
            JobResult(title="QA Engineer", company="", url="https://b.com/2", source="adzuna"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        # Both kept because empty company → dedup_key is "qa engineer|" which is skipped
        assert len(unique) == 2

    def test_preserves_order(self):
        """First occurrence is kept, subsequent duplicates dropped."""
        results = [
            JobResult(title="ML Engineer", company="Meta", url="https://indeed.com/ml", source="adzuna"),
            JobResult(title="DevOps Lead", company="Stripe", url="https://linkedin.com/devops", source="jsearch"),
            JobResult(title="ML Engineer", company="Meta", url="https://linkedin.com/ml", source="jsearch"),
        ]
        unique = AutoSearchService._deduplicate_results(results)
        assert len(unique) == 2
        assert unique[0].title == "ML Engineer"
        assert unique[0].source == "adzuna"  # First occurrence kept
        assert unique[1].title == "DevOps Lead"

    def test_no_results_returns_empty(self):
        assert AutoSearchService._deduplicate_results([]) == []


# ── DB-level dedup helpers ───────────────────────────

import sqlite3
from shared.db import migrate
from agents.job.repositories.job_repo import JobRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def job_repo(database_connection):
    return JobRepository(database_connection)


class TestJobRepoDedup:
    """Tests for get_existing_urls and find_by_title_and_company."""

    def test_get_existing_urls_returns_map(self, job_repo):
        """Returns {url: job_id} for all jobs with URLs."""
        job_id_1 = job_repo.save_job("SDET", company="Apple", source_url="https://linkedin.com/job/100")
        job_id_2 = job_repo.save_job("Backend Eng", company="Google", source_url="https://indeed.com/job/200")
        job_repo.save_job("No URL Job", company="Startup")  # No URL

        url_map = job_repo.get_existing_urls()
        assert url_map["https://linkedin.com/job/100"] == job_id_1
        assert url_map["https://indeed.com/job/200"] == job_id_2
        assert len(url_map) == 2  # No URL job excluded

    def test_find_by_title_and_company_exact(self, job_repo):
        """Finds existing job by exact title+company (case-insensitive)."""
        job_id = job_repo.save_job("Senior SDET", company="Apple")
        found = job_repo.find_by_title_and_company("senior sdet", "apple")
        assert found == job_id

    def test_find_by_title_and_company_no_match(self, job_repo):
        """Returns None when no match found."""
        job_repo.save_job("Frontend Dev", company="Netflix")
        found = job_repo.find_by_title_and_company("Backend Dev", "Netflix")
        assert found is None
