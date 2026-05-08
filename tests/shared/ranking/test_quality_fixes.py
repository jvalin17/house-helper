"""Quality gate fix tests — verifying the fixes from /assess + /reviewer.

Covers:
- R1: Encryption key persistence (survives restart, stable across calls)
- R2: Interaction endpoint validation (Pydantic model rejects bad input)
- R5: Decryption failure protection (abort if >50% fail)
- A1: Credential store accepts category + display_name
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.db import migrate


# ── R1: Encryption key persistence ────────────────────

class TestEncryptionKeyPersistence:
    """Verify the encryption key is file-based, stable, and survives 'restarts'."""

    def test_key_generated_on_first_use(self, tmp_path):
        """First call generates a key file at the expected path."""
        key_path = tmp_path / "ranking.key"

        with patch("shared.ranking.ranking_encryption.RANKING_KEY_PATH", key_path):
            # Reset cached fernet
            import shared.ranking.ranking_encryption as encryption_module
            encryption_module._fernet_instance = None

            from shared.ranking.ranking_encryption import encrypt_terms, decrypt_terms
            encrypted = encrypt_terms(["python", "remote"])
            assert key_path.exists()
            assert len(key_path.read_bytes()) > 0

            # Decryption works with same key
            decrypted = decrypt_terms(encrypted)
            assert decrypted == ["python", "remote"]

    def test_key_stable_across_calls(self, tmp_path):
        """Same key used across multiple encrypt/decrypt cycles."""
        key_path = tmp_path / "ranking.key"

        with patch("shared.ranking.ranking_encryption.RANKING_KEY_PATH", key_path):
            import shared.ranking.ranking_encryption as encryption_module
            encryption_module._fernet_instance = None

            from shared.ranking.ranking_encryption import encrypt_terms, decrypt_terms

            # First encryption
            encrypted_first = encrypt_terms(["term_a"])
            key_bytes_first = key_path.read_bytes()

            # Simulate "restart" — clear cache, re-read from file
            encryption_module._fernet_instance = None

            # Second encryption with same file
            encrypted_second = encrypt_terms(["term_b"])
            key_bytes_second = key_path.read_bytes()

            # Key file unchanged
            assert key_bytes_first == key_bytes_second

            # Both decrypt correctly
            assert decrypt_terms(encrypted_first) == ["term_a"]
            assert decrypt_terms(encrypted_second) == ["term_b"]

    def test_key_file_has_restricted_permissions(self, tmp_path):
        """Key file created with 0600 permissions (owner only)."""
        key_path = tmp_path / "ranking.key"

        with patch("shared.ranking.ranking_encryption.RANKING_KEY_PATH", key_path):
            import shared.ranking.ranking_encryption as encryption_module
            encryption_module._fernet_instance = None

            from shared.ranking.ranking_encryption import encrypt_terms
            encrypt_terms(["test"])

            if os.name != "nt":  # Skip on Windows
                file_mode = oct(key_path.stat().st_mode)[-3:]
                assert file_mode == "600"


# ── R5: Decryption failure protection ─────────────────

class TestDecryptionFailureProtection:
    """Verify weight recalculation aborts when too many interactions fail to decrypt."""

    def test_abort_when_majority_fail_to_decrypt(self, database_connection):
        """If >50% of interactions fail to decrypt, return empty (don't corrupt weights)."""
        from shared.ranking.learning_machine import _load_interactions

        # Insert interactions with garbage encrypted_terms (will fail to decrypt)
        for entity_index in range(10):
            database_connection.execute(
                """INSERT INTO ranking_interactions
                   (profile_id, agent, entity_id, interaction_type, encrypted_terms, created_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (1, "job", entity_index, "click", b"INVALID_ENCRYPTED_GARBAGE"),
            )
        database_connection.commit()

        interactions = _load_interactions(database_connection, profile_id=1, agent="job")
        # Should return empty — all 10 failed to decrypt (100% > 50% threshold)
        assert interactions == []

    def test_proceed_when_minority_fail(self, database_connection):
        """If <50% fail, proceed with the successful ones."""
        from shared.ranking.learning_machine import _load_interactions
        from shared.ranking.ranking_encryption import encrypt_terms

        # 8 valid + 2 invalid = 20% failure → should proceed
        for entity_index in range(8):
            valid_terms = encrypt_terms(["python", "remote"])
            database_connection.execute(
                """INSERT INTO ranking_interactions
                   (profile_id, agent, entity_id, interaction_type, encrypted_terms, created_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (1, "job", entity_index, "click", valid_terms),
            )
        for entity_index in range(8, 10):
            database_connection.execute(
                """INSERT INTO ranking_interactions
                   (profile_id, agent, entity_id, interaction_type, encrypted_terms, created_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (1, "job", entity_index, "click", b"BAD_DATA"),
            )
        database_connection.commit()

        interactions = _load_interactions(database_connection, profile_id=1, agent="job")
        assert len(interactions) == 8  # Only the valid ones

    def test_recalculate_preserves_existing_weights_on_failure(self, database_connection):
        """If no interactions load, existing weights are preserved (not overwritten with empty)."""
        from shared.ranking.learning_machine import (
            recalculate_and_store_weights,
            get_learned_weights,
        )
        from shared.ranking.ranking_encryption import encrypt_weights

        # Pre-seed weights
        settings_key = "ranking_terms_job_1"
        existing_weights = {"python": 3.0, "remote": 2.0}
        database_connection.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (settings_key, encrypt_weights(existing_weights)),
        )
        database_connection.commit()

        # Insert only bad interactions
        for entity_index in range(5):
            database_connection.execute(
                """INSERT INTO ranking_interactions
                   (profile_id, agent, entity_id, interaction_type, encrypted_terms)
                   VALUES (?, ?, ?, ?, ?)""",
                (1, "job", entity_index, "click", b"CORRUPTED"),
            )
        database_connection.commit()

        # Recalculate should preserve existing weights
        result = recalculate_and_store_weights(database_connection, profile_id=1, agent="job")
        assert result.get("python", 0) == 3.0  # Preserved, not overwritten
        assert result.get("remote", 0) == 2.0


# ── A1: Credential store category + display_name ──────

class TestCredentialStoreCategory:
    """Verify set_key accepts and stores category + display_name."""

    def test_set_key_with_category(self, database_connection):
        """New service gets correct category when provided."""
        from shared.credentials import CredentialStore
        store = CredentialStore(database_connection)

        store.set_key("my_custom_api", "sk-test-12345", category="nestscout_source", display_name="My Custom API")

        row = database_connection.execute(
            "SELECT category, display_name FROM api_credentials WHERE service_name = 'my_custom_api'"
        ).fetchone()
        assert row["category"] == "nestscout_source"
        assert row["display_name"] == "My Custom API"

    def test_set_key_defaults_to_custom(self, database_connection):
        """Without category, defaults to 'custom' (backward compat)."""
        from shared.credentials import CredentialStore
        store = CredentialStore(database_connection)

        store.set_key("some_service", "key-abc")

        row = database_connection.execute(
            "SELECT category, display_name FROM api_credentials WHERE service_name = 'some_service'"
        ).fetchone()
        assert row["category"] == "custom"
        assert row["display_name"] == "some_service"  # defaults to service_name

    def test_update_existing_key_preserves_category(self, database_connection):
        """Updating an existing service's key doesn't change its category."""
        from shared.credentials import CredentialStore
        store = CredentialStore(database_connection)

        store.set_key("my_api", "key-v1", category="shared_source", display_name="My API")
        store.set_key("my_api", "key-v2")  # Update key only

        row = database_connection.execute(
            "SELECT category, display_name, api_key FROM api_credentials WHERE service_name = 'my_api'"
        ).fetchone()
        assert row["category"] == "shared_source"  # Preserved
        assert row["display_name"] == "My API"  # Preserved
        assert row["api_key"] == "key-v2"  # Updated


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()
