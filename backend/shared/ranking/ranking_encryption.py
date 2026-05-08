"""Encryption for ranking behavioral data — zero developer access.

All term weights and interaction terms are encrypted at rest using Fernet
symmetric encryption. Key is generated randomly on first use and persisted
to ~/.panini/ranking.key (chmod 600). Developers cannot decrypt the data
even with DB file access.
"""

import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from shared.app_logger import get_logger

logger = get_logger("ranking.encryption")

RANKING_KEY_PATH = Path.home() / ".panini" / "ranking.key"

# Cache the Fernet instance — key is read once per process
_fernet_instance: Fernet | None = None


def _get_or_create_key() -> bytes:
    """Get existing key or generate a new one on first use.

    Key is a random 32-byte Fernet key, persisted to disk with 0600 permissions.
    This is stable across restarts — unlike MAC-address derivation which breaks
    on VMs, containers, and network adapter changes.
    """
    if RANKING_KEY_PATH.exists():
        return RANKING_KEY_PATH.read_bytes().strip()

    # Generate new random key
    new_key = Fernet.generate_key()

    # Save with restricted permissions (owner read/write only)
    RANKING_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    RANKING_KEY_PATH.write_bytes(new_key)
    try:
        os.chmod(RANKING_KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass  # Windows doesn't support Unix permissions

    logger.info("Generated new ranking encryption key at %s", RANKING_KEY_PATH)
    return new_key


def _get_fernet() -> Fernet:
    """Get or create the cached Fernet instance."""
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_get_or_create_key())
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
