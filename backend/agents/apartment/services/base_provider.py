"""Base class for apartment search providers.

Every API source (RealtyAPI, RentCast, custom) implements this contract.
The search orchestrator loops through registered providers, handling
failures per-provider so one broken source never kills the search.
"""

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchCriteria:
    """Search parameters shared by all providers."""
    city: str | None = None
    zip_code: str | None = None
    bedrooms: int | None = None
    max_rent: float | None = None
    bathrooms: int | None = None


class ApartmentSearchProvider(ABC):
    """Contract that every apartment search adapter must implement."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name shown in UI, e.g. 'RealtyAPI'."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider has a valid API key saved."""
        ...

    @abstractmethod
    def search(self, criteria: SearchCriteria) -> list[dict]:
        """Run the search and return normalized listing dicts.

        Should RAISE on actual failures (network errors, auth errors).
        Return empty list only for "searched successfully, found nothing".
        The orchestrator catches exceptions and reports which sources failed.
        """
        ...
