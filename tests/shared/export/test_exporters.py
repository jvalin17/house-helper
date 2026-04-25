"""Tests for all exporters — PDF, DOCX, TXT, MD."""

from pathlib import Path

import pytest

from shared.export.base import Exporter
from shared.export.markdown import MarkdownExporter
from shared.export.text import TextExporter
from shared.export.pdf import PdfExporter
from shared.export.docx import DocxExporter

SAMPLE_MARKDOWN = """# John Doe

## Experience

### Senior Engineer — Acme Corp
*2020-01 — 2023-06*

Built scalable APIs with Python and FastAPI.

## Skills

**Languages:** Python, TypeScript
**Frameworks:** FastAPI, React
"""


class TestMarkdownExporter:
    def test_implements_protocol(self):
        assert isinstance(MarkdownExporter(), Exporter)

    def test_export_returns_bytes(self):
        result = MarkdownExporter().export(SAMPLE_MARKDOWN, {})
        assert isinstance(result, bytes)

    def test_export_preserves_content(self):
        result = MarkdownExporter().export(SAMPLE_MARKDOWN, {})
        assert b"John Doe" in result
        assert b"Acme Corp" in result

    def test_format_name(self):
        assert MarkdownExporter().format_name() == "md"


class TestTextExporter:
    def test_implements_protocol(self):
        assert isinstance(TextExporter(), Exporter)

    def test_strips_markdown_headers(self):
        result = TextExporter().export(SAMPLE_MARKDOWN, {})
        text = result.decode("utf-8")
        assert "John Doe" in text
        # Should strip # characters
        assert "# John" not in text

    def test_strips_bold_and_italic(self):
        result = TextExporter().export("**bold** and *italic*", {})
        text = result.decode("utf-8")
        assert "bold" in text
        assert "**" not in text

    def test_format_name(self):
        assert TextExporter().format_name() == "txt"


class TestPdfExporter:
    def test_implements_protocol(self):
        assert isinstance(PdfExporter(), Exporter)

    def test_export_returns_bytes(self):
        result = PdfExporter().export(SAMPLE_MARKDOWN, {})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_is_valid_pdf(self):
        result = PdfExporter().export(SAMPLE_MARKDOWN, {})
        # PDF files start with %PDF
        assert result[:5] == b"%PDF-"

    def test_format_name(self):
        assert PdfExporter().format_name() == "pdf"


class TestDocxExporter:
    def test_implements_protocol(self):
        assert isinstance(DocxExporter(), Exporter)

    def test_export_returns_bytes(self):
        result = DocxExporter().export(SAMPLE_MARKDOWN, {})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_is_valid_docx(self):
        result = DocxExporter().export(SAMPLE_MARKDOWN, {})
        # DOCX files are ZIP archives starting with PK
        assert result[:2] == b"PK"

    def test_format_name(self):
        assert DocxExporter().format_name() == "docx"

    def test_export_to_file(self, tmp_path):
        result = DocxExporter().export(SAMPLE_MARKDOWN, {})
        path = tmp_path / "test.docx"
        path.write_bytes(result)
        assert path.exists()
        assert path.stat().st_size > 0
