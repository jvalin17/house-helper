"""Delete individual skill — TDD tests for skill deletion.

Covers:
- delete_skill removes the skill from DB
- delete_skill with non-existent ID doesn't crash
- deleted skill no longer appears in list_skills
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


class TestDeleteSkill:
    def test_delete_skill_removes_from_database(self, knowledge_repo):
        """Deleting a skill by ID should remove it from the skills table."""
        skill_id = knowledge_repo.save_skill(name="Python", category="Language", proficiency="expert")
        assert len(knowledge_repo.list_skills()) == 1

        knowledge_repo.delete_skill(skill_id)

        assert len(knowledge_repo.list_skills()) == 0

    def test_delete_skill_nonexistent_id_does_not_crash(self, knowledge_repo):
        """Deleting a skill with a non-existent ID should not raise."""
        knowledge_repo.delete_skill(9999)  # Should not raise

    def test_deleted_skill_not_in_list(self, knowledge_repo):
        """After deletion, the skill should not appear in list_skills."""
        skill_id_python = knowledge_repo.save_skill(name="Python", category="Language")
        skill_id_react = knowledge_repo.save_skill(name="React", category="Framework")

        knowledge_repo.delete_skill(skill_id_python)

        remaining_skills = knowledge_repo.list_skills()
        skill_names = [skill["name"] for skill in remaining_skills]
        assert "Python" not in skill_names
        assert "React" in skill_names
        assert len(remaining_skills) == 1
