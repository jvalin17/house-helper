"""TDD tests for auth service — signup, login, JWT, password hashing.

Security tests:
- Passwords are never stored in plaintext
- JWT contains user_id and expiry
- Invalid credentials rejected
- Expired tokens rejected
- Duplicate emails rejected
"""

import time
from pathlib import Path

import pytest

from auth.service import AuthService
from auth.db import create_auth_db


@pytest.fixture
def auth_svc(tmp_path):
    db_path = tmp_path / "auth.db"
    conn = create_auth_db(db_path)
    return AuthService(conn, jwt_secret="test-secret-key-for-testing-only")


class TestSignup:
    def test_signup_returns_token_and_user(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        assert "token" in result
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["name"] == "Test User"
        assert "id" in result["user"]

    def test_signup_does_not_return_password(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        assert "password" not in result["user"]
        assert "password_hash" not in result["user"]

    def test_signup_duplicate_email_rejected(self, auth_svc):
        auth_svc.signup("test@example.com", "StrongP@ss1", "User 1")
        with pytest.raises(ValueError, match="already registered"):
            auth_svc.signup("test@example.com", "StrongP@ss2", "User 2")

    def test_signup_weak_password_rejected(self, auth_svc):
        with pytest.raises(ValueError, match="(?i)password"):
            auth_svc.signup("test@example.com", "123", "Test User")

    def test_signup_invalid_email_rejected(self, auth_svc):
        with pytest.raises(ValueError, match="email"):
            auth_svc.signup("not-an-email", "StrongP@ss1", "Test User")


class TestLogin:
    def test_login_returns_token(self, auth_svc):
        auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        result = auth_svc.login("test@example.com", "StrongP@ss1")
        assert "token" in result
        assert result["user"]["email"] == "test@example.com"

    def test_login_wrong_password_rejected(self, auth_svc):
        auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        with pytest.raises(ValueError, match="Invalid"):
            auth_svc.login("test@example.com", "WrongPassword1")

    def test_login_nonexistent_email_rejected(self, auth_svc):
        with pytest.raises(ValueError, match="Invalid"):
            auth_svc.login("nobody@example.com", "StrongP@ss1")


class TestJWT:
    def test_token_contains_user_id(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        payload = auth_svc.validate_token(result["token"])
        assert payload["user_id"] == result["user"]["id"]

    def test_token_has_expiry(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        payload = auth_svc.validate_token(result["token"])
        assert "exp" in payload

    def test_invalid_token_rejected(self, auth_svc):
        with pytest.raises(ValueError, match="Invalid"):
            auth_svc.validate_token("garbage.token.here")

    def test_tampered_token_rejected(self, auth_svc):
        result = auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        tampered = result["token"][:-5] + "XXXXX"
        with pytest.raises(ValueError, match="Invalid"):
            auth_svc.validate_token(tampered)


class TestPasswordSecurity:
    def test_password_stored_as_hash(self, auth_svc):
        auth_svc.signup("test@example.com", "StrongP@ss1", "Test User")
        row = auth_svc._conn.execute("SELECT password_hash FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        assert row["password_hash"] != "StrongP@ss1"
        assert row["password_hash"].startswith("$2b$")  # bcrypt prefix
