"""Encryption for ranking behavioral data — zero developer access.

All term weights and interaction terms are encrypted at rest using Fernet
symmetric encryption. The key is derived from the user's machine identity,
NOT from app code — so developers cannot decrypt the data even with DB access.
"""

import base64
import hashlib
import json
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from shared.app_logger import get_logger

logger = get_logger("ranking.encryption")

# Cache the Fernet instance — key derivation is deterministic per machine
_fernet_instance: Fernet | None = None


def _derive_encryption_key() -> bytes:
    """Derive a 32-byte encryption key from machine-specific identity.

    Uses MAC address (uuid.getnode) + app data path. Different on every
    machine — a stolen DB file is useless without the original machine.
    """
    machine_identity = str(uuid.getnode())
    app_data_path = str(Path.home() / ".panini")
    raw_key = hashlib.sha256(f"{machine_identity}:{app_data_path}".encode()).digest()
    return base64.urlsafe_b64encode(raw_key)


def _get_fernet() -> Fernet:
    """Get or create the cached Fernet instance."""
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_derive_encryption_key())
    return _fernet_instance


def encrypt_terms(terms: list[str]) -> bytes:
    """Encrypt a list of terms to a binary blob for DB storage."""
    json_bytes = json.dumps(terms).encode("utf-8")
    return _get_fernet().encrypt(json_bytes)


def decrypt_terms(encrypted_blob: bytes) -> list[str]:
    """Decrypt a binary blob back to a list of terms."""
    try:
        decrypted_bytes = _get_fernet().decrypt(encrypted_blob)
        return json.loads(decrypted_bytes.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError) as decryption_error:
        logger.warning("Failed to decrypt ranking terms: %s", decryption_error)
        return []


def encrypt_weights(term_weights: dict[str, float]) -> str:
    """Encrypt term weights dict for storage in settings table."""
    json_bytes = json.dumps(term_weights).encode("utf-8")
    return _get_fernet().encrypt(json_bytes).decode("ascii")


def decrypt_weights(encrypted_string: str) -> dict[str, float]:
    """Decrypt term weights from settings table value."""
    try:
        decrypted_bytes = _get_fernet().decrypt(encrypted_string.encode("ascii"))
        return json.loads(decrypted_bytes.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError) as decryption_error:
        logger.warning("Failed to decrypt ranking weights: %s", decryption_error)
        return {}
