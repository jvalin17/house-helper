"""Job board plugin protocol and shared types."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class SearchFilters:
    keywords: list[str] = field(default_factory=list)
    title: str | None = None
    location: str | None = None
    remote: bool | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    posted_within_days: int = 7


@dataclass
class JobResult:
    title: str
    company: str
    url: str
    location: str | None = None
    salary: str | None = None
    description: str = ""
    source: str = ""
    posted_date: str | None = None


@runtime_checkable
class JobBoardPlugin(Protocol):
    def search(self, filters: SearchFilters) -> list[JobResult]:
        """Search this board with given filters."""
        ...

    def board_name(self) -> str:
        """Return board identifier."""
        ...

    def requires_api_key(self) -> bool:
        """Whether this board needs an API key."""
        ...

    def is_available(self) -> bool:
        """Whether this board is currently usable."""
        ...
