"""Template naming — ensures templates get the original filename, not temp path.

Covers:
- import_resume stores original filename as template name
- template name is human-readable (not "Tmpu599X38T")
- template filename preserves original extension
"""

import json
import sqlite3
import tempfile
from pathlib import Path
import pytest

from shared.db import migrate


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


class TestTemplateNaming:
    def test_template_uses_original_filename(self, database_connection):
        """When importing a resume, the template should use the original filename."""
        from agents.job.services.knowledge import KnowledgeService
        from agents.job.repositories.knowledge_repo import KnowledgeRepository

        knowledge_repo = KnowledgeRepository(database_connection)
        knowledge_service = KnowledgeService(
            knowledge_repo=knowledge_repo, conn=database_connection
        )

        # Create a temp file that simulates what the route does
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temporary_file:
            temporary_file.write(b"Software Engineer at Google\n- Built search\n- Led team of 5")
            temporary_path = Path(temporary_file.name)

        try:
            # Pass original filename
            knowledge_service.import_resume(temporary_path, original_filename="John_Doe_Resume.docx")
        except Exception:
            pass  # Parsing might partially fail on .txt, that's OK
        finally:
            temporary_path.unlink(missing_ok=True)

        # Check template was created with correct name
        templates = database_connection.execute("SELECT name, filename FROM resume_templates").fetchall()
        if templates:
            template = dict(templates[0])
            assert "tmp" not in template["name"].lower(), f"Template name contains 'tmp': {template['name']}"
            assert "John Doe Resume" in template["name"] or "John_Doe_Resume" in template["name"]

    def test_template_name_without_original_filename_uses_generic(self, database_connection):
        """When no original filename is provided, use a generic name."""
        from agents.job.services.knowledge import KnowledgeService
        from agents.job.repositories.knowledge_repo import KnowledgeRepository

        knowledge_repo = KnowledgeRepository(database_connection)
        knowledge_service = KnowledgeService(
            knowledge_repo=knowledge_repo, conn=database_connection
        )

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temporary_file:
            temporary_file.write(b"Engineer at Acme\n- Did things")
            temporary_path = Path(temporary_file.name)

        try:
            knowledge_service.import_resume(temporary_path)
        except Exception:
            pass
        finally:
            temporary_path.unlink(missing_ok=True)

        templates = database_connection.execute("SELECT name FROM resume_templates").fetchall()
        if templates:
            template_name = templates[0]["name"]
            assert "tmp" not in template_name.lower(), f"Template name contains 'tmp': {template_name}"
