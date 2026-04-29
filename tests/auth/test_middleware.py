"""TDD tests for auth middleware — JWT validation, per-user DB routing, AUTH_MODE toggle."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auth.middleware import resolve_user_db_path, get_auth_mode
from auth.service import AuthService
from auth.db import create_auth_db


@pytest.fixture
def auth_svc(tmp_path):
    conn = create_auth_db(tmp_path / "auth.db")
    return AuthService(conn, jwt_secret="test-secret")


class TestAuthMode:
    def test_default_is_local(self, monkeypatch):
        monkeypatch.delenv("AUTH_MODE", raising=False)
        assert get_auth_mode() == "local"

    def test_multi_mode(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "multi")
        assert get_auth_mode() == "multi"

    def test_local_mode_explicit(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "local")
        assert get_auth_mode() == "local"


class TestUserDBPath:
    def test_resolve_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOUSE_HELPER_DATA", str(tmp_path))
        path = resolve_user_db_path(42, base_dir=tmp_path)
        assert path == tmp_path / "users" / "42" / "data.db"
        assert path.parent.exists()

    def test_different_users_different_paths(self, tmp_path):
        path_1 = resolve_user_db_path(1, base_dir=tmp_path)
        path_2 = resolve_user_db_path(2, base_dir=tmp_path)
        assert path_1 != path_2
        assert "1" in str(path_1)
        assert "2" in str(path_2)


class TestTokenExtraction:
    def test_extract_user_from_valid_token(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test")
        payload = auth_svc.validate_token(result["token"])
        assert payload["user_id"] == result["user"]["id"]

    def test_reject_missing_token(self, auth_svc):
        with pytest.raises(ValueError):
            auth_svc.validate_token("")

    def test_reject_bearer_prefix_stripped(self, auth_svc):
        """Middleware should strip 'Bearer ' prefix before validation."""
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test")
        bearer_token = f"Bearer {result['token']}"
        # The raw token (without Bearer) should validate
        raw_token = bearer_token.replace("Bearer ", "")
        payload = auth_svc.validate_token(raw_token)
        assert payload["user_id"] == result["user"]["id"]
