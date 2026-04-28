"""Tests for knowledge bank merge logic — importing multiple resumes.

Key behavior:
- Same company + dates = merge unique bullets, don't skip
- Same institution = skip (education doesn't have mergeable bullets)
- Same project name = merge unique description/tech
- Same skill name = skip (already exists)
- Different companies = add normally
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.db import connect_sync
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.knowledge import KnowledgeService


@pytest.fixture
def db():
    """In-memory DB with schema."""
    conn = connect_sync(db_path=Path(":memory:"))
    return conn


@pytest.fixture
def svc(db):
    repo = KnowledgeRepository(db)
    return KnowledgeService(repo, db)  # no LLM — uses algorithmic parser


@pytest.fixture
def repo(db):
    return KnowledgeRepository(db)


def _import_with_mock(svc, parsed_data):
    """Import parsed data by writing a temp .txt file and mocking the parser."""
    tmp = Path(tempfile.mktemp(suffix=".txt"))
    tmp.write_text("placeholder resume text for testing")
    try:
        with patch("agents.job.services.knowledge.parse_resume", return_value=parsed_data):
            return svc.import_resume(tmp)
    finally:
        tmp.unlink(missing_ok=True)


class TestExperienceMerge:
    def test_first_import_creates_experience(self, svc, repo):
        resume_1 = {
            "experiences": [{
                "company": "Zillow",
                "title": "Senior Engineer",
                "start_date": "2022-10",
                "end_date": None,
                "bullets": [
                    "Built notification pipeline processing 2M daily events",
                    "Led migration to Kubernetes",
                ],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        result = _import_with_mock(svc, resume_1)

        assert result["experiences"] == 1
        exps = repo.list_experiences()
        assert len(exps) == 1
        assert "notification pipeline" in exps[0]["description"]
        assert "Kubernetes" in exps[0]["description"]

    def test_second_import_merges_unique_bullets(self, svc, repo):
        resume_1 = {
            "experiences": [{
                "company": "Zillow",
                "title": "Senior Engineer",
                "start_date": "2022-10",
                "end_date": None,
                "bullets": [
                    "Built notification pipeline processing 2M daily events",
                    "Led migration to Kubernetes",
                ],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        resume_2 = {
            "experiences": [{
                "company": "Zillow",
                "title": "Senior Engineer",
                "start_date": "2022-10",
                "end_date": None,
                "bullets": [
                    "Built notification pipeline processing 2M daily events",  # duplicate
                    "Designed analytics dashboard used by 50+ stakeholders",   # new
                ],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        _import_with_mock(svc, resume_1)

        result = _import_with_mock(svc, resume_2)

        assert result["experiences_merged"] == 1

        exps = repo.list_experiences()
        assert len(exps) == 1  # still one Zillow entry
        bullets = exps[0]["description"].split("\n")
        assert len(bullets) == 3  # 2 original + 1 new
        assert any("notification pipeline" in b for b in bullets)
        assert any("Kubernetes" in b for b in bullets)
        assert any("analytics dashboard" in b for b in bullets)

    def test_different_company_added_separately(self, svc, repo):
        resume_1 = {
            "experiences": [{
                "company": "Zillow", "title": "SWE",
                "start_date": "2022-10", "end_date": None,
                "bullets": ["Zillow bullet"],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        resume_2 = {
            "experiences": [{
                "company": "Dematic", "title": "SWE",
                "start_date": "2019-01", "end_date": "2022-09",
                "bullets": ["Dematic bullet"],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        _import_with_mock(svc, resume_1)
        _import_with_mock(svc, resume_2)

        exps = repo.list_experiences()
        assert len(exps) == 2

    def test_all_duplicate_bullets_not_merged(self, svc, repo):
        """If second import has only bullets that already exist, nothing changes."""
        resume = {
            "experiences": [{
                "company": "Zillow", "title": "SWE",
                "start_date": "2022-10", "end_date": None,
                "bullets": ["Same bullet"],
            }],
            "skills": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
        }

        _import_with_mock(svc, resume)
        result = _import_with_mock(svc, resume)

        exps = repo.list_experiences()
        assert len(exps) == 1
        bullets = exps[0]["description"].split("\n")
        assert len(bullets) == 1  # no duplicates added


class TestSkillMerge:
    def test_duplicate_skills_not_added(self, svc, repo):
        resume_1 = {
            "experiences": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
            "skills": [
                {"name": "Python", "category": "languages"},
                {"name": "Java", "category": "languages"},
            ],
        }
        resume_2 = {
            "experiences": [], "education": [], "projects": [],
            "contact": {}, "summary": "",
            "skills": [
                {"name": "Python", "category": "languages"},  # duplicate
                {"name": "Go", "category": "languages"},      # new
            ],
        }

        _import_with_mock(svc, resume_1)
        result = _import_with_mock(svc, resume_2)

        skills = repo.list_skills()
        names = {s["name"] for s in skills}
        assert names == {"Python", "Java", "Go"}
        assert result["skills"] == 1  # only Go added


class TestEducationMerge:
    def test_duplicate_institution_skipped(self, svc, repo):
        resume_1 = {
            "experiences": [], "skills": [], "projects": [],
            "contact": {}, "summary": "",
            "education": [{"institution": "Purdue", "degree": "BS", "field": "CS", "end_date": "2018"}],
        }
        resume_2 = {
            "experiences": [], "skills": [], "projects": [],
            "contact": {}, "summary": "",
            "education": [{"institution": "Purdue", "degree": "BS", "field": "CS", "end_date": "2018"}],
        }

        _import_with_mock(svc, resume_1)
        _import_with_mock(svc, resume_2)

        assert len(repo.list_education()) == 1

    def test_different_institution_added(self, svc, repo):
        resume_1 = {
            "experiences": [], "skills": [], "projects": [],
            "contact": {}, "summary": "",
            "education": [{"institution": "Purdue", "degree": "BS", "field": "CS", "end_date": "2018"}],
        }
        resume_2 = {
            "experiences": [], "skills": [], "projects": [],
            "contact": {}, "summary": "",
            "education": [{"institution": "UT Arlington", "degree": "MS", "field": "CS", "end_date": "2020"}],
        }

        _import_with_mock(svc, resume_1)
        _import_with_mock(svc, resume_2)

        assert len(repo.list_education()) == 2
