"""FastAPI application entry point.

Runs as a Tauri sidecar process. Manages database lifecycle,
LLM provider setup, and agent registration.
"""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
# Load .env from project root (works regardless of cwd)
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")
# Also try cwd in case running from project root
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path.cwd().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.db import connect_sync, get_db_path
from shared.llm.factory import create_provider, list_available_providers
from coordinator import Coordinator

_conn: sqlite3.Connection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open DB, register agents. Shutdown: close DB."""
    global _conn
    _conn = connect_sync()

    # Give job boards access to DB for API keys
    from shared.job_boards.factory import set_db_connection
    set_db_connection(_conn)

    # Seed API keys from env vars into DB (one-time, env → DB migration)
    _seed_api_keys_from_env(_conn)

    # Try to load LLM config from DB
    llm_provider = _load_llm_provider(_conn)

    coordinator = Coordinator(conn=_conn, llm_provider=llm_provider)
    app.include_router(coordinator.get_router())

    yield

    if _conn:
        _conn.close()


app = FastAPI(
    title="House Helper — Job Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri frontend on localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "agents": ["job"]}


@app.get("/api/settings/llm")
def get_llm_config():
    if not _conn:
        return {}
    row = _conn.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
    if not row:
        return {"provider": None, "model": None}
    return json.loads(row["value"])


@app.put("/api/settings/llm")
def update_llm_config(config: dict):
    if not _conn:
        return {}
    _conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('llm', ?, datetime('now'))",
        (json.dumps(config),),
    )
    _conn.commit()
    return {"status": "updated", **config}


@app.get("/api/settings/llm/providers")
def get_available_providers():
    return {"providers": list_available_providers()}


@app.get("/api/settings/ollama/status")
def check_ollama():
    """Check if Ollama is installed and running, list available models."""
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
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


@app.get("/api/settings/api-keys")
def get_api_keys():
    """Get configured API keys (masked)."""
    from shared.job_boards.factory import _get_api_keys
    keys = _get_api_keys()
    return {k: f"{v[:8]}..." if v else None for k, v in keys.items()}


@app.put("/api/settings/api-keys")
def set_api_keys(data: dict):
    """Save API keys to settings table."""
    if not _conn:
        return {}
    _conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('api_keys', ?, datetime('now'))",
        (json.dumps(data),),
    )
    _conn.commit()
    # Refresh factory
    from shared.job_boards.factory import set_db_connection
    set_db_connection(_conn)
    return {"status": "saved"}


def _seed_api_keys_from_env(conn: sqlite3.Connection):
    """On first run, copy any API keys from env vars to settings table."""
    import os
    row = conn.execute("SELECT value FROM settings WHERE key = 'api_keys'").fetchone()
    if row:
        return  # already has keys in DB, don't overwrite

    keys = {}
    if os.environ.get("RAPIDAPI_KEY"):
        keys["rapidapi"] = os.environ["RAPIDAPI_KEY"]
    if os.environ.get("ADZUNA_APP_ID"):
        keys["adzuna_id"] = os.environ["ADZUNA_APP_ID"]
    if os.environ.get("ADZUNA_APP_KEY"):
        keys["adzuna_key"] = os.environ["ADZUNA_APP_KEY"]

    if keys:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('api_keys', ?, datetime('now'))",
            (json.dumps(keys),),
        )
        conn.commit()


def _load_llm_provider(conn: sqlite3.Connection):
    """Load LLM provider from settings table."""
    row = conn.execute("SELECT value FROM settings WHERE key = 'llm'").fetchone()
    if not row:
        return None

    config = json.loads(row["value"])
    if not config.get("provider"):
        return None

    # Inject API key from env or DB api_keys
    import os
    if config["provider"] == "claude" and not config.get("api_key"):
        config["api_key"] = os.environ.get("ANTHROPIC_API_KEY")
    if config["provider"] == "openai" and not config.get("api_key"):
        config["api_key"] = os.environ.get("OPENAI_API_KEY")

    try:
        return create_provider(config)
    except (ValueError, NotImplementedError) as e:
        print(f"[llm] Failed to load provider: {e}")
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8040, reload=True)
