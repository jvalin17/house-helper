"""FastAPI application entry point.

Runs as a Tauri sidecar process. Manages database lifecycle,
LLM provider setup, and agent registration.
"""

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

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
    row = _conn.execute("SELECT * FROM llm_config WHERE id = 1").fetchone()
    if not row:
        return {"provider": None, "model": None}
    result = dict(row)
    result.pop("id", None)
    return result


@app.put("/api/settings/llm")
def update_llm_config(config: dict):
    if not _conn:
        return {}
    _conn.execute(
        """INSERT OR REPLACE INTO llm_config (id, provider, model, base_url, config)
           VALUES (1, ?, ?, ?, ?)""",
        (
            config.get("provider"),
            config.get("model"),
            config.get("base_url"),
            json.dumps({k: v for k, v in config.items() if k not in ("provider", "model", "base_url")}),
        ),
    )
    _conn.commit()
    return {"status": "updated", **config}


@app.get("/api/settings/llm/providers")
def get_available_providers():
    return {"providers": list_available_providers()}


def _load_llm_provider(conn: sqlite3.Connection):
    """Load LLM provider from DB config, if configured."""
    row = conn.execute("SELECT * FROM llm_config WHERE id = 1").fetchone()
    if not row or not row["provider"]:
        return None

    config = {
        "provider": row["provider"],
        "model": row["model"],
        "base_url": row["base_url"],
    }
    extra = json.loads(row["config"]) if row["config"] else {}
    config.update(extra)

    try:
        return create_provider(config)
    except (ValueError, NotImplementedError):
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8040, reload=True)
