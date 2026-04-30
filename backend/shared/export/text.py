"""Plain text exporter — strips markdown formatting."""

import re


class TextExporter:
    def export(self, content: str, metadata: dict) -> bytes:
        text = _strip_markdown(content)
        return text.encode("utf-8")

    def format_name(self) -> str:
        return "txt"


def _strip_markdown(markdown_text: str) -> str:
    """Remove markdown formatting, keeping plain text."""
    text = markdown_text
    # Remove headers (# ## ###)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold **text** and __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # Remove italic *text* and _text_
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    # Remove link syntax [text](url)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Clean up extra blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
