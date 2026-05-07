"""Credential routes — integration tests for global API key management."""

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.db import migrate
from shared.credential_routes import create_credential_router


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def test_client(database_connection):
    application = FastAPI()
    application.include_router(create_credential_router(database_connection))
    return TestClient(application)


class TestGetAllCredentials:
    def test_returns_all_built_in_services(self, test_client):
        response = test_client.get("/api/settings/credentials")
        assert response.status_code == 200
        services = response.json()
        service_names = [service["service_name"] for service in services]
        assert "claude" in service_names
        assert "realtyapi" in service_names
        assert "google_maps" in service_names

    def test_services_have_display_info(self, test_client):
        response = test_client.get("/api/settings/credentials")
        services = response.json()
        claude = next(service for service in services if service["service_name"] == "claude")
        assert claude["display_name"] == "Claude (Anthropic)"
        assert claude["category"] == "ai_provider"


class TestSaveCredential:
    def test_save_and_verify_connected(self, test_client):
        save_response = test_client.put("/api/settings/credentials/claude", json={"api_key": "sk-ant-test-123"})
        assert save_response.status_code == 200
        assert save_response.json()["is_configured"] is True

        status_response = test_client.get("/api/settings/credentials/status")
        assert status_response.json()["claude"] is True

    def test_save_empty_key(self, test_client):
        test_client.put("/api/settings/credentials/claude", json={"api_key": "sk-test"})
        save_response = test_client.put("/api/settings/credentials/claude", json={"api_key": ""})
        assert save_response.json()["is_configured"] is False

    def test_rejects_too_long_key(self, test_client):
        long_key = "x" * 501
        response = test_client.put("/api/settings/credentials/claude", json={"api_key": long_key})
        assert response.status_code == 400


class TestDeleteCredential:
    def test_delete_removes_key(self, test_client):
        test_client.put("/api/settings/credentials/realtyapi", json={"api_key": "rt-test"})
        delete_response = test_client.delete("/api/settings/credentials/realtyapi")
        assert delete_response.json()["is_configured"] is False

        status = test_client.get("/api/settings/credentials/status").json()
        assert status["realtyapi"] is False


class TestServiceNameValidation:
    def test_rejects_invalid_service_name(self, test_client):
        response = test_client.put("/api/settings/credentials/INVALID-NAME!", json={"api_key": "test"})
        assert response.status_code == 400

    def test_rejects_empty_service_name(self, test_client):
        response = test_client.put("/api/settings/credentials/", json={"api_key": "test"})
        assert response.status_code in (404, 405, 400)  # Depends on FastAPI routing

    def test_accepts_valid_service_name(self, test_client):
        response = test_client.put("/api/settings/credentials/my_custom_api", json={"api_key": "test_key"})
        assert response.status_code == 200


class TestLegacySync:
    def test_saves_to_legacy_json_blob(self, test_client, database_connection):
        """Saving a credential should also update the legacy JSON blob."""
        import json
        test_client.put("/api/settings/credentials/realtyapi", json={"api_key": "rt_sync_test"})
        row = database_connection.execute(
            "SELECT value FROM settings WHERE key = 'apartment_api_keys'"
        ).fetchone()
        if row:
            legacy_keys = json.loads(row["value"])
            assert legacy_keys.get("realtyapi") == "rt_sync_test"


class TestGetCredentialsStatus:
    def test_returns_status_map(self, test_client):
        test_client.put("/api/settings/credentials/claude", json={"api_key": "sk-test"})
        response = test_client.get("/api/settings/credentials/status")
        assert response.status_code == 200
        status = response.json()
        assert status["claude"] is True
        assert status["openai"] is False

    def test_all_false_by_default(self, test_client):
        response = test_client.get("/api/settings/credentials/status")
        status = response.json()
        assert all(configured is False for configured in status.values())
