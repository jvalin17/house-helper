"""Tests for knowledge_repo — CRUD for knowledge bank entries."""

import sqlite3

import pytest

from shared.db import migrate
from agents.job.repositories.knowledge_repo import KnowledgeRepository


@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn):
    return KnowledgeRepository(db_conn)


class TestExperiences:
    def test_save_and_get_experience(self, repo):
        exp_id = repo.save_experience(
            type="job",
            title="Engineer",
            company="Acme",
            start_date="2020-01",
            end_date="2023-06",
            description="Built APIs",
        )
        assert exp_id > 0
        exp = repo.get_experience(exp_id)
        assert exp["title"] == "Engineer"
        assert exp["company"] == "Acme"

    def test_list_experiences(self, repo):
        repo.save_experience(type="job", title="Eng1", company="A")
        repo.save_experience(type="job", title="Eng2", company="B")
        exps = repo.list_experiences()
        assert len(exps) == 2

    def test_update_experience(self, repo):
        exp_id = repo.save_experience(type="job", title="Old Title", company="Co")
        repo.update_experience(exp_id, title="New Title")
        exp = repo.get_experience(exp_id)
        assert exp["title"] == "New Title"

    def test_delete_experience(self, repo):
        exp_id = repo.save_experience(type="job", title="ToDelete", company="Co")
        repo.delete_experience(exp_id)
        exp = repo.get_experience(exp_id)
        assert exp is None


class TestSkills:
    def test_save_and_list_skills(self, repo):
        repo.save_skill(name="Python", category="language")
        repo.save_skill(name="React", category="framework")
        skills = repo.list_skills()
        assert len(skills) == 2
        names = [s["name"] for s in skills]
        assert "Python" in names

    def test_duplicate_skill_ignored(self, repo):
        repo.save_skill(name="Python", category="language")
        repo.save_skill(name="Python", category="language")
        skills = repo.list_skills()
        assert len(skills) == 1


class TestAchievements:
    def test_save_and_list_achievements(self, repo):
        exp_id = repo.save_experience(type="job", title="Eng", company="Co")
        repo.save_achievement(
            experience_id=exp_id,
            description="Reduced latency by 40%",
            metric="40% reduction",
        )
        achievements = repo.list_achievements(experience_id=exp_id)
        assert len(achievements) == 1
        assert "40%" in achievements[0]["description"]


class TestGetFullKnowledgeBank:
    def test_returns_all_sections(self, repo):
        repo.save_experience(type="job", title="Eng", company="Co")
        repo.save_skill(name="Python", category="language")
        kb = repo.get_full_knowledge_bank()
        assert "experiences" in kb
        assert "skills" in kb
        assert "achievements" in kb
        assert "education" in kb
        assert "projects" in kb
        assert len(kb["experiences"]) == 1
        assert len(kb["skills"]) == 1
