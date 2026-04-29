"""Auth service — signup, login, JWT token management."""

import re
import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(self, conn: sqlite3.Connection, jwt_secret: str):
        self._conn = conn
        self._jwt_secret = jwt_secret

    def signup(self, email: str, password: str, name: str) -> dict:
        """Create a new user account."""
        self._validate_email(email)
        self._validate_password(password)

        # Check for duplicate
        existing = self._conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise ValueError("Email already registered")

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        cursor = self._conn.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, password_hash, name),
        )
        self._conn.commit()

        user_id = cursor.lastrowid
        user = {"id": user_id, "email": email, "name": name}
        token = self._issue_token(user_id)

        return {"token": token, "user": user}

    def login(self, email: str, password: str) -> dict:
        """Authenticate a user."""
        row = self._conn.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if not row:
            raise ValueError("Invalid email or password")

        if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            raise ValueError("Invalid email or password")

        user = {"id": row["id"], "email": row["email"], "name": row["name"]}
        token = self._issue_token(row["id"])

        return {"token": token, "user": user}

    def validate_token(self, token: str) -> dict:
        """Validate a JWT token and return the payload."""
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.InvalidTokenError:
            raise ValueError("Invalid or expired token")

    def get_user(self, user_id: int) -> dict | None:
        """Get user by ID (no password)."""
        row = self._conn.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id: int, name: str | None = None) -> dict | None:
        """Update user profile."""
        if name:
            self._conn.execute(
                "UPDATE users SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (name, user_id),
            )
            self._conn.commit()
        return self.get_user(user_id)

    def _issue_token(self, user_id: int) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm=JWT_ALGORITHM)

    @staticmethod
    def _validate_email(email: str) -> None:
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Invalid email format")

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
