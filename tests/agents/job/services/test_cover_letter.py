"""Tests for cover letter service."""

import json
import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.cover_letter_repo import CoverLetterRepository
from agents.job.services.cover_letter import CoverLetterService


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(db_conn):
    kr = KnowledgeRepository(db_conn)
    jr = JobRepository(db_conn)
    clr = CoverLetterRepository(db_conn)
    kr.save_experience(type="job", title="Engineer", company="Acme", description="Built APIs with Python")
    kr.save_skill(name="Python", category="language")
    kr.save_skill(name="React", category="framework")
    job_id = jr.save_job(
        title="SWE", company="BigTech",
        parsed_data={"required_skills": ["Python", "React"]},
    )
    return db_conn, kr, jr, clr, job_id


@pytest.fixture
def service(populated_db):
    db_conn, kr, _, clr, _ = populated_db
    return CoverLetterService(
        knowledge_repo=kr,
        cover_letter_repo=clr,
        db_conn=db_conn,
        llm_provider=None,
    )


class TestGenerateCoverLetter:
    def test_generates_content(self, service, populated_db):
        *_, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        assert result["id"] > 0
        assert "BigTech" in result["content"]
        assert "SWE" in result["content"]

    def test_mentions_matching_skills(self, service, populated_db):
        *_, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        assert "Python" in result["content"]

    def test_saves_to_database(self, service, populated_db):
        db_conn, _, _, clr, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        cl = clr.get_cover_letter(result["id"])
        assert cl is not None
        assert cl["job_id"] == job_id


class TestUpdateCoverLetter:
    def test_update_content(self, service, populated_db):
        *_, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        updated = service.update(result["id"], "Edited cover letter content")
        assert updated["content"] == "Edited cover letter content"


class TestExportCoverLetter:
    def test_export_as_pdf(self, service, populated_db):
        *_, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="pdf")
        assert exported[:5] == b"%PDF-"

    def test_export_as_docx(self, service, populated_db):
        *_, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="docx")
        assert exported[:2] == b"PK"
