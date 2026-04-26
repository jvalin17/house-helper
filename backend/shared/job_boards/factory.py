"""Job board factory — returns all available board plugins.

Only includes legal API sources. No scraping.
"""

from shared.job_boards.base import JobBoardPlugin
from shared.job_boards.jsearch import JSearchPlugin
from shared.job_boards.adzuna import AdzunaPlugin
from shared.job_boards.remoteok import RemoteOKPlugin

ALL_BOARDS = [
    {"id": "jsearch", "name": "JSearch (LinkedIn, Indeed, Glassdoor via RapidAPI)", "signup": "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch", "free_tier": "500 requests/month"},
    {"id": "adzuna", "name": "Adzuna", "signup": "https://developer.adzuna.com", "free_tier": "250 requests/day"},
    {"id": "remoteok", "name": "RemoteOK (remote jobs only)", "signup": None, "free_tier": "Unlimited (no key needed)"},
]


def get_all_boards() -> list[JobBoardPlugin]:
    return [JSearchPlugin(), AdzunaPlugin(), RemoteOKPlugin()]


def get_available_boards() -> list[JobBoardPlugin]:
    return [b for b in get_all_boards() if b.is_available()]


def get_board_info() -> list[dict]:
    """Return info about all boards including availability status."""
    boards = get_all_boards()
    result = []
    for board, info in zip(boards, ALL_BOARDS):
        result.append({
            **info,
            "is_available": board.is_available(),
            "requires_api_key": board.requires_api_key(),
        })
    return result
