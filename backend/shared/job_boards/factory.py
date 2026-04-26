"""Job board factory — returns all available board plugins."""

from shared.job_boards.base import JobBoardPlugin
from shared.job_boards.jsearch import JSearchPlugin
from shared.job_boards.linkedin import LinkedInScraper
from shared.job_boards.indeed import IndeedScraper


def get_all_boards() -> list[JobBoardPlugin]:
    """Return all board plugins (available or not)."""
    return [JSearchPlugin(), LinkedInScraper(), IndeedScraper()]


def get_available_boards() -> list[JobBoardPlugin]:
    """Return only boards that are currently usable."""
    return [b for b in get_all_boards() if b.is_available()]
