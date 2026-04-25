"""Coordinator — routes requests to the right agent.

Thin for MVP (one agent). Extension point for future agents
(apartments, recipes, games).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter

from agents.job.routes import create_router as create_job_router


class Coordinator:
    """Manages agent registration and provides a combined router."""

    def __init__(self, conn: sqlite3.Connection, llm_provider=None):
        self._conn = conn
        self._llm = llm_provider
        self._agents: dict[str, APIRouter] = {}
        self._register_agents()

    def _register_agents(self):
        self._agents["job"] = create_job_router(self._conn, self._llm)

    def get_router(self) -> APIRouter:
        """Return a combined router with all agent routes."""
        combined = APIRouter()
        for router in self._agents.values():
            combined.include_router(router)
        return combined

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())
