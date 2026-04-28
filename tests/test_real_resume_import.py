"""Tests for importing real resume files — PDF and DOCX.

Uses actual resume files from the user's machine. These tests verify
the full import pipeline: parse → extract skills → store KB entries.
"""

import sqlite3
from pathlib import Path

import pytest

from shared.db import connect_sync
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.services.knowledge import KnowledgeService


# Set TEST_RESUME_PDF and TEST_RESUME_DOCX env vars to run these tests
# with real resume files. They are skipped by default.
import os
PDF_PATH = Path(os.environ.get("TEST_RESUME_PDF", "/nonexistent/test_resume.pdf"))
DOCX_PATH = Path(os.environ.get("TEST_RESUME_DOCX", "/nonexistent/test_resume.docx"))


@pytest.fixture
def fresh_db():
    """In-memory DB — clean slate for each test."""
    return connect_sync(db_path=Path(":memory:"))


@pytest.fixture
def svc(fresh_db):
    repo = KnowledgeRepository(fresh_db)
    return KnowledgeService(repo, fresh_db)


@pytest.fixture
def repo(fresh_db):
    return KnowledgeRepository(fresh_db)


class TestDocxImport:
    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_returns_counts(self, svc):
        result = svc.import_resume(DOCX_PATH)
        print(f"DOCX import result: {result}")
        assert result["experiences"] > 0, "No experiences extracted from DOCX"

    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_extracts_skills(self, svc, repo):
        svc.import_resume(DOCX_PATH)
        skills = repo.list_skills()
        print(f"Skills extracted: {len(skills)} — {[s['name'] for s in skills[:10]]}")
        assert len(skills) > 0, "No skills extracted from DOCX"

    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_extracts_experiences_with_bullets(self, svc, repo):
        svc.import_resume(DOCX_PATH)
        exps = repo.list_experiences()
        print(f"Experiences: {len(exps)}")
        for e in exps:
            bullets = (e["description"] or "").split("\n")
            print(f"  {e['company']} | {e['title']} — {len(bullets)} bullets")
        assert len(exps) > 0
        # At least one experience should have bullets
        assert any(e["description"] for e in exps), "No experience has bullet points"

    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_stores_original_text(self, svc, fresh_db):
        svc.import_resume(DOCX_PATH)
        import json
        row = fresh_db.execute("SELECT value FROM settings WHERE key = 'original_resume'").fetchone()
        assert row is not None, "original_resume not stored"
        text = json.loads(row["value"])
        assert len(text) > 100, f"Stored text too short: {len(text)} chars"
        print(f"Stored text: {len(text)} chars, {len(text.splitlines())} lines")

    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_stores_binary_and_map(self, svc, fresh_db):
        svc.import_resume(DOCX_PATH)
        docx_row = fresh_db.execute("SELECT 1 FROM settings WHERE key = 'original_resume_docx'").fetchone()
        map_row = fresh_db.execute("SELECT 1 FROM settings WHERE key = 'original_resume_map'").fetchone()
        assert docx_row is not None, "DOCX binary not stored"
        assert map_row is not None, "Paragraph map not stored"

    @pytest.mark.skipif(not DOCX_PATH.exists(), reason="DOCX file not found")
    def test_docx_import_extracts_education(self, svc, repo):
        svc.import_resume(DOCX_PATH)
        edu = repo.list_education()
        print(f"Education entries: {len(edu)}")
        for e in edu:
            print(f"  {e.get('degree')} — {e.get('institution')}")


class TestPdfImport:
    @pytest.mark.skipif(not PDF_PATH.exists(), reason="PDF file not found")
    def test_pdf_import_returns_counts(self, svc):
        result = svc.import_resume(PDF_PATH)
        print(f"PDF import result: {result}")
        assert result["experiences"] > 0 or result["skills"] > 0, \
            f"Nothing extracted from PDF: {result}"

    @pytest.mark.skipif(not PDF_PATH.exists(), reason="PDF file not found")
    def test_pdf_import_extracts_skills(self, svc, repo):
        svc.import_resume(PDF_PATH)
        skills = repo.list_skills()
        print(f"Skills extracted: {len(skills)} — {[s['name'] for s in skills[:10]]}")
        assert len(skills) > 0, "No skills extracted from PDF"

    @pytest.mark.skipif(not PDF_PATH.exists(), reason="PDF file not found")
    def test_pdf_import_extracts_experiences(self, svc, repo):
        svc.import_resume(PDF_PATH)
        exps = repo.list_experiences()
        print(f"Experiences from PDF: {len(exps)}")
        for e in exps:
            print(f"  {e['company']} | {e['title']}")

    @pytest.mark.skipif(not PDF_PATH.exists(), reason="PDF file not found")
    def test_pdf_no_docx_binary_stored(self, svc, fresh_db):
        """PDF import should NOT store DOCX binary."""
        svc.import_resume(PDF_PATH)
        row = fresh_db.execute("SELECT 1 FROM settings WHERE key = 'original_resume_docx'").fetchone()
        assert row is None, "DOCX binary should not be stored for PDF import"


class TestSecondImportMerges:
    @pytest.mark.skipif(not DOCX_PATH.exists() or not PDF_PATH.exists(), reason="Resume files not found")
    def test_import_both_merges_knowledge(self, svc, repo):
        """Import DOCX then PDF — should merge, not duplicate."""
        result1 = svc.import_resume(DOCX_PATH)
        print(f"First import (DOCX): {result1}")
        skills_after_first = len(repo.list_skills())
        exps_after_first = len(repo.list_experiences())

        result2 = svc.import_resume(PDF_PATH)
        print(f"Second import (PDF): {result2}")
        skills_after_second = len(repo.list_skills())
        exps_after_second = len(repo.list_experiences())

        print(f"Skills: {skills_after_first} → {skills_after_second}")
        print(f"Experiences: {exps_after_first} → {exps_after_second}")

        # Should have at least as many as first import
        assert skills_after_second >= skills_after_first
        assert exps_after_second >= exps_after_first
