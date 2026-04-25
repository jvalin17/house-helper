"""Tests for knowledge service — resume import + knowledge bank population."""

import sqlite3
from pathlib import Path

import pytest

from shared.db import migrate
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.knowledge import KnowledgeService

RESUME_PATH = Path("/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx")

skip_no_resume = pytest.mark.skipif(
    not RESUME_PATH.exists(),
    reason="Test resume not available",
)


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def service(db_conn):
    repo = KnowledgeRepository(db_conn)
    return KnowledgeService(knowledge_repo=repo)


@skip_no_resume
class TestImportResume:
    def test_import_returns_summary(self, service):
        result = service.import_resume(RESUME_PATH)
        assert "experiences" in result
        assert "skills" in result
        assert "education" in result

    def test_import_populates_experiences(self, service):
        result = service.import_resume(RESUME_PATH)
        assert result["experiences"] >= 2

    def test_import_populates_skills(self, service):
        result = service.import_resume(RESUME_PATH)
        assert result["skills"] >= 5

    def test_import_populates_education(self, service):
        result = service.import_resume(RESUME_PATH)
        assert result["education"] >= 2

    def test_knowledge_bank_has_data_after_import(self, service):
        service.import_resume(RESUME_PATH)
        kb = service._repo.get_full_knowledge_bank()
        assert len(kb["experiences"]) >= 2
        assert len(kb["skills"]) >= 5
        assert len(kb["education"]) >= 2

    def test_import_returns_preview(self, service):
        result = service.import_resume(RESUME_PATH, save=False)
        assert "preview" in result
        assert len(result["preview"]["experiences"]) >= 2

    def test_double_import_warns_duplicates(self, service):
        service.import_resume(RESUME_PATH)
        result = service.import_resume(RESUME_PATH)
        assert result.get("duplicates_skipped", 0) > 0
