"""Unified credential store — tests for API key management across all agents."""

import sqlite3

import pytest

from shared.db import migrate
from shared.credentials import CredentialStore


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def credential_store(database_connection):
    return CredentialStore(database_connection)


class TestGetAndSetKey:
    def test_get_key_returns_none_for_empty_built_in(self, credential_store):
        """Built-in services exist but have empty keys by default."""
        assert credential_store.get_key("claude") is None

    def test_set_and_get_key(self, credential_store):
        credential_store.set_key("claude", "sk-ant-test-key-123")
        assert credential_store.get_key("claude") == "sk-ant-test-key-123"

    def test_set_key_updates_existing(self, credential_store):
        credential_store.set_key("claude", "old-key")
        credential_store.set_key("claude", "new-key")
        assert credential_store.get_key("claude") == "new-key"

    def test_delete_key_clears_value(self, credential_store):
        credential_store.set_key("realtyapi", "rt_test_key")
        credential_store.delete_key("realtyapi")
        assert credential_store.get_key("realtyapi") is None

    def test_set_key_for_unknown_service_creates_custom(self, credential_store):
        credential_store.set_key("new_api", "custom_key_123")
        assert credential_store.get_key("new_api") == "custom_key_123"


class TestIsConfigured:
    def test_unconfigured_by_default(self, credential_store):
        assert credential_store.is_configured("claude") is False
        assert credential_store.is_configured("walkscore") is False

    def test_configured_after_setting_key(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        assert credential_store.is_configured("claude") is True

    def test_not_configured_after_deleting_key(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        credential_store.delete_key("claude")
        assert credential_store.is_configured("claude") is False


class TestGetAllServices:
    def test_returns_all_built_in_services(self, credential_store):
        services = credential_store.get_all_services()
        service_names = [service["service_name"] for service in services]
        assert "claude" in service_names
        assert "openai" in service_names
        assert "realtyapi" in service_names
        assert "rentcast" in service_names
        assert "google_maps" in service_names
        assert "adzuna" in service_names

    def test_services_have_display_info(self, credential_store):
        services = credential_store.get_all_services()
        claude_service = next(service for service in services if service["service_name"] == "claude")
        assert claude_service["display_name"] == "Claude (Anthropic)"
        assert claude_service["category"] == "ai_provider"
        assert "anthropic" in (claude_service["signup_url"] or "").lower()

    def test_shows_configured_status(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        services = credential_store.get_all_services()
        claude_service = next(service for service in services if service["service_name"] == "claude")
        assert claude_service["is_configured"] == 1

    def test_groups_by_category(self, credential_store):
        services = credential_store.get_all_services()
        categories = {service["category"] for service in services}
        assert "ai_provider" in categories
        assert "data_source" in categories


class TestGetConfiguredServices:
    def test_returns_empty_when_nothing_configured(self, credential_store):
        assert credential_store.get_configured_services() == []

    def test_returns_only_configured(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        credential_store.set_key("realtyapi", "rt-test")
        configured = credential_store.get_configured_services()
        assert "claude" in configured
        assert "realtyapi" in configured
        assert "openai" not in configured

    def test_filter_by_category(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        credential_store.set_key("realtyapi", "rt-test")
        ai_only = credential_store.get_configured_services(category="ai_provider")
        assert "claude" in ai_only
        assert "realtyapi" not in ai_only

    def test_auto_discovery_pattern(self, credential_store):
        """Agents use this to discover what's available without manual config."""
        credential_store.set_key("google_maps", "gm-key")
        # NestScout checks: is Google Maps available?
        available_data = credential_store.get_configured_services(category="data_source")
        assert "google_maps" in available_data
        # Travel agent would check the same — same key, no re-entry


class TestStatusMap:
    def test_returns_all_services_with_status(self, credential_store):
        credential_store.set_key("claude", "sk-test")
        status = credential_store.get_status_map()
        assert status["claude"] is True
        assert status["openai"] is False
        assert status["realtyapi"] is False


class TestBuiltInServicesSeeded:
    def test_13_built_in_services_exist(self, credential_store):
        services = credential_store.get_all_services()
        assert len(services) >= 13

    def test_ollama_has_no_signup_url(self, credential_store):
        """Ollama is local — no API key signup needed."""
        services = credential_store.get_all_services()
        ollama = next(service for service in services if service["service_name"] == "ollama")
        assert ollama["signup_url"] is None
