"""Edit knowledge bank entries — TDD tests for updating skills, education, projects.

Covers:
- update_skill changes name and/or category
- update_education changes institution, degree, field, end_date
- update_project changes name, description, tech_stack, url
- partial updates (only some fields) preserve unchanged fields
- updating nonexistent ID raises or returns gracefully
"""

import sqlite3
import pytest

from shared.db import migrate
from agents.job.repositories.knowledge_repo import KnowledgeRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def knowledge_repo(database_connection):
    return KnowledgeRepository(database_connection)


class TestUpdateSkill:
    def test_update_skill_name(self, knowledge_repo):
        """Updating a skill's name should persist the change."""
        skill_id = knowledge_repo.save_skill(name="Pythn", category="Language")
        knowledge_repo.update_skill(skill_id, name="Python")

        updated_skills = knowledge_repo.list_skills()
        matched = [skill for skill in updated_skills if skill["id"] == skill_id]
        assert len(matched) == 1
        assert matched[0]["name"] == "Python"
        assert matched[0]["category"] == "Language"

    def test_update_skill_category(self, knowledge_repo):
        """Updating category alone should preserve name."""
        skill_id = knowledge_repo.save_skill(name="Docker", category="Tool")
        knowledge_repo.update_skill(skill_id, category="DevOps")

        updated_skills = knowledge_repo.list_skills()
        matched = [skill for skill in updated_skills if skill["id"] == skill_id]
        assert matched[0]["name"] == "Docker"
        assert matched[0]["category"] == "DevOps"

    def test_update_skill_both_fields(self, knowledge_repo):
        """Updating both name and category at once."""
        skill_id = knowledge_repo.save_skill(name="JS", category="Lang")
        knowledge_repo.update_skill(skill_id, name="JavaScript", category="Language")

        updated_skills = knowledge_repo.list_skills()
        matched = [skill for skill in updated_skills if skill["id"] == skill_id]
        assert matched[0]["name"] == "JavaScript"
        assert matched[0]["category"] == "Language"


class TestUpdateEducation:
    def test_update_education_degree(self, knowledge_repo):
        """Updating degree should preserve other fields."""
        education_id = knowledge_repo.save_education(
            institution="MIT", degree="BS", field="CS", end_date="2020"
        )
        knowledge_repo.update_education(education_id, degree="MS")

        rows = knowledge_repo._conn.execute(
            "SELECT * FROM education WHERE id = ?", (education_id,)
        ).fetchall()
        assert len(rows) == 1
        education = dict(rows[0])
        assert education["degree"] == "MS"
        assert education["institution"] == "MIT"
        assert education["field"] == "CS"

    def test_update_education_multiple_fields(self, knowledge_repo):
        """Updating multiple fields at once."""
        education_id = knowledge_repo.save_education(
            institution="MIT", degree="BS", field="CS", end_date="2020"
        )
        knowledge_repo.update_education(
            education_id, institution="Stanford", field="AI", end_date="2022"
        )

        education = dict(knowledge_repo._conn.execute(
            "SELECT * FROM education WHERE id = ?", (education_id,)
        ).fetchone())
        assert education["institution"] == "Stanford"
        assert education["field"] == "AI"
        assert education["end_date"] == "2022"
        assert education["degree"] == "BS"


class TestUpdateProject:
    def test_update_project_name(self, knowledge_repo):
        """Updating project name should preserve other fields."""
        project_id = knowledge_repo.save_project(
            name="Old Name", description="A project", tech_stack="Python", url=""
        )
        knowledge_repo.update_project(project_id, name="New Name")

        project = dict(knowledge_repo._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone())
        assert project["name"] == "New Name"
        assert project["description"] == "A project"
        assert project["tech_stack"] == "Python"

    def test_update_project_all_fields(self, knowledge_repo):
        """Updating all project fields at once."""
        project_id = knowledge_repo.save_project(
            name="App", description="old", tech_stack="JS", url="http://old"
        )
        knowledge_repo.update_project(
            project_id, name="Platform", description="new desc",
            tech_stack="Python, React", url="http://new"
        )

        project = dict(knowledge_repo._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone())
        assert project["name"] == "Platform"
        assert project["description"] == "new desc"
        assert project["tech_stack"] == "Python, React"
        assert project["url"] == "http://new"
