"""Clear data per tab — tests for reset_knowledge_bank and budget limit persistence.

Covers:
- reset_knowledge_bank clears experiences, skills, education, projects
- reset_knowledge_bank preserves jobs, applications, settings
- budget daily_limit_cost persists and is returned correctly in GET /budget
- budget daily_limit_cost can be set and cleared
"""

import json
import sqlite3
import pytest

from shared.db import migrate


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class TestResetKnowledgeBank:
    def test_clears_experiences_skills_education_projects(self, database_connection):
        """reset_knowledge_bank should remove all KB entries."""
        # Seed some data
        database_connection.execute(
            "INSERT INTO experiences (profile_id, type, title, company, description) VALUES (1, 'work', 'Engineer', 'Acme', 'Built things')"
        )
        database_connection.execute(
            "INSERT INTO skills (profile_id, name, category) VALUES (1, 'Python', 'Language')"
        )
        database_connection.execute(
            "INSERT INTO education (institution, degree, field) VALUES ('MIT', 'BS', 'CS')"
        )
        database_connection.execute(
            "INSERT INTO projects (name, description) VALUES ('App', 'A cool app')"
        )
        database_connection.commit()

        from agents.job.services.reset import reset_knowledge_bank
        result = reset_knowledge_bank(database_connection)

        assert result["experiences_deleted"] == 1
        assert result["skills_deleted"] == 1
        assert result["education_deleted"] == 1
        assert result["projects_deleted"] == 1

        # Verify actually empty
        assert database_connection.execute("SELECT COUNT(*) FROM experiences").fetchone()[0] == 0
        assert database_connection.execute("SELECT COUNT(*) FROM skills").fetchone()[0] == 0
        assert database_connection.execute("SELECT COUNT(*) FROM education").fetchone()[0] == 0
        assert database_connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0

    def test_preserves_jobs_and_settings(self, database_connection):
        """reset_knowledge_bank should NOT touch jobs or settings."""
        database_connection.execute(
            "INSERT INTO jobs (profile_id, title, company, parsed_data) VALUES (1, 'Dev', 'Co', '{}')"
        )
        database_connection.execute(
            "INSERT INTO experiences (profile_id, type, title, company, description) VALUES (1, 'work', 'Eng', 'Co', 'x')"
        )
        database_connection.commit()

        from agents.job.services.reset import reset_knowledge_bank
        reset_knowledge_bank(database_connection)

        assert database_connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
        assert database_connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0] > 0


class TestBudgetLimitPersistence:
    def test_set_and_get_daily_limit(self, database_connection):
        """Setting daily_limit_cost should persist and be returned in get_budget."""
        from agents.job.repositories.token_repo import TokenRepository
        token_repository = TokenRepository(database_connection)

        token_repository.set_budget(daily_limit_cost=0.75)
        budget = token_repository.get_budget()
        assert budget["daily_limit_cost"] == 0.75

    def test_daily_limit_returned_in_remaining(self, database_connection):
        """get_remaining_today should include the budget with daily_limit_cost."""
        from agents.job.repositories.token_repo import TokenRepository
        token_repository = TokenRepository(database_connection)

        token_repository.set_budget(daily_limit_cost=1.50)
        remaining = token_repository.get_remaining_today()
        assert remaining["budget"]["daily_limit_cost"] == 1.50
        assert remaining["remaining_cost"] == 1.50

    def test_clear_daily_limit(self, database_connection):
        """Setting daily_limit_cost to None removes the limit."""
        from agents.job.repositories.token_repo import TokenRepository
        token_repository = TokenRepository(database_connection)

        token_repository.set_budget(daily_limit_cost=0.50)
        token_repository.set_budget(daily_limit_cost=None)
        budget = token_repository.get_budget()
        assert budget["daily_limit_cost"] is None

    def test_remaining_is_none_when_no_limit(self, database_connection):
        """With no limit, remaining_cost should be None."""
        from agents.job.repositories.token_repo import TokenRepository
        token_repository = TokenRepository(database_connection)

        token_repository.set_budget(daily_limit_cost=None)
        remaining = token_repository.get_remaining_today()
        assert remaining["remaining_cost"] is None
