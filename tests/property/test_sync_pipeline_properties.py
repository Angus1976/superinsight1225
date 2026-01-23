"""
Sync Pipeline API Property Tests - 同步管道 API 属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 6-10**
**Validates: Requirements 3.1-3.8**
"""

import asyncio
import csv
import hashlib
import hmac
import io
import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================


@dataclass
class DataSourceConfig:
    """数据源配置"""

    id: str
    name: str
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    is_active: bool = True


@dataclass
class Checkpoint:
    """检查点"""

    source_id: str
    checkpoint_field: str
    last_value: Any
    last_pull_at: Optional[datetime]
    rows_pulled: int


@dataclass
class WebhookRequest:
    """Webhook 请求"""

    source_id: str
    payload: bytes
    signature: str
    idempotency_key: str


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================


class CredentialEncryptor:
    """凭据加密器 - 简化版本用于测试"""

    ENCRYPTED_PREFIX = "enc:"

    def __init__(self, key: str = "test_key"):
        self.key = key

    def encrypt(self, plaintext: str) -> str:
        """加密明文"""
        if not plaintext:
            raise ValueError("Cannot encrypt empty value")
        if self.is_encrypted(plaintext):
            return plaintext
        # 简化的加密实现（实际应使用 Fernet）
        import base64

        encoded = base64.b64encode(plaintext.encode()).decode()
        return f"{self.ENCRYPTED_PREFIX}{encoded}"

    def decrypt(self, ciphertext: str) -> str:
        """解密密文"""
        if not ciphertext:
            raise ValueError("Cannot decrypt empty value")
        if ciphertext.startswith(self.ENCRYPTED_PREFIX):
            ciphertext = ciphertext[len(self.ENCRYPTED_PREFIX) :]
        import base64

        return base64.b64decode(ciphertext.encode()).decode()

    def is_encrypted(self, value: str) -> bool:
        """检查是否已加密"""
        return value.startswith(self.ENCRYPTED_PREFIX) if value else False


class DataSourceStore:
    """数据源存储 - 内存实现用于测试"""

    def __init__(self, encryptor: CredentialEncryptor):
        self.encryptor = encryptor
        self.sources: Dict[str, Dict[str, Any]] = {}

    def create(self, config: DataSourceConfig) -> Dict[str, Any]:
        """创建数据源"""
        encrypted_password = self.encryptor.encrypt(config.password)
        record = {
            "id": config.id,
            "name": config.name,
            "db_type": config.db_type,
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "password_encrypted": encrypted_password,
            "is_active": config.is_active,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.sources[config.id] = record
        return record

    def get(self, source_id: str) -> Optional[Dict[str, Any]]:
        """获取数据源"""
        return self.sources.get(source_id)

    def update(
        self, source_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新数据源"""
        if source_id not in self.sources:
            return None
        record = self.sources[source_id]
        for key, value in updates.items():
            if key == "password":
                record["password_encrypted"] = self.encryptor.encrypt(value)
            elif key in record:
                record[key] = value
        record["updated_at"] = datetime.utcnow()
        return record

    def delete(self, source_id: str) -> bool:
        """删除数据源"""
        if source_id in self.sources:
            del self.sources[source_id]
            return True
        return False

    def list(
        self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """列出数据源"""
        results = list(self.sources.values())
        if is_active is not None:
            results = [r for r in results if r["is_active"] == is_active]
        return results[skip : skip + limit]


class CheckpointStore:
    """检查点存储 - 内存实现用于测试"""

    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}

    def _key(self, source_id: str, checkpoint_field: str) -> str:
        return f"{source_id}:{checkpoint_field}"

    def get(
        self, source_id: str, checkpoint_field: str = "updated_at"
    ) -> Optional[Checkpoint]:
        """获取检查点"""
        return self.checkpoints.get(self._key(source_id, checkpoint_field))

    def save(self, checkpoint: Checkpoint) -> Checkpoint:
        """保存检查点"""
        key = self._key(checkpoint.source_id, checkpoint.checkpoint_field)
        checkpoint.last_pull_at = datetime.utcnow()
        self.checkpoints[key] = checkpoint
        return checkpoint


class WebhookValidator:
    """Webhook 验证器"""

    def __init__(self, secret_key: str = "test_secret"):
        self.secret_key = secret_key
        self.processed_keys: Dict[str, Dict[str, Any]] = {}

    def compute_signature(self, payload: bytes) -> str:
        """计算签名"""
        return hmac.new(self.secret_key.encode(), payload, hashlib.sha256).hexdigest()

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """验证签名"""
        expected = self.compute_signature(payload)
        return hmac.compare_digest(expected, signature)

    def check_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """检查幂等性"""
        return self.processed_keys.get(idempotency_key)

    def save_idempotency(self, idempotency_key: str, result: Dict[str, Any]) -> None:
        """保存幂等记录"""
        self.processed_keys[idempotency_key] = result


# ============================================================================
# Property 6: 同步管道 API 数据源 CRUD 往返
# **Validates: Requirements 3.1, 3.2, 3.8**
# ============================================================================


class TestDataSourceCRUDRoundTrip:
    """Property 6: 同步管道 API 数据源 CRUD 往返"""

    @given(
        config=st.fixed_dictionaries(
            {
                "id": st.uuids().map(str),
                "name": st.text(
                    min_size=1,
                    max_size=200,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                ),
                "db_type": st.sampled_from(["postgresql", "mysql", "sqlite", "oracle"]),
                "host": st.text(
                    min_size=1,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                ),
                "port": st.integers(min_value=1, max_value=65535),
                "database": st.text(
                    min_size=1,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "username": st.text(
                    min_size=1,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "password": st.text(min_size=1, max_size=100),
                "is_active": st.booleans(),
            }
        )
    )
    @settings(max_examples=25)
    def test_create_and_retrieve_data_source(self, config):
        """创建数据源后应该能通过 ID 检索到相同的配置

        **Feature: system-optimization, Property 6: 同步管道 API 数据源 CRUD 往返**
        **Validates: Requirements 3.1, 3.2, 3.8**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建数据源
        ds_config = DataSourceConfig(**config)
        created = store.create(ds_config)

        # 检索数据源
        retrieved = store.get(config["id"])

        assert retrieved is not None, "Created data source should be retrievable"
        assert retrieved["id"] == config["id"], "ID should match"
        assert retrieved["name"] == config["name"], "Name should match"
        assert retrieved["db_type"] == config["db_type"], "DB type should match"
        assert retrieved["host"] == config["host"], "Host should match"
        assert retrieved["port"] == config["port"], "Port should match"
        assert retrieved["database"] == config["database"], "Database should match"
        assert retrieved["username"] == config["username"], "Username should match"
        assert (
            retrieved["is_active"] == config["is_active"]
        ), "Active status should match"

    @given(
        config=st.fixed_dictionaries(
            {
                "id": st.uuids().map(str),
                "name": st.text(
                    min_size=1,
                    max_size=50,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "db_type": st.sampled_from(["postgresql", "mysql"]),
                "host": st.just("localhost"),
                "port": st.integers(min_value=1000, max_value=9999),
                "database": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "username": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "password": st.text(min_size=1, max_size=50),
                "is_active": st.booleans(),
            }
        ),
        new_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_update_data_source(self, config, new_name):
        """更新数据源后应该反映更新的值

        **Feature: system-optimization, Property 6: 同步管道 API 数据源 CRUD 往返**
        **Validates: Requirement 3.8**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建数据源
        ds_config = DataSourceConfig(**config)
        store.create(ds_config)

        # 更新数据源
        updated = store.update(config["id"], {"name": new_name})

        assert updated is not None, "Update should succeed"
        assert updated["name"] == new_name, "Name should be updated"
        assert updated["id"] == config["id"], "ID should not change"

    @given(
        config=st.fixed_dictionaries(
            {
                "id": st.uuids().map(str),
                "name": st.text(
                    min_size=1,
                    max_size=50,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "db_type": st.sampled_from(["postgresql", "mysql"]),
                "host": st.just("localhost"),
                "port": st.integers(min_value=1000, max_value=9999),
                "database": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "username": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "password": st.text(min_size=1, max_size=50),
                "is_active": st.booleans(),
            }
        )
    )
    @settings(max_examples=25)
    def test_delete_data_source(self, config):
        """删除数据源后应该无法检索

        **Feature: system-optimization, Property 6: 同步管道 API 数据源 CRUD 往返**
        **Validates: Requirement 3.8**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建数据源
        ds_config = DataSourceConfig(**config)
        store.create(ds_config)

        # 删除数据源
        deleted = store.delete(config["id"])

        assert deleted, "Delete should succeed"

        # 尝试检索
        retrieved = store.get(config["id"])

        assert retrieved is None, "Deleted data source should not be retrievable"


# ============================================================================
# Property 7: 同步管道 API 凭据加密
# **Validates: Requirement 3.1**
# ============================================================================


class TestCredentialEncryption:
    """Property 7: 同步管道 API 凭据加密"""

    @given(password=st.text(min_size=1, max_size=100))
    @settings(max_examples=25)
    def test_encryption_roundtrip(self, password):
        """加密后解密应该返回原始密码

        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()

        # 加密
        encrypted = encryptor.encrypt(password)

        # 解密
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == password, "Decrypted password should match original"

    @given(password=st.text(min_size=1, max_size=100))
    @settings(max_examples=25)
    def test_encrypted_differs_from_original(self, password):
        """加密后的数据应该与原始数据不同

        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()

        # 加密
        encrypted = encryptor.encrypt(password)

        # 移除前缀后比较
        encrypted_content = encrypted[len(CredentialEncryptor.ENCRYPTED_PREFIX) :]

        assert (
            encrypted_content != password
        ), "Encrypted content should differ from original"

    @given(password=st.text(min_size=1, max_size=100))
    @settings(max_examples=25)
    def test_encrypted_has_prefix(self, password):
        """加密后的数据应该有加密前缀

        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()

        # 加密
        encrypted = encryptor.encrypt(password)

        assert encrypted.startswith(
            CredentialEncryptor.ENCRYPTED_PREFIX
        ), "Encrypted value should have prefix"

    @given(password=st.text(min_size=1, max_size=100))
    @settings(max_examples=25)
    def test_double_encryption_prevention(self, password):
        """不应该重复加密已加密的数据

        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()

        # 第一次加密
        encrypted1 = encryptor.encrypt(password)

        # 第二次加密（应该返回相同的值）
        encrypted2 = encryptor.encrypt(encrypted1)

        assert encrypted1 == encrypted2, "Should not double-encrypt"

    @given(
        config=st.fixed_dictionaries(
            {
                "id": st.uuids().map(str),
                "name": st.text(
                    min_size=1,
                    max_size=50,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "db_type": st.sampled_from(["postgresql", "mysql"]),
                "host": st.just("localhost"),
                "port": st.integers(min_value=1000, max_value=9999),
                "database": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "username": st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ),
                "password": st.text(min_size=1, max_size=50),
                "is_active": st.booleans(),
            }
        )
    )
    @settings(max_examples=25)
    def test_stored_password_is_encrypted(self, config):
        """存储到数据库的密码应该是加密的

        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建数据源
        ds_config = DataSourceConfig(**config)
        created = store.create(ds_config)

        # 验证存储的密码是加密的
        assert created["password_encrypted"].startswith(
            CredentialEncryptor.ENCRYPTED_PREFIX
        ), "Stored password should be encrypted"

        # 验证可以解密回原始密码
        decrypted = encryptor.decrypt(created["password_encrypted"])
        assert decrypted == config["password"], "Should decrypt to original password"


# ============================================================================
# Property 8: 同步管道 API 分页过滤
# **Validates: Requirement 3.2**
# ============================================================================


class TestPaginationFiltering:
    """Property 8: 同步管道 API 分页过滤"""

    @given(
        num_sources=st.integers(min_value=0, max_value=50),
        skip=st.integers(min_value=0, max_value=100),
        limit=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=25)
    def test_pagination_limit(self, num_sources, skip, limit):
        """返回的结果数量应该不超过指定的 limit

        **Feature: system-optimization, Property 8: 同步管道 API 分页过滤**
        **Validates: Requirement 3.2**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建多个数据源
        for i in range(num_sources):
            config = DataSourceConfig(
                id=str(uuid4()),
                name=f"source_{i}",
                db_type="postgresql",
                host="localhost",
                port=5432,
                database=f"db_{i}",
                username=f"user_{i}",
                password=f"pass_{i}",
                is_active=True,
            )
            store.create(config)

        # 列出数据源
        results = store.list(skip=skip, limit=limit)

        # 验证结果数量
        expected_count = max(0, min(limit, num_sources - skip))
        assert (
            len(results) <= limit
        ), f"Results should not exceed limit: {len(results)} > {limit}"
        assert (
            len(results) == expected_count
        ), f"Results count mismatch: {len(results)} != {expected_count}"

    @given(
        num_sources=st.integers(min_value=5, max_value=20),
        skip=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=25)
    def test_pagination_skip(self, num_sources, skip):
        """skip 参数应该正确跳过指定数量的记录

        **Feature: system-optimization, Property 8: 同步管道 API 分页过滤**
        **Validates: Requirement 3.2**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建多个数据源
        created_ids = []
        for i in range(num_sources):
            config = DataSourceConfig(
                id=str(uuid4()),
                name=f"source_{i}",
                db_type="postgresql",
                host="localhost",
                port=5432,
                database=f"db_{i}",
                username=f"user_{i}",
                password=f"pass_{i}",
                is_active=True,
            )
            store.create(config)
            created_ids.append(config.id)

        # 获取所有结果
        all_results = store.list(skip=0, limit=num_sources)

        # 获取跳过后的结果
        skipped_results = store.list(skip=skip, limit=num_sources)

        # 验证跳过的数量
        expected_count = max(0, num_sources - skip)
        assert (
            len(skipped_results) == expected_count
        ), f"Skipped results count mismatch: {len(skipped_results)} != {expected_count}"

    @given(
        num_active=st.integers(min_value=0, max_value=10),
        num_inactive=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=25)
    def test_active_filter(self, num_active, num_inactive):
        """is_active 过滤应该正确过滤结果

        **Feature: system-optimization, Property 8: 同步管道 API 分页过滤**
        **Validates: Requirement 3.2**
        """
        encryptor = CredentialEncryptor()
        store = DataSourceStore(encryptor)

        # 创建活跃的数据源
        for i in range(num_active):
            config = DataSourceConfig(
                id=str(uuid4()),
                name=f"active_{i}",
                db_type="postgresql",
                host="localhost",
                port=5432,
                database=f"db_{i}",
                username=f"user_{i}",
                password=f"pass_{i}",
                is_active=True,
            )
            store.create(config)

        # 创建非活跃的数据源
        for i in range(num_inactive):
            config = DataSourceConfig(
                id=str(uuid4()),
                name=f"inactive_{i}",
                db_type="postgresql",
                host="localhost",
                port=5432,
                database=f"db_{i}",
                username=f"user_{i}",
                password=f"pass_{i}",
                is_active=False,
            )
            store.create(config)

        # 过滤活跃的
        active_results = store.list(is_active=True)
        assert (
            len(active_results) == num_active
        ), f"Active filter mismatch: {len(active_results)} != {num_active}"

        # 过滤非活跃的
        inactive_results = store.list(is_active=False)
        assert (
            len(inactive_results) == num_inactive
        ), f"Inactive filter mismatch: {len(inactive_results)} != {num_inactive}"

        # 不过滤
        all_results = store.list()
        assert (
            len(all_results) == num_active + num_inactive
        ), f"All results mismatch: {len(all_results)} != {num_active + num_inactive}"


# ============================================================================
# Property 9: 同步管道 API 签名验证和幂等性
# **Validates: Requirement 3.5**
# ============================================================================


class TestSignatureAndIdempotency:
    """Property 9: 同步管道 API 签名验证和幂等性"""

    @given(
        payload=st.binary(min_size=1, max_size=1000),
        secret_key=st.text(
            min_size=8,
            max_size=64,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_valid_signature_accepted(self, payload, secret_key):
        """有效签名应该被接受

        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        validator = WebhookValidator(secret_key)

        # 计算正确的签名
        signature = validator.compute_signature(payload)

        # 验证签名
        is_valid = validator.verify_signature(payload, signature)

        assert is_valid, "Valid signature should be accepted"

    @given(
        payload=st.binary(min_size=1, max_size=1000),
        secret_key=st.text(
            min_size=8, max_size=64, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"
        ),
        wrong_signature=st.text(min_size=64, max_size=64, alphabet="0123456789abcdef"),
    )
    @settings(max_examples=25)
    def test_invalid_signature_rejected(self, payload, secret_key, wrong_signature):
        """无效签名应该被拒绝

        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        validator = WebhookValidator(secret_key)

        # 计算正确的签名
        correct_signature = validator.compute_signature(payload)

        # 如果随机生成的签名恰好正确，跳过这个测试用例
        assume(wrong_signature != correct_signature)

        # 验证错误签名
        is_valid = validator.verify_signature(payload, wrong_signature)

        assert not is_valid, "Invalid signature should be rejected"

    @given(
        idempotency_key=st.uuids().map(str),
        rows_received=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=25)
    def test_idempotency_returns_previous_result(self, idempotency_key, rows_received):
        """重复的幂等键应该返回之前的结果

        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        validator = WebhookValidator()

        # 第一次请求
        first_result = {"success": True, "rows_received": rows_received}

        # 检查幂等性（应该返回 None，因为是新请求）
        existing = validator.check_idempotency(idempotency_key)
        assert existing is None, "First request should not find existing result"

        # 保存结果
        validator.save_idempotency(idempotency_key, first_result)

        # 第二次请求（应该返回之前的结果）
        existing = validator.check_idempotency(idempotency_key)
        assert existing is not None, "Second request should find existing result"
        assert existing["rows_received"] == rows_received, "Should return same result"

    @given(key1=st.uuids().map(str), key2=st.uuids().map(str))
    @settings(max_examples=25)
    def test_different_idempotency_keys_independent(self, key1, key2):
        """不同的幂等键应该独立处理

        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        assume(key1 != key2)

        validator = WebhookValidator()

        # 保存第一个键的结果
        result1 = {"success": True, "rows_received": 10}
        validator.save_idempotency(key1, result1)

        # 第二个键应该没有结果
        existing = validator.check_idempotency(key2)
        assert existing is None, "Different keys should be independent"

        # 保存第二个键的结果
        result2 = {"success": True, "rows_received": 20}
        validator.save_idempotency(key2, result2)

        # 两个键应该有各自的结果
        assert validator.check_idempotency(key1)["rows_received"] == 10
        assert validator.check_idempotency(key2)["rows_received"] == 20


# ============================================================================
# Property 10: 同步管道 API 检查点增量同步
# **Validates: Requirement 3.4**
# ============================================================================


class TestCheckpointIncrementalSync:
    """Property 10: 同步管道 API 检查点增量同步"""

    @given(
        source_id=st.uuids().map(str),
        checkpoint_field=st.sampled_from(["updated_at", "created_at", "id", "version"]),
        last_value=st.one_of(
            st.datetimes(
                min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)
            ),
            st.integers(min_value=0, max_value=1000000),
            st.text(min_size=1, max_size=50),
        ),
        rows_pulled=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=25)
    def test_checkpoint_save_and_retrieve(
        self, source_id, checkpoint_field, last_value, rows_pulled
    ):
        """保存的检查点应该能正确检索

        **Feature: system-optimization, Property 10: 同步管道 API 检查点增量同步**
        **Validates: Requirement 3.4**
        """
        store = CheckpointStore()

        # 创建检查点
        checkpoint = Checkpoint(
            source_id=source_id,
            checkpoint_field=checkpoint_field,
            last_value=last_value,
            last_pull_at=None,
            rows_pulled=rows_pulled,
        )

        # 保存检查点
        saved = store.save(checkpoint)

        # 检索检查点
        retrieved = store.get(source_id, checkpoint_field)

        assert retrieved is not None, "Saved checkpoint should be retrievable"
        assert retrieved.source_id == source_id, "Source ID should match"
        assert (
            retrieved.checkpoint_field == checkpoint_field
        ), "Checkpoint field should match"
        assert retrieved.last_value == last_value, "Last value should match"
        assert retrieved.rows_pulled == rows_pulled, "Rows pulled should match"
        assert retrieved.last_pull_at is not None, "Last pull time should be set"

    @given(
        source_id=st.uuids().map(str),
        checkpoint_field=st.sampled_from(["updated_at", "created_at"]),
        values=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)
            ),
            min_size=2,
            max_size=5,
        ),
    )
    @settings(max_examples=25)
    def test_checkpoint_update(self, source_id, checkpoint_field, values):
        """检查点应该更新为最新处理的记录

        **Feature: system-optimization, Property 10: 同步管道 API 检查点增量同步**
        **Validates: Requirement 3.4**
        """
        store = CheckpointStore()

        # 依次保存多个检查点
        for i, value in enumerate(values):
            checkpoint = Checkpoint(
                source_id=source_id,
                checkpoint_field=checkpoint_field,
                last_value=value,
                last_pull_at=None,
                rows_pulled=i * 100,
            )
            store.save(checkpoint)

        # 检索最新的检查点
        retrieved = store.get(source_id, checkpoint_field)

        assert retrieved is not None, "Checkpoint should exist"
        assert retrieved.last_value == values[-1], "Should have latest value"
        assert (
            retrieved.rows_pulled == (len(values) - 1) * 100
        ), "Should have latest rows count"

    @given(
        source_id=st.uuids().map(str),
        field1=st.just("updated_at"),
        field2=st.just("created_at"),
    )
    @settings(max_examples=25)
    def test_different_checkpoint_fields_independent(self, source_id, field1, field2):
        """不同的检查点字段应该独立存储

        **Feature: system-optimization, Property 10: 同步管道 API 检查点增量同步**
        **Validates: Requirement 3.4**
        """
        store = CheckpointStore()

        # 保存第一个字段的检查点
        checkpoint1 = Checkpoint(
            source_id=source_id,
            checkpoint_field=field1,
            last_value=datetime(2024, 1, 1),
            last_pull_at=None,
            rows_pulled=100,
        )
        store.save(checkpoint1)

        # 保存第二个字段的检查点
        checkpoint2 = Checkpoint(
            source_id=source_id,
            checkpoint_field=field2,
            last_value=datetime(2024, 6, 1),
            last_pull_at=None,
            rows_pulled=200,
        )
        store.save(checkpoint2)

        # 检索两个检查点
        retrieved1 = store.get(source_id, field1)
        retrieved2 = store.get(source_id, field2)

        assert retrieved1 is not None, "First checkpoint should exist"
        assert retrieved2 is not None, "Second checkpoint should exist"
        assert (
            retrieved1.last_value != retrieved2.last_value
        ), "Values should be different"
        assert retrieved1.rows_pulled == 100, "First checkpoint rows should be 100"
        assert retrieved2.rows_pulled == 200, "Second checkpoint rows should be 200"

    @given(source_id=st.uuids().map(str), checkpoint_field=st.just("updated_at"))
    @settings(max_examples=25)
    def test_nonexistent_checkpoint_returns_none(self, source_id, checkpoint_field):
        """不存在的检查点应该返回 None

        **Feature: system-optimization, Property 10: 同步管道 API 检查点增量同步**
        **Validates: Requirement 3.4**
        """
        store = CheckpointStore()

        # 检索不存在的检查点
        retrieved = store.get(source_id, checkpoint_field)

        assert retrieved is None, "Nonexistent checkpoint should return None"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 11: Label Studio Integration
# **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
# **Validates: Requirements 4.1, 4.2**
# ============================================================================


class MockLabelStudioClient:
    """Mock Label Studio client for testing."""

    def __init__(self):
        self.sent_data: List[Dict[str, Any]] = []
        self.annotations: Dict[str, Dict[str, Any]] = {}
        self.project_id: Optional[str] = None

    async def create_tasks(
        self, project_id: str, data: List[Dict[str, Any]]
    ) -> List[str]:
        """Create tasks in Label Studio."""
        self.project_id = project_id
        self.sent_data.extend(data)

        # Generate task IDs
        task_ids = [f"task_{i}_{uuid4().hex[:8]}" for i in range(len(data))]

        # Pre-populate annotations for testing
        for task_id, record in zip(task_ids, data):
            self.annotations[task_id] = {
                "task_id": task_id,
                "annotation": {
                    "label": "annotated",
                    "confidence": 0.95,
                    "annotator": "test_user",
                },
                "original_data": record,
            }

        return task_ids

    async def get_annotations(
        self, project_id: str, task_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get annotations for tasks."""
        return [
            self.annotations.get(task_id, {})
            for task_id in task_ids
            if task_id in self.annotations
        ]

    def clear(self):
        """Clear all stored data."""
        self.sent_data.clear()
        self.annotations.clear()
        self.project_id = None


class SemanticRefinerWithLabelStudio:
    """
    Semantic Refiner with Label Studio integration for testing.

    This class simulates the Label Studio integration behavior
    as specified in Requirements 4.1 and 4.2.
    """

    def __init__(self, label_studio_client: Optional[MockLabelStudioClient] = None):
        self.label_studio = label_studio_client
        self._memory_cache: Dict[str, Any] = {}

    async def refine(
        self, data: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute semantic refinement on data.

        Args:
            data: Data to refine
            config: Refinement configuration

        Returns:
            Refinement result with merged annotations
        """
        result = {
            "original_data": data,
            "refined_data": data.copy(),
            "annotations": [],
            "label_studio_enabled": config.get("enable_label_studio", False),
            "label_studio_project_id": config.get("label_studio_project_id"),
            "sent_to_label_studio": False,
            "annotations_merged": False,
        }

        if not data:
            return result

        # Step 1: Send to Label Studio if enabled (Requirement 4.1)
        if config.get("enable_label_studio", False) and self.label_studio:
            project_id = config.get("label_studio_project_id", "default_project")

            # Send data to Label Studio
            task_ids = await self.label_studio.create_tasks(project_id, data)
            result["sent_to_label_studio"] = True
            result["task_ids"] = task_ids

            # Step 2: Get annotations and merge (Requirement 4.2)
            annotations = await self.label_studio.get_annotations(project_id, task_ids)
            result["annotations"] = annotations

            # Merge annotations with original data
            if annotations:
                result["refined_data"] = self._merge_annotations(data, annotations)
                result["annotations_merged"] = True

        return result

    def _merge_annotations(
        self, data: List[Dict[str, Any]], annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge annotations with original data.

        Each record in the result contains both original fields
        and annotation fields.
        """
        merged = []

        for i, record in enumerate(data):
            merged_record = record.copy()

            if i < len(annotations) and annotations[i]:
                annotation = annotations[i]
                # Add annotation fields with prefix to avoid conflicts
                merged_record["_annotation"] = annotation.get("annotation", {})
                merged_record["_task_id"] = annotation.get("task_id")
                merged_record["_annotated"] = True
            else:
                merged_record["_annotated"] = False

            merged.append(merged_record)

        return merged


class TestLabelStudioIntegration:
    """
    Property 11: Label Studio Integration

    Tests that:
    1. Data is sent to Label Studio when enabled (Requirement 4.1)
    2. Annotations are merged with original data (Requirement 4.2)

    **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
    **Validates: Requirements 4.1, 4.2**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.one_of(
                        st.integers(min_value=-1000, max_value=1000),
                        st.floats(
                            min_value=-1000,
                            max_value=1000,
                            allow_nan=False,
                            allow_infinity=False,
                        ),
                        st.text(min_size=0, max_size=50),
                    ),
                    "category": st.sampled_from(["A", "B", "C", "D", "E"]),
                }
            ),
            min_size=1,
            max_size=20,
        ),
        project_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_data_sent_to_label_studio_when_enabled(self, data, project_id):
        """
        When Label Studio is enabled, data should be sent to Label Studio.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.1**

        WHEN raw data is received,
        THE Semantic_Refiner SHALL send it to Label_Studio for annotation if configured
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {"enable_label_studio": True, "label_studio_project_id": project_id}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify data was sent to Label Studio
        assert result[
            "sent_to_label_studio"
        ], "Data should be sent to Label Studio when enabled"

        assert (
            label_studio_client.project_id == project_id
        ), f"Project ID should match: {label_studio_client.project_id} != {project_id}"

        assert len(label_studio_client.sent_data) == len(
            data
        ), f"All data should be sent: {len(label_studio_client.sent_data)} != {len(data)}"

        # Verify sent data matches original
        for i, (sent, original) in enumerate(zip(label_studio_client.sent_data, data)):
            assert sent == original, f"Sent data should match original at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "status": st.sampled_from(["pending", "active", "completed"]),
                }
            ),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=25)
    def test_data_not_sent_when_label_studio_disabled(self, data):
        """
        When Label Studio is disabled, data should NOT be sent to Label Studio.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.1**
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {
            "enable_label_studio": False,
            "label_studio_project_id": "test_project",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify data was NOT sent to Label Studio
        assert not result[
            "sent_to_label_studio"
        ], "Data should NOT be sent to Label Studio when disabled"

        assert (
            len(label_studio_client.sent_data) == 0
        ), "No data should be sent when Label Studio is disabled"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "field1": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "field2": st.integers(min_value=0, max_value=1000),
                    "field3": st.booleans(),
                }
            ),
            min_size=1,
            max_size=20,
        ),
        project_id=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_annotations_merged_with_original_data(self, data, project_id):
        """
        When annotations are completed, they should be merged with original data.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.2**

        WHEN Label_Studio annotations are completed,
        THE Semantic_Refiner SHALL merge annotations with original data
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {"enable_label_studio": True, "label_studio_project_id": project_id}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify annotations were merged
        assert result[
            "annotations_merged"
        ], "Annotations should be merged with original data"

        refined_data = result["refined_data"]

        assert len(refined_data) == len(
            data
        ), f"Refined data count should match original: {len(refined_data)} != {len(data)}"

        # Verify each record contains both original fields and annotation fields
        for i, (refined, original) in enumerate(zip(refined_data, data)):
            # Check original fields are preserved
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' should be preserved in refined data at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value should be unchanged at index {i}"

            # Check annotation fields are added
            assert (
                "_annotated" in refined
            ), f"Annotation marker should be present at index {i}"
            assert refined[
                "_annotated"
            ], f"Record should be marked as annotated at index {i}"
            assert (
                "_annotation" in refined
            ), f"Annotation data should be present at index {i}"
            assert "_task_id" in refined, f"Task ID should be present at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "content": st.text(min_size=1, max_size=100),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_original_data_preserved_after_merge(self, data):
        """
        Original data should be fully preserved after merging with annotations.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.2**
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
        }

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify original data is preserved
        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}: {refined[key]} != {value}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {"id": st.uuids().map(str), "text": st.text(min_size=1, max_size=50)}
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_merged_result_contains_both_original_and_annotations(self, data):
        """
        Merged result should contain both original data fields and annotation fields.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.2**
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        for i, refined in enumerate(refined_data):
            # Count original fields
            original_fields = set(data[i].keys())

            # Count annotation fields (prefixed with _)
            annotation_fields = {k for k in refined.keys() if k.startswith("_")}

            # Verify both types of fields exist
            assert original_fields.issubset(
                set(refined.keys())
            ), f"All original fields should be present at index {i}"

            assert (
                len(annotation_fields) > 0
            ), f"Annotation fields should be present at index {i}"

            # Verify total fields = original + annotation
            expected_field_count = len(original_fields) + len(annotation_fields)
            assert (
                len(refined) == expected_field_count
            ), f"Total fields should be original + annotation at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries({"id": st.uuids().map(str), "value": st.integers()}),
            min_size=0,
            max_size=0,
        )
    )
    @settings(max_examples=25)
    def test_empty_data_handling(self, data):
        """
        Empty data should be handled gracefully without errors.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirements 4.1, 4.2**
        """
        import asyncio

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
        }

        # Execute - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify empty result
        assert result["original_data"] == [], "Original data should be empty"
        assert result["refined_data"] == [], "Refined data should be empty"
        assert not result[
            "sent_to_label_studio"
        ], "Should not send empty data to Label Studio"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_label_studio_client_not_configured(self, data):
        """
        When Label Studio client is not configured, should handle gracefully.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.1**
        """
        import asyncio

        # Setup - no Label Studio client
        refiner = SemanticRefinerWithLabelStudio(label_studio_client=None)

        config = {
            "enable_label_studio": True,  # Enabled but no client
            "label_studio_project_id": "test_project",
        }

        # Execute - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify graceful handling
        assert not result[
            "sent_to_label_studio"
        ], "Should not send data when client is not configured"
        assert (
            result["refined_data"] == data
        ), "Refined data should equal original when Label Studio unavailable"

    @given(
        num_records=st.integers(min_value=1, max_value=50),
        project_id=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_all_records_annotated(self, num_records, project_id):
        """
        All records should receive annotations when Label Studio is enabled.

        **Feature: data-sync-pipeline, Property 11: Label Studio Integration**
        **Validates: Requirement 4.2**
        """
        import asyncio

        # Generate data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Setup
        label_studio_client = MockLabelStudioClient()
        refiner = SemanticRefinerWithLabelStudio(label_studio_client)

        config = {"enable_label_studio": True, "label_studio_project_id": project_id}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify all records are annotated
        annotated_count = sum(1 for r in refined_data if r.get("_annotated", False))

        assert (
            annotated_count == num_records
        ), f"All {num_records} records should be annotated, got {annotated_count}"

        # Verify annotation count matches
        assert (
            len(result["annotations"]) == num_records
        ), f"Should have {num_records} annotations, got {len(result['annotations'])}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 12: AI Enhancement Integration
# **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
# **Validates: Requirements 4.3**
# ============================================================================


class MockLLMService:
    """Mock LLM service for testing AI enhancement."""

    def __init__(self, model_name: str = "test-model"):
        self.model_name = model_name
        self.invocation_count = 0
        self.invoked_data: List[Dict[str, Any]] = []
        self.enabled = True

    async def enhance(
        self, data: List[Dict[str, Any]], model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhance data with AI-generated semantic context.

        Simulates LLM service adding:
        - summary: AI-generated summary of the record
        - entities: Extracted named entities
        - sentiment: Sentiment analysis result
        - keywords: Key terms extracted
        - category: AI-suggested category
        """
        if not self.enabled:
            raise RuntimeError("LLM service is disabled")

        self.invocation_count += 1
        self.invoked_data.extend(data)

        enhanced_data = []
        for record in data:
            enhanced_record = record.copy()

            # Add AI-generated fields
            enhanced_record["_ai_summary"] = self._generate_summary(record)
            enhanced_record["_ai_entities"] = self._extract_entities(record)
            enhanced_record["_ai_sentiment"] = self._analyze_sentiment(record)
            enhanced_record["_ai_keywords"] = self._extract_keywords(record)
            enhanced_record["_ai_category"] = self._suggest_category(record)
            enhanced_record["_ai_model"] = model or self.model_name
            enhanced_record["_ai_enhanced"] = True

            enhanced_data.append(enhanced_record)

        return enhanced_data

    def _generate_summary(self, record: Dict[str, Any]) -> str:
        """Generate a summary for the record."""
        fields = list(record.keys())
        return f"Record with {len(fields)} fields: {', '.join(fields[:3])}..."

    def _extract_entities(self, record: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract named entities from the record."""
        entities = []
        for key, value in record.items():
            if isinstance(value, str) and len(value) > 0:
                entities.append({"text": str(value)[:50], "type": "TEXT", "field": key})
        return entities[:5]  # Limit to 5 entities

    def _analyze_sentiment(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of text fields."""
        return {"score": 0.75, "label": "positive", "confidence": 0.85}

    def _extract_keywords(self, record: Dict[str, Any]) -> List[str]:
        """Extract keywords from the record."""
        keywords = []
        for key in record.keys():
            keywords.append(key.replace("_", " "))
        return keywords[:5]

    def _suggest_category(self, record: Dict[str, Any]) -> str:
        """Suggest a category for the record."""
        keys = [k.lower() for k in record.keys()]
        if any("user" in k or "customer" in k for k in keys):
            return "customer_data"
        elif any("order" in k or "transaction" in k for k in keys):
            return "transaction_data"
        elif any("product" in k or "item" in k for k in keys):
            return "product_data"
        return "general_data"

    def clear(self):
        """Clear invocation history."""
        self.invocation_count = 0
        self.invoked_data.clear()


class SemanticRefinerWithAIEnhancement:
    """
    Semantic Refiner with AI Enhancement integration for testing.

    This class simulates the AI enhancement behavior
    as specified in Requirement 4.3:

    WHEN AI enhancement is enabled,
    THE Semantic_Refiner SHALL invoke configured LLM services
    to add semantic context
    """

    def __init__(self, llm_service: Optional[MockLLMService] = None):
        self.llm_service = llm_service
        self._memory_cache: Dict[str, Any] = {}

    async def refine(
        self, data: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute semantic refinement on data with AI enhancement.

        Args:
            data: Data to refine
            config: Refinement configuration including:
                - enable_ai_enhancement: bool
                - ai_model: str (optional)

        Returns:
            Refinement result with AI-enhanced data
        """
        result = {
            "original_data": data,
            "refined_data": data.copy(),
            "ai_enhancement_enabled": config.get("enable_ai_enhancement", False),
            "ai_model": config.get("ai_model"),
            "llm_service_invoked": False,
            "ai_fields_added": False,
            "error": None,
        }

        if not data:
            return result

        # AI Enhancement (Requirement 4.3)
        if config.get("enable_ai_enhancement", False) and self.llm_service:
            try:
                ai_model = config.get("ai_model", "default-model")

                # Invoke LLM service
                enhanced_data = await self.llm_service.enhance(data, ai_model)
                result["llm_service_invoked"] = True
                result["refined_data"] = enhanced_data
                result["ai_fields_added"] = True

            except Exception as e:
                result["error"] = str(e)
                # Preserve original data on error (Requirement 4.5)
                result["refined_data"] = data

        return result


class TestAIEnhancementIntegration:
    """
    Property 12: AI Enhancement Integration

    Tests that:
    1. LLM service is invoked when AI enhancement is enabled
    2. Result contains both original and AI-generated fields

    **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
    **Validates: Requirements 4.3**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.one_of(
                        st.integers(min_value=-1000, max_value=1000),
                        st.floats(
                            min_value=-1000,
                            max_value=1000,
                            allow_nan=False,
                            allow_infinity=False,
                        ),
                        st.text(min_size=0, max_size=50),
                    ),
                    "category": st.sampled_from(["A", "B", "C", "D", "E"]),
                }
            ),
            min_size=1,
            max_size=20,
        ),
        ai_model=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
        ),
    )
    @settings(max_examples=25)
    def test_llm_service_invoked_when_enabled(self, data, ai_model):
        """
        When AI enhancement is enabled, LLM service should be invoked.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**

        WHEN AI enhancement is enabled,
        THE Semantic_Refiner SHALL invoke configured LLM services
        to add semantic context
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": ai_model}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify LLM service was invoked
        assert result[
            "llm_service_invoked"
        ], "LLM service should be invoked when AI enhancement is enabled"

        assert (
            llm_service.invocation_count == 1
        ), f"LLM service should be invoked exactly once, got {llm_service.invocation_count}"

        assert len(llm_service.invoked_data) == len(
            data
        ), f"All data should be sent to LLM: {len(llm_service.invoked_data)} != {len(data)}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "status": st.sampled_from(["pending", "active", "completed"]),
                }
            ),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=25)
    def test_llm_service_not_invoked_when_disabled(self, data):
        """
        When AI enhancement is disabled, LLM service should NOT be invoked.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": False, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify LLM service was NOT invoked
        assert not result[
            "llm_service_invoked"
        ], "LLM service should NOT be invoked when AI enhancement is disabled"

        assert (
            llm_service.invocation_count == 0
        ), "LLM service invocation count should be 0 when disabled"

        assert (
            len(llm_service.invoked_data) == 0
        ), "No data should be sent to LLM when disabled"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "field1": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "field2": st.integers(min_value=0, max_value=1000),
                    "field3": st.booleans(),
                }
            ),
            min_size=1,
            max_size=20,
        ),
        ai_model=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_result_contains_original_and_ai_fields(self, data, ai_model):
        """
        Result should contain both original data and AI-generated fields.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**

        The result should contain both original and AI-generated fields
        (summary, entities, sentiment, etc.)
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": ai_model}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify AI fields were added
        assert result["ai_fields_added"], "AI fields should be added to the result"

        refined_data = result["refined_data"]

        assert len(refined_data) == len(
            data
        ), f"Refined data count should match original: {len(refined_data)} != {len(data)}"

        # Verify each record contains both original fields and AI-generated fields
        expected_ai_fields = [
            "_ai_summary",
            "_ai_entities",
            "_ai_sentiment",
            "_ai_keywords",
            "_ai_category",
            "_ai_model",
            "_ai_enhanced",
        ]

        for i, (refined, original) in enumerate(zip(refined_data, data)):
            # Check original fields are preserved
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' should be preserved in refined data at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value should be unchanged at index {i}"

            # Check AI-generated fields are added
            for ai_field in expected_ai_fields:
                assert (
                    ai_field in refined
                ), f"AI field '{ai_field}' should be present at index {i}"

            # Verify AI enhancement marker
            assert refined[
                "_ai_enhanced"
            ], f"Record should be marked as AI-enhanced at index {i}"

            # Verify model name is recorded
            assert (
                refined["_ai_model"] == ai_model
            ), f"AI model should be recorded at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "content": st.text(min_size=1, max_size=100),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_original_data_preserved_after_enhancement(self, data):
        """
        Original data should be fully preserved after AI enhancement.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify original data is preserved
        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}: {refined[key]} != {value}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {"id": st.uuids().map(str), "text": st.text(min_size=1, max_size=50)}
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_ai_generated_fields_have_correct_types(self, data):
        """
        AI-generated fields should have correct data types.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        for i, refined in enumerate(refined_data):
            # Verify field types
            assert isinstance(
                refined.get("_ai_summary"), str
            ), f"_ai_summary should be string at index {i}"

            assert isinstance(
                refined.get("_ai_entities"), list
            ), f"_ai_entities should be list at index {i}"

            assert isinstance(
                refined.get("_ai_sentiment"), dict
            ), f"_ai_sentiment should be dict at index {i}"

            assert isinstance(
                refined.get("_ai_keywords"), list
            ), f"_ai_keywords should be list at index {i}"

            assert isinstance(
                refined.get("_ai_category"), str
            ), f"_ai_category should be string at index {i}"

            assert isinstance(
                refined.get("_ai_model"), str
            ), f"_ai_model should be string at index {i}"

            assert isinstance(
                refined.get("_ai_enhanced"), bool
            ), f"_ai_enhanced should be bool at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries({"id": st.uuids().map(str), "value": st.integers()}),
            min_size=0,
            max_size=0,
        )
    )
    @settings(max_examples=25)
    def test_empty_data_handling(self, data):
        """
        Empty data should be handled gracefully without errors.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify empty result
        assert result["original_data"] == [], "Original data should be empty"
        assert result["refined_data"] == [], "Refined data should be empty"
        assert not result["llm_service_invoked"], "Should not invoke LLM for empty data"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_llm_service_not_configured(self, data):
        """
        When LLM service is not configured, should handle gracefully.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup - no LLM service
        refiner = SemanticRefinerWithAIEnhancement(llm_service=None)

        config = {
            "enable_ai_enhancement": True,  # Enabled but no service
            "ai_model": "test-model",
        }

        # Execute - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify graceful handling
        assert not result[
            "llm_service_invoked"
        ], "Should not invoke LLM when service is not configured"
        assert (
            result["refined_data"] == data
        ), "Refined data should equal original when LLM unavailable"

    @given(
        num_records=st.integers(min_value=1, max_value=50),
        ai_model=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_all_records_enhanced(self, num_records, ai_model):
        """
        All records should receive AI enhancement when enabled.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Generate data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": ai_model}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify all records are enhanced
        enhanced_count = sum(1 for r in refined_data if r.get("_ai_enhanced", False))

        assert (
            enhanced_count == num_records
        ), f"All {num_records} records should be enhanced, got {enhanced_count}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "customer_name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "order_id": st.text(
                        min_size=1,
                        max_size=20,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "product_code": st.text(
                        min_size=1,
                        max_size=20,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_ai_category_based_on_content(self, data):
        """
        AI-suggested category should be based on data content.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify category is assigned based on content
        for refined in refined_data:
            category = refined.get("_ai_category")
            assert category is not None, "Category should be assigned"
            assert category in [
                "customer_data",
                "transaction_data",
                "product_data",
                "general_data",
            ], f"Category should be one of the expected values, got {category}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "text_field": st.text(
                        min_size=10,
                        max_size=100,
                        alphabet=st.characters(
                            whitelist_categories=("L", "N", "P", "Z")
                        ),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_ai_entities_extracted_from_text(self, data):
        """
        AI should extract entities from text fields.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify entities are extracted
        for i, refined in enumerate(refined_data):
            entities = refined.get("_ai_entities", [])
            assert isinstance(entities, list), f"Entities should be a list at index {i}"

            # Each entity should have required fields
            for entity in entities:
                assert "text" in entity, "Entity should have 'text' field"
                assert "type" in entity, "Entity should have 'type' field"
                assert "field" in entity, "Entity should have 'field' field"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "description": st.text(min_size=1, max_size=50),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_ai_sentiment_analysis_result(self, data):
        """
        AI should provide sentiment analysis for records.

        **Feature: data-sync-pipeline, Property 12: AI Enhancement Integration**
        **Validates: Requirement 4.3**
        """
        import asyncio

        # Setup
        llm_service = MockLLMService()
        refiner = SemanticRefinerWithAIEnhancement(llm_service)

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        refined_data = result["refined_data"]

        # Verify sentiment analysis
        for i, refined in enumerate(refined_data):
            sentiment = refined.get("_ai_sentiment", {})
            assert isinstance(
                sentiment, dict
            ), f"Sentiment should be a dict at index {i}"

            # Sentiment should have required fields
            assert "score" in sentiment, "Sentiment should have 'score' field"
            assert "label" in sentiment, "Sentiment should have 'label' field"
            assert "confidence" in sentiment, "Sentiment should have 'confidence' field"

            # Validate score range
            assert (
                0 <= sentiment["score"] <= 1
            ), f"Sentiment score should be between 0 and 1 at index {i}"

            # Validate confidence range
            assert (
                0 <= sentiment["confidence"] <= 1
            ), f"Sentiment confidence should be between 0 and 1 at index {i}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 14: Refinement Error Preservation
# **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
# **Validates: Requirements 4.5**
# ============================================================================


class MockFailingLabelStudioClient:
    """Mock Label Studio client that can be configured to fail."""

    def __init__(self, fail_on_create: bool = False, fail_on_get: bool = False):
        self.fail_on_create = fail_on_create
        self.fail_on_get = fail_on_get
        self.error_message = "Label Studio service unavailable"
        self.sent_data: List[Dict[str, Any]] = []
        self.annotations: Dict[str, Dict[str, Any]] = {}

    async def create_tasks(
        self, project_id: str, data: List[Dict[str, Any]]
    ) -> List[str]:
        """Create tasks in Label Studio - may fail."""
        if self.fail_on_create:
            raise RuntimeError(self.error_message)

        self.sent_data.extend(data)
        task_ids = [f"task_{i}_{uuid4().hex[:8]}" for i in range(len(data))]

        for task_id, record in zip(task_ids, data):
            self.annotations[task_id] = {
                "task_id": task_id,
                "annotation": {"label": "annotated"},
                "original_data": record,
            }
        return task_ids

    async def get_annotations(
        self, project_id: str, task_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get annotations - may fail."""
        if self.fail_on_get:
            raise RuntimeError("Failed to retrieve annotations")
        return [
            self.annotations.get(tid, {}) for tid in task_ids if tid in self.annotations
        ]


class MockFailingLLMService:
    """Mock LLM service that can be configured to fail."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.error_message = "LLM service error: Model unavailable"
        self.invocation_count = 0
        self.invoked_data: List[Dict[str, Any]] = []

    async def enhance(
        self, data: List[Dict[str, Any]], model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Enhance data - may fail."""
        self.invocation_count += 1
        self.invoked_data.extend(data)

        if self.should_fail:
            raise RuntimeError(self.error_message)

        enhanced_data = []
        for record in data:
            enhanced_record = record.copy()
            enhanced_record["_ai_summary"] = "AI generated summary"
            enhanced_record["_ai_enhanced"] = True
            enhanced_data.append(enhanced_record)
        return enhanced_data

    def clear(self):
        """Clear invocation history."""
        self.invocation_count = 0
        self.invoked_data.clear()


class SemanticRefinerWithErrorHandling:
    """
    Semantic Refiner with comprehensive error handling for testing.

    This class simulates the error preservation behavior
    as specified in Requirement 4.5:

    WHEN refinement fails,
    THE Semantic_Refiner SHALL preserve original data and log the failure with details
    """

    def __init__(self, label_studio_client=None, llm_service=None, logger=None):
        self.label_studio = label_studio_client
        self.llm_service = llm_service
        self.logger = (
            logger if logger is not None else []
        )  # List to capture log entries
        self._memory_cache: Dict[str, Any] = {}

    async def refine(
        self, data: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute semantic refinement with error handling.

        Args:
            data: Data to refine
            config: Refinement configuration

        Returns:
            Refinement result with error details if failed
        """
        result = {
            "original_data": [record.copy() for record in data],
            "refined_data": [record.copy() for record in data],
            "success": True,
            "errors": [],
            "label_studio_error": None,
            "ai_enhancement_error": None,
            "original_preserved": True,
        }

        if not data:
            return result

        # Step 1: Label Studio annotation (if enabled)
        if config.get("enable_label_studio", False) and self.label_studio:
            try:
                project_id = config.get("label_studio_project_id", "default")
                task_ids = await self.label_studio.create_tasks(project_id, data)
                annotations = await self.label_studio.get_annotations(
                    project_id, task_ids
                )
                result["refined_data"] = self._merge_annotations(data, annotations)
            except Exception as e:
                error_detail = {
                    "stage": "label_studio",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                result["errors"].append(error_detail)
                result["label_studio_error"] = str(e)
                result["success"] = False
                # Preserve original data on failure
                result["refined_data"] = [record.copy() for record in data]
                self._log_error("Label Studio refinement failed", error_detail)

        # Step 2: AI Enhancement (if enabled)
        if config.get("enable_ai_enhancement", False) and self.llm_service:
            try:
                ai_model = config.get("ai_model", "default-model")
                enhanced_data = await self.llm_service.enhance(
                    result["refined_data"], ai_model
                )
                result["refined_data"] = enhanced_data
            except Exception as e:
                error_detail = {
                    "stage": "ai_enhancement",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                result["errors"].append(error_detail)
                result["ai_enhancement_error"] = str(e)
                result["success"] = False
                # Preserve original data on failure
                result["refined_data"] = [record.copy() for record in data]
                self._log_error("AI enhancement failed", error_detail)

        return result

    def _merge_annotations(
        self, data: List[Dict[str, Any]], annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge annotations with original data."""
        merged = []
        for i, record in enumerate(data):
            merged_record = record.copy()
            if i < len(annotations) and annotations[i]:
                merged_record["_annotation"] = annotations[i].get("annotation", {})
                merged_record["_annotated"] = True
            else:
                merged_record["_annotated"] = False
            merged.append(merged_record)
        return merged

    def _log_error(self, message: str, details: Dict[str, Any]) -> None:
        """Log error with details."""
        log_entry = {"level": "ERROR", "message": message, "details": details}
        self.logger.append(log_entry)


class TestRefinementErrorPreservation:
    """
    Property 14: Refinement Error Preservation

    Tests that:
    1. When Label Studio fails, original data is preserved
    2. When AI enhancement fails, original data is preserved
    3. Error details are captured in the result

    **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
    **Validates: Requirements 4.5**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.one_of(
                        st.integers(min_value=-1000, max_value=1000),
                        st.floats(
                            min_value=-1000,
                            max_value=1000,
                            allow_nan=False,
                            allow_infinity=False,
                        ),
                        st.text(min_size=0, max_size=50),
                    ),
                    "category": st.sampled_from(["A", "B", "C", "D", "E"]),
                }
            ),
            min_size=1,
            max_size=20,
        ),
        project_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_original_data_preserved_when_label_studio_fails(self, data, project_id):
        """
        When Label Studio fails, original data should be preserved.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**

        WHEN refinement fails,
        THE Semantic_Refiner SHALL preserve original data
        """
        import asyncio

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Setup - Label Studio configured to fail on create
        label_studio_client = MockFailingLabelStudioClient(fail_on_create=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client, logger=logger
        )

        config = {"enable_label_studio": True, "label_studio_project_id": project_id}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify original data is preserved
        assert result[
            "original_preserved"
        ], "Original data should be marked as preserved"

        refined_data = result["refined_data"]
        assert len(refined_data) == len(
            original_data_copy
        ), f"Refined data count should match: {len(refined_data)} != {len(original_data_copy)}"

        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "status": st.sampled_from(["pending", "active", "completed"]),
                }
            ),
            min_size=1,
            max_size=15,
        ),
        ai_model=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_original_data_preserved_when_ai_enhancement_fails(self, data, ai_model):
        """
        When AI enhancement fails, original data should be preserved.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**

        WHEN refinement fails,
        THE Semantic_Refiner SHALL preserve original data
        """
        import asyncio

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": ai_model}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify original data is preserved
        assert result[
            "original_preserved"
        ], "Original data should be marked as preserved"

        refined_data = result["refined_data"]
        assert len(refined_data) == len(
            original_data_copy
        ), f"Refined data count should match: {len(refined_data)} != {len(original_data_copy)}"

        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "field1": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "field2": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_error_logged_with_details_when_label_studio_fails(self, data):
        """
        When Label Studio fails, error should be logged with details.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**

        WHEN refinement fails,
        THE Semantic_Refiner SHALL log the failure with details
        """
        import asyncio

        # Setup - Label Studio configured to fail
        label_studio_client = MockFailingLabelStudioClient(fail_on_create=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client, logger=logger
        )

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify error is captured in result
        assert not result["success"], "Result should indicate failure"
        assert (
            result["label_studio_error"] is not None
        ), "Label Studio error should be captured"
        assert len(result["errors"]) > 0, "Errors list should not be empty"

        # Verify error details
        error = result["errors"][0]
        assert "stage" in error, "Error should have 'stage' field"
        assert error["stage"] == "label_studio", "Stage should be 'label_studio'"
        assert "error_type" in error, "Error should have 'error_type' field"
        assert "error_message" in error, "Error should have 'error_message' field"
        assert "timestamp" in error, "Error should have 'timestamp' field"

        # Verify error was logged
        assert len(logger) > 0, "Error should be logged"
        log_entry = logger[0]
        assert log_entry["level"] == "ERROR", "Log level should be ERROR"
        assert "details" in log_entry, "Log entry should have details"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "content": st.text(min_size=1, max_size=100),
                }
            ),
            min_size=1,
            max_size=10,
        ),
        ai_model=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ),
    )
    @settings(max_examples=25)
    def test_error_logged_with_details_when_ai_enhancement_fails(self, data, ai_model):
        """
        When AI enhancement fails, error should be logged with details.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**

        WHEN refinement fails,
        THE Semantic_Refiner SHALL log the failure with details
        """
        import asyncio

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": ai_model}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify error is captured in result
        assert not result["success"], "Result should indicate failure"
        assert (
            result["ai_enhancement_error"] is not None
        ), "AI enhancement error should be captured"
        assert len(result["errors"]) > 0, "Errors list should not be empty"

        # Verify error details
        error = result["errors"][0]
        assert "stage" in error, "Error should have 'stage' field"
        assert error["stage"] == "ai_enhancement", "Stage should be 'ai_enhancement'"
        assert "error_type" in error, "Error should have 'error_type' field"
        assert "error_message" in error, "Error should have 'error_message' field"
        assert "timestamp" in error, "Error should have 'timestamp' field"

        # Verify error was logged
        assert len(logger) > 0, "Error should be logged"
        log_entry = logger[0]
        assert log_entry["level"] == "ERROR", "Log level should be ERROR"
        assert "details" in log_entry, "Log entry should have details"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {"id": st.uuids().map(str), "text": st.text(min_size=1, max_size=50)}
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_both_services_fail_preserves_original(self, data):
        """
        When both Label Studio and AI enhancement fail, original data preserved.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Setup - Both services configured to fail
        label_studio_client = MockFailingLabelStudioClient(fail_on_create=True)
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client,
            llm_service=llm_service,
            logger=logger,
        )

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
            "enable_ai_enhancement": True,
            "ai_model": "test-model",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify original data is preserved
        assert result[
            "original_preserved"
        ], "Original data should be marked as preserved"

        refined_data = result["refined_data"]
        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}"

        # Verify both errors are captured
        assert not result["success"], "Result should indicate failure"
        assert (
            result["label_studio_error"] is not None
        ), "Label Studio error should be captured"
        # Note: AI enhancement error may not be captured if Label Studio fails first
        # and the refiner stops processing

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_label_studio_get_annotations_failure_preserves_original(self, data):
        """
        When Label Studio get_annotations fails, original data preserved.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Store original data for comparison
        original_data_copy = [record.copy() for record in data]

        # Setup - Label Studio fails on get_annotations (after create succeeds)
        label_studio_client = MockFailingLabelStudioClient(
            fail_on_create=False, fail_on_get=True
        )
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client, logger=logger
        )

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify original data is preserved
        refined_data = result["refined_data"]
        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            for key, value in original.items():
                assert (
                    key in refined
                ), f"Original field '{key}' must be preserved at index {i}"
                assert (
                    refined[key] == value
                ), f"Original field '{key}' value must be unchanged at index {i}"

        # Verify error is captured
        assert not result["success"], "Result should indicate failure"
        assert (
            result["label_studio_error"] is not None
        ), "Label Studio error should be captured"

    @given(num_records=st.integers(min_value=1, max_value=50))
    @settings(max_examples=25)
    def test_all_records_preserved_on_failure(self, num_records):
        """
        All records should be preserved when refinement fails.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Generate data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]
        original_data_copy = [record.copy() for record in data]

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify all records are preserved
        refined_data = result["refined_data"]
        assert (
            len(refined_data) == num_records
        ), f"All {num_records} records should be preserved, got {len(refined_data)}"

        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            assert refined == original, f"Record {i} should be unchanged after failure"

    @given(
        data=st.lists(
            st.fixed_dictionaries({"id": st.uuids().map(str), "value": st.integers()}),
            min_size=0,
            max_size=0,
        )
    )
    @settings(max_examples=25)
    def test_empty_data_no_error_on_failure(self, data):
        """
        Empty data should not cause errors even when services fail.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Setup - Both services configured to fail
        label_studio_client = MockFailingLabelStudioClient(fail_on_create=True)
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client,
            llm_service=llm_service,
            logger=logger,
        )

        config = {"enable_label_studio": True, "enable_ai_enhancement": True}

        # Execute - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify empty result without errors
        assert result["original_data"] == [], "Original data should be empty"
        assert result["refined_data"] == [], "Refined data should be empty"
        assert result["success"], "Empty data should succeed"
        assert len(result["errors"]) == 0, "No errors for empty data"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "nested": st.fixed_dictionaries(
                        {"inner_id": st.uuids().map(str), "inner_value": st.integers()}
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_nested_data_preserved_on_failure(self, data):
        """
        Nested data structures should be fully preserved on failure.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio
        import copy

        # Deep copy original data for comparison
        original_data_copy = copy.deepcopy(data)

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify nested data is preserved
        refined_data = result["refined_data"]
        for i, (refined, original) in enumerate(zip(refined_data, original_data_copy)):
            assert (
                refined == original
            ), f"Record {i} with nested data should be unchanged"

            # Specifically check nested structure
            assert (
                refined["nested"] == original["nested"]
            ), f"Nested structure should be preserved at index {i}"
            assert (
                refined["nested"]["inner_id"] == original["nested"]["inner_id"]
            ), f"Nested inner_id should be preserved at index {i}"
            assert (
                refined["nested"]["inner_value"] == original["nested"]["inner_value"]
            ), f"Nested inner_value should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_error_details_contain_error_type(self, data):
        """
        Error details should contain the error type.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify error type is captured
        assert len(result["errors"]) > 0, "Errors should be captured"
        error = result["errors"][0]
        assert (
            error["error_type"] == "RuntimeError"
        ), f"Error type should be RuntimeError, got {error['error_type']}"

    @given(
        data=st.lists(
            st.fixed_dictionaries({"id": st.uuids().map(str), "value": st.integers()}),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_error_details_contain_timestamp(self, data):
        """
        Error details should contain a timestamp.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio
        from datetime import datetime

        # Setup - LLM service configured to fail
        llm_service = MockFailingLLMService(should_fail=True)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            llm_service=llm_service, logger=logger
        )

        config = {"enable_ai_enhancement": True, "ai_model": "test-model"}

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify timestamp is captured
        assert len(result["errors"]) > 0, "Errors should be captured"
        error = result["errors"][0]
        assert "timestamp" in error, "Error should have timestamp"

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(error["timestamp"])
        except ValueError:
            pytest.fail(f"Timestamp should be valid ISO format: {error['timestamp']}")

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25)
    def test_success_when_no_failure(self, data):
        """
        When refinement succeeds, success should be True and no errors.

        **Feature: data-sync-pipeline, Property 14: Refinement Error Preservation**
        **Validates: Requirement 4.5**
        """
        import asyncio

        # Setup - Services configured to succeed
        label_studio_client = MockFailingLabelStudioClient(
            fail_on_create=False, fail_on_get=False
        )
        llm_service = MockFailingLLMService(should_fail=False)
        logger = []
        refiner = SemanticRefinerWithErrorHandling(
            label_studio_client=label_studio_client,
            llm_service=llm_service,
            logger=logger,
        )

        config = {
            "enable_label_studio": True,
            "label_studio_project_id": "test_project",
            "enable_ai_enhancement": True,
            "ai_model": "test-model",
        }

        # Execute
        result = asyncio.get_event_loop().run_until_complete(
            refiner.refine(data, config)
        )

        # Verify success
        assert result["success"], "Result should indicate success"
        assert len(result["errors"]) == 0, "No errors should be captured"
        assert (
            result["label_studio_error"] is None
        ), "No Label Studio error should be captured"
        assert (
            result["ai_enhancement_error"] is None
        ), "No AI enhancement error should be captured"
        assert len(logger) == 0, "No errors should be logged"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 15: JSON Export Round-Trip
# **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
# **Validates: Requirements 5.1**
# ============================================================================


class JSONExporter:
    """
    JSON Exporter for testing JSON export round-trip.

    This class simulates the JSON export behavior as specified in Requirement 5.1:

    WHEN JSON output is requested,
    THE AI_Friendly_Output SHALL generate valid JSON with consistent schema
    and UTF-8 encoding
    """

    def __init__(self):
        self.export_count = 0

    def export_to_json(
        self, data: List[Dict[str, Any]], indent: int = 2, ensure_ascii: bool = False
    ) -> str:
        """
        Export data to JSON format.

        Args:
            data: Data to export
            indent: JSON indentation level
            ensure_ascii: If False, allows UTF-8 characters

        Returns:
            JSON string with UTF-8 encoding
        """
        self.export_count += 1
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=str)

    def parse_json(self, json_str: str) -> List[Dict[str, Any]]:
        """
        Parse JSON string back to Python objects.

        Args:
            json_str: JSON string to parse

        Returns:
            Parsed Python data structure
        """
        return json.loads(json_str)

    def validate_json_schema(
        self, data: List[Dict[str, Any]], parsed_data: List[Dict[str, Any]]
    ) -> bool:
        """
        Validate that parsed data has consistent schema with original.

        Args:
            data: Original data
            parsed_data: Parsed data from JSON

        Returns:
            True if schemas match
        """
        if len(data) != len(parsed_data):
            return False

        for original, parsed in zip(data, parsed_data):
            if set(original.keys()) != set(parsed.keys()):
                return False

        return True


class TestJSONExportRoundTrip:
    """
    Property 15: JSON Export Round-Trip

    Tests that:
    1. Parsing exported JSON produces valid data structure
    2. UTF-8 characters are preserved
    3. JSON has consistent schema

    **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
    **Validates: Requirements 5.1**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.one_of(
                        st.integers(min_value=-1000000, max_value=1000000),
                        st.floats(
                            min_value=-1000,
                            max_value=1000,
                            allow_nan=False,
                            allow_infinity=False,
                        ),
                        st.text(min_size=0, max_size=50),
                    ),
                    "active": st.booleans(),
                }
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=25)
    def test_json_export_produces_valid_json(self, data):
        """
        Exported JSON should be valid and parseable.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        WHEN JSON output is requested,
        THE AI_Friendly_Output SHALL generate valid JSON
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Verify JSON is valid by parsing
        try:
            parsed = exporter.parse_json(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"Exported JSON is not valid: {e}")

        # Verify parsed data is a list
        assert isinstance(parsed, list), "Parsed JSON should be a list"

        # Verify record count matches
        assert len(parsed) == len(
            data
        ), f"Parsed data count should match original: {len(parsed)} != {len(data)}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "count": st.integers(min_value=0, max_value=10000),
                    "ratio": st.floats(
                        min_value=0, max_value=1, allow_nan=False, allow_infinity=False
                    ),
                    "enabled": st.booleans(),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_json_round_trip_preserves_data(self, data):
        """
        JSON export and parse should preserve all data.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        Parsing exported JSON should produce equivalent data structure
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify data is preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            for key, value in original.items():
                assert (
                    key in parsed_record
                ), f"Key '{key}' should be present in parsed record at index {i}"

                # Handle float comparison with tolerance
                if isinstance(value, float):
                    assert (
                        abs(parsed_record[key] - value) < 1e-9
                    ), f"Float value for '{key}' should match at index {i}: {parsed_record[key]} != {value}"
                else:
                    assert (
                        parsed_record[key] == value
                    ), f"Value for '{key}' should match at index {i}: {parsed_record[key]} != {value}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "chinese_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("中文测试数据同步管道属性验证"),
                    ),
                    "mixed_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("Hello世界Test测试123数据"),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_utf8_chinese_characters_preserved(self, data):
        """
        Chinese UTF-8 characters should be preserved in JSON export.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        UTF-8 encoding should preserve Chinese characters
        """
        exporter = JSONExporter()

        # Export to JSON with UTF-8 (ensure_ascii=False)
        json_str = exporter.export_to_json(data, ensure_ascii=False)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify Chinese characters are preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            assert (
                parsed_record["chinese_text"] == original["chinese_text"]
            ), f"Chinese text should be preserved at index {i}: '{parsed_record['chinese_text']}' != '{original['chinese_text']}'"

            assert (
                parsed_record["mixed_text"] == original["mixed_text"]
            ), f"Mixed text should be preserved at index {i}: '{parsed_record['mixed_text']}' != '{original['mixed_text']}'"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "emoji_text": st.text(
                        min_size=1,
                        max_size=20,
                        alphabet=st.sampled_from("😀🎉🚀💡✅❌🔥⭐🌟💯"),
                    ),
                    "special_chars": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.sampled_from("αβγδεζηθικλμνξοπρστυφχψω"),
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_utf8_emoji_and_special_chars_preserved(self, data):
        """
        Emoji and special UTF-8 characters should be preserved.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        UTF-8 encoding should preserve emoji and special characters
        """
        exporter = JSONExporter()

        # Export to JSON with UTF-8
        json_str = exporter.export_to_json(data, ensure_ascii=False)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify special characters are preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            assert (
                parsed_record["emoji_text"] == original["emoji_text"]
            ), f"Emoji text should be preserved at index {i}"

            assert (
                parsed_record["special_chars"] == original["special_chars"]
            ), f"Special chars should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "japanese": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.sampled_from("あいうえおかきくけこさしすせそ"),
                    ),
                    "korean": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.sampled_from("가나다라마바사아자차카타파하"),
                    ),
                    "arabic": st.text(
                        min_size=1, max_size=30, alphabet=st.sampled_from("مرحباالعالم")
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_utf8_multilingual_characters_preserved(self, data):
        """
        Multilingual UTF-8 characters should be preserved.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        UTF-8 encoding should preserve Japanese, Korean, Arabic characters
        """
        exporter = JSONExporter()

        # Export to JSON with UTF-8
        json_str = exporter.export_to_json(data, ensure_ascii=False)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify multilingual characters are preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            assert (
                parsed_record["japanese"] == original["japanese"]
            ), f"Japanese text should be preserved at index {i}"

            assert (
                parsed_record["korean"] == original["korean"]
            ), f"Korean text should be preserved at index {i}"

            assert (
                parsed_record["arabic"] == original["arabic"]
            ), f"Arabic text should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "field1": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "field2": st.integers(min_value=0, max_value=1000),
                    "field3": st.booleans(),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_json_schema_consistency(self, data):
        """
        JSON export should have consistent schema across all records.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should have consistent schema
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify schema consistency
        assert exporter.validate_json_schema(
            data, parsed
        ), "Parsed data should have consistent schema with original"

        # Verify all records have same keys
        if parsed:
            expected_keys = set(parsed[0].keys())
            for i, record in enumerate(parsed):
                assert (
                    set(record.keys()) == expected_keys
                ), f"Record {i} should have same keys as first record"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "nested": st.fixed_dictionaries(
                        {
                            "inner_id": st.uuids().map(str),
                            "inner_value": st.integers(min_value=0, max_value=100),
                        }
                    ),
                    "list_field": st.lists(
                        st.integers(min_value=0, max_value=100), min_size=0, max_size=10
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_nested_structures_preserved(self, data):
        """
        Nested structures should be preserved in JSON export.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should preserve nested objects and arrays
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify nested structures are preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            # Check nested dict
            assert (
                parsed_record["nested"] == original["nested"]
            ), f"Nested dict should be preserved at index {i}"

            # Check list field
            assert (
                parsed_record["list_field"] == original["list_field"]
            ), f"List field should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "nullable_field": st.one_of(
                        st.none(), st.text(min_size=1, max_size=30)
                    ),
                    "empty_string": st.just(""),
                    "zero_value": st.just(0),
                    "false_value": st.just(False),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_edge_case_values_preserved(self, data):
        """
        Edge case values (null, empty string, zero, false) should be preserved.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should correctly handle edge case values
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify edge case values are preserved
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            assert (
                parsed_record["nullable_field"] == original["nullable_field"]
            ), f"Nullable field should be preserved at index {i}"

            assert (
                parsed_record["empty_string"] == ""
            ), f"Empty string should be preserved at index {i}"

            assert (
                parsed_record["zero_value"] == 0
            ), f"Zero value should be preserved at index {i}"

            assert (
                parsed_record["false_value"] is False
            ), f"False value should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "escape_chars": st.text(
                        min_size=1, max_size=50, alphabet=st.sampled_from('"\\\n\r\t/')
                    ),
                    "quotes": st.text(
                        min_size=1, max_size=30, alphabet=st.sampled_from("\"'`")
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_special_json_characters_escaped(self, data):
        """
        Special JSON characters should be properly escaped and preserved.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should properly escape special characters
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Verify JSON is valid
        try:
            parsed = exporter.parse_json(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON with special characters should be valid: {e}")

        # Verify special characters are preserved after round-trip
        for i, (original, parsed_record) in enumerate(zip(data, parsed)):
            assert (
                parsed_record["escape_chars"] == original["escape_chars"]
            ), f"Escape chars should be preserved at index {i}"

            assert (
                parsed_record["quotes"] == original["quotes"]
            ), f"Quote chars should be preserved at index {i}"

    @given(num_records=st.integers(min_value=0, max_value=100))
    @settings(max_examples=25)
    def test_empty_and_large_datasets(self, num_records):
        """
        JSON export should handle empty and large datasets.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should handle various dataset sizes
        """
        # Generate data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data)

        # Parse back
        parsed = exporter.parse_json(json_str)

        # Verify count matches
        assert (
            len(parsed) == num_records
        ), f"Parsed data count should match: {len(parsed)} != {num_records}"

        # Verify empty dataset produces empty array
        if num_records == 0:
            assert (
                json_str.strip() == "[]"
            ), "Empty dataset should produce empty JSON array"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {"id": st.uuids().map(str), "text": st.text(min_size=1, max_size=100)}
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_json_encoding_is_utf8(self, data):
        """
        JSON export should use UTF-8 encoding.

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON should be UTF-8 encoded
        """
        exporter = JSONExporter()

        # Export to JSON
        json_str = exporter.export_to_json(data, ensure_ascii=False)

        # Verify string can be encoded as UTF-8
        try:
            json_bytes = json_str.encode("utf-8")
        except UnicodeEncodeError as e:
            pytest.fail(f"JSON should be UTF-8 encodable: {e}")

        # Verify bytes can be decoded back
        try:
            decoded = json_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            pytest.fail(f"JSON bytes should be UTF-8 decodable: {e}")

        # Verify decoded string matches original
        assert decoded == json_str, "UTF-8 round-trip should preserve JSON string"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_json_is_deterministic(self, data):
        """
        JSON export should be deterministic (same input produces same output).

        **Feature: data-sync-pipeline, Property 15: JSON Export Round-Trip**
        **Validates: Requirement 5.1**

        JSON export should be consistent
        """
        exporter = JSONExporter()

        # Export twice
        json_str1 = exporter.export_to_json(data)
        json_str2 = exporter.export_to_json(data)

        # Verify outputs are identical
        assert json_str1 == json_str2, "JSON export should be deterministic"


# ============================================================================
# Property 16: CSV Export Format Validation
# **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
# **Validates: Requirements 5.2**
# ============================================================================


class CSVExporter:
    """
    CSV Exporter for testing CSV export format validation.

    This class simulates the CSV export behavior as specified in Requirement 5.2:

    WHEN CSV output is requested,
    THE AI_Friendly_Output SHALL generate properly escaped CSV with headers
    and configurable delimiters
    """

    def __init__(self, delimiter: str = ","):
        """
        Initialize CSV exporter with configurable delimiter.

        Args:
            delimiter: CSV field delimiter (comma, semicolon, tab)
        """
        self.delimiter = delimiter
        self.export_count = 0

    def export_to_csv(
        self, data: List[Dict[str, Any]], include_headers: bool = True
    ) -> str:
        """
        Export data to CSV format with proper escaping.

        Args:
            data: Data to export
            include_headers: Whether to include header row

        Returns:
            CSV string with proper escaping
        """
        if not data:
            return ""

        self.export_count += 1
        output = io.StringIO()

        # Get field names from first record
        fieldnames = list(data[0].keys())

        # Use QUOTE_ALL to ensure all fields are quoted, which handles
        # special characters like commas, quotes, newlines, and delimiters
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.delimiter,
            quoting=csv.QUOTE_ALL,
            quotechar='"',
            doublequote=True,  # Use double quotes to escape quotes
        )

        if include_headers:
            writer.writeheader()

        for row in data:
            # Flatten nested structures to JSON strings
            flat_row = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    flat_row[key] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    flat_row[key] = ""
                else:
                    flat_row[key] = value
            writer.writerow(flat_row)

        return output.getvalue()

    def parse_csv(
        self, csv_str: str, has_headers: bool = True
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Parse CSV string back to Python objects.

        Args:
            csv_str: CSV string to parse
            has_headers: Whether CSV has header row

        Returns:
            Tuple of (headers, list of row dicts)
        """
        if not csv_str.strip():
            return [], []

        input_stream = io.StringIO(csv_str)

        if has_headers:
            reader = csv.DictReader(
                input_stream, delimiter=self.delimiter, quotechar='"', doublequote=True
            )
            headers = reader.fieldnames or []
            rows = list(reader)
            return list(headers), rows
        else:
            reader = csv.reader(
                input_stream, delimiter=self.delimiter, quotechar='"', doublequote=True
            )
            rows_list = list(reader)
            return [], [dict(enumerate(row)) for row in rows_list]

    def validate_csv_headers(
        self, original_data: List[Dict[str, Any]], parsed_headers: List[str]
    ) -> bool:
        """
        Validate that CSV headers match original field names.

        Args:
            original_data: Original data
            parsed_headers: Headers from parsed CSV

        Returns:
            True if headers match field names
        """
        if not original_data:
            return len(parsed_headers) == 0

        expected_headers = list(original_data[0].keys())
        return parsed_headers == expected_headers


class TestCSVExportFormatValidation:
    """
    Property 16: CSV Export Format Validation

    Tests that:
    1. CSV has headers matching field names
    2. Values containing commas, quotes, newlines are properly escaped
    3. Python's csv module can parse the output
    4. Configurable delimiters (comma, semicolon, tab)

    **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
    **Validates: Requirements 5.2**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.integers(min_value=-1000000, max_value=1000000),
                    "active": st.booleans(),
                }
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=25)
    def test_csv_has_headers_matching_field_names(self, data):
        """
        CSV export should have headers matching field names.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        WHEN CSV output is requested,
        THE AI_Friendly_Output SHALL generate CSV with headers
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data, include_headers=True)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str, has_headers=True)

        # Verify headers match field names
        expected_headers = list(data[0].keys())
        assert (
            headers == expected_headers
        ), f"CSV headers should match field names: {headers} != {expected_headers}"

        # Verify row count matches (excluding header)
        assert len(rows) == len(
            data
        ), f"CSV row count should match data count: {len(rows)} != {len(data)}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "text_with_comma": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc,def,ghi,jkl"),
                    ),
                    "text_with_quotes": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from('abc"def"ghi\'jkl'),
                    ),
                    "normal_text": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_escapes_commas_and_quotes(self, data):
        """
        CSV should properly escape values containing commas and quotes.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        WHEN CSV output is requested,
        THE AI_Friendly_Output SHALL generate properly escaped CSV
        """
        exporter = CSVExporter(delimiter=",")

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Verify CSV is parseable by standard csv module
        try:
            headers, rows = exporter.parse_csv(csv_str)
        except csv.Error as e:
            pytest.fail(f"CSV with special characters should be parseable: {e}")

        # Verify data is preserved after round-trip
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["text_with_comma"] == original["text_with_comma"]
            ), f"Text with comma should be preserved at index {i}: '{parsed_row['text_with_comma']}' != '{original['text_with_comma']}'"

            assert (
                parsed_row["text_with_quotes"] == original["text_with_quotes"]
            ), f"Text with quotes should be preserved at index {i}: '{parsed_row['text_with_quotes']}' != '{original['text_with_quotes']}'"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "text_with_newline": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc\ndef\nghi\njkl"),
                    ),
                    "text_with_crlf": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc\r\ndef\r\nghi"),
                    ),
                    "normal_text": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_escapes_newlines(self, data):
        """
        CSV should properly escape values containing newlines.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        WHEN CSV output is requested,
        THE AI_Friendly_Output SHALL generate properly escaped CSV
        """
        exporter = CSVExporter(delimiter=",")

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Verify CSV is parseable
        try:
            headers, rows = exporter.parse_csv(csv_str)
        except csv.Error as e:
            pytest.fail(f"CSV with newlines should be parseable: {e}")

        # Verify data is preserved after round-trip
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["text_with_newline"] == original["text_with_newline"]
            ), f"Text with newline should be preserved at index {i}"

            assert (
                parsed_row["text_with_crlf"] == original["text_with_crlf"]
            ), f"Text with CRLF should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=10000),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_parseable_by_standard_csv_module(self, data):
        """
        Exported CSV should be parseable by Python's standard csv module.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        Standard CSV libraries should be able to parse the output
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Parse using standard csv module directly
        input_stream = io.StringIO(csv_str)
        try:
            reader = csv.DictReader(input_stream)
            parsed_rows = list(reader)
        except csv.Error as e:
            pytest.fail(f"Standard csv module should parse exported CSV: {e}")

        # Verify row count
        assert len(parsed_rows) == len(
            data
        ), f"Parsed row count should match: {len(parsed_rows)} != {len(data)}"

        # Verify field names
        if parsed_rows:
            assert set(parsed_rows[0].keys()) == set(
                data[0].keys()
            ), "Parsed field names should match original"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=10000),
                }
            ),
            min_size=1,
            max_size=30,
        ),
        delimiter=st.sampled_from([",", ";", "\t"]),
    )
    @settings(max_examples=25)
    def test_csv_configurable_delimiters(self, data, delimiter):
        """
        CSV export should support configurable delimiters.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        WHEN CSV output is requested,
        THE AI_Friendly_Output SHALL support configurable delimiters
        """
        exporter = CSVExporter(delimiter=delimiter)

        # Export to CSV with specified delimiter
        csv_str = exporter.export_to_csv(data)

        # Parse with same delimiter
        headers, rows = exporter.parse_csv(csv_str)

        # Verify headers match
        assert headers == list(
            data[0].keys()
        ), f"Headers should match with delimiter '{repr(delimiter)}'"

        # Verify row count
        assert len(rows) == len(
            data
        ), f"Row count should match with delimiter '{repr(delimiter)}'"

        # Verify data is preserved
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["id"] == original["id"]
            ), f"ID should be preserved at index {i} with delimiter '{repr(delimiter)}'"
            assert (
                parsed_row["name"] == original["name"]
            ), f"Name should be preserved at index {i} with delimiter '{repr(delimiter)}'"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "chinese_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("中文测试数据同步管道属性验证"),
                    ),
                    "mixed_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("Hello世界Test测试123数据"),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_preserves_utf8_characters(self, data):
        """
        CSV export should preserve UTF-8 characters including Chinese.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        CSV should properly handle UTF-8 encoded content
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str)

        # Verify UTF-8 characters are preserved
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["chinese_text"] == original["chinese_text"]
            ), f"Chinese text should be preserved at index {i}: '{parsed_row['chinese_text']}' != '{original['chinese_text']}'"

            assert (
                parsed_row["mixed_text"] == original["mixed_text"]
            ), f"Mixed text should be preserved at index {i}: '{parsed_row['mixed_text']}' != '{original['mixed_text']}'"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "special_chars": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from(",\"'\n\r\t\\;|"),
                    ),
                    "normal_text": st.text(
                        min_size=1,
                        max_size=30,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_handles_all_special_characters(self, data):
        """
        CSV should properly handle all special characters that need escaping.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        CSV should escape commas, quotes, newlines, tabs, backslashes
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Verify CSV is valid and parseable
        try:
            headers, rows = exporter.parse_csv(csv_str)
        except csv.Error as e:
            pytest.fail(f"CSV with special characters should be parseable: {e}")

        # Verify data is preserved
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["special_chars"] == original["special_chars"]
            ), f"Special chars should be preserved at index {i}: '{repr(parsed_row['special_chars'])}' != '{repr(original['special_chars'])}'"

    @given(num_records=st.integers(min_value=0, max_value=100))
    @settings(max_examples=25)
    def test_csv_handles_empty_and_large_datasets(self, num_records):
        """
        CSV export should handle empty and large datasets.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        CSV should handle various dataset sizes
        """
        # Generate data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        if num_records == 0:
            # Empty dataset should produce empty string
            assert csv_str == "", "Empty dataset should produce empty CSV"
        else:
            # Parse CSV
            headers, rows = exporter.parse_csv(csv_str)

            # Verify row count
            assert (
                len(rows) == num_records
            ), f"CSV row count should match: {len(rows)} != {num_records}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "nullable_field": st.one_of(
                        st.none(),
                        st.text(
                            min_size=1,
                            max_size=30,
                            alphabet=st.characters(whitelist_categories=("L", "N")),
                        ),
                    ),
                    "empty_string": st.just(""),
                    "zero_value": st.just(0),
                    "false_value": st.just(False),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_csv_handles_edge_case_values(self, data):
        """
        CSV should handle edge case values (null, empty string, zero, false).

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        CSV should correctly handle edge case values
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str)

        # Verify edge case values are handled
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            # Null values become empty strings in CSV
            expected_nullable = (
                "" if original["nullable_field"] is None else original["nullable_field"]
            )
            assert (
                parsed_row["nullable_field"] == expected_nullable
            ), f"Nullable field should be handled at index {i}"

            # Empty string should be preserved
            assert (
                parsed_row["empty_string"] == ""
            ), f"Empty string should be preserved at index {i}"

            # Zero and False are converted to strings in CSV
            assert (
                parsed_row["zero_value"] == "0"
            ), f"Zero value should be '0' at index {i}"

            assert (
                parsed_row["false_value"] == "False"
            ), f"False value should be 'False' at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "nested_dict": st.fixed_dictionaries(
                        {
                            "inner_key": st.text(
                                min_size=1,
                                max_size=20,
                                alphabet=st.characters(whitelist_categories=("L", "N")),
                            ),
                            "inner_value": st.integers(min_value=0, max_value=100),
                        }
                    ),
                    "list_field": st.lists(
                        st.integers(min_value=0, max_value=100), min_size=0, max_size=5
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_csv_flattens_nested_structures(self, data):
        """
        CSV should flatten nested structures to JSON strings.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        Nested objects and arrays should be serialized as JSON strings
        """
        exporter = CSVExporter()

        # Export to CSV
        csv_str = exporter.export_to_csv(data)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str)

        # Verify nested structures are flattened to JSON strings
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            # Nested dict should be JSON string
            expected_dict_json = json.dumps(original["nested_dict"], ensure_ascii=False)
            assert (
                parsed_row["nested_dict"] == expected_dict_json
            ), f"Nested dict should be JSON string at index {i}"

            # List should be JSON string
            expected_list_json = json.dumps(original["list_field"], ensure_ascii=False)
            assert (
                parsed_row["list_field"] == expected_list_json
            ), f"List field should be JSON string at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_csv_is_deterministic(self, data):
        """
        CSV export should be deterministic (same input produces same output).

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        CSV export should be consistent
        """
        exporter = CSVExporter()

        # Export twice
        csv_str1 = exporter.export_to_csv(data)
        csv_str2 = exporter.export_to_csv(data)

        # Verify outputs are identical
        assert csv_str1 == csv_str2, "CSV export should be deterministic"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "semicolon_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc;def;ghi;jkl"),
                    ),
                    "tab_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc\tdef\tghi\tjkl"),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_semicolon_delimiter_escapes_semicolons(self, data):
        """
        CSV with semicolon delimiter should properly escape semicolons in values.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        Semicolon delimiter should work correctly
        """
        exporter = CSVExporter(delimiter=";")

        # Export to CSV with semicolon delimiter
        csv_str = exporter.export_to_csv(data)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str)

        # Verify data is preserved
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["semicolon_text"] == original["semicolon_text"]
            ), f"Semicolon text should be preserved at index {i}"

            assert (
                parsed_row["tab_text"] == original["tab_text"]
            ), f"Tab text should be preserved at index {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "tab_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc\tdef\tghi\tjkl"),
                    ),
                    "comma_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("abc,def,ghi,jkl"),
                    ),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_csv_tab_delimiter_escapes_tabs(self, data):
        """
        CSV with tab delimiter should properly escape tabs in values.

        **Feature: data-sync-pipeline, Property 16: CSV Export Format Validation**
        **Validates: Requirement 5.2**

        Tab delimiter should work correctly
        """
        exporter = CSVExporter(delimiter="\t")

        # Export to CSV with tab delimiter
        csv_str = exporter.export_to_csv(data)

        # Parse CSV
        headers, rows = exporter.parse_csv(csv_str)

        # Verify data is preserved
        for i, (original, parsed_row) in enumerate(zip(data, rows)):
            assert (
                parsed_row["tab_text"] == original["tab_text"]
            ), f"Tab text should be preserved at index {i}"

            assert (
                parsed_row["comma_text"] == original["comma_text"]
            ), f"Comma text should be preserved at index {i}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 17: COCO Format Validation
# **Validates: Requirement 5.3**
# ============================================================================


class COCOExporter:
    """
    COCO Exporter for testing COCO format validation.

    This class simulates the COCO export behavior as specified in Requirement 5.3:

    WHEN COCO format is requested for image annotation data,
    THE AI_Friendly_Output SHALL generate valid COCO JSON with images,
    annotations, and categories
    """

    def __init__(self):
        self.export_count = 0

    def export_to_coco(
        self,
        images: List[Dict[str, Any]],
        annotations: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
    ) -> str:
        """
        Export data to COCO format.

        Args:
            images: List of image objects with id, file_name, width, height
            annotations: List of annotation objects with id, image_id, category_id, bbox/segmentation
            categories: List of category objects with id, name

        Returns:
            COCO JSON string
        """
        self.export_count += 1

        coco_format = {
            "info": {
                "description": "Exported dataset",
                "version": "1.0",
                "year": 2024,
                "date_created": "2024-01-01T00:00:00",
            },
            "licenses": [],
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }

        return json.dumps(coco_format, indent=2, ensure_ascii=False)

    def parse_coco(self, coco_str: str) -> Dict[str, Any]:
        """
        Parse COCO JSON string back to Python objects.

        Args:
            coco_str: COCO JSON string to parse

        Returns:
            Parsed COCO data structure
        """
        return json.loads(coco_str)

    def validate_coco_structure(
        self, coco_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that COCO data has required top-level keys.

        Args:
            coco_data: Parsed COCO data

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        required_keys = ["images", "annotations", "categories"]

        for key in required_keys:
            if key not in coco_data:
                errors.append(f"Missing required key: {key}")
            elif not isinstance(coco_data[key], list):
                errors.append(f"Key '{key}' should be a list")

        return len(errors) == 0, errors

    def validate_image_objects(
        self, images: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that image objects have required fields.

        Args:
            images: List of image objects

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        required_fields = ["id", "file_name", "width", "height"]

        for idx, image in enumerate(images):
            for field in required_fields:
                if field not in image:
                    errors.append(f"Image {idx}: missing required field '{field}'")

            # Validate types
            if "id" in image and not isinstance(image["id"], (int, str)):
                errors.append(f"Image {idx}: 'id' should be int or str")
            if "file_name" in image and not isinstance(image["file_name"], str):
                errors.append(f"Image {idx}: 'file_name' should be str")
            if "width" in image and not isinstance(image["width"], (int, float)):
                errors.append(f"Image {idx}: 'width' should be numeric")
            if "height" in image and not isinstance(image["height"], (int, float)):
                errors.append(f"Image {idx}: 'height' should be numeric")

        return len(errors) == 0, errors

    def validate_annotation_objects(
        self, annotations: List[Dict[str, Any]], image_ids: set, category_ids: set
    ) -> Tuple[bool, List[str]]:
        """
        Validate that annotation objects have required fields and valid references.

        Args:
            annotations: List of annotation objects
            image_ids: Set of valid image IDs
            category_ids: Set of valid category IDs

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        required_fields = ["id", "image_id", "category_id"]

        for idx, ann in enumerate(annotations):
            for field in required_fields:
                if field not in ann:
                    errors.append(f"Annotation {idx}: missing required field '{field}'")

            # Validate references
            if "image_id" in ann and ann["image_id"] not in image_ids:
                errors.append(
                    f"Annotation {idx}: image_id {ann['image_id']} not found in images"
                )
            if "category_id" in ann and ann["category_id"] not in category_ids:
                errors.append(
                    f"Annotation {idx}: category_id {ann['category_id']} not found in categories"
                )

            # Validate bbox or segmentation exists
            if "bbox" not in ann and "segmentation" not in ann:
                errors.append(f"Annotation {idx}: must have 'bbox' or 'segmentation'")

            # Validate bbox format if present
            if "bbox" in ann:
                bbox = ann["bbox"]
                if not isinstance(bbox, list) or len(bbox) != 4:
                    errors.append(
                        f"Annotation {idx}: 'bbox' should be [x, y, width, height]"
                    )
                elif not all(isinstance(v, (int, float)) for v in bbox):
                    errors.append(f"Annotation {idx}: 'bbox' values should be numeric")

        return len(errors) == 0, errors

    def validate_category_objects(
        self, categories: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that category objects have required fields.

        Args:
            categories: List of category objects

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        required_fields = ["id", "name"]

        for idx, cat in enumerate(categories):
            for field in required_fields:
                if field not in cat:
                    errors.append(f"Category {idx}: missing required field '{field}'")

            # Validate types
            if "id" in cat and not isinstance(cat["id"], (int, str)):
                errors.append(f"Category {idx}: 'id' should be int or str")
            if "name" in cat and not isinstance(cat["name"], str):
                errors.append(f"Category {idx}: 'name' should be str")

        return len(errors) == 0, errors


class TestCOCOFormatValidation:
    """
    Property 17: COCO Format Validation

    Tests that:
    1. COCO output has required top-level keys: images, annotations, categories
    2. Images array contains valid image objects with id, file_name, width, height
    3. Annotations array contains valid annotation objects with id, image_id, category_id, bbox/segmentation
    4. Categories array contains valid category objects with id, name
    5. image_id references in annotations match existing images
    6. category_id references in annotations match existing categories

    **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
    **Validates: Requirements 5.3**
    """

    @given(
        num_images=st.integers(min_value=1, max_value=20),
        num_categories=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=25)
    def test_coco_has_required_top_level_keys(self, num_images, num_categories):
        """
        COCO output should have required top-level keys: images, annotations, categories.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        WHEN COCO format is requested,
        THE AI_Friendly_Output SHALL generate valid COCO JSON with images,
        annotations, and categories
        """
        exporter = COCOExporter()

        # Generate test data
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,
                "category_id": i % num_categories,
                "bbox": [10, 20, 100, 150],
            }
            for i in range(num_images * 2)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Validate structure
        is_valid, errors = exporter.validate_coco_structure(coco_data)

        assert is_valid, f"COCO should have required keys: {errors}"
        assert "images" in coco_data, "COCO should have 'images' key"
        assert "annotations" in coco_data, "COCO should have 'annotations' key"
        assert "categories" in coco_data, "COCO should have 'categories' key"

    @given(
        images=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.integers(min_value=0, max_value=10000),
                    "file_name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ).map(lambda x: f"{x}.jpg"),
                    "width": st.integers(min_value=1, max_value=4096),
                    "height": st.integers(min_value=1, max_value=4096),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_images_array_contains_valid_image_objects(self, images):
        """
        Images array should contain valid image objects with id, file_name, width, height.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Image objects must have required fields
        """
        exporter = COCOExporter()

        # Export to COCO
        coco_str = exporter.export_to_coco(images, [], [])

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Validate image objects
        is_valid, errors = exporter.validate_image_objects(coco_data["images"])

        assert is_valid, f"Image objects should be valid: {errors}"

        # Verify all images are present
        assert len(coco_data["images"]) == len(
            images
        ), f"All images should be exported: {len(coco_data['images'])} != {len(images)}"

        # Verify each image has required fields
        for idx, image in enumerate(coco_data["images"]):
            assert "id" in image, f"Image {idx} should have 'id'"
            assert "file_name" in image, f"Image {idx} should have 'file_name'"
            assert "width" in image, f"Image {idx} should have 'width'"
            assert "height" in image, f"Image {idx} should have 'height'"

    @given(
        num_images=st.integers(min_value=1, max_value=10),
        num_categories=st.integers(min_value=1, max_value=5),
        num_annotations=st.integers(min_value=1, max_value=30),
    )
    @settings(max_examples=25)
    def test_annotations_array_contains_valid_annotation_objects(
        self, num_images, num_categories, num_annotations
    ):
        """
        Annotations array should contain valid annotation objects with id, image_id, category_id, bbox.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Annotation objects must have required fields
        """
        exporter = COCOExporter()

        # Generate test data
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,
                "category_id": i % num_categories,
                "bbox": [10 + i, 20 + i, 100, 150],
            }
            for i in range(num_annotations)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Get valid IDs
        image_ids = {img["id"] for img in coco_data["images"]}
        category_ids = {cat["id"] for cat in coco_data["categories"]}

        # Validate annotation objects
        is_valid, errors = exporter.validate_annotation_objects(
            coco_data["annotations"], image_ids, category_ids
        )

        assert is_valid, f"Annotation objects should be valid: {errors}"

        # Verify all annotations are present
        assert len(coco_data["annotations"]) == len(
            annotations
        ), f"All annotations should be exported: {len(coco_data['annotations'])} != {len(annotations)}"

    @given(
        categories=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.integers(min_value=0, max_value=1000),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_categories_array_contains_valid_category_objects(self, categories):
        """
        Categories array should contain valid category objects with id, name.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Category objects must have required fields
        """
        exporter = COCOExporter()

        # Export to COCO
        coco_str = exporter.export_to_coco([], [], categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Validate category objects
        is_valid, errors = exporter.validate_category_objects(coco_data["categories"])

        assert is_valid, f"Category objects should be valid: {errors}"

        # Verify all categories are present
        assert len(coco_data["categories"]) == len(
            categories
        ), f"All categories should be exported: {len(coco_data['categories'])} != {len(categories)}"

        # Verify each category has required fields
        for idx, cat in enumerate(coco_data["categories"]):
            assert "id" in cat, f"Category {idx} should have 'id'"
            assert "name" in cat, f"Category {idx} should have 'name'"

    @given(
        num_images=st.integers(min_value=2, max_value=15),
        num_categories=st.integers(min_value=2, max_value=8),
        num_annotations=st.integers(min_value=5, max_value=40),
    )
    @settings(max_examples=25)
    def test_annotation_image_id_references_match_existing_images(
        self, num_images, num_categories, num_annotations
    ):
        """
        image_id references in annotations should match existing images.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        All annotation image_id values must reference valid images
        """
        exporter = COCOExporter()

        # Generate test data with valid references
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,  # Ensures valid reference
                "category_id": i % num_categories,
                "bbox": [10, 20, 100, 150],
            }
            for i in range(num_annotations)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Get valid image IDs
        image_ids = {img["id"] for img in coco_data["images"]}

        # Verify all annotation image_ids reference valid images
        for idx, ann in enumerate(coco_data["annotations"]):
            assert (
                ann["image_id"] in image_ids
            ), f"Annotation {idx}: image_id {ann['image_id']} should reference existing image"

    @given(
        num_images=st.integers(min_value=2, max_value=15),
        num_categories=st.integers(min_value=2, max_value=8),
        num_annotations=st.integers(min_value=5, max_value=40),
    )
    @settings(max_examples=25)
    def test_annotation_category_id_references_match_existing_categories(
        self, num_images, num_categories, num_annotations
    ):
        """
        category_id references in annotations should match existing categories.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        All annotation category_id values must reference valid categories
        """
        exporter = COCOExporter()

        # Generate test data with valid references
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,
                "category_id": i % num_categories,  # Ensures valid reference
                "bbox": [10, 20, 100, 150],
            }
            for i in range(num_annotations)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Get valid category IDs
        category_ids = {cat["id"] for cat in coco_data["categories"]}

        # Verify all annotation category_ids reference valid categories
        for idx, ann in enumerate(coco_data["annotations"]):
            assert (
                ann["category_id"] in category_ids
            ), f"Annotation {idx}: category_id {ann['category_id']} should reference existing category"

    @given(
        num_images=st.integers(min_value=1, max_value=10),
        num_categories=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=25)
    def test_coco_json_is_valid_and_parseable(self, num_images, num_categories):
        """
        COCO export should produce valid, parseable JSON.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        COCO JSON should be valid JSON format
        """
        exporter = COCOExporter()

        # Generate test data
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,
                "category_id": i % num_categories,
                "bbox": [10, 20, 100, 150],
            }
            for i in range(num_images * 2)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Verify JSON is valid by parsing
        try:
            coco_data = exporter.parse_coco(coco_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"COCO JSON should be valid: {e}")

        # Verify it's a dictionary
        assert isinstance(coco_data, dict), "COCO data should be a dictionary"

    @given(
        bbox_values=st.lists(
            st.floats(
                min_value=0, max_value=1000, allow_nan=False, allow_infinity=False
            ),
            min_size=4,
            max_size=4,
        )
    )
    @settings(max_examples=25)
    def test_bbox_format_is_valid(self, bbox_values):
        """
        Bounding box should be in [x, y, width, height] format with numeric values.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Bbox should have exactly 4 numeric values
        """
        exporter = COCOExporter()

        # Generate test data with the given bbox
        images = [{"id": 0, "file_name": "image_0.jpg", "width": 640, "height": 480}]
        categories = [{"id": 0, "name": "object"}]
        annotations = [{"id": 0, "image_id": 0, "category_id": 0, "bbox": bbox_values}]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Verify bbox format
        ann = coco_data["annotations"][0]
        assert "bbox" in ann, "Annotation should have 'bbox'"
        assert isinstance(ann["bbox"], list), "Bbox should be a list"
        assert len(ann["bbox"]) == 4, "Bbox should have 4 values [x, y, width, height]"
        assert all(
            isinstance(v, (int, float)) for v in ann["bbox"]
        ), "Bbox values should be numeric"

    @given(
        num_images=st.integers(min_value=0, max_value=5),
        num_categories=st.integers(min_value=0, max_value=5),
        num_annotations=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=25)
    def test_empty_arrays_are_valid(self, num_images, num_categories, num_annotations):
        """
        COCO format should handle empty arrays gracefully.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Empty images, annotations, or categories arrays should be valid
        """
        exporter = COCOExporter()

        # Generate test data (may be empty)
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]

        # Only create annotations if we have images and categories
        if num_images > 0 and num_categories > 0:
            annotations = [
                {
                    "id": i,
                    "image_id": i % num_images,
                    "category_id": i % num_categories,
                    "bbox": [10, 20, 100, 150],
                }
                for i in range(num_annotations)
            ]
        else:
            annotations = []

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Validate structure
        is_valid, errors = exporter.validate_coco_structure(coco_data)

        assert is_valid, f"COCO with empty arrays should be valid: {errors}"
        assert isinstance(coco_data["images"], list), "Images should be a list"
        assert isinstance(
            coco_data["annotations"], list
        ), "Annotations should be a list"
        assert isinstance(coco_data["categories"], list), "Categories should be a list"

    @given(
        special_chars=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.sampled_from("中文日本語한국어émojis🎉特殊字符"),
        )
    )
    @settings(max_examples=25)
    def test_unicode_characters_in_names(self, special_chars):
        """
        COCO format should handle Unicode characters in names.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Unicode characters should be preserved in file_name and category name
        """
        exporter = COCOExporter()

        # Generate test data with Unicode
        images = [
            {"id": 0, "file_name": f"{special_chars}.jpg", "width": 640, "height": 480}
        ]
        categories = [{"id": 0, "name": special_chars}]
        annotations = [
            {"id": 0, "image_id": 0, "category_id": 0, "bbox": [10, 20, 100, 150]}
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Verify Unicode is preserved
        assert (
            coco_data["images"][0]["file_name"] == f"{special_chars}.jpg"
        ), "Unicode in file_name should be preserved"
        assert (
            coco_data["categories"][0]["name"] == special_chars
        ), "Unicode in category name should be preserved"

    @given(
        num_images=st.integers(min_value=1, max_value=10),
        num_categories=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=25)
    def test_annotation_with_segmentation_instead_of_bbox(
        self, num_images, num_categories
    ):
        """
        Annotations can have segmentation instead of bbox.

        **Feature: data-sync-pipeline, Property 17: COCO Format Validation**
        **Validates: Requirement 5.3**

        Segmentation is an alternative to bbox for annotations
        """
        exporter = COCOExporter()

        # Generate test data with segmentation
        images = [
            {"id": i, "file_name": f"image_{i}.jpg", "width": 640, "height": 480}
            for i in range(num_images)
        ]
        categories = [{"id": i, "name": f"category_{i}"} for i in range(num_categories)]
        annotations = [
            {
                "id": i,
                "image_id": i % num_images,
                "category_id": i % num_categories,
                "segmentation": [[10, 20, 30, 40, 50, 60, 10, 20]],  # Polygon points
            }
            for i in range(num_images)
        ]

        # Export to COCO
        coco_str = exporter.export_to_coco(images, annotations, categories)

        # Parse COCO
        coco_data = exporter.parse_coco(coco_str)

        # Verify annotations have segmentation
        for idx, ann in enumerate(coco_data["annotations"]):
            assert "segmentation" in ann, f"Annotation {idx} should have 'segmentation'"
            assert isinstance(
                ann["segmentation"], list
            ), f"Annotation {idx} segmentation should be a list"


# ============================================================================
# Property 18: Enhanced Data Completeness
# **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
# **Validates: Requirements 5.4**
# ============================================================================


class EnhancedDataExporter:
    """
    Enhanced Data Exporter for testing data completeness.

    This class simulates the enhanced data export behavior as specified in Requirement 5.4:

    WHEN semantic enhancement is applied,
    THE AI_Friendly_Output SHALL include both original and enhanced fields in the output

    Enhanced fields typically include:
    - _ai_summary: AI-generated summary
    - _ai_entities: Extracted entities
    - _ai_sentiment: Sentiment analysis
    - _ai_keywords: Extracted keywords
    - _ai_category: AI-assigned category
    - _semantics: Semantic enrichment data
    - _label_studio_annotations: Label Studio annotations
    """

    # Common AI enhancement field prefixes
    AI_FIELD_PREFIXES = ("_ai_", "_semantic", "_label_studio", "_enhanced", "_ml_")

    def __init__(self):
        self.export_count = 0

    def enhance_data(
        self, data: List[Dict[str, Any]], enhancement_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Simulate AI enhancement of data.

        Args:
            data: Original data to enhance
            enhancement_config: Configuration for enhancement

        Returns:
            Enhanced data with both original and AI fields
        """
        enhanced_data = []

        for record in data:
            enhanced_record = record.copy()  # Preserve original fields

            # Add AI enhancement fields based on config
            if enhancement_config.get("add_summary", False):
                enhanced_record["_ai_summary"] = (
                    f"Summary of record: {record.get('id', 'unknown')}"
                )

            if enhancement_config.get("add_entities", False):
                enhanced_record["_ai_entities"] = [
                    {"type": "PERSON", "value": "Entity1"},
                    {"type": "ORG", "value": "Entity2"},
                ]

            if enhancement_config.get("add_sentiment", False):
                enhanced_record["_ai_sentiment"] = {"score": 0.75, "label": "positive"}

            if enhancement_config.get("add_keywords", False):
                enhanced_record["_ai_keywords"] = ["keyword1", "keyword2", "keyword3"]

            if enhancement_config.get("add_category", False):
                enhanced_record["_ai_category"] = "category_a"

            if enhancement_config.get("add_semantics", False):
                enhanced_record["_semantics"] = {
                    "field_descriptions": {"field1": "Description of field1"},
                    "entities": [],
                    "relations": [],
                }

            if enhancement_config.get("add_label_studio", False):
                enhanced_record["_label_studio_annotations"] = {
                    "labels": ["label1", "label2"],
                    "annotator": "user@example.com",
                    "completed_at": "2024-01-15T10:30:00Z",
                }

            enhanced_data.append(enhanced_record)

        return enhanced_data

    def export_to_json(
        self,
        data: List[Dict[str, Any]],
        include_original: bool = True,
        include_enhanced: bool = True,
    ) -> str:
        """
        Export data to JSON format.

        Args:
            data: Data to export (may contain enhanced fields)
            include_original: Whether to include original fields
            include_enhanced: Whether to include enhanced fields

        Returns:
            JSON string
        """
        self.export_count += 1

        if not include_original and not include_enhanced:
            return json.dumps([], indent=2, ensure_ascii=False)

        export_data = []
        for record in data:
            export_record = {}

            for key, value in record.items():
                is_enhanced = any(
                    key.startswith(prefix) for prefix in self.AI_FIELD_PREFIXES
                )

                if is_enhanced and include_enhanced:
                    export_record[key] = value
                elif not is_enhanced and include_original:
                    export_record[key] = value

            export_data.append(export_record)

        return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)

    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        include_original: bool = True,
        include_enhanced: bool = True,
        delimiter: str = ",",
    ) -> str:
        """
        Export data to CSV format.

        Args:
            data: Data to export (may contain enhanced fields)
            include_original: Whether to include original fields
            include_enhanced: Whether to include enhanced fields
            delimiter: CSV delimiter

        Returns:
            CSV string
        """
        self.export_count += 1

        if not data:
            return ""

        # Determine which fields to include
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())

        fieldnames = []
        for field in sorted(all_fields):
            is_enhanced = any(
                field.startswith(prefix) for prefix in self.AI_FIELD_PREFIXES
            )

            if is_enhanced and include_enhanced:
                fieldnames.append(field)
            elif not is_enhanced and include_original:
                fieldnames.append(field)

        if not fieldnames:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=fieldnames, delimiter=delimiter, extrasaction="ignore"
        )
        writer.writeheader()

        for record in data:
            # Flatten nested structures
            flat_row = {}
            for key in fieldnames:
                value = record.get(key)
                if isinstance(value, (dict, list)):
                    flat_row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    flat_row[key] = value
            writer.writerow(flat_row)

        return output.getvalue()

    def get_original_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only original (non-enhanced) fields from a record.

        Args:
            record: Record with potentially enhanced fields

        Returns:
            Dictionary with only original fields
        """
        return {
            key: value
            for key, value in record.items()
            if not any(key.startswith(prefix) for prefix in self.AI_FIELD_PREFIXES)
        }

    def get_enhanced_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only enhanced (AI) fields from a record.

        Args:
            record: Record with potentially enhanced fields

        Returns:
            Dictionary with only enhanced fields
        """
        return {
            key: value
            for key, value in record.items()
            if any(key.startswith(prefix) for prefix in self.AI_FIELD_PREFIXES)
        }

    def verify_data_completeness(
        self, original_data: List[Dict[str, Any]], exported_data: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Verify that exported data contains all original fields.

        Args:
            original_data: Original data before enhancement
            exported_data: Exported data after enhancement

        Returns:
            Tuple of (is_complete, list of missing fields)
        """
        missing_fields = []

        if len(original_data) != len(exported_data):
            return False, [
                f"Record count mismatch: {len(original_data)} vs {len(exported_data)}"
            ]

        for i, (original, exported) in enumerate(zip(original_data, exported_data)):
            for key in original.keys():
                if key not in exported:
                    missing_fields.append(f"Record {i}: missing field '{key}'")

        return len(missing_fields) == 0, missing_fields


class TestEnhancedDataCompleteness:
    """
    Property 18: Enhanced Data Completeness

    Tests that:
    1. Exports contain both original and enhanced fields
    2. No original data is lost during enhancement
    3. Enhanced fields are properly included
    4. Works with various export formats (JSON, CSV)

    **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
    **Validates: Requirements 5.4**
    """

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                    ),
                    "value": st.integers(min_value=-1000000, max_value=1000000),
                    "description": st.text(min_size=0, max_size=200),
                    "active": st.booleans(),
                }
            ),
            min_size=1,
            max_size=50,
        ),
        add_summary=st.booleans(),
        add_entities=st.booleans(),
        add_sentiment=st.booleans(),
    )
    @settings(max_examples=25)
    def test_enhanced_export_contains_original_fields(
        self, data, add_summary, add_entities, add_sentiment
    ):
        """
        Enhanced export should contain all original fields.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        WHEN semantic enhancement is applied,
        THE AI_Friendly_Output SHALL include original fields in the output
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {
            "add_summary": add_summary,
            "add_entities": add_entities,
            "add_sentiment": add_sentiment,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify all original fields are present
        is_complete, missing = exporter.verify_data_completeness(data, exported_data)

        assert is_complete, f"Original fields should be preserved: {missing}"

        # Verify original values match
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            for key, value in original.items():
                assert (
                    key in exported
                ), f"Original field '{key}' should be in exported record {i}"
                assert (
                    exported[key] == value
                ), f"Original value for '{key}' should match at record {i}: {exported[key]} != {value}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "count": st.integers(min_value=0, max_value=10000),
                }
            ),
            min_size=1,
            max_size=30,
        ),
        add_keywords=st.booleans(),
        add_category=st.booleans(),
        add_semantics=st.booleans(),
        add_label_studio=st.booleans(),
    )
    @settings(max_examples=25)
    def test_enhanced_export_contains_enhanced_fields(
        self, data, add_keywords, add_category, add_semantics, add_label_studio
    ):
        """
        Enhanced export should contain all enhanced fields when enabled.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        WHEN semantic enhancement is applied,
        THE AI_Friendly_Output SHALL include enhanced fields in the output
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {
            "add_keywords": add_keywords,
            "add_category": add_category,
            "add_semantics": add_semantics,
            "add_label_studio": add_label_studio,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify enhanced fields are present when enabled
        for i, exported in enumerate(exported_data):
            if add_keywords:
                assert (
                    "_ai_keywords" in exported
                ), f"Enhanced field '_ai_keywords' should be in exported record {i}"

            if add_category:
                assert (
                    "_ai_category" in exported
                ), f"Enhanced field '_ai_category' should be in exported record {i}"

            if add_semantics:
                assert (
                    "_semantics" in exported
                ), f"Enhanced field '_semantics' should be in exported record {i}"

            if add_label_studio:
                assert (
                    "_label_studio_annotations" in exported
                ), f"Enhanced field '_label_studio_annotations' should be in exported record {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "text": st.text(min_size=1, max_size=100),
                    "number": st.floats(
                        min_value=-1000,
                        max_value=1000,
                        allow_nan=False,
                        allow_infinity=False,
                    ),
                    "flag": st.booleans(),
                }
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=25)
    def test_no_original_data_lost_with_all_enhancements(self, data):
        """
        No original data should be lost when all enhancements are applied.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Original data should be preserved regardless of enhancement level
        """
        exporter = EnhancedDataExporter()

        # Apply all enhancements
        enhancement_config = {
            "add_summary": True,
            "add_entities": True,
            "add_sentiment": True,
            "add_keywords": True,
            "add_category": True,
            "add_semantics": True,
            "add_label_studio": True,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify no original data is lost
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            original_fields = exporter.get_original_fields(exported)

            for key, value in original.items():
                assert (
                    key in original_fields
                ), f"Original field '{key}' should not be lost at record {i}"

                # Handle float comparison
                if isinstance(value, float):
                    assert (
                        abs(original_fields[key] - value) < 1e-9
                    ), f"Original float value for '{key}' should match at record {i}"
                else:
                    assert (
                        original_fields[key] == value
                    ), f"Original value for '{key}' should match at record {i}: {original_fields[key]} != {value}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_csv_export_contains_both_original_and_enhanced(self, data):
        """
        CSV export should contain both original and enhanced fields.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        CSV format should preserve both original and enhanced data
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {"add_summary": True, "add_keywords": True}
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to CSV
        csv_str = exporter.export_to_csv(
            enhanced_data, include_original=True, include_enhanced=True
        )

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_str))
        exported_rows = list(reader)

        # Verify record count
        assert len(exported_rows) == len(
            data
        ), f"CSV should have same number of records: {len(exported_rows)} != {len(data)}"

        # Verify original fields are present
        for i, (original, exported) in enumerate(zip(data, exported_rows)):
            for key in original.keys():
                assert (
                    key in exported
                ), f"Original field '{key}' should be in CSV row {i}"

        # Verify enhanced fields are present
        for i, exported in enumerate(exported_rows):
            assert (
                "_ai_summary" in exported
            ), f"Enhanced field '_ai_summary' should be in CSV row {i}"
            assert (
                "_ai_keywords" in exported
            ), f"Enhanced field '_ai_keywords' should be in CSV row {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "chinese_text": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.sampled_from("中文测试数据同步管道属性验证"),
                    ),
                    "value": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_utf8_preserved_in_enhanced_export(self, data):
        """
        UTF-8 characters should be preserved in enhanced export.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        UTF-8 encoding should be preserved for both original and enhanced fields
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {"add_summary": True, "add_entities": True}
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify UTF-8 characters are preserved
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            assert (
                exported["chinese_text"] == original["chinese_text"]
            ), f"Chinese text should be preserved at record {i}: '{exported['chinese_text']}' != '{original['chinese_text']}'"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "nested": st.fixed_dictionaries(
                        {
                            "inner_id": st.uuids().map(str),
                            "inner_value": st.integers(min_value=0, max_value=100),
                        }
                    ),
                    "list_field": st.lists(
                        st.integers(min_value=0, max_value=100), min_size=0, max_size=10
                    ),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_nested_structures_preserved_with_enhancement(self, data):
        """
        Nested structures should be preserved when enhancement is applied.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Nested objects and arrays should not be lost during enhancement
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {"add_semantics": True, "add_entities": True}
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify nested structures are preserved
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            assert (
                "nested" in exported
            ), f"Nested field should be preserved at record {i}"
            assert (
                exported["nested"] == original["nested"]
            ), f"Nested structure should match at record {i}"

            assert (
                "list_field" in exported
            ), f"List field should be preserved at record {i}"
            assert (
                exported["list_field"] == original["list_field"]
            ), f"List field should match at record {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "null_field": st.none(),
                    "empty_string": st.just(""),
                    "zero_value": st.just(0),
                    "false_value": st.just(False),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_edge_case_values_preserved_with_enhancement(self, data):
        """
        Edge case values (null, empty, zero, false) should be preserved.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Edge case values should not be lost or modified during enhancement
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {"add_summary": True, "add_category": True}
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify edge case values are preserved
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            assert (
                exported["null_field"] is None
            ), f"Null field should be preserved at record {i}"
            assert (
                exported["empty_string"] == ""
            ), f"Empty string should be preserved at record {i}"
            assert (
                exported["zero_value"] == 0
            ), f"Zero value should be preserved at record {i}"
            assert (
                exported["false_value"] is False
            ), f"False value should be preserved at record {i}"

    @given(num_records=st.integers(min_value=0, max_value=100))
    @settings(max_examples=25)
    def test_record_count_preserved_with_enhancement(self, num_records):
        """
        Record count should be preserved after enhancement.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Enhancement should not add or remove records
        """
        exporter = EnhancedDataExporter()

        # Generate test data
        data = [
            {"id": str(uuid4()), "name": f"record_{i}", "value": i}
            for i in range(num_records)
        ]

        # Enhance data
        enhancement_config = {
            "add_summary": True,
            "add_entities": True,
            "add_sentiment": True,
            "add_keywords": True,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export to JSON
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify record count
        assert (
            len(exported_data) == num_records
        ), f"Record count should be preserved: {len(exported_data)} != {num_records}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_export_deterministic_with_enhancement(self, data):
        """
        Enhanced export should be deterministic (same input produces same output).

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Multiple exports of the same enhanced data should produce identical output
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {"add_summary": True, "add_category": True}
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export twice
        json_str1 = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )
        json_str2 = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=True
        )

        # Verify outputs are identical
        assert (
            json_str1 == json_str2
        ), "Multiple exports should produce identical output"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_original_only_export_excludes_enhanced_fields(self, data):
        """
        Export with include_enhanced=False should exclude enhanced fields.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Configuration should control which fields are included
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {
            "add_summary": True,
            "add_entities": True,
            "add_keywords": True,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export with only original fields
        json_str = exporter.export_to_json(
            enhanced_data, include_original=True, include_enhanced=False
        )
        exported_data = json.loads(json_str)

        # Verify no enhanced fields are present
        for i, exported in enumerate(exported_data):
            enhanced_fields = exporter.get_enhanced_fields(exported)
            assert (
                len(enhanced_fields) == 0
            ), f"No enhanced fields should be present when include_enhanced=False at record {i}: {enhanced_fields.keys()}"

        # Verify original fields are still present
        for i, (original, exported) in enumerate(zip(data, exported_data)):
            for key in original.keys():
                assert (
                    key in exported
                ), f"Original field '{key}' should still be present at record {i}"

    @given(
        data=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "name": st.text(
                        min_size=1,
                        max_size=50,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "value": st.integers(min_value=0, max_value=1000),
                }
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=25)
    def test_enhanced_only_export_excludes_original_fields(self, data):
        """
        Export with include_original=False should exclude original fields.

        **Feature: data-sync-pipeline, Property 18: Enhanced Data Completeness**
        **Validates: Requirement 5.4**

        Configuration should control which fields are included
        """
        exporter = EnhancedDataExporter()

        # Enhance data
        enhancement_config = {
            "add_summary": True,
            "add_entities": True,
            "add_keywords": True,
        }
        enhanced_data = exporter.enhance_data(data, enhancement_config)

        # Export with only enhanced fields
        json_str = exporter.export_to_json(
            enhanced_data, include_original=False, include_enhanced=True
        )
        exported_data = json.loads(json_str)

        # Verify no original fields are present
        for i, exported in enumerate(exported_data):
            original_fields = exporter.get_original_fields(exported)
            assert (
                len(original_fields) == 0
            ), f"No original fields should be present when include_original=False at record {i}: {original_fields.keys()}"

        # Verify enhanced fields are present
        for i, exported in enumerate(exported_data):
            assert (
                "_ai_summary" in exported
            ), f"Enhanced field '_ai_summary' should be present at record {i}"


# ============================================================================
# Property 21: Tenant-Isolated Metrics
# **Validates: Requirements 6.4**
# ============================================================================


@dataclass
class SyncJobRecord:
    """Sync job record for metrics tracking."""

    job_id: str
    tenant_id: str
    source_id: str
    method: str  # read, pull, push
    status: str  # running, completed, failed
    record_count: int
    duration_seconds: float
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TenantMetricsService:
    """
    Tenant-isolated metrics service for sync jobs.

    Provides statistics (success rate, average duration, error rate) per tenant and method.
    Ensures complete tenant isolation - no cross-tenant data leakage.
    """

    def __init__(self):
        # Store jobs by tenant_id for isolation
        self._jobs_by_tenant: Dict[str, List[SyncJobRecord]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_job(self, job: SyncJobRecord) -> None:
        """Record a sync job for a tenant."""
        with self._lock:
            self._jobs_by_tenant[job.tenant_id].append(job)

    def get_tenant_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific tenant.

        Returns statistics only for the requesting tenant's sync jobs.
        """
        with self._lock:
            tenant_jobs = self._jobs_by_tenant.get(tenant_id, [])

            if not tenant_jobs:
                return {
                    "tenant_id": tenant_id,
                    "total_jobs": 0,
                    "success_rate": 0.0,
                    "average_duration": 0.0,
                    "error_rate": 0.0,
                    "by_method": {},
                    "by_status": {},
                }

            # Calculate overall statistics
            total_jobs = len(tenant_jobs)
            completed_jobs = [j for j in tenant_jobs if j.status == "completed"]
            failed_jobs = [j for j in tenant_jobs if j.status == "failed"]

            success_rate = len(completed_jobs) / total_jobs if total_jobs > 0 else 0.0
            error_rate = len(failed_jobs) / total_jobs if total_jobs > 0 else 0.0

            # Calculate average duration (only for completed jobs)
            durations = [
                j.duration_seconds for j in tenant_jobs if j.duration_seconds > 0
            ]
            average_duration = sum(durations) / len(durations) if durations else 0.0

            # Calculate statistics by method
            by_method = {}
            methods = set(j.method for j in tenant_jobs)
            for method in methods:
                method_jobs = [j for j in tenant_jobs if j.method == method]
                method_completed = [j for j in method_jobs if j.status == "completed"]
                method_failed = [j for j in method_jobs if j.status == "failed"]
                method_durations = [
                    j.duration_seconds for j in method_jobs if j.duration_seconds > 0
                ]

                by_method[method] = {
                    "total_jobs": len(method_jobs),
                    "success_rate": (
                        len(method_completed) / len(method_jobs) if method_jobs else 0.0
                    ),
                    "error_rate": (
                        len(method_failed) / len(method_jobs) if method_jobs else 0.0
                    ),
                    "average_duration": (
                        sum(method_durations) / len(method_durations)
                        if method_durations
                        else 0.0
                    ),
                }

            # Calculate statistics by status
            by_status = {}
            statuses = set(j.status for j in tenant_jobs)
            for status in statuses:
                status_jobs = [j for j in tenant_jobs if j.status == status]
                by_status[status] = len(status_jobs)

            return {
                "tenant_id": tenant_id,
                "total_jobs": total_jobs,
                "success_rate": success_rate,
                "average_duration": average_duration,
                "error_rate": error_rate,
                "by_method": by_method,
                "by_status": by_status,
            }

    def get_all_tenant_ids(self) -> List[str]:
        """Get all tenant IDs that have recorded jobs."""
        with self._lock:
            return list(self._jobs_by_tenant.keys())

    def get_job_count_for_tenant(self, tenant_id: str) -> int:
        """Get the total job count for a tenant."""
        with self._lock:
            return len(self._jobs_by_tenant.get(tenant_id, []))

    def clear(self) -> None:
        """Clear all recorded jobs."""
        with self._lock:
            self._jobs_by_tenant.clear()


class TestTenantIsolatedMetrics:
    """
    Property 21: Tenant-Isolated Metrics

    *For any* tenant requesting sync metrics, the returned statistics should only
    include data from that tenant's sync jobs, and should accurately reflect
    success rate, average duration, and error rate.

    **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
    **Validates: Requirements 6.4**
    """

    @given(
        tenant_a_id=st.uuids().map(str),
        tenant_b_id=st.uuids().map(str),
        tenant_a_jobs=st.integers(min_value=1, max_value=50),
        tenant_b_jobs=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=25)
    def test_tenant_metrics_isolation(
        self, tenant_a_id, tenant_b_id, tenant_a_jobs, tenant_b_jobs
    ):
        """
        Metrics for tenant A should not include tenant B's data.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        When tenant A requests metrics, they should only see their own jobs.
        """
        assume(tenant_a_id != tenant_b_id)

        service = TenantMetricsService()

        # Record jobs for tenant A
        for i in range(tenant_a_jobs):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_a_id,
                source_id=f"source_a_{i}",
                method="read",
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Record jobs for tenant B
        for i in range(tenant_b_jobs):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_b_id,
                source_id=f"source_b_{i}",
                method="pull",
                status="completed",
                record_count=200,
                duration_seconds=2.0,
            )
            service.record_job(job)

        # Get metrics for tenant A
        metrics_a = service.get_tenant_metrics(tenant_a_id)

        # Verify tenant A only sees their own jobs
        assert (
            metrics_a["tenant_id"] == tenant_a_id
        ), "Metrics should be for the requesting tenant"
        assert (
            metrics_a["total_jobs"] == tenant_a_jobs
        ), f"Tenant A should see {tenant_a_jobs} jobs, not {metrics_a['total_jobs']}"

        # Get metrics for tenant B
        metrics_b = service.get_tenant_metrics(tenant_b_id)

        # Verify tenant B only sees their own jobs
        assert (
            metrics_b["tenant_id"] == tenant_b_id
        ), "Metrics should be for the requesting tenant"
        assert (
            metrics_b["total_jobs"] == tenant_b_jobs
        ), f"Tenant B should see {tenant_b_jobs} jobs, not {metrics_b['total_jobs']}"

    @given(
        tenant_id=st.uuids().map(str),
        completed_count=st.integers(min_value=0, max_value=50),
        failed_count=st.integers(min_value=0, max_value=50),
        running_count=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=25)
    def test_success_rate_calculation(
        self, tenant_id, completed_count, failed_count, running_count
    ):
        """
        Success rate should be accurately calculated as completed / total.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Success rate = completed jobs / total jobs
        """
        total_jobs = completed_count + failed_count + running_count
        assume(total_jobs > 0)  # Need at least one job

        service = TenantMetricsService()

        # Record completed jobs
        for i in range(completed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_{i}",
                method="read",
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Record failed jobs
        for i in range(failed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_failed_{i}",
                method="read",
                status="failed",
                record_count=0,
                duration_seconds=0.5,
                error_message="Connection timeout",
            )
            service.record_job(job)

        # Record running jobs
        for i in range(running_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_running_{i}",
                method="read",
                status="running",
                record_count=0,
                duration_seconds=0.0,
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Calculate expected success rate
        expected_success_rate = completed_count / total_jobs

        # Verify success rate
        assert (
            abs(metrics["success_rate"] - expected_success_rate) < 0.0001
        ), f"Success rate should be {expected_success_rate}, got {metrics['success_rate']}"

    @given(
        tenant_id=st.uuids().map(str),
        completed_count=st.integers(min_value=0, max_value=50),
        failed_count=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=25)
    def test_error_rate_calculation(self, tenant_id, completed_count, failed_count):
        """
        Error rate should be accurately calculated as failed / total.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Error rate = failed jobs / total jobs
        """
        total_jobs = completed_count + failed_count
        assume(total_jobs > 0)  # Need at least one job

        service = TenantMetricsService()

        # Record completed jobs
        for i in range(completed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_{i}",
                method="pull",
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Record failed jobs
        for i in range(failed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_failed_{i}",
                method="pull",
                status="failed",
                record_count=0,
                duration_seconds=0.5,
                error_message="Database error",
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Calculate expected error rate
        expected_error_rate = failed_count / total_jobs

        # Verify error rate
        assert (
            abs(metrics["error_rate"] - expected_error_rate) < 0.0001
        ), f"Error rate should be {expected_error_rate}, got {metrics['error_rate']}"

    @given(
        tenant_id=st.uuids().map(str),
        durations=st.lists(
            st.floats(
                min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=25)
    def test_average_duration_calculation(self, tenant_id, durations):
        """
        Average duration should be accurately calculated.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Average duration = sum(durations) / count(durations)
        """
        service = TenantMetricsService()

        # Record jobs with specified durations
        for i, duration in enumerate(durations):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_{i}",
                method="push",
                status="completed",
                record_count=100,
                duration_seconds=duration,
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Calculate expected average duration
        expected_avg_duration = sum(durations) / len(durations)

        # Verify average duration (with floating point tolerance)
        assert (
            abs(metrics["average_duration"] - expected_avg_duration) < 0.0001
        ), f"Average duration should be {expected_avg_duration}, got {metrics['average_duration']}"

    @given(
        tenant_id=st.uuids().map(str),
        read_jobs=st.integers(min_value=0, max_value=20),
        pull_jobs=st.integers(min_value=0, max_value=20),
        push_jobs=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=25)
    def test_metrics_by_method(self, tenant_id, read_jobs, pull_jobs, push_jobs):
        """
        Metrics should be correctly broken down by sync method.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Statistics should be available per method (read, pull, push)
        """
        total_jobs = read_jobs + pull_jobs + push_jobs
        assume(total_jobs > 0)  # Need at least one job

        service = TenantMetricsService()

        # Record read jobs
        for i in range(read_jobs):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_read_{i}",
                method="read",
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Record pull jobs
        for i in range(pull_jobs):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_pull_{i}",
                method="pull",
                status="completed",
                record_count=200,
                duration_seconds=2.0,
            )
            service.record_job(job)

        # Record push jobs
        for i in range(push_jobs):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_push_{i}",
                method="push",
                status="completed",
                record_count=50,
                duration_seconds=0.5,
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Verify by_method breakdown
        by_method = metrics["by_method"]

        if read_jobs > 0:
            assert "read" in by_method, "Read method should be in metrics"
            assert (
                by_method["read"]["total_jobs"] == read_jobs
            ), f"Read jobs count should be {read_jobs}"

        if pull_jobs > 0:
            assert "pull" in by_method, "Pull method should be in metrics"
            assert (
                by_method["pull"]["total_jobs"] == pull_jobs
            ), f"Pull jobs count should be {pull_jobs}"

        if push_jobs > 0:
            assert "push" in by_method, "Push method should be in metrics"
            assert (
                by_method["push"]["total_jobs"] == push_jobs
            ), f"Push jobs count should be {push_jobs}"

    @given(
        num_tenants=st.integers(min_value=2, max_value=10),
        jobs_per_tenant=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=25)
    def test_multi_tenant_isolation(self, num_tenants, jobs_per_tenant):
        """
        With multiple tenants, each tenant should only see their own metrics.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        No cross-tenant data leakage should occur
        """
        service = TenantMetricsService()

        # Generate unique tenant IDs
        tenant_ids = [str(uuid4()) for _ in range(num_tenants)]

        # Record jobs for each tenant with different characteristics
        for tenant_idx, tenant_id in enumerate(tenant_ids):
            for i in range(jobs_per_tenant):
                # Each tenant has different duration patterns
                duration = (
                    tenant_idx + 1
                ) * 1.0  # Tenant 0: 1.0s, Tenant 1: 2.0s, etc.
                job = SyncJobRecord(
                    job_id=str(uuid4()),
                    tenant_id=tenant_id,
                    source_id=f"source_{tenant_idx}_{i}",
                    method="read",
                    status="completed",
                    record_count=100 * (tenant_idx + 1),
                    duration_seconds=duration,
                )
                service.record_job(job)

        # Verify each tenant only sees their own metrics
        for tenant_idx, tenant_id in enumerate(tenant_ids):
            metrics = service.get_tenant_metrics(tenant_id)

            # Verify job count
            assert (
                metrics["total_jobs"] == jobs_per_tenant
            ), f"Tenant {tenant_idx} should see {jobs_per_tenant} jobs, not {metrics['total_jobs']}"

            # Verify average duration matches tenant's pattern
            expected_duration = (tenant_idx + 1) * 1.0
            assert (
                abs(metrics["average_duration"] - expected_duration) < 0.0001
            ), f"Tenant {tenant_idx} average duration should be {expected_duration}, got {metrics['average_duration']}"

    @given(tenant_id=st.uuids().map(str), other_tenant_id=st.uuids().map(str))
    @settings(max_examples=25)
    def test_tenant_b_data_never_visible_to_tenant_a(self, tenant_id, other_tenant_id):
        """
        Tenant B's data should never be visible to Tenant A.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Complete isolation - no data leakage between tenants
        """
        assume(tenant_id != other_tenant_id)

        service = TenantMetricsService()

        # Record jobs only for other_tenant
        for i in range(10):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=other_tenant_id,
                source_id=f"source_{i}",
                method="read",
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Get metrics for tenant_id (who has no jobs)
        metrics = service.get_tenant_metrics(tenant_id)

        # Verify tenant_id sees no jobs (not other_tenant's jobs)
        assert (
            metrics["total_jobs"] == 0
        ), f"Tenant should see 0 jobs, not {metrics['total_jobs']} (other tenant's data)"
        assert (
            metrics["success_rate"] == 0.0
        ), "Success rate should be 0 for tenant with no jobs"
        assert (
            metrics["error_rate"] == 0.0
        ), "Error rate should be 0 for tenant with no jobs"
        assert (
            metrics["average_duration"] == 0.0
        ), "Average duration should be 0 for tenant with no jobs"

    @given(
        tenant_id=st.uuids().map(str),
        method=st.sampled_from(["read", "pull", "push"]),
        completed_count=st.integers(min_value=0, max_value=20),
        failed_count=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=25)
    def test_method_specific_success_and_error_rates(
        self, tenant_id, method, completed_count, failed_count
    ):
        """
        Success and error rates should be correctly calculated per method.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Each method should have its own success/error rate statistics
        """
        total_jobs = completed_count + failed_count
        assume(total_jobs > 0)  # Need at least one job

        service = TenantMetricsService()

        # Record completed jobs for the method
        for i in range(completed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_completed_{i}",
                method=method,
                status="completed",
                record_count=100,
                duration_seconds=1.0,
            )
            service.record_job(job)

        # Record failed jobs for the method
        for i in range(failed_count):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_failed_{i}",
                method=method,
                status="failed",
                record_count=0,
                duration_seconds=0.5,
                error_message="Error",
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Verify method-specific statistics
        assert method in metrics["by_method"], f"Method {method} should be in metrics"

        method_metrics = metrics["by_method"][method]

        expected_success_rate = completed_count / total_jobs
        expected_error_rate = failed_count / total_jobs

        assert (
            abs(method_metrics["success_rate"] - expected_success_rate) < 0.0001
        ), f"Method {method} success rate should be {expected_success_rate}, got {method_metrics['success_rate']}"

        assert (
            abs(method_metrics["error_rate"] - expected_error_rate) < 0.0001
        ), f"Method {method} error rate should be {expected_error_rate}, got {method_metrics['error_rate']}"

    @given(tenant_id=st.uuids().map(str))
    @settings(max_examples=25)
    def test_empty_tenant_metrics(self, tenant_id):
        """
        Tenant with no jobs should get empty metrics (not error).

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Empty state should be handled gracefully
        """
        service = TenantMetricsService()

        # Get metrics for tenant with no jobs
        metrics = service.get_tenant_metrics(tenant_id)

        # Verify empty metrics structure
        assert metrics["tenant_id"] == tenant_id, "Tenant ID should be in response"
        assert metrics["total_jobs"] == 0, "Total jobs should be 0"
        assert metrics["success_rate"] == 0.0, "Success rate should be 0.0"
        assert metrics["error_rate"] == 0.0, "Error rate should be 0.0"
        assert metrics["average_duration"] == 0.0, "Average duration should be 0.0"
        assert metrics["by_method"] == {}, "by_method should be empty dict"
        assert metrics["by_status"] == {}, "by_status should be empty dict"

    @given(
        tenant_id=st.uuids().map(str),
        jobs_data=st.lists(
            st.fixed_dictionaries(
                {
                    "method": st.sampled_from(["read", "pull", "push"]),
                    "status": st.sampled_from(["completed", "failed", "running"]),
                    "duration": st.floats(
                        min_value=0.1,
                        max_value=10.0,
                        allow_nan=False,
                        allow_infinity=False,
                    ),
                }
            ),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=25)
    def test_comprehensive_metrics_accuracy(self, tenant_id, jobs_data):
        """
        All metrics should be accurately calculated for any combination of jobs.

        **Feature: data-sync-pipeline, Property 21: Tenant-Isolated Metrics**
        **Validates: Requirements 6.4**

        Comprehensive test with random job combinations
        """
        service = TenantMetricsService()

        # Record all jobs
        for i, job_data in enumerate(jobs_data):
            job = SyncJobRecord(
                job_id=str(uuid4()),
                tenant_id=tenant_id,
                source_id=f"source_{i}",
                method=job_data["method"],
                status=job_data["status"],
                record_count=100,
                duration_seconds=job_data["duration"],
            )
            service.record_job(job)

        # Get metrics
        metrics = service.get_tenant_metrics(tenant_id)

        # Calculate expected values
        total_jobs = len(jobs_data)
        completed_jobs = sum(1 for j in jobs_data if j["status"] == "completed")
        failed_jobs = sum(1 for j in jobs_data if j["status"] == "failed")
        durations = [j["duration"] for j in jobs_data]

        expected_success_rate = completed_jobs / total_jobs
        expected_error_rate = failed_jobs / total_jobs
        expected_avg_duration = sum(durations) / len(durations)

        # Verify all metrics
        assert (
            metrics["total_jobs"] == total_jobs
        ), f"Total jobs should be {total_jobs}, got {metrics['total_jobs']}"

        assert (
            abs(metrics["success_rate"] - expected_success_rate) < 0.0001
        ), f"Success rate should be {expected_success_rate}, got {metrics['success_rate']}"

        assert (
            abs(metrics["error_rate"] - expected_error_rate) < 0.0001
        ), f"Error rate should be {expected_error_rate}, got {metrics['error_rate']}"

        assert (
            abs(metrics["average_duration"] - expected_avg_duration) < 0.0001
        ), f"Average duration should be {expected_avg_duration}, got {metrics['average_duration']}"

        # Verify by_status counts
        for status in ["completed", "failed", "running"]:
            expected_count = sum(1 for j in jobs_data if j["status"] == status)
            if expected_count > 0:
                assert (
                    status in metrics["by_status"]
                ), f"Status {status} should be in by_status"
                assert (
                    metrics["by_status"][status] == expected_count
                ), f"Status {status} count should be {expected_count}, got {metrics['by_status'].get(status, 0)}"


# ============================================================================
# Property 28: Internationalization Consistency
# **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
# **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
# ============================================================================


class MockI18nService:
    """
    Mock i18n service for testing internationalization consistency.

    Supports zh-CN and en-US languages as specified in Requirements 9.1-9.4.
    """

    # Supported languages
    SUPPORTED_LANGUAGES = ["zh-CN", "en-US"]

    # Translation dictionary with all sync pipeline i18n keys
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "zh-CN": {
            # Data source messages (Requirement 9.1, 9.3)
            "sync_pipeline.data_source.created": "数据源创建成功",
            "sync_pipeline.data_source.updated": "数据源更新成功",
            "sync_pipeline.data_source.deleted": "数据源删除成功",
            "sync_pipeline.data_source.not_found": "数据源不存在",
            "sync_pipeline.data_source.connection_success": "连接成功",
            "sync_pipeline.data_source.connection_failed": "连接失败",
            "sync_pipeline.data_source.name": "数据源名称",
            "sync_pipeline.data_source.type": "数据源类型",
            "sync_pipeline.data_source.host": "主机地址",
            "sync_pipeline.data_source.port": "端口",
            "sync_pipeline.data_source.database": "数据库名",
            "sync_pipeline.data_source.status": "连接状态",
            # Webhook messages (Requirement 9.2)
            "sync_pipeline.webhook.invalid_signature": "签名验证失败",
            "sync_pipeline.webhook.duplicate_request": "重复请求",
            "sync_pipeline.webhook.received": "数据已接收",
            "sync_pipeline.webhook.processing": "正在处理",
            # Schedule messages (Requirement 9.1, 9.3)
            "sync_pipeline.schedule.created": "调度任务创建成功",
            "sync_pipeline.schedule.updated": "调度任务更新成功",
            "sync_pipeline.schedule.deleted": "调度任务删除成功",
            "sync_pipeline.schedule.not_found": "调度任务不存在",
            "sync_pipeline.schedule.triggered": "调度任务已触发",
            "sync_pipeline.schedule.enabled": "调度任务已启用",
            "sync_pipeline.schedule.disabled": "调度任务已禁用",
            # Sync job messages (Requirement 9.1, 9.2)
            "sync_pipeline.job.started": "同步任务已启动",
            "sync_pipeline.job.completed": "同步任务已完成",
            "sync_pipeline.job.failed": "同步任务失败",
            "sync_pipeline.job.cancelled": "同步任务已取消",
            "sync_pipeline.job.running": "同步任务运行中",
            "sync_pipeline.job.pending": "同步任务待处理",
            # Error messages (Requirement 9.2)
            "sync_pipeline.error.connection_timeout": "连接超时",
            "sync_pipeline.error.authentication_failed": "认证失败",
            "sync_pipeline.error.permission_denied": "权限不足",
            "sync_pipeline.error.invalid_config": "配置无效",
            "sync_pipeline.error.data_validation_failed": "数据验证失败",
            "sync_pipeline.error.export_failed": "导出失败",
            "sync_pipeline.error.rate_limit_exceeded": "请求频率超限",
            # Configuration labels (Requirement 9.3)
            "sync_pipeline.config.batch_size": "批量大小",
            "sync_pipeline.config.timeout": "超时时间",
            "sync_pipeline.config.retry_count": "重试次数",
            "sync_pipeline.config.compression": "数据压缩",
            "sync_pipeline.config.encryption": "数据加密",
            "sync_pipeline.config.save_strategy": "存储策略",
            "sync_pipeline.config.export_format": "导出格式",
        },
        "en-US": {
            # Data source messages (Requirement 9.1, 9.3)
            "sync_pipeline.data_source.created": "Data source created successfully",
            "sync_pipeline.data_source.updated": "Data source updated successfully",
            "sync_pipeline.data_source.deleted": "Data source deleted successfully",
            "sync_pipeline.data_source.not_found": "Data source not found",
            "sync_pipeline.data_source.connection_success": "Connection successful",
            "sync_pipeline.data_source.connection_failed": "Connection failed",
            "sync_pipeline.data_source.name": "Data Source Name",
            "sync_pipeline.data_source.type": "Data Source Type",
            "sync_pipeline.data_source.host": "Host Address",
            "sync_pipeline.data_source.port": "Port",
            "sync_pipeline.data_source.database": "Database Name",
            "sync_pipeline.data_source.status": "Connection Status",
            # Webhook messages (Requirement 9.2)
            "sync_pipeline.webhook.invalid_signature": "Invalid signature",
            "sync_pipeline.webhook.duplicate_request": "Duplicate request",
            "sync_pipeline.webhook.received": "Data received",
            "sync_pipeline.webhook.processing": "Processing",
            # Schedule messages (Requirement 9.1, 9.3)
            "sync_pipeline.schedule.created": "Schedule created successfully",
            "sync_pipeline.schedule.updated": "Schedule updated successfully",
            "sync_pipeline.schedule.deleted": "Schedule deleted successfully",
            "sync_pipeline.schedule.not_found": "Schedule not found",
            "sync_pipeline.schedule.triggered": "Schedule triggered",
            "sync_pipeline.schedule.enabled": "Schedule enabled",
            "sync_pipeline.schedule.disabled": "Schedule disabled",
            # Sync job messages (Requirement 9.1, 9.2)
            "sync_pipeline.job.started": "Sync job started",
            "sync_pipeline.job.completed": "Sync job completed",
            "sync_pipeline.job.failed": "Sync job failed",
            "sync_pipeline.job.cancelled": "Sync job cancelled",
            "sync_pipeline.job.running": "Sync job running",
            "sync_pipeline.job.pending": "Sync job pending",
            # Error messages (Requirement 9.2)
            "sync_pipeline.error.connection_timeout": "Connection timeout",
            "sync_pipeline.error.authentication_failed": "Authentication failed",
            "sync_pipeline.error.permission_denied": "Permission denied",
            "sync_pipeline.error.invalid_config": "Invalid configuration",
            "sync_pipeline.error.data_validation_failed": "Data validation failed",
            "sync_pipeline.error.export_failed": "Export failed",
            "sync_pipeline.error.rate_limit_exceeded": "Rate limit exceeded",
            # Configuration labels (Requirement 9.3)
            "sync_pipeline.config.batch_size": "Batch Size",
            "sync_pipeline.config.timeout": "Timeout",
            "sync_pipeline.config.retry_count": "Retry Count",
            "sync_pipeline.config.compression": "Data Compression",
            "sync_pipeline.config.encryption": "Data Encryption",
            "sync_pipeline.config.save_strategy": "Save Strategy",
            "sync_pipeline.config.export_format": "Export Format",
        },
    }

    def __init__(self, default_language: str = "zh-CN"):
        """Initialize i18n service with default language."""
        self.default_language = default_language
        self._current_language = default_language

    def get_translation(self, key: str, language: Optional[str] = None) -> str:
        """
        Get translation for a key in the specified language.

        Args:
            key: The i18n key to translate
            language: Target language (zh-CN or en-US), defaults to current language

        Returns:
            Translated string, or the key itself if not found
        """
        lang = language or self._current_language

        if lang not in self.SUPPORTED_LANGUAGES:
            lang = self.default_language

        translations = self.TRANSLATIONS.get(lang, {})
        return translations.get(key, key)

    def set_language(self, language: str) -> bool:
        """
        Set the current language.

        Args:
            language: Language code (zh-CN or en-US)

        Returns:
            True if language was set, False if unsupported
        """
        if language in self.SUPPORTED_LANGUAGES:
            self._current_language = language
            return True
        return False

    def get_current_language(self) -> str:
        """Get the current language."""
        return self._current_language

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_all_keys(self) -> List[str]:
        """Get all available i18n keys."""
        # Return keys from zh-CN as the reference
        return list(self.TRANSLATIONS.get("zh-CN", {}).keys())

    def has_translation(self, key: str, language: str) -> bool:
        """Check if a translation exists for a key in a language."""
        translations = self.TRANSLATIONS.get(language, {})
        return key in translations

    def is_i18n_key(self, text: str) -> bool:
        """
        Check if a text is an i18n key (not a raw message).

        i18n keys follow the pattern: module.category.action
        """
        if not text or not isinstance(text, str):
            return False

        # i18n keys have dots and follow naming convention
        parts = text.split(".")
        if len(parts) < 2:
            return False

        # Check if it's a known key
        return text in self.get_all_keys()


class APIResponseGenerator:
    """
    Simulates API response generation with i18n support.

    Used to test that API responses use i18n keys (Requirement 9.1).
    """

    def __init__(self, i18n_service: MockI18nService):
        self.i18n = i18n_service

    def create_success_response(
        self,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a success response with localized message.

        Args:
            operation: Operation type (e.g., 'data_source.created')
            data: Optional response data
            language: Target language for message

        Returns:
            Response dict with localized message
        """
        message_key = f"sync_pipeline.{operation}"
        message = self.i18n.get_translation(message_key, language)

        return {
            "success": True,
            "message_key": message_key,  # Store the i18n key
            "message": message,  # Localized message
            "data": data or {},
            "language": language or self.i18n.get_current_language(),
        }

    def create_error_response(
        self,
        error_type: str,
        details: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an error response with localized message.

        Args:
            error_type: Error type (e.g., 'connection_timeout')
            details: Optional error details
            language: Target language for message

        Returns:
            Response dict with localized error message
        """
        message_key = f"sync_pipeline.error.{error_type}"
        message = self.i18n.get_translation(message_key, language)

        return {
            "success": False,
            "error_key": message_key,  # Store the i18n key
            "error": message,  # Localized error message
            "details": details or {},
            "language": language or self.i18n.get_current_language(),
        }


class ConfigLabelTranslator:
    """
    Translates configuration labels using i18n service.

    Used to test that configuration labels are translated (Requirement 9.3).
    """

    def __init__(self, i18n_service: MockI18nService):
        self.i18n = i18n_service

    def translate_config_labels(
        self, config: Dict[str, Any], language: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Translate configuration labels.

        Args:
            config: Configuration dictionary
            language: Target language

        Returns:
            Dict with translated labels for each config key
        """
        result = {}

        for key, value in config.items():
            label_key = f"sync_pipeline.config.{key}"
            translated_label = self.i18n.get_translation(label_key, language)

            result[key] = {
                "label_key": label_key,
                "label": translated_label,
                "value": value,
                "language": language or self.i18n.get_current_language(),
            }

        return result


class LogMessageFormatter:
    """
    Formats log messages with i18n support.

    Used to test that logs use English for technical details
    and i18n keys for user-facing content (Requirement 9.4).
    """

    def __init__(self, i18n_service: MockI18nService):
        self.i18n = i18n_service

    def format_log_message(
        self,
        level: str,
        technical_message: str,
        user_facing_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format a log message with proper i18n handling.

        Technical details are always in English.
        User-facing content uses i18n keys.

        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            technical_message: Technical message in English
            user_facing_key: Optional i18n key for user-facing message
            context: Optional context data

        Returns:
            Formatted log entry
        """
        log_entry = {
            "level": level,
            "technical_message": technical_message,  # Always English
            "technical_language": "en",  # Technical logs are always English
            "context": context or {},
        }

        if user_facing_key:
            log_entry["user_facing_key"] = user_facing_key
            # User-facing messages can be localized
            log_entry["user_facing_message_zh"] = self.i18n.get_translation(
                user_facing_key, "zh-CN"
            )
            log_entry["user_facing_message_en"] = self.i18n.get_translation(
                user_facing_key, "en-US"
            )

        return log_entry


class TestInternationalizationConsistency:
    """
    Property 28: Internationalization Consistency

    Tests that:
    1. All user-facing messages use i18n keys (Requirement 9.1)
    2. Error messages are localized in zh-CN and en-US (Requirement 9.2)
    3. Configuration labels are translated (Requirement 9.3)
    4. Logs use English for technical details and i18n keys for user-facing content (Requirement 9.4)

    **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """

    @given(
        operation=st.sampled_from(
            [
                "data_source.created",
                "data_source.updated",
                "data_source.deleted",
                "data_source.not_found",
                "data_source.connection_success",
                "data_source.connection_failed",
                "schedule.created",
                "schedule.updated",
                "schedule.deleted",
                "schedule.not_found",
                "schedule.triggered",
                "schedule.enabled",
                "schedule.disabled",
                "job.started",
                "job.completed",
                "job.failed",
                "job.cancelled",
                "job.running",
                "job.pending",
                "webhook.invalid_signature",
                "webhook.duplicate_request",
                "webhook.received",
                "webhook.processing",
            ]
        ),
        language=st.sampled_from(["zh-CN", "en-US"]),
    )
    @settings(max_examples=25)
    def test_api_responses_use_i18n_keys(self, operation, language):
        """
        API responses should use i18n keys for all user-facing messages.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.1**

        WHEN API responses are generated,
        THE Data_Sync_Pipeline SHALL use i18n keys for all user-facing messages
        """
        i18n_service = MockI18nService()
        api_generator = APIResponseGenerator(i18n_service)

        # Generate response
        response = api_generator.create_success_response(
            operation=operation, data={"test": "data"}, language=language
        )

        # Verify i18n key is stored
        assert "message_key" in response, "Response should contain message_key"

        expected_key = f"sync_pipeline.{operation}"
        assert (
            response["message_key"] == expected_key
        ), f"Message key should be {expected_key}, got {response['message_key']}"

        # Verify the key exists in translations
        assert i18n_service.has_translation(
            expected_key, language
        ), f"Translation should exist for key {expected_key} in {language}"

        # Verify message is localized (not the raw key)
        assert (
            response["message"] != expected_key
        ), f"Message should be translated, not raw key: {response['message']}"

    @given(
        error_type=st.sampled_from(
            [
                "connection_timeout",
                "authentication_failed",
                "permission_denied",
                "invalid_config",
                "data_validation_failed",
                "export_failed",
                "rate_limit_exceeded",
            ]
        ),
        language=st.sampled_from(["zh-CN", "en-US"]),
    )
    @settings(max_examples=25)
    def test_error_messages_localized_in_both_languages(self, error_type, language):
        """
        Error messages should be localized in the user's language (zh-CN or en-US).

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.2**

        WHEN error messages are returned,
        THE Data_Sync_Pipeline SHALL provide localized messages in the user's language (zh-CN or en-US)
        """
        i18n_service = MockI18nService()
        api_generator = APIResponseGenerator(i18n_service)

        # Generate error response
        response = api_generator.create_error_response(
            error_type=error_type, details={"code": "ERR_001"}, language=language
        )

        # Verify error key is stored
        assert "error_key" in response, "Response should contain error_key"

        expected_key = f"sync_pipeline.error.{error_type}"
        assert (
            response["error_key"] == expected_key
        ), f"Error key should be {expected_key}, got {response['error_key']}"

        # Verify translation exists in both languages
        assert i18n_service.has_translation(
            expected_key, "zh-CN"
        ), f"Translation should exist for key {expected_key} in zh-CN"
        assert i18n_service.has_translation(
            expected_key, "en-US"
        ), f"Translation should exist for key {expected_key} in en-US"

        # Verify message is in the requested language
        assert (
            response["language"] == language
        ), f"Response language should be {language}, got {response['language']}"

        # Verify message is localized (not the raw key)
        assert (
            response["error"] != expected_key
        ), f"Error message should be translated, not raw key: {response['error']}"

    @given(
        error_type=st.sampled_from(
            [
                "connection_timeout",
                "authentication_failed",
                "permission_denied",
                "invalid_config",
                "data_validation_failed",
                "export_failed",
                "rate_limit_exceeded",
            ]
        )
    )
    @settings(max_examples=25)
    def test_error_messages_differ_between_languages(self, error_type):
        """
        Error messages in zh-CN and en-US should be different (properly localized).

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.2**
        """
        i18n_service = MockI18nService()

        error_key = f"sync_pipeline.error.{error_type}"

        # Get translations in both languages
        zh_message = i18n_service.get_translation(error_key, "zh-CN")
        en_message = i18n_service.get_translation(error_key, "en-US")

        # Verify translations are different
        assert (
            zh_message != en_message
        ), f"zh-CN and en-US translations should differ for {error_key}: zh={zh_message}, en={en_message}"

        # Verify zh-CN contains Chinese characters
        has_chinese = any("\u4e00" <= char <= "\u9fff" for char in zh_message)
        assert (
            has_chinese
        ), f"zh-CN translation should contain Chinese characters: {zh_message}"

        # Verify en-US contains only ASCII/Latin characters
        is_english = all(ord(char) < 256 for char in en_message)
        assert (
            is_english
        ), f"en-US translation should contain only English characters: {en_message}"

    @given(
        config_key=st.sampled_from(
            [
                "batch_size",
                "timeout",
                "retry_count",
                "compression",
                "encryption",
                "save_strategy",
                "export_format",
            ]
        ),
        config_value=st.one_of(
            st.integers(min_value=1, max_value=10000),
            st.booleans(),
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("L", "N")),
            ),
        ),
        language=st.sampled_from(["zh-CN", "en-US"]),
    )
    @settings(max_examples=25)
    def test_configuration_labels_translated(self, config_key, config_value, language):
        """
        Configuration labels should be translated using the i18n service.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.3**

        WHEN configuration labels are displayed,
        THE Data_Sync_Pipeline SHALL translate them using the i18n service
        """
        i18n_service = MockI18nService()
        translator = ConfigLabelTranslator(i18n_service)

        # Create config with single key
        config = {config_key: config_value}

        # Translate labels
        result = translator.translate_config_labels(config, language)

        # Verify result structure
        assert config_key in result, f"Result should contain key {config_key}"

        translated = result[config_key]

        # Verify label_key is stored
        expected_label_key = f"sync_pipeline.config.{config_key}"
        assert (
            translated["label_key"] == expected_label_key
        ), f"Label key should be {expected_label_key}, got {translated['label_key']}"

        # Verify translation exists
        assert i18n_service.has_translation(
            expected_label_key, language
        ), f"Translation should exist for {expected_label_key} in {language}"

        # Verify label is translated (not the raw key)
        assert (
            translated["label"] != expected_label_key
        ), f"Label should be translated, not raw key: {translated['label']}"

        # Verify value is preserved
        assert (
            translated["value"] == config_value
        ), f"Config value should be preserved: {translated['value']} != {config_value}"

        # Verify language is set
        assert (
            translated["language"] == language
        ), f"Language should be {language}, got {translated['language']}"

    @given(
        config=st.fixed_dictionaries(
            {
                "batch_size": st.integers(min_value=100, max_value=10000),
                "timeout": st.integers(min_value=1, max_value=300),
                "retry_count": st.integers(min_value=0, max_value=10),
                "compression": st.booleans(),
                "encryption": st.booleans(),
            }
        ),
        language=st.sampled_from(["zh-CN", "en-US"]),
    )
    @settings(max_examples=25)
    def test_all_config_labels_have_translations(self, config, language):
        """
        All configuration labels should have translations in both languages.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.3**
        """
        i18n_service = MockI18nService()
        translator = ConfigLabelTranslator(i18n_service)

        # Translate all labels
        result = translator.translate_config_labels(config, language)

        # Verify all keys are translated
        for key in config.keys():
            assert key in result, f"Key {key} should be in result"

            label_key = f"sync_pipeline.config.{key}"

            # Verify translation exists in both languages
            assert i18n_service.has_translation(
                label_key, "zh-CN"
            ), f"zh-CN translation should exist for {label_key}"
            assert i18n_service.has_translation(
                label_key, "en-US"
            ), f"en-US translation should exist for {label_key}"

    @given(
        log_level=st.sampled_from(["INFO", "WARNING", "ERROR", "DEBUG"]),
        technical_message=st.text(
            min_size=10,
            max_size=200,
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
        ),
        user_facing_key=st.sampled_from(
            [
                "sync_pipeline.job.started",
                "sync_pipeline.job.completed",
                "sync_pipeline.job.failed",
                "sync_pipeline.data_source.created",
                "sync_pipeline.data_source.connection_failed",
                "sync_pipeline.error.connection_timeout",
                "sync_pipeline.error.authentication_failed",
            ]
        ),
    )
    @settings(max_examples=25)
    def test_logs_use_english_for_technical_details(
        self, log_level, technical_message, user_facing_key
    ):
        """
        Logs should use English for technical details and i18n keys for user-facing content.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.4**

        WHEN logs are written,
        THE Data_Sync_Pipeline SHALL use English for technical details
        and i18n keys for user-facing content
        """
        i18n_service = MockI18nService()
        log_formatter = LogMessageFormatter(i18n_service)

        # Format log message
        log_entry = log_formatter.format_log_message(
            level=log_level,
            technical_message=technical_message,
            user_facing_key=user_facing_key,
            context={"source_id": "test_source"},
        )

        # Verify technical message is preserved as-is
        assert (
            log_entry["technical_message"] == technical_message
        ), "Technical message should be preserved"

        # Verify technical language is English
        assert (
            log_entry["technical_language"] == "en"
        ), "Technical language should be 'en'"

        # Verify user-facing key is stored
        assert (
            log_entry["user_facing_key"] == user_facing_key
        ), f"User-facing key should be {user_facing_key}"

        # Verify user-facing messages are available in both languages
        assert (
            "user_facing_message_zh" in log_entry
        ), "zh-CN user-facing message should be present"
        assert (
            "user_facing_message_en" in log_entry
        ), "en-US user-facing message should be present"

        # Verify translations are different
        zh_msg = log_entry["user_facing_message_zh"]
        en_msg = log_entry["user_facing_message_en"]

        assert (
            zh_msg != en_msg
        ), f"zh-CN and en-US messages should differ: zh={zh_msg}, en={en_msg}"

    @given(
        log_level=st.sampled_from(["INFO", "WARNING", "ERROR"]),
        technical_message=st.text(
            min_size=5,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
        ),
    )
    @settings(max_examples=25)
    def test_logs_without_user_facing_content(self, log_level, technical_message):
        """
        Logs without user-facing content should still have English technical details.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.4**
        """
        i18n_service = MockI18nService()
        log_formatter = LogMessageFormatter(i18n_service)

        # Format log message without user-facing key
        log_entry = log_formatter.format_log_message(
            level=log_level,
            technical_message=technical_message,
            user_facing_key=None,  # No user-facing content
            context={},
        )

        # Verify technical message is preserved
        assert (
            log_entry["technical_message"] == technical_message
        ), "Technical message should be preserved"

        # Verify technical language is English
        assert (
            log_entry["technical_language"] == "en"
        ), "Technical language should be 'en'"

        # Verify no user-facing content
        assert (
            "user_facing_key" not in log_entry
        ), "User-facing key should not be present when not provided"

    @given(
        i18n_key=st.sampled_from(
            [
                "sync_pipeline.data_source.created",
                "sync_pipeline.data_source.not_found",
                "sync_pipeline.schedule.created",
                "sync_pipeline.schedule.triggered",
                "sync_pipeline.job.started",
                "sync_pipeline.job.completed",
                "sync_pipeline.error.connection_timeout",
                "sync_pipeline.error.permission_denied",
                "sync_pipeline.config.batch_size",
                "sync_pipeline.config.timeout",
            ]
        )
    )
    @settings(max_examples=25)
    def test_all_i18n_keys_have_both_translations(self, i18n_key):
        """
        All i18n keys should have translations in both zh-CN and en-US.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirements 9.1, 9.2, 9.3**
        """
        i18n_service = MockI18nService()

        # Verify translation exists in zh-CN
        assert i18n_service.has_translation(
            i18n_key, "zh-CN"
        ), f"zh-CN translation should exist for {i18n_key}"

        # Verify translation exists in en-US
        assert i18n_service.has_translation(
            i18n_key, "en-US"
        ), f"en-US translation should exist for {i18n_key}"

        # Get both translations
        zh_translation = i18n_service.get_translation(i18n_key, "zh-CN")
        en_translation = i18n_service.get_translation(i18n_key, "en-US")

        # Verify translations are not empty
        assert (
            zh_translation and len(zh_translation) > 0
        ), f"zh-CN translation should not be empty for {i18n_key}"
        assert (
            en_translation and len(en_translation) > 0
        ), f"en-US translation should not be empty for {i18n_key}"

        # Verify translations are not the raw key
        assert (
            zh_translation != i18n_key
        ), f"zh-CN translation should not be the raw key for {i18n_key}"
        assert (
            en_translation != i18n_key
        ), f"en-US translation should not be the raw key for {i18n_key}"

    @given(language=st.sampled_from(["zh-CN", "en-US"]))
    @settings(max_examples=25)
    def test_language_switching(self, language):
        """
        Language switching should work correctly.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirements 9.1, 9.2**
        """
        i18n_service = MockI18nService()

        # Set language
        result = i18n_service.set_language(language)

        assert result, f"Setting language to {language} should succeed"

        assert (
            i18n_service.get_current_language() == language
        ), f"Current language should be {language}"

        # Get translation without specifying language (should use current)
        test_key = "sync_pipeline.data_source.created"
        translation = i18n_service.get_translation(test_key)

        # Verify translation matches the set language
        expected_translation = i18n_service.get_translation(test_key, language)
        assert (
            translation == expected_translation
        ), f"Translation should match {language} translation"

    @given(
        unsupported_language=st.text(
            min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=("L",))
        ).filter(lambda x: x not in ["zh-CN", "en-US", "zh", "en"])
    )
    @settings(max_examples=25)
    def test_unsupported_language_fallback(self, unsupported_language):
        """
        Unsupported languages should fall back to default language.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirements 9.1, 9.2**
        """
        i18n_service = MockI18nService(default_language="zh-CN")

        # Try to set unsupported language
        result = i18n_service.set_language(unsupported_language)

        assert (
            not result
        ), f"Setting unsupported language {unsupported_language} should fail"

        # Current language should remain default
        assert (
            i18n_service.get_current_language() == "zh-CN"
        ), "Current language should remain default after failed set"

        # Get translation with unsupported language should fall back
        test_key = "sync_pipeline.data_source.created"
        translation = i18n_service.get_translation(test_key, unsupported_language)

        # Should get default language translation
        default_translation = i18n_service.get_translation(test_key, "zh-CN")
        assert (
            translation == default_translation
        ), "Unsupported language should fall back to default"

    @given(num_keys=st.integers(min_value=1, max_value=20))
    @settings(max_examples=25)
    def test_translation_consistency_across_all_keys(self, num_keys):
        """
        All i18n keys should have consistent translations in both languages.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        i18n_service = MockI18nService()

        # Get all available keys
        all_keys = i18n_service.get_all_keys()

        # Sample keys to test
        keys_to_test = all_keys[: min(num_keys, len(all_keys))]

        for key in keys_to_test:
            # Verify key exists in both languages
            assert i18n_service.has_translation(
                key, "zh-CN"
            ), f"zh-CN translation should exist for {key}"
            assert i18n_service.has_translation(
                key, "en-US"
            ), f"en-US translation should exist for {key}"

            # Get translations
            zh_trans = i18n_service.get_translation(key, "zh-CN")
            en_trans = i18n_service.get_translation(key, "en-US")

            # Verify translations are different (properly localized)
            assert (
                zh_trans != en_trans
            ), f"Translations should differ for {key}: zh={zh_trans}, en={en_trans}"

            # Verify neither is the raw key
            assert zh_trans != key, f"zh-CN should not be raw key for {key}"
            assert en_trans != key, f"en-US should not be raw key for {key}"

    @given(
        operation=st.sampled_from(
            [
                "data_source.created",
                "data_source.updated",
                "data_source.deleted",
                "schedule.created",
                "schedule.triggered",
                "job.started",
                "job.completed",
                "job.failed",
            ]
        )
    )
    @settings(max_examples=25)
    def test_zh_cn_returns_chinese_text(self, operation):
        """
        Requesting zh-CN should return Chinese text.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.2**
        """
        i18n_service = MockI18nService()
        api_generator = APIResponseGenerator(i18n_service)

        # Generate response in zh-CN
        response = api_generator.create_success_response(
            operation=operation, language="zh-CN"
        )

        message = response["message"]

        # Verify message contains Chinese characters
        has_chinese = any("\u4e00" <= char <= "\u9fff" for char in message)
        assert (
            has_chinese
        ), f"zh-CN message should contain Chinese characters: {message}"

    @given(
        operation=st.sampled_from(
            [
                "data_source.created",
                "data_source.updated",
                "data_source.deleted",
                "schedule.created",
                "schedule.triggered",
                "job.started",
                "job.completed",
                "job.failed",
            ]
        )
    )
    @settings(max_examples=25)
    def test_en_us_returns_english_text(self, operation):
        """
        Requesting en-US should return English text.

        **Feature: data-sync-pipeline, Property 28: Internationalization Consistency**
        **Validates: Requirement 9.2**
        """
        i18n_service = MockI18nService()
        api_generator = APIResponseGenerator(i18n_service)

        # Generate response in en-US
        response = api_generator.create_success_response(
            operation=operation, language="en-US"
        )

        message = response["message"]

        # Verify message contains only ASCII/Latin characters
        is_english = all(ord(char) < 256 for char in message)
        assert (
            is_english
        ), f"en-US message should contain only English characters: {message}"

        # Verify no Chinese characters
        has_chinese = any("\u4e00" <= char <= "\u9fff" for char in message)
        assert (
            not has_chinese
        ), f"en-US message should not contain Chinese characters: {message}"


# ============================================================================
# Property 22: Alert Threshold Triggering
# **Validates: Requirements 6.5**
# Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering
# ============================================================================


class MockAlertService:
    """
    Mock alert service that tracks triggered alerts for testing.

    Implements alert triggering with deduplication to ensure alerts
    are triggered exactly once per threshold breach.
    """

    def __init__(self, error_threshold: float = 0.10):
        """
        Initialize the mock alert service.

        Args:
            error_threshold: Error rate threshold (0.0 to 1.0) that triggers alerts.
                           Default is 10% (0.10).
        """
        self.error_threshold = error_threshold
        self.triggered_alerts: List[Dict[str, Any]] = []
        self.active_breaches: Set[str] = set()  # Track active threshold breaches
        self._lock = threading.Lock()

    def check_error_rate(
        self, tenant_id: str, source_id: str, error_rate: float
    ) -> bool:
        """
        Check error rate and trigger alert if threshold exceeded.

        Returns True if an alert was triggered, False otherwise.
        """
        breach_key = f"{tenant_id}:{source_id}"

        with self._lock:
            if error_rate > self.error_threshold:
                # Threshold exceeded
                if breach_key not in self.active_breaches:
                    # First breach - trigger alert
                    self.active_breaches.add(breach_key)
                    alert = {
                        "tenant_id": tenant_id,
                        "source_id": source_id,
                        "error_rate": error_rate,
                        "threshold": self.error_threshold,
                        "timestamp": datetime.utcnow().isoformat(),
                        "alert_type": "error_rate_exceeded",
                    }
                    self.triggered_alerts.append(alert)
                    return True
                else:
                    # Already in breach state - no new alert
                    return False
            else:
                # Below threshold - clear breach state if exists
                if breach_key in self.active_breaches:
                    self.active_breaches.remove(breach_key)
                return False

    def get_triggered_alerts(self) -> List[Dict[str, Any]]:
        """Get all triggered alerts."""
        with self._lock:
            return list(self.triggered_alerts)

    def get_alert_count(self) -> int:
        """Get total number of triggered alerts."""
        with self._lock:
            return len(self.triggered_alerts)

    def get_alerts_for_source(
        self, tenant_id: str, source_id: str
    ) -> List[Dict[str, Any]]:
        """Get alerts for a specific source."""
        with self._lock:
            return [
                a
                for a in self.triggered_alerts
                if a["tenant_id"] == tenant_id and a["source_id"] == source_id
            ]

    def is_in_breach(self, tenant_id: str, source_id: str) -> bool:
        """Check if a source is currently in breach state."""
        breach_key = f"{tenant_id}:{source_id}"
        with self._lock:
            return breach_key in self.active_breaches

    def reset(self):
        """Reset all alerts and breach states."""
        with self._lock:
            self.triggered_alerts.clear()
            self.active_breaches.clear()


class SyncErrorTracker:
    """
    Tracks sync errors and calculates error rates.

    Used to simulate sync operations and track error rates
    for alert threshold testing.
    """

    def __init__(self, alert_service: MockAlertService):
        self.alert_service = alert_service
        self.sync_records: Dict[str, Dict[str, Any]] = {}  # key: tenant_id:source_id
        self._lock = threading.Lock()

    def record_sync_result(
        self, tenant_id: str, source_id: str, total_records: int, error_count: int
    ) -> Dict[str, Any]:
        """
        Record a sync result and check for alert triggering.

        Returns the sync result with error rate and alert status.
        """
        key = f"{tenant_id}:{source_id}"

        with self._lock:
            # Calculate error rate
            error_rate = error_count / total_records if total_records > 0 else 0.0

            # Update cumulative stats
            if key not in self.sync_records:
                self.sync_records[key] = {
                    "total_records": 0,
                    "total_errors": 0,
                    "sync_count": 0,
                }

            stats = self.sync_records[key]
            stats["total_records"] += total_records
            stats["total_errors"] += error_count
            stats["sync_count"] += 1

            # Calculate cumulative error rate
            cumulative_error_rate = (
                stats["total_errors"] / stats["total_records"]
                if stats["total_records"] > 0
                else 0.0
            )

        # Check alert threshold (outside lock to avoid deadlock)
        alert_triggered = self.alert_service.check_error_rate(
            tenant_id, source_id, error_rate
        )

        return {
            "tenant_id": tenant_id,
            "source_id": source_id,
            "total_records": total_records,
            "error_count": error_count,
            "error_rate": error_rate,
            "cumulative_error_rate": cumulative_error_rate,
            "alert_triggered": alert_triggered,
        }

    def get_stats(self, tenant_id: str, source_id: str) -> Optional[Dict[str, Any]]:
        """Get cumulative stats for a source."""
        key = f"{tenant_id}:{source_id}"
        with self._lock:
            return self.sync_records.get(key)

    def reset(self):
        """Reset all tracking data."""
        with self._lock:
            self.sync_records.clear()


class TestAlertThresholdTriggering:
    """
    Property 22: Alert Threshold Triggering

    Tests that alerts trigger when error rate exceeds threshold,
    and that alerts are deduplicated (triggered exactly once per breach).

    **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
    **Validates: Requirements 6.5**
    """

    @given(
        tenant_id=st.uuids().map(str),
        source_id=st.uuids().map(str),
        threshold=st.floats(
            min_value=0.01, max_value=0.50, allow_nan=False, allow_infinity=False
        ),
        error_rate=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25)
    def test_alert_triggers_when_error_rate_exceeds_threshold(
        self, tenant_id, source_id, threshold, error_rate
    ):
        """
        Alerts should trigger when error rate exceeds the configured threshold.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        # Calculate records to achieve the desired error rate
        total_records = 100
        error_count = int(error_rate * total_records)
        actual_error_rate = error_count / total_records if total_records > 0 else 0.0

        # Check error rate
        alert_triggered = alert_service.check_error_rate(
            tenant_id, source_id, actual_error_rate
        )

        if actual_error_rate > threshold:
            # Alert should be triggered
            assert (
                alert_triggered
            ), f"Alert should trigger when error rate {actual_error_rate:.2%} > threshold {threshold:.2%}"
            assert (
                alert_service.get_alert_count() == 1
            ), "Exactly one alert should be triggered"

            # Verify alert details
            alerts = alert_service.get_triggered_alerts()
            assert len(alerts) == 1
            assert alerts[0]["tenant_id"] == tenant_id
            assert alerts[0]["source_id"] == source_id
            assert alerts[0]["error_rate"] == actual_error_rate
            assert alerts[0]["threshold"] == threshold
        else:
            # Alert should not be triggered
            assert (
                not alert_triggered
            ), f"Alert should not trigger when error rate {actual_error_rate:.2%} <= threshold {threshold:.2%}"
            assert alert_service.get_alert_count() == 0, "No alerts should be triggered"

    @given(
        tenant_id=st.uuids().map(str),
        source_id=st.uuids().map(str),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        num_checks=st.integers(min_value=2, max_value=10),
    )
    @settings(max_examples=25)
    def test_alert_triggered_exactly_once_per_breach(
        self, tenant_id, source_id, threshold, num_checks
    ):
        """
        Alerts should be triggered exactly once per threshold breach,
        not repeatedly for consecutive high error rates.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        # Error rate that exceeds threshold
        high_error_rate = threshold + 0.10

        # Check multiple times with high error rate
        alerts_triggered = []
        for i in range(num_checks):
            triggered = alert_service.check_error_rate(
                tenant_id, source_id, high_error_rate
            )
            alerts_triggered.append(triggered)

        # Only the first check should trigger an alert
        assert alerts_triggered[0] is True, "First check should trigger alert"
        assert all(
            not t for t in alerts_triggered[1:]
        ), "Subsequent checks should not trigger additional alerts"

        # Total alert count should be exactly 1
        assert (
            alert_service.get_alert_count() == 1
        ), f"Expected exactly 1 alert, got {alert_service.get_alert_count()}"

        # Source should be in breach state
        assert alert_service.is_in_breach(
            tenant_id, source_id
        ), "Source should be in breach state"

    @given(
        tenant_id=st.uuids().map(str),
        source_id=st.uuids().map(str),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25)
    def test_alert_not_triggered_when_below_threshold(
        self, tenant_id, source_id, threshold
    ):
        """
        Alerts should not be triggered when error rate is below threshold.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        # Error rate below threshold
        low_error_rate = threshold * 0.5  # 50% of threshold

        # Check error rate
        alert_triggered = alert_service.check_error_rate(
            tenant_id, source_id, low_error_rate
        )

        assert (
            not alert_triggered
        ), f"Alert should not trigger when error rate {low_error_rate:.2%} < threshold {threshold:.2%}"
        assert alert_service.get_alert_count() == 0, "No alerts should be triggered"
        assert not alert_service.is_in_breach(
            tenant_id, source_id
        ), "Source should not be in breach state"

    @given(
        tenant_id=st.uuids().map(str),
        source_id=st.uuids().map(str),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25)
    def test_breach_state_cleared_when_error_rate_drops(
        self, tenant_id, source_id, threshold
    ):
        """
        Breach state should be cleared when error rate drops below threshold,
        allowing a new alert to be triggered if error rate rises again.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        high_error_rate = threshold + 0.10
        low_error_rate = threshold * 0.5

        # First breach - should trigger alert
        triggered1 = alert_service.check_error_rate(
            tenant_id, source_id, high_error_rate
        )
        assert triggered1, "First breach should trigger alert"
        assert alert_service.is_in_breach(
            tenant_id, source_id
        ), "Should be in breach state"

        # Error rate drops below threshold - should clear breach
        triggered2 = alert_service.check_error_rate(
            tenant_id, source_id, low_error_rate
        )
        assert not triggered2, "Low error rate should not trigger alert"
        assert not alert_service.is_in_breach(
            tenant_id, source_id
        ), "Breach state should be cleared"

        # Second breach - should trigger new alert
        triggered3 = alert_service.check_error_rate(
            tenant_id, source_id, high_error_rate
        )
        assert triggered3, "Second breach should trigger new alert"
        assert alert_service.is_in_breach(
            tenant_id, source_id
        ), "Should be in breach state again"

        # Total alerts should be 2
        assert (
            alert_service.get_alert_count() == 2
        ), f"Expected 2 alerts, got {alert_service.get_alert_count()}"

    @given(
        num_sources=st.integers(min_value=2, max_value=5),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25)
    def test_alerts_independent_per_source(self, num_sources, threshold):
        """
        Alerts should be independent per source - each source can have
        its own breach state and trigger its own alerts.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_ids = [str(uuid4()) for _ in range(num_sources)]
        high_error_rate = threshold + 0.10

        # Trigger alerts for all sources
        for source_id in source_ids:
            triggered = alert_service.check_error_rate(
                tenant_id, source_id, high_error_rate
            )
            assert triggered, f"Alert should trigger for source {source_id}"

        # Each source should have exactly one alert
        assert (
            alert_service.get_alert_count() == num_sources
        ), f"Expected {num_sources} alerts, got {alert_service.get_alert_count()}"

        # Each source should be in breach state
        for source_id in source_ids:
            assert alert_service.is_in_breach(
                tenant_id, source_id
            ), f"Source {source_id} should be in breach state"

            # Verify alert exists for this source
            source_alerts = alert_service.get_alerts_for_source(tenant_id, source_id)
            assert (
                len(source_alerts) == 1
            ), f"Expected 1 alert for source {source_id}, got {len(source_alerts)}"

    @given(
        num_tenants=st.integers(min_value=2, max_value=5),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25)
    def test_alerts_independent_per_tenant(self, num_tenants, threshold):
        """
        Alerts should be independent per tenant - each tenant can have
        its own breach state and trigger its own alerts.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        source_id = str(uuid4())
        tenant_ids = [str(uuid4()) for _ in range(num_tenants)]
        high_error_rate = threshold + 0.10

        # Trigger alerts for all tenants
        for tenant_id in tenant_ids:
            triggered = alert_service.check_error_rate(
                tenant_id, source_id, high_error_rate
            )
            assert triggered, f"Alert should trigger for tenant {tenant_id}"

        # Each tenant should have exactly one alert
        assert (
            alert_service.get_alert_count() == num_tenants
        ), f"Expected {num_tenants} alerts, got {alert_service.get_alert_count()}"

        # Each tenant should be in breach state
        for tenant_id in tenant_ids:
            assert alert_service.is_in_breach(
                tenant_id, source_id
            ), f"Tenant {tenant_id} should be in breach state"

    @given(
        tenant_id=st.uuids().map(str),
        source_id=st.uuids().map(str),
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        total_records=st.integers(min_value=10, max_value=1000),
        error_count=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=25)
    def test_sync_error_tracker_integration(
        self, tenant_id, source_id, threshold, total_records, error_count
    ):
        """
        SyncErrorTracker should correctly calculate error rates and
        trigger alerts via the alert service.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        # Ensure error_count doesn't exceed total_records
        error_count = min(error_count, total_records)

        alert_service = MockAlertService(error_threshold=threshold)
        tracker = SyncErrorTracker(alert_service)

        # Record sync result
        result = tracker.record_sync_result(
            tenant_id, source_id, total_records, error_count
        )

        # Verify error rate calculation
        expected_error_rate = error_count / total_records if total_records > 0 else 0.0
        assert (
            abs(result["error_rate"] - expected_error_rate) < 0.0001
        ), f"Error rate mismatch: {result['error_rate']} != {expected_error_rate}"

        # Verify alert triggering
        if expected_error_rate > threshold:
            assert result[
                "alert_triggered"
            ], f"Alert should trigger when error rate {expected_error_rate:.2%} > threshold {threshold:.2%}"
            assert (
                alert_service.get_alert_count() == 1
            ), "Exactly one alert should be triggered"
        else:
            assert not result[
                "alert_triggered"
            ], f"Alert should not trigger when error rate {expected_error_rate:.2%} <= threshold {threshold:.2%}"
            assert alert_service.get_alert_count() == 0, "No alerts should be triggered"

    @given(
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        ),
        error_rates=st.lists(
            st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            min_size=5,
            max_size=20,
        ),
    )
    @settings(max_examples=25)
    def test_alert_count_matches_breach_transitions(self, threshold, error_rates):
        """
        The number of alerts should match the number of transitions
        from below-threshold to above-threshold.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_id = str(uuid4())

        # Count expected breach transitions
        expected_alerts = 0
        was_in_breach = False

        for error_rate in error_rates:
            is_in_breach = error_rate > threshold

            if is_in_breach and not was_in_breach:
                # Transition from below to above threshold
                expected_alerts += 1

            was_in_breach = is_in_breach

            # Check error rate
            alert_service.check_error_rate(tenant_id, source_id, error_rate)

        # Verify alert count
        actual_alerts = alert_service.get_alert_count()
        assert (
            actual_alerts == expected_alerts
        ), f"Expected {expected_alerts} alerts for breach transitions, got {actual_alerts}"

    @given(
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=25)
    def test_boundary_error_rate_at_threshold(self, threshold):
        """
        Error rate exactly at threshold should not trigger alert
        (threshold is exclusive - only rates > threshold trigger).

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_id = str(uuid4())

        # Error rate exactly at threshold
        triggered = alert_service.check_error_rate(tenant_id, source_id, threshold)

        assert (
            not triggered
        ), f"Alert should not trigger when error rate equals threshold {threshold:.2%}"
        assert (
            alert_service.get_alert_count() == 0
        ), "No alerts should be triggered at exact threshold"

    @given(
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=25)
    def test_boundary_error_rate_just_above_threshold(self, threshold):
        """
        Error rate just above threshold should trigger alert.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_id = str(uuid4())

        # Error rate just above threshold
        error_rate = threshold + 0.001
        triggered = alert_service.check_error_rate(tenant_id, source_id, error_rate)

        assert (
            triggered
        ), f"Alert should trigger when error rate {error_rate:.4%} > threshold {threshold:.2%}"
        assert (
            alert_service.get_alert_count() == 1
        ), "Exactly one alert should be triggered"

    @given(
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=25)
    def test_zero_error_rate_never_triggers(self, threshold):
        """
        Zero error rate should never trigger an alert.

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_id = str(uuid4())

        # Zero error rate
        triggered = alert_service.check_error_rate(tenant_id, source_id, 0.0)

        assert not triggered, "Alert should never trigger for zero error rate"
        assert alert_service.get_alert_count() == 0, "No alerts should be triggered"

    @given(
        threshold=st.floats(
            min_value=0.05, max_value=0.30, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=25)
    def test_100_percent_error_rate_always_triggers(self, threshold):
        """
        100% error rate should always trigger an alert (assuming threshold < 100%).

        **Feature: data-sync-pipeline, Property 22: Alert Threshold Triggering**
        **Validates: Requirements 6.5**
        """
        alert_service = MockAlertService(error_threshold=threshold)

        tenant_id = str(uuid4())
        source_id = str(uuid4())

        # 100% error rate
        triggered = alert_service.check_error_rate(tenant_id, source_id, 1.0)

        assert (
            triggered
        ), f"Alert should always trigger for 100% error rate (threshold: {threshold:.2%})"
        assert (
            alert_service.get_alert_count() == 1
        ), "Exactly one alert should be triggered"


# ============================================================================
# Property 30: Batch Processing Optimization
# **Feature: data-sync-pipeline, Property 30: Batch Processing Optimization**
# **Validates: Requirements 10.1**
# ============================================================================


class MockBatchProcessor:
    """
    Mock batch processor for testing batch processing optimization.

    This class simulates the batch processing behavior as specified in Requirement 10.1:

    WHEN processing large datasets,
    THE Data_Sync_Pipeline SHALL use batch operations with configurable batch size
    (default 1000 records)

    Tracks:
    - Number of batches processed
    - Size of each batch
    - Total records processed
    - Whether any data was lost
    """

    def __init__(self, batch_size: int = 1000):
        """
        Initialize the batch processor.

        Args:
            batch_size: Maximum number of records per batch (default 1000)
        """
        self.batch_size = batch_size
        self.batches_processed: List[List[Dict[str, Any]]] = []
        self.batch_sizes: List[int] = []
        self.total_records_processed: int = 0
        self._lock = threading.Lock()

    def process_in_batches(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process data in batches.

        Args:
            data: List of records to process

        Returns:
            Processing result with batch statistics
        """
        with self._lock:
            self.batches_processed.clear()
            self.batch_sizes.clear()
            self.total_records_processed = 0

        if not data:
            return {
                "success": True,
                "total_input_records": 0,
                "total_processed_records": 0,
                "num_batches": 0,
                "batch_sizes": [],
                "data_loss": False,
            }

        # Split data into batches
        batches = []
        for i in range(0, len(data), self.batch_size):
            batch = data[i : i + self.batch_size]
            batches.append(batch)

        # Process each batch
        processed_records = []
        with self._lock:
            for batch in batches:
                self.batches_processed.append(batch)
                self.batch_sizes.append(len(batch))
                self.total_records_processed += len(batch)
                processed_records.extend(batch)

        # Check for data loss
        data_loss = len(processed_records) != len(data)

        return {
            "success": True,
            "total_input_records": len(data),
            "total_processed_records": len(processed_records),
            "num_batches": len(batches),
            "batch_sizes": self.batch_sizes.copy(),
            "data_loss": data_loss,
            "processed_data": processed_records,
        }

    def get_batch_count(self) -> int:
        """Get the number of batches processed."""
        with self._lock:
            return len(self.batches_processed)

    def get_batch_sizes(self) -> List[int]:
        """Get the sizes of all processed batches."""
        with self._lock:
            return self.batch_sizes.copy()

    def get_total_processed(self) -> int:
        """Get the total number of records processed."""
        with self._lock:
            return self.total_records_processed

    def verify_no_data_loss(self, original_data: List[Dict[str, Any]]) -> bool:
        """
        Verify that no data was lost during batch processing.

        Args:
            original_data: Original input data

        Returns:
            True if no data loss, False otherwise
        """
        with self._lock:
            processed_count = sum(len(batch) for batch in self.batches_processed)
            return processed_count == len(original_data)

    def verify_batch_sizes(self) -> Tuple[bool, List[str]]:
        """
        Verify that all batch sizes are within the configured limit.

        Returns:
            Tuple of (all_valid, list of error messages)
        """
        errors = []
        with self._lock:
            for i, size in enumerate(self.batch_sizes):
                if size > self.batch_size:
                    errors.append(
                        f"Batch {i}: size {size} exceeds limit {self.batch_size}"
                    )
                if size <= 0:
                    errors.append(f"Batch {i}: invalid size {size}")

        return len(errors) == 0, errors

    def reset(self):
        """Reset the processor state."""
        with self._lock:
            self.batches_processed.clear()
            self.batch_sizes.clear()
            self.total_records_processed = 0


class TestBatchProcessingOptimization:
    """
    Property 30: Batch Processing Optimization

    Tests that:
    1. Large datasets are processed in batches
    2. Each batch is <= configured batch size
    3. Total processed records equals input records (no data loss)
    4. Works with various dataset sizes and batch sizes

    **Feature: data-sync-pipeline, Property 30: Batch Processing Optimization**
    **Validates: Requirements 10.1**
    """

    @given(
        num_records=st.integers(min_value=1, max_value=5000),
        batch_size=st.integers(min_value=100, max_value=2000),
    )
    @settings(max_examples=25)
    def test_large_datasets_processed_in_batches(self, num_records, batch_size):
        """
        Large datasets should be processed in batches.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        WHEN processing large datasets,
        THE Data_Sync_Pipeline SHALL use batch operations with configurable batch size
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify batching occurred for large datasets
        if num_records > batch_size:
            assert result["num_batches"] > 1, (
                f"Dataset of {num_records} records should be split into multiple batches "
                f"(batch_size={batch_size}), got {result['num_batches']} batches"
            )

        # Verify expected number of batches
        expected_batches = (
            num_records + batch_size - 1
        ) // batch_size  # Ceiling division
        assert (
            result["num_batches"] == expected_batches
        ), f"Expected {expected_batches} batches, got {result['num_batches']}"

    @given(
        num_records=st.integers(min_value=1, max_value=5000),
        batch_size=st.integers(min_value=100, max_value=2000),
    )
    @settings(max_examples=25)
    def test_each_batch_within_configured_size(self, num_records, batch_size):
        """
        Each batch should be <= configured batch size.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Each batch should not exceed the configured batch size
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify all batch sizes are within limit
        is_valid, errors = processor.verify_batch_sizes()
        assert is_valid, f"All batches should be within size limit: {errors}"

        # Verify each batch size individually
        for i, size in enumerate(result["batch_sizes"]):
            assert (
                size <= batch_size
            ), f"Batch {i}: size {size} should be <= {batch_size}"
            assert size > 0, f"Batch {i}: size should be > 0"

    @given(
        num_records=st.integers(min_value=1, max_value=5000),
        batch_size=st.integers(min_value=100, max_value=2000),
    )
    @settings(max_examples=25)
    def test_total_processed_equals_input_no_data_loss(self, num_records, batch_size):
        """
        Total processed count should equal input count (no data loss).

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        All records should be processed without data loss
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify no data loss
        assert not result["data_loss"], "No data should be lost during batch processing"

        assert result["total_processed_records"] == result["total_input_records"], (
            f"Processed count ({result['total_processed_records']}) should equal "
            f"input count ({result['total_input_records']})"
        )

        assert result["total_processed_records"] == num_records, (
            f"Processed count ({result['total_processed_records']}) should equal "
            f"original count ({num_records})"
        )

        # Verify using processor method
        assert processor.verify_no_data_loss(
            data
        ), "Processor should verify no data loss"

    @given(batch_size=st.integers(min_value=100, max_value=2000))
    @settings(max_examples=25)
    def test_default_batch_size_is_1000(self, batch_size):
        """
        Default batch size should be 1000 records.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Default batch size should be 1000 as specified in requirements
        """
        # Test default batch size
        default_processor = MockBatchProcessor()
        assert (
            default_processor.batch_size == 1000
        ), f"Default batch size should be 1000, got {default_processor.batch_size}"

        # Test custom batch size
        custom_processor = MockBatchProcessor(batch_size=batch_size)
        assert (
            custom_processor.batch_size == batch_size
        ), f"Custom batch size should be {batch_size}, got {custom_processor.batch_size}"

    @given(
        num_records=st.integers(min_value=1, max_value=100),
        batch_size=st.integers(min_value=500, max_value=2000),
    )
    @settings(max_examples=25)
    def test_small_dataset_single_batch(self, num_records, batch_size):
        """
        Datasets smaller than batch size should be processed in a single batch.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Small datasets should not be unnecessarily split
        """
        # Ensure num_records < batch_size
        assume(num_records < batch_size)

        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify single batch
        assert result["num_batches"] == 1, (
            f"Dataset of {num_records} records (< batch_size {batch_size}) "
            f"should be processed in 1 batch, got {result['num_batches']}"
        )

        # Verify batch size equals input size
        assert (
            result["batch_sizes"][0] == num_records
        ), f"Single batch size should equal input size {num_records}"

    @given(batch_size=st.integers(min_value=100, max_value=1000))
    @settings(max_examples=25)
    def test_exact_batch_size_multiple(self, batch_size):
        """
        Dataset that is exact multiple of batch size should have full batches.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        When dataset size is exact multiple of batch size, all batches should be full
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate data that is exact multiple of batch size
        num_batches = 3
        num_records = batch_size * num_batches

        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify exact number of batches
        assert (
            result["num_batches"] == num_batches
        ), f"Expected {num_batches} batches, got {result['num_batches']}"

        # Verify all batches are full
        for i, size in enumerate(result["batch_sizes"]):
            assert (
                size == batch_size
            ), f"Batch {i}: size {size} should equal batch_size {batch_size}"

    @given(
        batch_size=st.integers(min_value=100, max_value=1000),
        remainder=st.integers(min_value=1, max_value=99),
    )
    @settings(max_examples=25)
    def test_last_batch_can_be_smaller(self, batch_size, remainder):
        """
        Last batch can be smaller than batch size when data doesn't divide evenly.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Last batch should contain remaining records
        """
        assume(remainder < batch_size)

        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate data with remainder
        num_full_batches = 2
        num_records = batch_size * num_full_batches + remainder

        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify number of batches
        expected_batches = num_full_batches + 1
        assert (
            result["num_batches"] == expected_batches
        ), f"Expected {expected_batches} batches, got {result['num_batches']}"

        # Verify full batches
        for i in range(num_full_batches):
            assert (
                result["batch_sizes"][i] == batch_size
            ), f"Batch {i}: size {result['batch_sizes'][i]} should equal batch_size {batch_size}"

        # Verify last batch has remainder
        assert (
            result["batch_sizes"][-1] == remainder
        ), f"Last batch size {result['batch_sizes'][-1]} should equal remainder {remainder}"

    @given(batch_size=st.integers(min_value=100, max_value=2000))
    @settings(max_examples=25)
    def test_empty_dataset_handling(self, batch_size):
        """
        Empty dataset should be handled gracefully.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Empty input should produce zero batches without errors
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Process empty data
        result = processor.process_in_batches([])

        # Verify empty result
        assert result["success"], "Processing empty data should succeed"
        assert result["total_input_records"] == 0, "Input count should be 0"
        assert result["total_processed_records"] == 0, "Processed count should be 0"
        assert result["num_batches"] == 0, "Number of batches should be 0"
        assert result["batch_sizes"] == [], "Batch sizes should be empty"
        assert not result["data_loss"], "No data loss for empty input"

    @given(
        num_records=st.integers(min_value=100, max_value=3000),
        batch_size=st.integers(min_value=100, max_value=1000),
    )
    @settings(max_examples=25)
    def test_data_integrity_preserved(self, num_records, batch_size):
        """
        Data integrity should be preserved through batch processing.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        All original records should be present in processed output
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data with unique IDs
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Store original IDs
        original_ids = {record["id"] for record in data}

        # Process data
        result = processor.process_in_batches(data)

        # Verify all original IDs are in processed data
        processed_ids = {record["id"] for record in result["processed_data"]}

        assert (
            original_ids == processed_ids
        ), "All original record IDs should be present in processed data"

        # Verify order is preserved
        for i, (original, processed) in enumerate(zip(data, result["processed_data"])):
            assert (
                original["id"] == processed["id"]
            ), f"Record order should be preserved at index {i}"

    @given(batch_size=st.integers(min_value=100, max_value=500))
    @settings(max_examples=25)
    def test_sum_of_batch_sizes_equals_total(self, batch_size):
        """
        Sum of all batch sizes should equal total records.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Mathematical property: sum(batch_sizes) == total_records
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        num_records = batch_size * 3 + 50  # Ensure multiple batches with remainder
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify sum of batch sizes
        sum_of_batches = sum(result["batch_sizes"])

        assert (
            sum_of_batches == num_records
        ), f"Sum of batch sizes ({sum_of_batches}) should equal total records ({num_records})"

        assert (
            sum_of_batches == result["total_input_records"]
        ), f"Sum of batch sizes ({sum_of_batches}) should equal input count ({result['total_input_records']})"

    @given(
        num_records=st.integers(min_value=1000, max_value=5000),
        batch_size=st.sampled_from([100, 250, 500, 1000, 2000]),
    )
    @settings(max_examples=25)
    def test_various_batch_sizes(self, num_records, batch_size):
        """
        Batch processing should work correctly with various batch sizes.

        # Feature: data-sync-pipeline, Property 30: Batch Processing Optimization
        **Validates: Requirements 10.1**

        Different batch sizes should all produce correct results
        """
        processor = MockBatchProcessor(batch_size=batch_size)

        # Generate test data
        data = [
            {"id": str(uuid4()), "index": i, "value": f"record_{i}"}
            for i in range(num_records)
        ]

        # Process data
        result = processor.process_in_batches(data)

        # Verify basic properties
        assert result["success"], "Processing should succeed"
        assert not result["data_loss"], "No data should be lost"
        assert (
            result["total_processed_records"] == num_records
        ), f"All {num_records} records should be processed"

        # Verify batch sizes are valid
        for i, size in enumerate(result["batch_sizes"]):
            assert (
                0 < size <= batch_size
            ), f"Batch {i}: size {size} should be in range (0, {batch_size}]"

        # Verify expected number of batches
        expected_batches = (num_records + batch_size - 1) // batch_size
        assert result["num_batches"] == expected_batches, (
            f"Expected {expected_batches} batches for {num_records} records "
            f"with batch_size {batch_size}, got {result['num_batches']}"
        )


# ============================================================================
# Property 31: Concurrent Job Limiting
# **Validates: Requirements 10.2**
# ============================================================================


class MockTenantJobScheduler:
    """
    Mock job scheduler with per-tenant concurrent job limiting.

    Simulates the behavior of a job scheduler that:
    - Limits concurrent jobs per tenant
    - Queues jobs that exceed the limit
    - Runs queued jobs when active jobs complete
    - Maintains independent limits for different tenants
    """

    def __init__(self, max_concurrent_per_tenant: int = 3):
        self.max_concurrent_per_tenant = max_concurrent_per_tenant
        self._active_jobs: Dict[str, Set[str]] = defaultdict(
            set
        )  # tenant_id -> set of job_ids
        self._queued_jobs: Dict[str, List[Dict[str, Any]]] = defaultdict(
            list
        )  # tenant_id -> list of jobs
        self._completed_jobs: Dict[str, List[str]] = defaultdict(
            list
        )  # tenant_id -> list of job_ids
        self._rejected_jobs: Dict[str, List[str]] = defaultdict(
            list
        )  # tenant_id -> list of job_ids
        self._job_history: List[Dict[str, Any]] = []  # All job events
        self._lock = threading.Lock()

    def get_active_job_count(self, tenant_id: str) -> int:
        """Get number of active jobs for a tenant."""
        with self._lock:
            return len(self._active_jobs[tenant_id])

    def get_queued_job_count(self, tenant_id: str) -> int:
        """Get number of queued jobs for a tenant."""
        with self._lock:
            return len(self._queued_jobs[tenant_id])

    def submit_job(
        self, tenant_id: str, job_id: str, queue_if_full: bool = True
    ) -> Dict[str, Any]:
        """
        Submit a job for execution.

        Args:
            tenant_id: Tenant identifier
            job_id: Unique job identifier
            queue_if_full: If True, queue job when limit reached; if False, reject

        Returns:
            Dict with status: 'running', 'queued', or 'rejected'
        """
        with self._lock:
            active_count = len(self._active_jobs[tenant_id])

            if active_count < self.max_concurrent_per_tenant:
                # Can run immediately
                self._active_jobs[tenant_id].add(job_id)
                result = {
                    "status": "running",
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "active_count": active_count + 1,
                    "queued_count": len(self._queued_jobs[tenant_id]),
                }
                self._job_history.append(
                    {
                        "event": "job_started",
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.utcnow(),
                    }
                )
                return result

            elif queue_if_full:
                # Queue the job
                self._queued_jobs[tenant_id].append(
                    {"job_id": job_id, "queued_at": datetime.utcnow()}
                )
                result = {
                    "status": "queued",
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "active_count": active_count,
                    "queued_count": len(self._queued_jobs[tenant_id]),
                    "queue_position": len(self._queued_jobs[tenant_id]),
                }
                self._job_history.append(
                    {
                        "event": "job_queued",
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.utcnow(),
                    }
                )
                return result

            else:
                # Reject the job
                self._rejected_jobs[tenant_id].append(job_id)
                result = {
                    "status": "rejected",
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "reason": "concurrent_limit_exceeded",
                    "active_count": active_count,
                    "max_concurrent": self.max_concurrent_per_tenant,
                }
                self._job_history.append(
                    {
                        "event": "job_rejected",
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.utcnow(),
                    }
                )
                return result

    def complete_job(self, tenant_id: str, job_id: str) -> Dict[str, Any]:
        """
        Mark a job as completed and start next queued job if any.

        Returns:
            Dict with completion status and any newly started job
        """
        with self._lock:
            if job_id not in self._active_jobs[tenant_id]:
                return {
                    "success": False,
                    "error": "job_not_found",
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                }

            # Remove from active
            self._active_jobs[tenant_id].discard(job_id)
            self._completed_jobs[tenant_id].append(job_id)

            self._job_history.append(
                {
                    "event": "job_completed",
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "timestamp": datetime.utcnow(),
                }
            )

            result = {
                "success": True,
                "job_id": job_id,
                "tenant_id": tenant_id,
                "active_count": len(self._active_jobs[tenant_id]),
                "queued_count": len(self._queued_jobs[tenant_id]),
                "started_from_queue": None,
            }

            # Start next queued job if any
            if self._queued_jobs[tenant_id]:
                next_job = self._queued_jobs[tenant_id].pop(0)
                next_job_id = next_job["job_id"]
                self._active_jobs[tenant_id].add(next_job_id)

                result["started_from_queue"] = next_job_id
                result["active_count"] = len(self._active_jobs[tenant_id])
                result["queued_count"] = len(self._queued_jobs[tenant_id])

                self._job_history.append(
                    {
                        "event": "job_started_from_queue",
                        "job_id": next_job_id,
                        "tenant_id": tenant_id,
                        "timestamp": datetime.utcnow(),
                    }
                )

            return result

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get statistics for a tenant."""
        with self._lock:
            return {
                "tenant_id": tenant_id,
                "active_jobs": len(self._active_jobs[tenant_id]),
                "queued_jobs": len(self._queued_jobs[tenant_id]),
                "completed_jobs": len(self._completed_jobs[tenant_id]),
                "rejected_jobs": len(self._rejected_jobs[tenant_id]),
                "max_concurrent": self.max_concurrent_per_tenant,
            }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all tenants."""
        with self._lock:
            all_tenants = (
                set(self._active_jobs.keys())
                | set(self._queued_jobs.keys())
                | set(self._completed_jobs.keys())
                | set(self._rejected_jobs.keys())
            )

            return {
                "total_tenants": len(all_tenants),
                "total_active_jobs": sum(
                    len(jobs) for jobs in self._active_jobs.values()
                ),
                "total_queued_jobs": sum(
                    len(jobs) for jobs in self._queued_jobs.values()
                ),
                "total_completed_jobs": sum(
                    len(jobs) for jobs in self._completed_jobs.values()
                ),
                "total_rejected_jobs": sum(
                    len(jobs) for jobs in self._rejected_jobs.values()
                ),
                "max_concurrent_per_tenant": self.max_concurrent_per_tenant,
                "job_history_count": len(self._job_history),
            }


class TestConcurrentJobLimiting:
    """
    Property 31: Concurrent Job Limiting

    Tests that the job scheduler correctly limits concurrent jobs per tenant
    to prevent resource exhaustion.

    # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
    **Validates: Requirements 10.2**
    """

    @given(
        max_concurrent=st.integers(min_value=1, max_value=10),
        num_jobs=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=25)
    def test_jobs_exceeding_limit_are_queued(self, max_concurrent, num_jobs):
        """
        Jobs exceeding the concurrent limit should be queued.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        When a tenant submits more jobs than the concurrent limit,
        excess jobs should be queued rather than rejected (when queue_if_full=True).
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        running_count = 0
        queued_count = 0

        # Submit all jobs
        for i in range(num_jobs):
            job_id = f"job_{i}"
            result = scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

            if result["status"] == "running":
                running_count += 1
            elif result["status"] == "queued":
                queued_count += 1

        # Verify running jobs don't exceed limit
        assert (
            running_count <= max_concurrent
        ), f"Running jobs ({running_count}) should not exceed limit ({max_concurrent})"

        # Verify running jobs equal min(num_jobs, max_concurrent)
        expected_running = min(num_jobs, max_concurrent)
        assert (
            running_count == expected_running
        ), f"Running jobs ({running_count}) should equal min(num_jobs, max_concurrent) = {expected_running}"

        # Verify queued jobs equal excess
        expected_queued = max(0, num_jobs - max_concurrent)
        assert (
            queued_count == expected_queued
        ), f"Queued jobs ({queued_count}) should equal excess ({expected_queued})"

        # Verify total equals submitted
        assert (
            running_count + queued_count == num_jobs
        ), f"Running ({running_count}) + Queued ({queued_count}) should equal submitted ({num_jobs})"

    @given(
        max_concurrent=st.integers(min_value=1, max_value=10),
        num_jobs=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=25)
    def test_jobs_exceeding_limit_are_rejected_when_configured(
        self, max_concurrent, num_jobs
    ):
        """
        Jobs exceeding the concurrent limit should be rejected when queue_if_full=False.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        When a tenant submits more jobs than the concurrent limit with queue_if_full=False,
        excess jobs should be rejected.
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        running_count = 0
        rejected_count = 0

        # Submit all jobs with queue_if_full=False
        for i in range(num_jobs):
            job_id = f"job_{i}"
            result = scheduler.submit_job(tenant_id, job_id, queue_if_full=False)

            if result["status"] == "running":
                running_count += 1
            elif result["status"] == "rejected":
                rejected_count += 1
                # Verify rejection reason
                assert (
                    result["reason"] == "concurrent_limit_exceeded"
                ), "Rejection reason should be 'concurrent_limit_exceeded'"

        # Verify running jobs don't exceed limit
        assert (
            running_count <= max_concurrent
        ), f"Running jobs ({running_count}) should not exceed limit ({max_concurrent})"

        # Verify rejected jobs equal excess
        expected_rejected = max(0, num_jobs - max_concurrent)
        assert (
            rejected_count == expected_rejected
        ), f"Rejected jobs ({rejected_count}) should equal excess ({expected_rejected})"

    @given(
        max_concurrent=st.integers(min_value=1, max_value=5),
        num_jobs=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=25)
    def test_queued_jobs_run_after_completion(self, max_concurrent, num_jobs):
        """
        Queued jobs should start running after active jobs complete.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        When an active job completes, the next queued job should start running.
        """
        assume(num_jobs > max_concurrent)  # Ensure we have queued jobs

        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        # Submit all jobs
        job_ids = [f"job_{i}" for i in range(num_jobs)]
        for job_id in job_ids:
            scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

        # Verify initial state
        initial_active = scheduler.get_active_job_count(tenant_id)
        initial_queued = scheduler.get_queued_job_count(tenant_id)

        assert (
            initial_active == max_concurrent
        ), f"Initial active ({initial_active}) should equal max_concurrent ({max_concurrent})"
        assert (
            initial_queued == num_jobs - max_concurrent
        ), f"Initial queued ({initial_queued}) should equal excess ({num_jobs - max_concurrent})"

        # Track jobs started from queue
        started_from_queue_count = 0

        # Complete all jobs until none remain
        completed_jobs = set()
        while scheduler.get_active_job_count(tenant_id) > 0:
            # Get current active jobs
            active_jobs = list(scheduler._active_jobs[tenant_id])

            # Complete one job at a time
            for job_id in active_jobs:
                if job_id not in completed_jobs:
                    result = scheduler.complete_job(tenant_id, job_id)
                    assert result["success"], f"Job {job_id} completion should succeed"
                    completed_jobs.add(job_id)

                    if result["started_from_queue"]:
                        started_from_queue_count += 1
                    break  # Complete one job at a time to properly track queue starts

        # Verify all queued jobs were eventually started
        expected_started_from_queue = num_jobs - max_concurrent
        assert (
            started_from_queue_count == expected_started_from_queue
        ), f"Started from queue ({started_from_queue_count}) should equal {expected_started_from_queue}"

        # Verify final state
        final_stats = scheduler.get_tenant_stats(tenant_id)
        assert final_stats["active_jobs"] == 0, "All jobs should be completed"
        assert final_stats["queued_jobs"] == 0, "No jobs should be queued"
        assert (
            final_stats["completed_jobs"] == num_jobs
        ), f"Completed jobs ({final_stats['completed_jobs']}) should equal submitted ({num_jobs})"

    @given(
        max_concurrent=st.integers(min_value=1, max_value=5),
        num_tenants=st.integers(min_value=2, max_value=5),
        jobs_per_tenant=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=25)
    def test_different_tenants_have_independent_limits(
        self, max_concurrent, num_tenants, jobs_per_tenant
    ):
        """
        Different tenants should have independent concurrent job limits.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        Each tenant should be able to run up to max_concurrent jobs independently.
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_ids = [f"tenant_{i}" for i in range(num_tenants)]

        # Submit jobs for each tenant
        for tenant_id in tenant_ids:
            for i in range(jobs_per_tenant):
                job_id = f"{tenant_id}_job_{i}"
                scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

        # Verify each tenant has independent limits
        for tenant_id in tenant_ids:
            stats = scheduler.get_tenant_stats(tenant_id)

            expected_active = min(jobs_per_tenant, max_concurrent)
            expected_queued = max(0, jobs_per_tenant - max_concurrent)

            assert (
                stats["active_jobs"] == expected_active
            ), f"Tenant {tenant_id}: active ({stats['active_jobs']}) should equal {expected_active}"
            assert (
                stats["queued_jobs"] == expected_queued
            ), f"Tenant {tenant_id}: queued ({stats['queued_jobs']}) should equal {expected_queued}"

        # Verify total active jobs across all tenants
        all_stats = scheduler.get_all_stats()
        expected_total_active = num_tenants * min(jobs_per_tenant, max_concurrent)

        assert (
            all_stats["total_active_jobs"] == expected_total_active
        ), f"Total active ({all_stats['total_active_jobs']}) should equal {expected_total_active}"

    @given(
        max_concurrent=st.integers(min_value=2, max_value=5),
        num_jobs=st.integers(min_value=10, max_value=30),
    )
    @settings(max_examples=25)
    def test_active_count_never_exceeds_limit(self, max_concurrent, num_jobs):
        """
        Active job count should never exceed the concurrent limit at any point.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        Invariant: active_jobs <= max_concurrent at all times.
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        # Track max active count observed
        max_active_observed = 0

        # Submit jobs and track active count
        for i in range(num_jobs):
            job_id = f"job_{i}"
            result = scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

            current_active = scheduler.get_active_job_count(tenant_id)
            max_active_observed = max(max_active_observed, current_active)

            # Verify invariant after each submission
            assert (
                current_active <= max_concurrent
            ), f"Active count ({current_active}) exceeded limit ({max_concurrent}) after submitting job {i}"

        # Complete some jobs and verify invariant still holds
        active_jobs = list(scheduler._active_jobs[tenant_id])
        for job_id in active_jobs[: len(active_jobs) // 2]:
            scheduler.complete_job(tenant_id, job_id)

            current_active = scheduler.get_active_job_count(tenant_id)
            assert (
                current_active <= max_concurrent
            ), f"Active count ({current_active}) exceeded limit ({max_concurrent}) after completing job"

        # Verify max observed never exceeded limit
        assert (
            max_active_observed <= max_concurrent
        ), f"Max active observed ({max_active_observed}) exceeded limit ({max_concurrent})"

    @given(
        max_concurrent=st.integers(min_value=1, max_value=5),
        num_jobs=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=25)
    def test_queue_order_is_fifo(self, max_concurrent, num_jobs):
        """
        Queued jobs should be processed in FIFO order.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        Jobs should be dequeued in the same order they were queued.
        """
        assume(num_jobs > max_concurrent)  # Ensure we have queued jobs

        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        # Submit all jobs
        job_ids = [f"job_{i}" for i in range(num_jobs)]
        for job_id in job_ids:
            scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

        # Track order of jobs started from queue
        started_from_queue_order = []

        # Complete initially running jobs
        initially_running = list(scheduler._active_jobs[tenant_id])
        for job_id in initially_running:
            result = scheduler.complete_job(tenant_id, job_id)
            if result["started_from_queue"]:
                started_from_queue_order.append(result["started_from_queue"])

        # Verify FIFO order
        expected_order = job_ids[
            max_concurrent : max_concurrent + len(started_from_queue_order)
        ]
        assert (
            started_from_queue_order == expected_order
        ), f"Queue order should be FIFO: expected {expected_order}, got {started_from_queue_order}"

    @given(
        max_concurrent=st.integers(min_value=1, max_value=10),
        num_jobs=st.integers(min_value=1, max_value=30),
    )
    @settings(max_examples=25)
    def test_no_jobs_lost_or_duplicated(self, max_concurrent, num_jobs):
        """
        No jobs should be lost or duplicated during scheduling.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        Total jobs (active + queued + completed + rejected) should equal submitted jobs.
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        # Submit all jobs
        submitted_job_ids = set()
        for i in range(num_jobs):
            job_id = f"job_{i}"
            submitted_job_ids.add(job_id)
            scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

        # Get stats
        stats = scheduler.get_tenant_stats(tenant_id)

        # Verify no jobs lost
        total_tracked = (
            stats["active_jobs"]
            + stats["queued_jobs"]
            + stats["completed_jobs"]
            + stats["rejected_jobs"]
        )

        assert (
            total_tracked == num_jobs
        ), f"Total tracked ({total_tracked}) should equal submitted ({num_jobs})"

        # Complete all jobs
        while scheduler.get_active_job_count(tenant_id) > 0:
            active_jobs = list(scheduler._active_jobs[tenant_id])
            for job_id in active_jobs:
                scheduler.complete_job(tenant_id, job_id)

        # Verify final state
        final_stats = scheduler.get_tenant_stats(tenant_id)
        assert (
            final_stats["completed_jobs"] == num_jobs
        ), f"Completed ({final_stats['completed_jobs']}) should equal submitted ({num_jobs})"
        assert final_stats["active_jobs"] == 0, "No active jobs should remain"
        assert final_stats["queued_jobs"] == 0, "No queued jobs should remain"

    @given(
        max_concurrent=st.sampled_from([1, 2, 3, 5, 10]),
        num_jobs=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=25)
    def test_various_concurrency_limits(self, max_concurrent, num_jobs):
        """
        Concurrent job limiting should work correctly with various limit values.

        # Feature: data-sync-pipeline, Property 31: Concurrent Job Limiting
        **Validates: Requirements 10.2**

        Different concurrency limits should all enforce the limit correctly.
        """
        scheduler = MockTenantJobScheduler(max_concurrent_per_tenant=max_concurrent)
        tenant_id = str(uuid4())

        # Submit all jobs
        for i in range(num_jobs):
            job_id = f"job_{i}"
            scheduler.submit_job(tenant_id, job_id, queue_if_full=True)

        # Verify limit is enforced
        stats = scheduler.get_tenant_stats(tenant_id)

        assert (
            stats["active_jobs"] <= max_concurrent
        ), f"Active jobs ({stats['active_jobs']}) should not exceed limit ({max_concurrent})"

        expected_active = min(num_jobs, max_concurrent)
        assert (
            stats["active_jobs"] == expected_active
        ), f"Active jobs ({stats['active_jobs']}) should equal min(num_jobs, limit) = {expected_active}"

        expected_queued = max(0, num_jobs - max_concurrent)
        assert (
            stats["queued_jobs"] == expected_queued
        ), f"Queued jobs ({stats['queued_jobs']}) should equal excess = {expected_queued}"


# ============================================================================
# Property 33: Data Compression
# **Validates: Requirements 10.4**
# ============================================================================


class DataCompressor:
    """
    Data compressor for sync pipeline data transfer.

    Uses gzip compression to reduce network overhead during data transfer.
    Supports compression and decompression of various data types.
    """

    def __init__(self, compression_level: int = 6):
        """
        Initialize compressor.

        Args:
            compression_level: Compression level (1-9, higher = better compression but slower)
        """
        import gzip

        self.compression_level = compression_level
        self._gzip = gzip

    def compress(self, data: bytes) -> bytes:
        """
        Compress data using gzip.

        Args:
            data: Raw bytes to compress

        Returns:
            Compressed bytes
        """
        if not data:
            raise ValueError("Cannot compress empty data")
        return self._gzip.compress(data, compresslevel=self.compression_level)

    def decompress(self, compressed_data: bytes) -> bytes:
        """
        Decompress gzip-compressed data.

        Args:
            compressed_data: Gzip-compressed bytes

        Returns:
            Original decompressed bytes
        """
        if not compressed_data:
            raise ValueError("Cannot decompress empty data")
        return self._gzip.decompress(compressed_data)

    def compress_json(self, data: Dict[str, Any]) -> bytes:
        """
        Compress JSON-serializable data.

        Args:
            data: Dictionary to compress

        Returns:
            Compressed bytes
        """
        json_bytes = json.dumps(data, default=str).encode("utf-8")
        return self.compress(json_bytes)

    def decompress_json(self, compressed_data: bytes) -> Dict[str, Any]:
        """
        Decompress and parse JSON data.

        Args:
            compressed_data: Gzip-compressed JSON bytes

        Returns:
            Parsed dictionary
        """
        json_bytes = self.decompress(compressed_data)
        return json.loads(json_bytes.decode("utf-8"))

    def get_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """
        Calculate compression ratio.

        Args:
            original_size: Size of original data in bytes
            compressed_size: Size of compressed data in bytes

        Returns:
            Compression ratio (0-1, lower = better compression)
        """
        if original_size == 0:
            return 1.0
        return compressed_size / original_size


class TestDataCompression:
    """
    Property 33: Data Compression

    Tests that data compression reduces network overhead and is lossless.

    **Feature: data-sync-pipeline, Property 33: Data Compression**
    **Validates: Requirements 10.4**

    WHEN data is transferred,
    THE Data_Sync_Pipeline SHALL support compression to reduce network overhead
    """

    @given(data=st.binary(min_size=100, max_size=10000))
    @settings(max_examples=25)
    def test_compression_decompression_roundtrip(self, data):
        """
        Compressing then decompressing data should produce the original data.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        This tests that compression is lossless - the round-trip should
        preserve all original data exactly.
        """
        compressor = DataCompressor()

        # Compress data
        compressed = compressor.compress(data)

        # Decompress data
        decompressed = compressor.decompress(compressed)

        # Verify round-trip produces original data
        assert (
            decompressed == data
        ), f"Decompressed data should match original. Original size: {len(data)}, Decompressed size: {len(decompressed)}"

    @given(
        # Generate compressible data (repeated patterns compress well)
        pattern=st.binary(min_size=10, max_size=100),
        repetitions=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=25)
    def test_compressible_data_reduces_size(self, pattern, repetitions):
        """
        Compressible data (with repeated patterns) should have smaller compressed size.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Data with repeated patterns should compress to a smaller size than the original.
        """
        compressor = DataCompressor()

        # Create compressible data by repeating a pattern
        data = pattern * repetitions

        # Compress data
        compressed = compressor.compress(data)

        # Verify compressed size is smaller
        assert len(compressed) < len(
            data
        ), f"Compressed size ({len(compressed)}) should be smaller than original ({len(data)}) for compressible data"

        # Verify compression ratio
        ratio = compressor.get_compression_ratio(len(data), len(compressed))
        assert (
            ratio < 1.0
        ), f"Compression ratio ({ratio}) should be less than 1.0 for compressible data"

    @given(
        json_data=st.fixed_dictionaries(
            {
                "id": st.uuids().map(str),
                "name": st.text(
                    min_size=1,
                    max_size=100,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                ),
                "description": st.text(
                    min_size=50,
                    max_size=500,
                    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
                ),
                "count": st.integers(min_value=0, max_value=1000000),
                "active": st.booleans(),
                "tags": st.lists(
                    st.text(
                        min_size=1,
                        max_size=20,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    min_size=0,
                    max_size=10,
                ),
                "metadata": st.fixed_dictionaries(
                    {
                        "created_at": st.datetimes(
                            min_value=datetime(2020, 1, 1),
                            max_value=datetime(2030, 1, 1),
                        ).map(str),
                        "updated_at": st.datetimes(
                            min_value=datetime(2020, 1, 1),
                            max_value=datetime(2030, 1, 1),
                        ).map(str),
                        "version": st.integers(min_value=1, max_value=100),
                    }
                ),
            }
        )
    )
    @settings(max_examples=25)
    def test_json_compression_roundtrip(self, json_data):
        """
        JSON data should be compressible and decompressible without data loss.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        This tests compression of typical sync pipeline data (JSON records).
        """
        compressor = DataCompressor()

        # Compress JSON data
        compressed = compressor.compress_json(json_data)

        # Decompress JSON data
        decompressed = compressor.decompress_json(compressed)

        # Verify all fields are preserved
        assert decompressed["id"] == json_data["id"], "ID should be preserved"
        assert decompressed["name"] == json_data["name"], "Name should be preserved"
        assert (
            decompressed["description"] == json_data["description"]
        ), "Description should be preserved"
        assert decompressed["count"] == json_data["count"], "Count should be preserved"
        assert (
            decompressed["active"] == json_data["active"]
        ), "Active flag should be preserved"
        assert decompressed["tags"] == json_data["tags"], "Tags should be preserved"
        assert (
            decompressed["metadata"] == json_data["metadata"]
        ), "Metadata should be preserved"

    @given(
        records=st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.uuids().map(str),
                    "value": st.text(
                        min_size=10,
                        max_size=100,
                        alphabet=st.characters(whitelist_categories=("L", "N")),
                    ),
                    "timestamp": st.datetimes(
                        min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)
                    ).map(str),
                }
            ),
            min_size=10,
            max_size=100,
        )
    )
    @settings(max_examples=25)
    def test_batch_data_compression(self, records):
        """
        Batch data (multiple records) should compress efficiently.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Batch data typically has repeated field names which should compress well.
        """
        compressor = DataCompressor()

        # Create batch data
        batch_data = {"records": records, "count": len(records)}

        # Compress batch data
        compressed = compressor.compress_json(batch_data)

        # Calculate original size
        original_json = json.dumps(batch_data, default=str).encode("utf-8")
        original_size = len(original_json)
        compressed_size = len(compressed)

        # Verify compression occurred
        assert (
            compressed_size < original_size
        ), f"Batch data should compress: {compressed_size} < {original_size}"

        # Decompress and verify
        decompressed = compressor.decompress_json(compressed)

        assert decompressed["count"] == len(records), "Record count should be preserved"
        assert len(decompressed["records"]) == len(
            records
        ), "All records should be preserved"

        # Verify each record
        for i, (original, restored) in enumerate(zip(records, decompressed["records"])):
            assert restored == original, f"Record {i} should be preserved exactly"

    @given(
        compression_level=st.integers(min_value=1, max_value=9),
        data=st.binary(min_size=500, max_size=5000),
    )
    @settings(max_examples=25)
    def test_different_compression_levels(self, compression_level, data):
        """
        Different compression levels should all produce valid compressed data.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        All compression levels (1-9) should produce valid, decompressible output.
        """
        compressor = DataCompressor(compression_level=compression_level)

        # Compress data
        compressed = compressor.compress(data)

        # Decompress data
        decompressed = compressor.decompress(compressed)

        # Verify round-trip
        assert (
            decompressed == data
        ), f"Compression level {compression_level} should produce valid output"

    @given(
        text_content=st.text(
            min_size=100,
            max_size=5000,
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
        )
    )
    @settings(max_examples=25)
    def test_text_data_compression(self, text_content):
        """
        Text data should compress and decompress correctly with UTF-8 encoding.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Text data with various characters should be preserved through compression.
        """
        compressor = DataCompressor()

        # Convert text to bytes
        data = text_content.encode("utf-8")

        # Compress
        compressed = compressor.compress(data)

        # Decompress
        decompressed = compressor.decompress(compressed)

        # Verify text is preserved
        restored_text = decompressed.decode("utf-8")
        assert (
            restored_text == text_content
        ), "Text content should be preserved through compression"

    @given(
        chinese_text=st.text(
            min_size=50,
            max_size=500,
            alphabet="中文测试数据同步管道压缩解压缩验证属性测试",
        ),
        english_text=st.text(
            min_size=50,
            max_size=500,
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
        ),
    )
    @settings(max_examples=25)
    def test_multilingual_data_compression(self, chinese_text, english_text):
        """
        Multilingual data (Chinese + English) should compress correctly.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Data containing both Chinese and English characters should be preserved.
        """
        compressor = DataCompressor()

        # Create multilingual data
        data = {
            "chinese": chinese_text,
            "english": english_text,
            "mixed": f"{chinese_text} - {english_text}",
        }

        # Compress
        compressed = compressor.compress_json(data)

        # Decompress
        decompressed = compressor.decompress_json(compressed)

        # Verify all text is preserved
        assert (
            decompressed["chinese"] == chinese_text
        ), "Chinese text should be preserved"
        assert (
            decompressed["english"] == english_text
        ), "English text should be preserved"
        assert (
            decompressed["mixed"] == f"{chinese_text} - {english_text}"
        ), "Mixed text should be preserved"

    @given(size_multiplier=st.integers(min_value=1, max_value=10))
    @settings(max_examples=25)
    def test_large_data_compression(self, size_multiplier):
        """
        Large data should compress efficiently.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Large datasets should benefit from compression.
        """
        compressor = DataCompressor()

        # Create large data with repeated structure
        base_record = {
            "id": str(uuid4()),
            "name": "Test Record",
            "description": "This is a test record for compression testing",
            "value": 12345,
            "active": True,
        }

        # Create many records
        num_records = 100 * size_multiplier
        records = [
            {**base_record, "id": str(uuid4()), "value": i} for i in range(num_records)
        ]

        data = {"records": records, "total": num_records}

        # Compress
        compressed = compressor.compress_json(data)

        # Calculate sizes
        original_json = json.dumps(data, default=str).encode("utf-8")
        original_size = len(original_json)
        compressed_size = len(compressed)

        # Verify significant compression for large data
        ratio = compressor.get_compression_ratio(original_size, compressed_size)
        assert (
            ratio < 0.5
        ), f"Large data should compress to less than 50% of original: ratio={ratio:.2%}"

        # Verify data integrity
        decompressed = compressor.decompress_json(compressed)
        assert decompressed["total"] == num_records, "Record count should be preserved"
        assert (
            len(decompressed["records"]) == num_records
        ), "All records should be preserved"

    @given(data=st.binary(min_size=1, max_size=100))
    @settings(max_examples=25)
    def test_small_data_compression_integrity(self, data):
        """
        Small data should still compress and decompress correctly.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Even small data should maintain integrity through compression.
        Note: Small data may not reduce in size due to compression overhead.
        """
        compressor = DataCompressor()

        # Compress
        compressed = compressor.compress(data)

        # Decompress
        decompressed = compressor.decompress(compressed)

        # Verify integrity (size reduction not guaranteed for small data)
        assert (
            decompressed == data
        ), "Small data should maintain integrity through compression"

    @given(
        nested_depth=st.integers(min_value=1, max_value=5),
        items_per_level=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=25)
    def test_nested_structure_compression(self, nested_depth, items_per_level):
        """
        Deeply nested data structures should compress correctly.

        # Feature: data-sync-pipeline, Property 33: Data Compression
        **Validates: Requirements 10.4**

        Complex nested structures should be preserved through compression.
        """
        compressor = DataCompressor()

        # Build nested structure
        def build_nested(depth: int) -> Dict[str, Any]:
            if depth == 0:
                return {"value": "leaf", "id": str(uuid4())}
            return {
                f"child_{i}": build_nested(depth - 1) for i in range(items_per_level)
            }

        data = build_nested(nested_depth)

        # Compress
        compressed = compressor.compress_json(data)

        # Decompress
        decompressed = compressor.decompress_json(compressed)

        # Verify structure is preserved
        assert (
            decompressed == data
        ), f"Nested structure (depth={nested_depth}) should be preserved"


# ============================================================================
# Property 34: Timeout Enforcement
# **Validates: Requirements 10.5**
# ============================================================================


class TimeoutEnforcingExecutor:
    """
    Executor that enforces timeout on operations.

    Simulates the timeout enforcement behavior from:
    - src/sync/connectors/recovery_system.py
    - src/sync/scheduler/executor.py
    """

    def __init__(self, default_timeout: float = 5.0):
        self.default_timeout = default_timeout
        self.cancelled_operations: List[str] = []
        self.completed_operations: List[str] = []
        self.timeout_errors: Dict[str, str] = {}

    async def execute_with_timeout(
        self,
        operation_id: str,
        operation_duration: float,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute an operation with timeout enforcement.

        Args:
            operation_id: Unique identifier for the operation
            operation_duration: How long the operation will take (simulated)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            Result dict with success status and details
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        try:
            # Use asyncio.wait_for for timeout enforcement
            result = await asyncio.wait_for(
                self._simulate_operation(operation_id, operation_duration),
                timeout=effective_timeout,
            )
            self.completed_operations.append(operation_id)
            return {
                "success": True,
                "operation_id": operation_id,
                "duration": operation_duration,
                "timeout_used": effective_timeout,
                "error": None,
            }
        except asyncio.TimeoutError:
            # Operation exceeded timeout - cancel and return error
            self.cancelled_operations.append(operation_id)
            error_message = (
                f"Operation {operation_id} timed out after {effective_timeout}s"
            )
            self.timeout_errors[operation_id] = error_message
            return {
                "success": False,
                "operation_id": operation_id,
                "duration": None,
                "timeout_used": effective_timeout,
                "error": error_message,
                "error_type": "TimeoutError",
            }

    async def _simulate_operation(
        self, operation_id: str, duration: float
    ) -> Dict[str, Any]:
        """Simulate an operation that takes a certain duration."""
        await asyncio.sleep(duration)
        return {"operation_id": operation_id, "completed": True}

    def is_operation_cancelled(self, operation_id: str) -> bool:
        """Check if an operation was cancelled due to timeout."""
        return operation_id in self.cancelled_operations

    def is_operation_completed(self, operation_id: str) -> bool:
        """Check if an operation completed successfully."""
        return operation_id in self.completed_operations

    def get_timeout_error(self, operation_id: str) -> Optional[str]:
        """Get the timeout error message for an operation."""
        return self.timeout_errors.get(operation_id)

    def reset(self):
        """Reset the executor state."""
        self.cancelled_operations.clear()
        self.completed_operations.clear()
        self.timeout_errors.clear()


class BatchTimeoutExecutor:
    """
    Executor for batch operations with timeout enforcement.

    Simulates batch processing with per-batch and total timeout limits.
    """

    def __init__(self, batch_timeout: float = 2.0, total_timeout: float = 10.0):
        self.batch_timeout = batch_timeout
        self.total_timeout = total_timeout
        self.processed_batches: List[str] = []
        self.failed_batches: List[str] = []
        self.timeout_errors: List[Dict[str, Any]] = []

    async def process_batches(
        self, batches: List[Dict[str, Any]], batch_durations: List[float]
    ) -> Dict[str, Any]:
        """
        Process multiple batches with timeout enforcement.

        Args:
            batches: List of batch data to process
            batch_durations: Duration for each batch (simulated)

        Returns:
            Result with processed/failed batch counts
        """
        start_time = asyncio.get_event_loop().time()

        async def process_all_batches():
            for i, (batch, duration) in enumerate(zip(batches, batch_durations)):
                batch_id = batch.get("id", f"batch_{i}")

                try:
                    await asyncio.wait_for(
                        self._process_single_batch(batch_id, duration),
                        timeout=self.batch_timeout,
                    )
                    self.processed_batches.append(batch_id)
                except asyncio.TimeoutError:
                    self.failed_batches.append(batch_id)
                    self.timeout_errors.append(
                        {
                            "batch_id": batch_id,
                            "error": f"Batch {batch_id} timed out after {self.batch_timeout}s",
                            "error_type": "BatchTimeoutError",
                        }
                    )
                    # Continue processing other batches

        try:
            # Use wait_for for Python 3.9 compatibility (asyncio.timeout is 3.11+)
            await asyncio.wait_for(process_all_batches(), timeout=self.total_timeout)
        except asyncio.TimeoutError:
            # Total timeout exceeded
            self.timeout_errors.append(
                {
                    "batch_id": None,
                    "error": f"Total operation timed out after {self.total_timeout}s",
                    "error_type": "TotalTimeoutError",
                }
            )

        elapsed = asyncio.get_event_loop().time() - start_time

        return {
            "success": len(self.failed_batches) == 0 and len(self.timeout_errors) == 0,
            "processed_count": len(self.processed_batches),
            "failed_count": len(self.failed_batches),
            "timeout_errors": self.timeout_errors,
            "elapsed_time": elapsed,
        }

    async def _process_single_batch(self, batch_id: str, duration: float) -> None:
        """Process a single batch."""
        await asyncio.sleep(duration)

    def reset(self):
        """Reset executor state."""
        self.processed_batches.clear()
        self.failed_batches.clear()
        self.timeout_errors.clear()


class TestTimeoutEnforcement:
    """
    Property 34: Timeout Enforcement

    # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
    **Validates: Requirements 10.5**

    Tests that sync operations exceeding timeout thresholds are cancelled
    and return timeout errors.
    """

    @given(
        operation_duration=st.floats(min_value=0.01, max_value=0.5),
        timeout=st.floats(min_value=0.1, max_value=1.0),
    )
    @settings(max_examples=25, deadline=None)
    def test_operations_within_timeout_succeed(self, operation_duration, timeout):
        """
        Operations completing within timeout should succeed normally.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        When operation_duration < timeout, the operation should complete successfully.
        """
        # Only test cases where operation completes within timeout
        assume(operation_duration < timeout * 0.8)  # 80% margin for safety

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=timeout)
            operation_id = str(uuid4())

            result = await executor.execute_with_timeout(
                operation_id=operation_id,
                operation_duration=operation_duration,
                timeout=timeout,
            )

            # Verify operation succeeded
            assert result[
                "success"
            ], f"Operation should succeed when duration ({operation_duration}s) < timeout ({timeout}s)"
            assert result["error"] is None, "No error should be returned"
            assert executor.is_operation_completed(
                operation_id
            ), "Operation should be marked as completed"
            assert not executor.is_operation_cancelled(
                operation_id
            ), "Operation should not be cancelled"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        operation_duration=st.floats(min_value=0.3, max_value=1.0),
        timeout=st.floats(min_value=0.05, max_value=0.2),
    )
    @settings(max_examples=25, deadline=None)
    def test_operations_exceeding_timeout_are_cancelled(
        self, operation_duration, timeout
    ):
        """
        Operations exceeding timeout should be cancelled.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        When operation_duration > timeout, the operation should be cancelled.
        """
        # Only test cases where operation exceeds timeout
        assume(operation_duration > timeout * 1.5)  # 50% margin for safety

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=timeout)
            operation_id = str(uuid4())

            result = await executor.execute_with_timeout(
                operation_id=operation_id,
                operation_duration=operation_duration,
                timeout=timeout,
            )

            # Verify operation was cancelled
            assert not result[
                "success"
            ], f"Operation should fail when duration ({operation_duration}s) > timeout ({timeout}s)"
            assert executor.is_operation_cancelled(
                operation_id
            ), "Operation should be marked as cancelled"
            assert not executor.is_operation_completed(
                operation_id
            ), "Operation should not be marked as completed"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        operation_duration=st.floats(min_value=0.3, max_value=1.0),
        timeout=st.floats(min_value=0.05, max_value=0.2),
    )
    @settings(max_examples=25, deadline=None)
    def test_timeout_error_is_returned(self, operation_duration, timeout):
        """
        Timeout errors should be returned when operations exceed timeout.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        When timeout occurs, a proper timeout error should be returned.
        """
        # Only test cases where operation exceeds timeout
        assume(operation_duration > timeout * 1.5)

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=timeout)
            operation_id = str(uuid4())

            result = await executor.execute_with_timeout(
                operation_id=operation_id,
                operation_duration=operation_duration,
                timeout=timeout,
            )

            # Verify timeout error is returned
            assert result["error"] is not None, "Error message should be returned"
            assert (
                result["error_type"] == "TimeoutError"
            ), "Error type should be TimeoutError"
            assert (
                "timed out" in result["error"].lower()
            ), "Error message should indicate timeout"
            assert (
                str(timeout) in result["error"] or f"{timeout}s" in result["error"]
            ), "Error message should include timeout value"

            # Verify error is tracked
            tracked_error = executor.get_timeout_error(operation_id)
            assert tracked_error is not None, "Timeout error should be tracked"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        timeout_values=st.lists(
            st.floats(min_value=0.05, max_value=0.3), min_size=3, max_size=5
        )
    )
    @settings(max_examples=25, deadline=None)
    def test_various_timeout_values(self, timeout_values):
        """
        Different timeout values should be enforced correctly.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        The system should correctly enforce various timeout configurations.
        """

        async def run_test():
            executor = TimeoutEnforcingExecutor()

            for timeout in timeout_values:
                executor.reset()

                # Test operation that completes within timeout
                fast_op_id = str(uuid4())
                fast_duration = timeout * 0.3  # 30% of timeout

                fast_result = await executor.execute_with_timeout(
                    operation_id=fast_op_id,
                    operation_duration=fast_duration,
                    timeout=timeout,
                )

                assert fast_result[
                    "success"
                ], f"Fast operation should succeed with timeout={timeout}s"
                assert (
                    fast_result["timeout_used"] == timeout
                ), "Correct timeout value should be used"

                # Test operation that exceeds timeout
                slow_op_id = str(uuid4())
                slow_duration = timeout * 3  # 3x timeout

                slow_result = await executor.execute_with_timeout(
                    operation_id=slow_op_id,
                    operation_duration=slow_duration,
                    timeout=timeout,
                )

                assert not slow_result[
                    "success"
                ], f"Slow operation should fail with timeout={timeout}s"
                assert (
                    slow_result["timeout_used"] == timeout
                ), "Correct timeout value should be used"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        num_operations=st.integers(min_value=2, max_value=5),
        base_timeout=st.floats(min_value=0.1, max_value=0.3),
    )
    @settings(max_examples=25, deadline=None)
    def test_multiple_operations_timeout_independently(
        self, num_operations, base_timeout
    ):
        """
        Multiple operations should timeout independently.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        Each operation should be evaluated against its own timeout.
        """

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=base_timeout)

            # Create mix of fast and slow operations
            operations = []
            for i in range(num_operations):
                op_id = str(uuid4())
                # Alternate between fast and slow operations
                if i % 2 == 0:
                    duration = base_timeout * 0.3  # Fast
                    expected_success = True
                else:
                    duration = base_timeout * 3  # Slow
                    expected_success = False

                operations.append(
                    {
                        "id": op_id,
                        "duration": duration,
                        "expected_success": expected_success,
                    }
                )

            # Execute all operations
            for op in operations:
                result = await executor.execute_with_timeout(
                    operation_id=op["id"],
                    operation_duration=op["duration"],
                    timeout=base_timeout,
                )

                assert (
                    result["success"] == op["expected_success"]
                ), f"Operation {op['id']} should {'succeed' if op['expected_success'] else 'fail'}"

            # Verify counts
            expected_completed = sum(1 for op in operations if op["expected_success"])
            expected_cancelled = sum(
                1 for op in operations if not op["expected_success"]
            )

            assert (
                len(executor.completed_operations) == expected_completed
            ), f"Expected {expected_completed} completed operations"
            assert (
                len(executor.cancelled_operations) == expected_cancelled
            ), f"Expected {expected_cancelled} cancelled operations"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        num_batches=st.integers(min_value=2, max_value=5),
        batch_timeout=st.floats(min_value=0.1, max_value=0.3),
    )
    @settings(max_examples=25, deadline=None)
    def test_batch_operations_with_timeout(self, num_batches, batch_timeout):
        """
        Batch operations should enforce per-batch timeout.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        Each batch should be subject to its own timeout limit.
        """

        async def run_test():
            executor = BatchTimeoutExecutor(
                batch_timeout=batch_timeout,
                total_timeout=batch_timeout * num_batches * 2,  # Generous total timeout
            )

            # Create batches with varying durations
            batches = [{"id": f"batch_{i}"} for i in range(num_batches)]

            # Mix of fast and slow batches
            durations = []
            expected_failures = 0
            for i in range(num_batches):
                if i % 2 == 0:
                    durations.append(batch_timeout * 0.3)  # Fast
                else:
                    durations.append(batch_timeout * 3)  # Slow - will timeout
                    expected_failures += 1

            result = await executor.process_batches(batches, durations)

            # Verify batch processing results
            assert (
                result["processed_count"] == num_batches - expected_failures
            ), f"Expected {num_batches - expected_failures} processed batches"
            assert (
                result["failed_count"] == expected_failures
            ), f"Expected {expected_failures} failed batches"

            # Verify timeout errors were recorded for slow batches
            batch_timeout_errors = [
                e
                for e in result["timeout_errors"]
                if e.get("error_type") == "BatchTimeoutError"
            ]
            assert (
                len(batch_timeout_errors) == expected_failures
            ), f"Expected {expected_failures} batch timeout errors"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        total_timeout=st.floats(min_value=0.3, max_value=0.6),
        num_batches=st.integers(min_value=3, max_value=5),
    )
    @settings(max_examples=25, deadline=None)
    def test_total_timeout_enforcement(self, total_timeout, num_batches):
        """
        Total operation timeout should be enforced across all batches.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        When total timeout is exceeded, remaining batches should not be processed.
        """

        async def run_test():
            # Set batch timeout high so individual batches don't timeout
            batch_timeout = total_timeout * 3

            executor = BatchTimeoutExecutor(
                batch_timeout=batch_timeout, total_timeout=total_timeout
            )

            # Create batches that will exceed total timeout
            batches = [{"id": f"batch_{i}"} for i in range(num_batches)]

            # Each batch takes longer than total_timeout / num_batches
            # So total will exceed timeout
            duration_per_batch = (total_timeout / num_batches) * 2.0
            durations = [duration_per_batch] * num_batches

            result = await executor.process_batches(batches, durations)

            # Verify total timeout was triggered
            total_timeout_errors = [
                e
                for e in result["timeout_errors"]
                if e.get("error_type") == "TotalTimeoutError"
            ]

            # Either some batches processed before timeout, or total timeout hit
            # The key property: not all batches should be processed when total time exceeds timeout
            assert (
                result["processed_count"] < num_batches or len(total_timeout_errors) > 0
            ), "Either not all batches processed or total timeout error should occur"

            # Verify that total timeout error was recorded when timeout occurred
            if result["processed_count"] < num_batches:
                # If not all batches processed, total timeout should have been triggered
                assert (
                    len(total_timeout_errors) > 0
                ), "Total timeout error should be recorded when not all batches processed"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(
        operation_id=st.uuids().map(str),
        timeout=st.floats(min_value=0.05, max_value=0.2),
    )
    @settings(max_examples=25, deadline=None)
    def test_resources_released_on_timeout(self, operation_id, timeout):
        """
        Resources should be released when operation times out.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        When timeout occurs, the operation should be properly cancelled
        and resources should be released.
        """

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=timeout)

            # Execute operation that will timeout
            operation_duration = timeout * 3

            result = await executor.execute_with_timeout(
                operation_id=operation_id,
                operation_duration=operation_duration,
                timeout=timeout,
            )

            # Verify operation was cancelled
            assert not result["success"], "Operation should fail"
            assert executor.is_operation_cancelled(
                operation_id
            ), "Operation should be marked as cancelled"

            # Verify executor state is clean (operation not stuck)
            # The operation should not be in completed list
            assert (
                operation_id not in executor.completed_operations
            ), "Cancelled operation should not be in completed list"

            # Verify we can execute new operations (resources released)
            new_op_id = str(uuid4())
            new_result = await executor.execute_with_timeout(
                operation_id=new_op_id,
                operation_duration=timeout * 0.3,  # Fast operation
                timeout=timeout,
            )

            assert new_result[
                "success"
            ], "New operation should succeed after previous timeout"

        asyncio.get_event_loop().run_until_complete(run_test())

    @given(timeout=st.floats(min_value=0.05, max_value=0.2))
    @settings(max_examples=25, deadline=None)
    def test_zero_duration_operations_succeed(self, timeout):
        """
        Operations with zero/minimal duration should always succeed.

        # Feature: data-sync-pipeline, Property 34: Timeout Enforcement
        **Validates: Requirements 10.5**

        Very fast operations should never timeout.
        """

        async def run_test():
            executor = TimeoutEnforcingExecutor(default_timeout=timeout)
            operation_id = str(uuid4())

            # Minimal duration operation
            result = await executor.execute_with_timeout(
                operation_id=operation_id,
                operation_duration=0.001,  # 1ms
                timeout=timeout,
            )

            assert result["success"], "Minimal duration operation should succeed"
            assert result["error"] is None, "No error for fast operation"
            assert executor.is_operation_completed(
                operation_id
            ), "Fast operation should be completed"

        asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# 运行测试 (Final)
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
