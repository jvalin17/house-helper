"""Markdown exporter — passthrough, encodes to UTF-8 bytes."""


class MarkdownExporter:
    def export(self, content: str, metadata: dict) -> bytes:
        return content.encode("utf-8")

    def format_name(self) -> str:
        return "md"
