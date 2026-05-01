"""Save by category — TDD tests for saving extracted items to correct table.

When type="project", the entry should go to the projects table.
When type="job" or "volunteering", the entry should go to the experiences table.
When type="education", the entry should go to the education table.

Covers:
- type="project" saves to projects table
- type="job" saves to experiences table
- type="volunteering" saves to experiences table
- type="education" saves to education table
"""

import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

from shared.db import migrate


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def test_client(database_connection):
    from agents.job.routes import create_router
    from fastapi import FastAPI

    application = FastAPI()
    router = create_router(database_connection)
    application.include_router(router)
    return TestClient(application)


class TestSaveByCategory:
    def test_type_project_saves_to_projects_table(self, test_client, database_connection):
        """When type='project', the item should be saved to the projects table."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "project",
            "title": "Judgement Card Game",
            "description": "A trick-taking card game",
        })
        assert response.status_code == 200

        projects = database_connection.execute("SELECT * FROM projects").fetchall()
        assert len(projects) == 1
        assert projects[0]["name"] == "Judgement Card Game"
        assert projects[0]["description"] == "A trick-taking card game"

    def test_type_job_saves_to_experiences_table(self, test_client, database_connection):
        """When type='job', the item should be saved to the experiences table."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "job",
            "title": "Software Engineer",
            "company": "Google",
            "description": "Built search systems",
        })
        assert response.status_code == 200

        experiences = database_connection.execute("SELECT * FROM experiences WHERE type = 'job'").fetchall()
        assert len(experiences) == 1
        assert experiences[0]["title"] == "Software Engineer"
        assert experiences[0]["company"] == "Google"

    def test_type_volunteering_saves_to_experiences_table(self, test_client, database_connection):
        """Volunteering is stored in experiences table with type='volunteering'."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "volunteering",
            "title": "Mentor",
            "company": "Code.org",
            "description": "Mentored 20 students in Python",
        })
        assert response.status_code == 200

        experiences = database_connection.execute("SELECT * FROM experiences WHERE type = 'volunteering'").fetchall()
        assert len(experiences) == 1
        assert experiences[0]["title"] == "Mentor"
        assert experiences[0]["company"] == "Code.org"

    def test_source_url_stored_in_project_url_field(self, test_client, database_connection):
        """When saving a project with source_url, it goes to the project's url column."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "project",
            "title": "Judgement Card Game",
            "description": "A trick-taking card game",
            "source_url": "https://github.com/alexjohnson/judgement",
        })
        assert response.status_code == 200

        project = database_connection.execute("SELECT url FROM projects WHERE name = 'Judgement Card Game'").fetchone()
        assert project["url"] == "https://github.com/alexjohnson/judgement"

    def test_source_url_stored_in_experience_metadata(self, test_client, database_connection):
        """When saving an experience with source_url, it goes to metadata JSON."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "volunteering",
            "title": "Mentor",
            "company": "Code.org",
            "description": "Mentored students",
            "source_url": "https://code.org/about",
        })
        assert response.status_code == 200

        import json as json_module
        experience = database_connection.execute(
            "SELECT metadata FROM experiences WHERE title = 'Mentor'"
        ).fetchone()
        metadata = json_module.loads(experience["metadata"])
        assert metadata["source_url"] == "https://code.org/about"

    def test_type_education_saves_to_education_table(self, test_client, database_connection):
        """When type='education', the item should be saved to the education table."""
        response = test_client.post("/api/knowledge/entries", json={
            "type": "education",
            "title": "BS Computer Science",
            "company": "MIT",
            "description": "Graduated with honors",
        })
        assert response.status_code == 200

        education_entries = database_connection.execute("SELECT * FROM education").fetchall()
        assert len(education_entries) == 1
        assert education_entries[0]["degree"] == "BS Computer Science"
        assert education_entries[0]["institution"] == "MIT"
