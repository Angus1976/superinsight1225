"""
Unit tests for the security module: encryption and audit logging.

Covers:
- Encryption round-trip (encrypt → decrypt returns original)
- Encrypted output differs from plaintext
- Audit log records operations correctly
- Audit log filtering by user_id, operation_type, resource_id
- Audit log thread safety
- AuditEntry model validation
"""

import threading
from datetime import datetime

import pytest

from src.toolkit.security.encryption import SimpleEncryptionProvider
from src.toolkit.security.audit import AuditLogger
from src.toolkit.models.security import AuditEntry, EncryptionConfig


# ---------------------------------------------------------------
# Encryption tests
# ---------------------------------------------------------------

class TestSimpleEncryptionProvider:
    """Tests for SimpleEncryptionProvider."""

    def test_round_trip_bytes(self):
        provider = SimpleEncryptionProvider()
        original = b"hello world"
        encrypted = provider.encrypt(original)
        assert provider.decrypt(encrypted) == original

    def test_round_trip_string(self):
        provider = SimpleEncryptionProvider()
        original = "sensitive data 中文测试"
        encrypted = provider.encrypt_string(original)
        assert provider.decrypt_string(encrypted) == original

    def test_encrypted_differs_from_plaintext(self):
        provider = SimpleEncryptionProvider()
        original = b"secret"
        encrypted = provider.encrypt(original)
        assert encrypted != original

    def test_empty_data_round_trip(self):
        provider = SimpleEncryptionProvider()
        assert provider.encrypt(b"") == b""
        assert provider.decrypt(b"") == b""

    def test_generate_key_returns_32_bytes(self):
        provider = SimpleEncryptionProvider()
        key = provider.generate_key()
        assert len(key) == 32

    def test_same_key_produces_same_output(self):
        key = b"a" * 32
        p1 = SimpleEncryptionProvider(key=key)
        p2 = SimpleEncryptionProvider(key=key)
        data = b"deterministic"
        assert p1.encrypt(data) == p2.encrypt(data)

    def test_different_keys_produce_different_output(self):
        data = b"test data"
        p1 = SimpleEncryptionProvider(key=b"a" * 32)
        p2 = SimpleEncryptionProvider(key=b"b" * 32)
        assert p1.encrypt(data) != p2.encrypt(data)

    def test_key_property(self):
        key = b"x" * 32
        provider = SimpleEncryptionProvider(key=key)
        assert provider.key == key


# ---------------------------------------------------------------
# Audit logger tests
# ---------------------------------------------------------------

class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_log_operation_returns_entry(self):
        logger = AuditLogger()
        entry = logger.log_operation("user1", "read", "res1")
        assert entry.user_id == "user1"
        assert entry.operation_type == "read"
        assert entry.resource_id == "res1"
        assert entry.status == "success"

    def test_log_operation_with_details(self):
        logger = AuditLogger()
        details = {"rows_affected": 42}
        entry = logger.log_operation("u1", "write", "r1", details=details)
        assert entry.details == {"rows_affected": 42}

    def test_log_operation_with_custom_timestamp(self):
        logger = AuditLogger()
        ts = datetime(2025, 1, 1, 12, 0, 0)
        entry = logger.log_operation("u1", "delete", "r1", timestamp=ts)
        assert entry.timestamp == ts

    def test_log_operation_validates_required_fields(self):
        logger = AuditLogger()
        with pytest.raises(ValueError):
            logger.log_operation("", "read", "r1")
        with pytest.raises(ValueError):
            logger.log_operation("u1", "", "r1")
        with pytest.raises(ValueError):
            logger.log_operation("u1", "read", "")

    def test_get_audit_trail_returns_all(self):
        logger = AuditLogger()
        logger.log_operation("u1", "read", "r1")
        logger.log_operation("u2", "write", "r2")
        assert len(logger.get_audit_trail()) == 2

    def test_filter_by_user_id(self):
        logger = AuditLogger()
        logger.log_operation("alice", "read", "r1")
        logger.log_operation("bob", "write", "r2")
        logger.log_operation("alice", "delete", "r3")
        results = logger.get_audit_trail(user_id="alice")
        assert len(results) == 2
        assert all(e.user_id == "alice" for e in results)

    def test_filter_by_operation_type(self):
        logger = AuditLogger()
        logger.log_operation("u1", "read", "r1")
        logger.log_operation("u1", "write", "r2")
        logger.log_operation("u2", "read", "r3")
        results = logger.get_audit_trail(operation_type="read")
        assert len(results) == 2

    def test_filter_by_resource_id(self):
        logger = AuditLogger()
        logger.log_operation("u1", "read", "dataset-1")
        logger.log_operation("u1", "write", "dataset-2")
        results = logger.get_audit_trail(resource_id="dataset-1")
        assert len(results) == 1
        assert results[0].resource_id == "dataset-1"

    def test_combined_filters(self):
        logger = AuditLogger()
        logger.log_operation("alice", "read", "r1")
        logger.log_operation("alice", "write", "r1")
        logger.log_operation("bob", "read", "r1")
        results = logger.get_audit_trail(user_id="alice", operation_type="read")
        assert len(results) == 1

    def test_get_entry_by_id(self):
        logger = AuditLogger()
        entry = logger.log_operation("u1", "read", "r1")
        found = logger.get_entry(entry.entry_id)
        assert found is not None
        assert found.entry_id == entry.entry_id

    def test_get_entry_not_found(self):
        logger = AuditLogger()
        assert logger.get_entry("nonexistent") is None

    def test_entry_count(self):
        logger = AuditLogger()
        assert logger.entry_count == 0
        logger.log_operation("u1", "read", "r1")
        assert logger.entry_count == 1

    def test_clear(self):
        logger = AuditLogger()
        logger.log_operation("u1", "read", "r1")
        logger.clear()
        assert logger.entry_count == 0

    def test_thread_safety(self):
        """Concurrent writes should not lose entries."""
        logger = AuditLogger()
        num_threads = 10
        ops_per_thread = 50
        barrier = threading.Barrier(num_threads)

        def worker(tid: int):
            barrier.wait()
            for i in range(ops_per_thread):
                logger.log_operation(f"user-{tid}", "op", f"res-{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert logger.entry_count == num_threads * ops_per_thread


# ---------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------

class TestAuditEntryModel:
    """Tests for AuditEntry pydantic model."""

    def test_default_fields(self):
        entry = AuditEntry(user_id="u1", operation_type="read", resource_id="r1")
        assert entry.entry_id  # auto-generated uuid
        assert entry.status == "success"
        assert isinstance(entry.timestamp, datetime)
        assert entry.details == {}

    def test_custom_status(self):
        entry = AuditEntry(
            user_id="u1", operation_type="write", resource_id="r1", status="failure"
        )
        assert entry.status == "failure"


class TestEncryptionConfigModel:
    """Tests for EncryptionConfig pydantic model."""

    def test_defaults(self):
        config = EncryptionConfig()
        assert config.algorithm == "xor-b64"
        assert config.key_id is None

    def test_custom_values(self):
        config = EncryptionConfig(algorithm="aes-256", key_id="key-001")
        assert config.algorithm == "aes-256"
        assert config.key_id == "key-001"
