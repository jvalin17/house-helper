"""FastAPI application entry point.

Runs as a Tauri sidecar process. Manages database lifecycle,
LLM provider setup, and agent registration.
"""

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
# Load .env — try multiple locations so it works in dev, desktop, and frozen binary
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".panini" / ".env")  # Desktop app users
load_dotenv(_project_root / ".env")                    # Dev (project root)
load_dotenv(Path.cwd() / ".env")                       # CWD fallback
load_dotenv(Path.cwd().parent / ".env")                # CWD parent fallback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from shared.db import connect_sync, get_db_path
from pydantic import BaseModel

from shared.llm.factory import list_available_providers
from coordinator import Coordinator
from auth.middleware import get_auth_mode, resolve_user_db_path, extract_token_from_header

_database_connection: sqlite3.Connection | None = None
_auth_service = None

# Public paths that don't require auth (even in multi mode)
PUBLIC_PATHS = {"/health", "/api/auth/signup", "/api/auth/login", "/api/auth/config", "/docs", "/openapi.json"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open DB, register agents. Shutdown: close DB."""
    global _database_connection, _auth_service

    auth_mode = get_auth_mode()

    # In multi mode, set up auth DB
    if auth_mode == "multi":
        from auth.db import create_auth_db
        from auth.service import AuthService
        from auth.routes import create_auth_router

        jwt_secret = os.environ.get("JWT_SECRET", "change-me-in-production-please")
        if jwt_secret == "change-me-in-production-please":
            import logging
            logging.getLogger("panini.auth").warning("Using default JWT secret — set JWT_SECRET env var for production")
        auth_db_path = Path.home() / ".panini" / "auth.db"
        auth_conn = create_auth_db(auth_db_path)
        _auth_service = AuthService(auth_conn, jwt_secret=jwt_secret)
        app.include_router(create_auth_router(_auth_service))

    # In local mode, use single shared DB (current behavior)
    _database_connection = connect_sync()

    # Give job boards access to DB for API keys
    from shared.job_boards.factory import set_db_connection
    set_db_connection(_database_connection)

    # Sync built-in services (adds new sources without requiring fresh DB)
    from shared.service_registry import sync_built_in_services
    sync_built_in_services(_database_connection)

    # Migrate existing keys to unified credential store
    from shared.credential_routes import create_credential_router, migrate_existing_keys_to_credentials
    migrate_existing_keys_to_credentials(_database_connection)
    app.include_router(create_credential_router(_database_connection))

    # Lazy LLM provider — reads from DB on each call, no restart needed
    from shared.llm.lazy_provider import LazyLLMProvider
    llm_provider = LazyLLMProvider(_database_connection)

    coordinator = Coordinator(conn=_database_connection, llm_provider=llm_provider)
    app.include_router(coordinator.get_router())

    yield

    if _database_connection:
        _database_connection.close()


app = FastAPI(
    title="Panini — Jobsmith",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8040", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle BudgetExceededError with 429 status so frontend can show confirmation."""
    from shared.llm.lazy_provider import BudgetExceededError
    if isinstance(exc, BudgetExceededError):
        return JSONResponse(status_code=429, content={"detail": exc.to_dict()})
    raise exc


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Auth middleware — in local mode, pass through. In multi mode, validate JWT."""
    auth_mode = get_auth_mode()

    if auth_mode == "local":
        # Desktop/local mode — no auth, use global connection
        request.state.user_id = None
        request.state.db_conn = _database_connection
        return await call_next(request)

    # Multi mode — check if public path
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
        request.state.user_id = None
        request.state.db_conn = None
        return await call_next(request)

    # Validate JWT
    auth_header = request.headers.get("authorization")
    token = extract_token_from_header(auth_header)
    if not token or not _auth_service:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    try:
        payload = _auth_service.validate_token(token)
        user_id = payload["user_id"]
    except ValueError:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    # Connect to user's isolated DB
    user_db_path = resolve_user_db_path(user_id)
    request.state.user_id = user_id
    request.state.db_conn = connect_sync(db_path=user_db_path)

    response = await call_next(request)

    # Close per-request connection
    if request.state.db_conn and request.state.db_conn != _database_connection:
        request.state.db_conn.close()

    return response


@app.get("/health")
def health():
    return {"status": "ok", "agents": ["job", "apartment"]}


@app.get("/api/settings/llm")
def get_llm_config(request: Request):
    if not _database_connection:
        return {}
    row = _database_connection.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
    if not row:
        return {"provider": None, "model": None}
    return json.loads(row["value"])


class LLMConfigUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


@app.put("/api/settings/llm")
def update_llm_config(config: LLMConfigUpdate):
    if not _database_connection:
        return {}
    config_dict = config.model_dump(exclude_none=True)
    # Merge with existing config — preserve api_key if not sent
    existing_row = _database_connection.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
    if existing_row:
        existing = json.loads(existing_row["value"])
        if "api_key" not in config_dict and existing.get("api_key"):
            config_dict["api_key"] = existing["api_key"]

    _database_connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('llm', ?, datetime('now'))",
        (json.dumps(config_dict),),
    )
    _database_connection.commit()
    return {"status": "saved", **config_dict}


@app.get("/api/settings/llm/status")
def get_llm_status():
    """Check if LLM is currently active and which model."""
    from shared.llm.lazy_provider import LazyLLMProvider
    if _database_connection:
        provider = LazyLLMProvider(_database_connection)
        return provider.get_status()
    return {"active": False}


@app.get("/api/settings/llm/providers")
def get_available_providers():
    return {"providers": list_available_providers()}


@app.get("/api/settings/ollama/status")
def check_ollama():
    """Check if Ollama is installed and running, list available models."""
    import httpx
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = [model_entry["name"] for model_entry in response.json().get("models", [])]
            return {"installed": True, "running": True, "models": models}
    except Exception:
        pass

    # Check if ollama binary exists
    import shutil
    has_binary = shutil.which("ollama") is not None

    return {
        "installed": has_binary,
        "running": False,
        "models": [],
        "install_instructions": {
            "mac": "brew install ollama && ollama serve",
            "linux": "curl -fsSL https://ollama.com/install.sh | sh && ollama serve",
            "windows": "Download from https://ollama.com/download",
            "pull_model": "ollama pull llama3.1",
        },
    }


@app.get("/api/settings/llm/models")
def get_models():
    """Return all available models with pricing info."""
    from shared.llm.pricing import get_all_models, estimate_resume_cost
    all_models = get_all_models()
    result = {}
    for provider, models in all_models.items():
        result[provider] = []
        for model in models:
            result[provider].append({
                **model,
                "est_per_resume": f"${estimate_resume_cost(provider, model['id']):.4f}",
            })
    return result


if __name__ == "__main__":
    import sys
    import uvicorn

    # Disable reload when running as PyInstaller frozen binary
    is_frozen = getattr(sys, "frozen", False)
    uvicorn.run("main:app", host="0.0.0.0", port=8040, reload=not is_frozen)
