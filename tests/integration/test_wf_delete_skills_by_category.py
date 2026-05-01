"""Delete skills by category — TDD tests.

Covers:
- delete_skills_by_category removes all skills in a given category
- other categories remain untouched
- empty/nonexistent category returns 0 and doesn't crash
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


class TestDeleteSkillsByCategory:
    def test_removes_all_skills_in_category(self, knowledge_repo):
        """Deleting category 'Language' removes Python and Java but not React."""
        knowledge_repo.save_skill(name="Python", category="Language")
        knowledge_repo.save_skill(name="Java", category="Language")
        knowledge_repo.save_skill(name="React", category="Framework")

        deleted_count = knowledge_repo.delete_skills_by_category("Language")

        assert deleted_count == 2
        remaining_skills = knowledge_repo.list_skills()
        remaining_names = [skill["name"] for skill in remaining_skills]
        assert "Python" not in remaining_names
        assert "Java" not in remaining_names
        assert "React" in remaining_names

    def test_nonexistent_category_returns_zero(self, knowledge_repo):
        """Deleting a category that doesn't exist returns 0."""
        knowledge_repo.save_skill(name="Python", category="Language")

        deleted_count = knowledge_repo.delete_skills_by_category("NonExistent")

        assert deleted_count == 0
        assert len(knowledge_repo.list_skills()) == 1

    def test_empty_category_string_returns_zero(self, knowledge_repo):
        """Empty string category returns 0."""
        deleted_count = knowledge_repo.delete_skills_by_category("")
        assert deleted_count == 0
