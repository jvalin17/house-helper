"""AES-256-GCM encryption for API keys — encrypt at rest, decrypt on use."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_encryption_key() -> str:
    """Generate a random 256-bit key, base64-encoded for storage in .env."""
    raw_key = os.urandom(32)
    return base64.b64encode(raw_key).decode()


def encrypt_value(plaintext: str, key_b64: str) -> str:
    """Encrypt a string with AES-256-GCM. Returns base64-encoded nonce+ciphertext."""
    key = base64.b64decode(key_b64)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_value(encrypted_b64: str, key_b64: str) -> str:
    """Decrypt an AES-256-GCM encrypted string."""
    key = base64.b64decode(key_b64)
    data = base64.b64decode(encrypted_b64)
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
