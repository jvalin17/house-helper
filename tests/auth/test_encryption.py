"""TDD tests for API key encryption — AES-256-GCM."""

import pytest

from auth.encryption import encrypt_value, decrypt_value, generate_encryption_key


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        key = generate_encryption_key()
        plaintext = "sk-ant-api03-abcdef123456"
        encrypted = encrypt_value(plaintext, key)
        decrypted = decrypt_value(encrypted, key)
        assert decrypted == plaintext

    def test_encrypted_is_not_plaintext(self):
        key = generate_encryption_key()
        plaintext = "sk-ant-api03-abcdef123456"
        encrypted = encrypt_value(plaintext, key)
        assert encrypted != plaintext
        assert "sk-ant" not in encrypted

    def test_different_encryptions_differ(self):
        """Each encryption produces different output (random IV)."""
        key = generate_encryption_key()
        plaintext = "sk-ant-api03-abcdef123456"
        enc1 = encrypt_value(plaintext, key)
        enc2 = encrypt_value(plaintext, key)
        assert enc1 != enc2  # random IV makes each unique

    def test_wrong_key_fails(self):
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        plaintext = "sk-ant-api03-abcdef123456"
        encrypted = encrypt_value(plaintext, key1)
        with pytest.raises(Exception):
            decrypt_value(encrypted, key2)

    def test_tampered_ciphertext_fails(self):
        key = generate_encryption_key()
        encrypted = encrypt_value("secret", key)
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(Exception):
            decrypt_value(tampered, key)

    def test_empty_string(self):
        key = generate_encryption_key()
        encrypted = encrypt_value("", key)
        decrypted = decrypt_value(encrypted, key)
        assert decrypted == ""

    def test_key_is_valid_length(self):
        key = generate_encryption_key()
        # Key should be base64-encoded 32-byte key
        assert len(key) > 30
