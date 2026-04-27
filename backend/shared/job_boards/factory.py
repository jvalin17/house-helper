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


_db_conn = None


def set_db_connection(conn):
    """Called once from main.py so boards can read API keys from settings table."""
    global _db_conn
    _db_conn = conn


def _get_api_keys() -> dict:
    """Read API keys from settings table, fallback to env vars."""
    import os
    import json
    keys = {
        "rapidapi": os.environ.get("RAPIDAPI_KEY"),
        "adzuna_id": os.environ.get("ADZUNA_APP_ID"),
        "adzuna_key": os.environ.get("ADZUNA_APP_KEY"),
    }
    if _db_conn:
        try:
            row = _db_conn.execute("SELECT value FROM settings WHERE key = 'api_keys'").fetchone()
            if row:
                db_keys = json.loads(row["value"])
                # DB overrides env vars
                if db_keys.get("rapidapi"): keys["rapidapi"] = db_keys["rapidapi"]
                if db_keys.get("adzuna_id"): keys["adzuna_id"] = db_keys["adzuna_id"]
                if db_keys.get("adzuna_key"): keys["adzuna_key"] = db_keys["adzuna_key"]
        except Exception:
            pass
    return keys


def get_all_boards() -> list[JobBoardPlugin]:
    keys = _get_api_keys()
    return [
        JSearchPlugin(api_key=keys.get("rapidapi")),
        AdzunaPlugin(app_id=keys.get("adzuna_id"), app_key=keys.get("adzuna_key")),
        RemoteOKPlugin(),
    ]


def get_available_boards() -> list[JobBoardPlugin]:
    """Return available boards. If a premium source (JSearch/Adzuna) is available,
    skip free generic sources (RemoteOK) to keep results relevant."""
    all_boards = get_all_boards()
    available = [b for b in all_boards if b.is_available()]

    # If any API-key board is available, skip free generic ones
    has_premium = any(b.requires_api_key() and b.is_available() for b in all_boards)
    if has_premium:
        return [b for b in available if b.requires_api_key()]

    return available


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
