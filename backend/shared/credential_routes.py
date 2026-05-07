"""Global credential management routes — shared across all agents.

GET  /api/settings/credentials         — all services with status
PUT  /api/settings/credentials/{name}  — save API key
DELETE /api/settings/credentials/{name} — remove API key
GET  /api/settings/credentials/status   — {service: is_configured} map
"""

import json
import sqlite3

import re

from fastapi import APIRouter
from pydantic import BaseModel

from shared.credentials import CredentialStore

SERVICE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,50}$")


class CredentialUpdate(BaseModel):
    api_key: str = ""

def create_credential_router(connection: sqlite3.Connection) -> APIRouter:
    """Create credential management router."""
    router = APIRouter(prefix="/api/settings")

    @router.get("/credentials/status")
    def get_credentials_status():
        """Return {service_name: is_configured} map — for auto-discovery."""
        return CredentialStore(connection).get_status_map()

    @router.get("/credentials")
    def get_all_credentials():
        """Get all API services with their status — for global settings UI."""
        return CredentialStore(connection).get_all_services()

    @router.put("/credentials/{service_name}")
    def save_credential(service_name: str, credential_data: CredentialUpdate):
        """Save API key for a service."""
        from fastapi import HTTPException
        if not SERVICE_NAME_PATTERN.match(service_name):
            raise HTTPException(400, detail="Invalid service name (lowercase letters, numbers, underscores only)")
        api_key = credential_data.api_key.strip()
        try:
            CredentialStore(connection).set_key(service_name, api_key)
        except ValueError as validation_error:
            raise HTTPException(400, detail=str(validation_error))
        _sync_credential_to_legacy(service_name, api_key, connection)
        return {"service": service_name, "is_configured": bool(api_key)}

    @router.delete("/credentials/{service_name}")
    def delete_credential(service_name: str):
        """Remove API key for a service."""
        from fastapi import HTTPException
        if not SERVICE_NAME_PATTERN.match(service_name):
            raise HTTPException(400, detail="Invalid service name")
        CredentialStore(connection).delete_key(service_name)
        _sync_credential_to_legacy(service_name, "", connection)
        return {"service": service_name, "is_configured": False}

    return router


def _sync_credential_to_legacy(service_name: str, api_key: str, connection: sqlite3.Connection) -> None:
    """Sync credential to legacy JSON blobs for backward compatibility."""
    apartment_sources = {"realtyapi", "rentcast", "walkscore", "google_maps"}
    job_sources = {"rapidapi", "adzuna_app_id", "adzuna_app_key", "adzuna_id", "adzuna_key"}

    if service_name in apartment_sources:
        _sync_to_json_blob(connection, "apartment_api_keys", service_name, api_key)
    elif service_name in job_sources:
        _sync_to_json_blob(connection, "api_keys", service_name, api_key)


def _sync_to_json_blob(connection: sqlite3.Connection, settings_key: str, service_name: str, api_key: str) -> None:
    """Update a JSON blob in the settings table."""
    row = connection.execute(
        "SELECT value FROM settings WHERE key = ?", (settings_key,)
    ).fetchone()
    existing = {}
    if row:
        try:
            existing = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    existing[service_name] = api_key
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (settings_key, json.dumps(existing)),
    )
    connection.commit()


def migrate_existing_keys_to_credentials(connection: sqlite3.Connection) -> None:
    """One-time migration: copy existing keys from JSON blobs to api_credentials."""
    credential_store = CredentialStore(connection)

    # Check if already migrated
    configured_count = len(credential_store.get_configured_services())
    if configured_count > 0:
        return  # Already has keys, skip migration

    import logging
    migration_logger = logging.getLogger("credential_migration")

    for settings_key in ("apartment_api_keys", "api_keys"):
        try:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?", (settings_key,)
            ).fetchone()
            if row:
                keys = json.loads(row["value"])
                for service_name, api_key in keys.items():
                    if api_key:
                        credential_store.set_key(service_name, api_key)
        except Exception as migration_error:
            migration_logger.warning("Failed to migrate %s keys: %s", settings_key, migration_error)

    # Migrate LLM API key
    try:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = 'llm'"
        ).fetchone()
        if row:
            config = json.loads(row["value"])
            provider_name = config.get("provider")
            api_key = config.get("api_key")
            if provider_name and api_key:
                credential_store.set_key(provider_name, api_key)
    except Exception as llm_migration_error:
        migration_logger.warning("Failed to migrate LLM key: %s", llm_migration_error)
