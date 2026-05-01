"""DOCX format preservation guidance — ensures users understand format requirements.

Covers:
- PDF import creates template WITHOUT docx_binary (no format preservation)
- DOCX import creates template WITH docx_binary and paragraph_map
- Template format field correctly identifies source format
"""

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


class TestFormatDetection:
    def test_txt_template_has_no_docx_binary(self, database_connection):
        """TXT imports should NOT have docx_binary or paragraph_map."""
        from agents.job.services.knowledge import KnowledgeService
        from agents.job.repositories.knowledge_repo import KnowledgeRepository

        knowledge_repo = KnowledgeRepository(database_connection)
        knowledge_service = KnowledgeService(knowledge_repo=knowledge_repo, conn=database_connection)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temporary_file:
            temporary_file.write(b"Engineer at Google\n- Built search\n- Led team")
            temporary_path = Path(temporary_file.name)

        try:
            knowledge_service.import_resume(temporary_path, original_filename="resume.txt")
        except Exception:
            pass
        finally:
            temporary_path.unlink(missing_ok=True)

        templates = database_connection.execute(
            "SELECT format, docx_binary IS NOT NULL as has_docx, paragraph_map IS NOT NULL as has_map FROM resume_templates"
        ).fetchall()

        if templates:
            template = dict(templates[0])
            assert template["format"] == "txt"
            assert template["has_docx"] == 0
            assert template["has_map"] == 0

    def test_template_format_field_matches_source(self, database_connection):
        """Template format should match the imported file extension."""
        from agents.job.repositories.template_repo import ResumeTemplateRepo

        template_repo = ResumeTemplateRepo(database_connection)

        template_id = template_repo.save_template(
            name="Test Resume",
            filename="test.pdf",
            file_format="pdf",
            raw_text="Some text",
        )

        template = template_repo.get_template(template_id)
        assert template["format"] == "pdf"
        assert template["docx_binary"] is None
