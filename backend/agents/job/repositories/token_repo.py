"""Backward-compatible re-export. TokenRepository moved to shared/repositories/."""

from shared.repositories.token_repo import TokenRepository

__all__ = ["TokenRepository"]
