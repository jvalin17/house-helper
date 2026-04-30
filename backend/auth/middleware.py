"""Auth middleware — JWT validation, per-user DB routing, AUTH_MODE toggle.

AUTH_MODE=local: no auth, single DB (desktop/Tauri mode)
AUTH_MODE=multi: JWT required, per-user SQLite file
"""

import os
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".sahaiy"


def get_auth_mode() -> str:
    """Get current auth mode from environment."""
    return os.environ.get("AUTH_MODE", "local")


def resolve_user_db_path(user_id: int, base_dir: Path | None = None) -> Path:
    """Resolve the SQLite DB path for a specific user."""
    base = base_dir or DEFAULT_DATA_DIR
    user_dir = base / "users" / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "data.db"


def extract_token_from_header(authorization: str | None) -> str | None:
    """Extract JWT token from Authorization header, stripping 'Bearer ' prefix."""
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization
