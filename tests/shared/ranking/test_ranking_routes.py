"""Ranking routes — tests for interaction endpoint validation.

Covers: valid interaction recorded, invalid agent rejected, invalid type rejected,
negative duration rejected, missing fields rejected.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from shared.db import migrate
from shared.ranking.routes import create_ranking_router


@pytest.fixture
def test_client():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)

    app = FastAPI()
    app.include_router(create_ranking_router(connection))
    client = TestClient(app)
    yield client
    connection.close()


def test_valid_interaction_recorded(test_client):
    """Valid interaction returns 200 with recorded status."""
    response = test_client.post("/api/ranking/interact", json={
        "agent": "job",
        "entity_id": 42,
        "interaction_type": "click",
        "terms": ["python", "remote"],
    })
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
    assert response.json()["interaction_id"] > 0


def test_invalid_agent_returns_400(test_client):
    """Invalid agent name returns 400."""
    response = test_client.post("/api/ranking/interact", json={
        "agent": "recipes",
        "entity_id": 1,
        "interaction_type": "click",
    })
    assert response.status_code == 400
    assert "Invalid agent" in response.json()["detail"]


def test_invalid_interaction_type_returns_400(test_client):
    """Invalid interaction type returns 400."""
    response = test_client.post("/api/ranking/interact", json={
        "agent": "job",
        "entity_id": 1,
        "interaction_type": "dislike",
    })
    assert response.status_code == 400
    assert "Invalid interaction type" in response.json()["detail"]


def test_negative_duration_rejected(test_client):
    """Negative duration_seconds rejected by Pydantic validation."""
    response = test_client.post("/api/ranking/interact", json={
        "agent": "job",
        "entity_id": 1,
        "interaction_type": "click",
        "duration_seconds": -5,
    })
    assert response.status_code == 422  # Pydantic validation error


def test_duration_over_3600_rejected(test_client):
    """Duration over 3600 seconds rejected."""
    response = test_client.post("/api/ranking/interact", json={
        "agent": "job",
        "entity_id": 1,
        "interaction_type": "click",
        "duration_seconds": 9999,
    })
    assert response.status_code == 422


def test_missing_required_fields_rejected(test_client):
    """Missing agent or entity_id returns 422."""
    response = test_client.post("/api/ranking/interact", json={
        "interaction_type": "click",
    })
    assert response.status_code == 422


def test_profile_endpoint_cold_start(test_client):
    """Profile endpoint returns cold_start when no weights exist."""
    response = test_client.get("/api/ranking/profile/job")
    assert response.status_code == 200
    assert response.json()["status"] == "cold_start"


def test_profile_invalid_agent(test_client):
    """Profile endpoint rejects invalid agent."""
    response = test_client.get("/api/ranking/profile/recipes")
    assert response.status_code == 400
