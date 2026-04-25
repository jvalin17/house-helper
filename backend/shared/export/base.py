"""Exporter protocol — the interface all format exporters implement."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Exporter(Protocol):
    def export(self, content: str, metadata: dict) -> bytes:
        """Convert markdown content to the target format. Returns bytes."""
        ...

    def format_name(self) -> str:
        """Return the format identifier (e.g., 'pdf', 'docx', 'md', 'txt')."""
        ...
