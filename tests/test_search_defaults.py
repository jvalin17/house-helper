"""TDD tests for default search criteria + extra filters + resume selector.

Features 1-3 from requirements/search-filters-budget-reset.md:
1. Default role/location/keywords saved in active profile
2. Sponsorship/clearance/internship filters in profile preferences
3. Filtering jobs post-fetch by description keywords
"""

import json
from pathlib import Path

import pytest

from shared.db import connect_sync
from agents.job.repositories.profile_repo import ProfileRepository


@pytest.fixture
def db():
    conn = connect_sync(db_path=Path(":memory:"))
    return conn


@pytest.fixture
def repo(db):
    return ProfileRepository(db)


class TestDefaultSearchCriteria:
    def test_active_profile_has_search_fields(self, repo):
        """Default profile (auto-created) should have search fields."""
        profile = repo.get_active_profile()
        assert profile is not None
        assert "search_title" in profile
        assert "search_location" in profile

    def test_update_search_defaults(self, repo):
        repo.update_profile(1,
            search_title="Senior Software Engineer",
            search_location="United States",
            search_keywords="Python, Java, AWS",
            search_remote=1,
        )
        profile = repo.get_active_profile()
        assert profile["search_title"] == "Senior Software Engineer"
        assert profile["search_location"] == "United States"
        assert profile["search_keywords"] == "Python, Java, AWS"
        assert profile["search_remote"] == 1

    def test_empty_defaults_allowed(self, repo):
        repo.update_profile(1, search_title=None, search_location=None)
        profile = repo.get_active_profile()
        assert profile["search_title"] is None


class TestExtraFilters:
    def test_save_filter_preferences(self, db, repo):
        """Sponsorship/clearance/internship stored in resume_preferences JSON."""
        prefs = {
            "exclude_sponsorship": True,
            "exclude_clearance": True,
            "exclude_internship": False,
        }
        repo.update_profile(1, resume_preferences=json.dumps(prefs))
        profile = repo.get_active_profile()
        loaded = json.loads(profile["resume_preferences"])
        assert loaded["exclude_sponsorship"] is True
        assert loaded["exclude_clearance"] is True
        assert loaded["exclude_internship"] is False


class TestJobDescriptionFiltering:
    def test_filter_sponsorship_jobs(self):
        from agents.job.services.job_filter import filter_jobs_by_preferences

        jobs = [
            {"id": 1, "title": "SWE", "parsed_data": json.dumps({"description": "Must have visa sponsorship"})},
            {"id": 2, "title": "SWE", "parsed_data": json.dumps({"description": "Build distributed systems"})},
            {"id": 3, "title": "SWE", "parsed_data": json.dumps({"description": "US citizen required"})},
        ]
        prefs = {"exclude_sponsorship": True}
        filtered = filter_jobs_by_preferences(jobs, prefs)
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_filter_clearance_jobs(self):
        from agents.job.services.job_filter import filter_jobs_by_preferences

        jobs = [
            {"id": 1, "title": "SWE", "parsed_data": json.dumps({"description": "TS/SCI clearance required"})},
            {"id": 2, "title": "SWE", "parsed_data": json.dumps({"description": "Build web apps"})},
        ]
        prefs = {"exclude_clearance": True}
        filtered = filter_jobs_by_preferences(jobs, prefs)
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_filter_internship_jobs(self):
        from agents.job.services.job_filter import filter_jobs_by_preferences

        jobs = [
            {"id": 1, "title": "Intern", "parsed_data": json.dumps({"description": "Summer internship program"})},
            {"id": 2, "title": "SWE", "parsed_data": json.dumps({"description": "Full-time position"})},
        ]
        prefs = {"exclude_internship": True}
        filtered = filter_jobs_by_preferences(jobs, prefs)
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_no_filters_returns_all(self):
        from agents.job.services.job_filter import filter_jobs_by_preferences

        jobs = [{"id": 1, "title": "SWE", "parsed_data": json.dumps({"description": "anything"})}]
        filtered = filter_jobs_by_preferences(jobs, {})
        assert len(filtered) == 1

    def test_multiple_filters_combined(self):
        from agents.job.services.job_filter import filter_jobs_by_preferences

        jobs = [
            {"id": 1, "title": "SWE", "parsed_data": json.dumps({"description": "visa sponsorship available"})},
            {"id": 2, "title": "SWE", "parsed_data": json.dumps({"description": "security clearance needed"})},
            {"id": 3, "title": "Intern", "parsed_data": json.dumps({"description": "intern co-op program"})},
            {"id": 4, "title": "SWE", "parsed_data": json.dumps({"description": "Remote Python developer"})},
        ]
        prefs = {"exclude_sponsorship": True, "exclude_clearance": True, "exclude_internship": True}
        filtered = filter_jobs_by_preferences(jobs, prefs)
        assert len(filtered) == 1
        assert filtered[0]["id"] == 4
