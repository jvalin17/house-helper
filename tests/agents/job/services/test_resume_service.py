"""Tests for resume service — generate and export resumes."""

import json
import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.job_repo import JobRepository
from agents.job.services.resume import ResumeService


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
    kr.save_experience(type="job", title="Engineer", company="Acme", description="Built APIs")
    kr.save_skill(name="Python", category="language")
    kr.save_skill(name="React", category="framework")
    job_id = jr.save_job(
        title="SWE", company="BigTech",
        parsed_data={"required_skills": ["Python", "React"]},
    )
    return db_conn, kr, jr, job_id


@pytest.fixture
def service(populated_db, tmp_path):
    db_conn, kr, jr, _ = populated_db
    return ResumeService(
        knowledge_repo=kr,
        db_conn=db_conn,
        llm_provider=None,
        export_dir=tmp_path / "exports",
    )


class TestGenerateResume:
    def test_generates_markdown_content(self, service, populated_db):
        _, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        assert result["id"] > 0
        assert len(result["content"]) > 50
        assert "Acme" in result["content"]

    def test_saves_to_database(self, service, populated_db):
        db_conn, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        row = db_conn.execute(
            "SELECT * FROM resumes WHERE id = ?", (result["id"],)
        ).fetchone()
        assert row is not None
        assert row["job_id"] == job_id


class TestExportResume:
    def test_export_as_markdown(self, service, populated_db):
        _, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="md")
        assert isinstance(exported, bytes)
        assert b"Acme" in exported

    def test_export_as_txt(self, service, populated_db):
        _, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="txt")
        assert isinstance(exported, bytes)

    def test_export_as_pdf(self, service, populated_db):
        _, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="pdf")
        assert exported[:5] == b"%PDF-"

    def test_export_as_docx(self, service, populated_db):
        _, _, _, job_id = populated_db
        result = service.generate(job_id=job_id, preferences={})
        exported = service.export(result["id"], format="docx")
        assert exported[:2] == b"PK"
