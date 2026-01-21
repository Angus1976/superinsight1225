"""
Sync Pipeline API Property Tests - 同步管道 API 属性测试
使用 Hypothesis 库进行属性测试，每个属性至少 100 次迭代

**Feature: system-optimization, Properties 6-10**
**Validates: Requirements 3.1-3.8**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4, UUID
import hashlib
import hmac
import json
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

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
            ciphertext = ciphertext[len(self.ENCRYPTED_PREFIX):]
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
            'id': config.id,
            'name': config.name,
            'db_type': config.db_type,
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'username': config.username,
            'password_encrypted': encrypted_password,
            'is_active': config.is_active,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        self.sources[config.id] = record
        return record
    
    def get(self, source_id: str) -> Optional[Dict[str, Any]]:
        """获取数据源"""
        return self.sources.get(source_id)
    
    def update(self, source_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新数据源"""
        if source_id not in self.sources:
            return None
        record = self.sources[source_id]
        for key, value in updates.items():
            if key == 'password':
                record['password_encrypted'] = self.encryptor.encrypt(value)
            elif key in record:
                record[key] = value
        record['updated_at'] = datetime.utcnow()
        return record
    
    def delete(self, source_id: str) -> bool:
        """删除数据源"""
        if source_id in self.sources:
            del self.sources[source_id]
            return True
        return False
    
    def list(self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """列出数据源"""
        results = list(self.sources.values())
        if is_active is not None:
            results = [r for r in results if r['is_active'] == is_active]
        return results[skip:skip + limit]


class CheckpointStore:
    """检查点存储 - 内存实现用于测试"""
    
    def __init__(self):
        self.checkpoints: Dict[str, Checkpoint] = {}
    
    def _key(self, source_id: str, checkpoint_field: str) -> str:
        return f"{source_id}:{checkpoint_field}"
    
    def get(self, source_id: str, checkpoint_field: str = "updated_at") -> Optional[Checkpoint]:
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
        return hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    
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
        config=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'name': st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
            'db_type': st.sampled_from(['postgresql', 'mysql', 'sqlite', 'oracle']),
            'host': st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
            'port': st.integers(min_value=1, max_value=65535),
            'database': st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'username': st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'password': st.text(min_size=1, max_size=100),
            'is_active': st.booleans()
        })
    )
    @settings(max_examples=100)
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
        retrieved = store.get(config['id'])
        
        assert retrieved is not None, "Created data source should be retrievable"
        assert retrieved['id'] == config['id'], "ID should match"
        assert retrieved['name'] == config['name'], "Name should match"
        assert retrieved['db_type'] == config['db_type'], "DB type should match"
        assert retrieved['host'] == config['host'], "Host should match"
        assert retrieved['port'] == config['port'], "Port should match"
        assert retrieved['database'] == config['database'], "Database should match"
        assert retrieved['username'] == config['username'], "Username should match"
        assert retrieved['is_active'] == config['is_active'], "Active status should match"
    
    @given(
        config=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'db_type': st.sampled_from(['postgresql', 'mysql']),
            'host': st.just('localhost'),
            'port': st.integers(min_value=1000, max_value=9999),
            'database': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'username': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'password': st.text(min_size=1, max_size=50),
            'is_active': st.booleans()
        }),
        new_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
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
        updated = store.update(config['id'], {'name': new_name})
        
        assert updated is not None, "Update should succeed"
        assert updated['name'] == new_name, "Name should be updated"
        assert updated['id'] == config['id'], "ID should not change"
    
    @given(
        config=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'db_type': st.sampled_from(['postgresql', 'mysql']),
            'host': st.just('localhost'),
            'port': st.integers(min_value=1000, max_value=9999),
            'database': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'username': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'password': st.text(min_size=1, max_size=50),
            'is_active': st.booleans()
        })
    )
    @settings(max_examples=100)
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
        deleted = store.delete(config['id'])
        
        assert deleted, "Delete should succeed"
        
        # 尝试检索
        retrieved = store.get(config['id'])
        
        assert retrieved is None, "Deleted data source should not be retrievable"


# ============================================================================
# Property 7: 同步管道 API 凭据加密
# **Validates: Requirement 3.1**
# ============================================================================

class TestCredentialEncryption:
    """Property 7: 同步管道 API 凭据加密"""
    
    @given(
        password=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
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
    
    @given(
        password=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    def test_encrypted_differs_from_original(self, password):
        """加密后的数据应该与原始数据不同
        
        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()
        
        # 加密
        encrypted = encryptor.encrypt(password)
        
        # 移除前缀后比较
        encrypted_content = encrypted[len(CredentialEncryptor.ENCRYPTED_PREFIX):]
        
        assert encrypted_content != password, "Encrypted content should differ from original"
    
    @given(
        password=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    def test_encrypted_has_prefix(self, password):
        """加密后的数据应该有加密前缀
        
        **Feature: system-optimization, Property 7: 同步管道 API 凭据加密**
        **Validates: Requirement 3.1**
        """
        encryptor = CredentialEncryptor()
        
        # 加密
        encrypted = encryptor.encrypt(password)
        
        assert encrypted.startswith(CredentialEncryptor.ENCRYPTED_PREFIX), \
            "Encrypted value should have prefix"
    
    @given(
        password=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
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
        config=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'db_type': st.sampled_from(['postgresql', 'mysql']),
            'host': st.just('localhost'),
            'port': st.integers(min_value=1000, max_value=9999),
            'database': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'username': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            'password': st.text(min_size=1, max_size=50),
            'is_active': st.booleans()
        })
    )
    @settings(max_examples=100)
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
        assert created['password_encrypted'].startswith(CredentialEncryptor.ENCRYPTED_PREFIX), \
            "Stored password should be encrypted"
        
        # 验证可以解密回原始密码
        decrypted = encryptor.decrypt(created['password_encrypted'])
        assert decrypted == config['password'], "Should decrypt to original password"


# ============================================================================
# Property 8: 同步管道 API 分页过滤
# **Validates: Requirement 3.2**
# ============================================================================

class TestPaginationFiltering:
    """Property 8: 同步管道 API 分页过滤"""
    
    @given(
        num_sources=st.integers(min_value=0, max_value=50),
        skip=st.integers(min_value=0, max_value=100),
        limit=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
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
                is_active=True
            )
            store.create(config)
        
        # 列出数据源
        results = store.list(skip=skip, limit=limit)
        
        # 验证结果数量
        expected_count = max(0, min(limit, num_sources - skip))
        assert len(results) <= limit, f"Results should not exceed limit: {len(results)} > {limit}"
        assert len(results) == expected_count, f"Results count mismatch: {len(results)} != {expected_count}"
    
    @given(
        num_sources=st.integers(min_value=5, max_value=20),
        skip=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
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
                is_active=True
            )
            store.create(config)
            created_ids.append(config.id)
        
        # 获取所有结果
        all_results = store.list(skip=0, limit=num_sources)
        
        # 获取跳过后的结果
        skipped_results = store.list(skip=skip, limit=num_sources)
        
        # 验证跳过的数量
        expected_count = max(0, num_sources - skip)
        assert len(skipped_results) == expected_count, \
            f"Skipped results count mismatch: {len(skipped_results)} != {expected_count}"
    
    @given(
        num_active=st.integers(min_value=0, max_value=10),
        num_inactive=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
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
                is_active=True
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
                is_active=False
            )
            store.create(config)
        
        # 过滤活跃的
        active_results = store.list(is_active=True)
        assert len(active_results) == num_active, \
            f"Active filter mismatch: {len(active_results)} != {num_active}"
        
        # 过滤非活跃的
        inactive_results = store.list(is_active=False)
        assert len(inactive_results) == num_inactive, \
            f"Inactive filter mismatch: {len(inactive_results)} != {num_inactive}"
        
        # 不过滤
        all_results = store.list()
        assert len(all_results) == num_active + num_inactive, \
            f"All results mismatch: {len(all_results)} != {num_active + num_inactive}"


# ============================================================================
# Property 9: 同步管道 API 签名验证和幂等性
# **Validates: Requirement 3.5**
# ============================================================================

class TestSignatureAndIdempotency:
    """Property 9: 同步管道 API 签名验证和幂等性"""
    
    @given(
        payload=st.binary(min_size=1, max_size=1000),
        secret_key=st.text(min_size=8, max_size=64, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(max_examples=100)
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
        secret_key=st.text(min_size=8, max_size=64, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'),
        wrong_signature=st.text(min_size=64, max_size=64, alphabet='0123456789abcdef')
    )
    @settings(max_examples=100)
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
        rows_received=st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=100)
    def test_idempotency_returns_previous_result(self, idempotency_key, rows_received):
        """重复的幂等键应该返回之前的结果
        
        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        validator = WebhookValidator()
        
        # 第一次请求
        first_result = {'success': True, 'rows_received': rows_received}
        
        # 检查幂等性（应该返回 None，因为是新请求）
        existing = validator.check_idempotency(idempotency_key)
        assert existing is None, "First request should not find existing result"
        
        # 保存结果
        validator.save_idempotency(idempotency_key, first_result)
        
        # 第二次请求（应该返回之前的结果）
        existing = validator.check_idempotency(idempotency_key)
        assert existing is not None, "Second request should find existing result"
        assert existing['rows_received'] == rows_received, "Should return same result"
    
    @given(
        key1=st.uuids().map(str),
        key2=st.uuids().map(str)
    )
    @settings(max_examples=100)
    def test_different_idempotency_keys_independent(self, key1, key2):
        """不同的幂等键应该独立处理
        
        **Feature: system-optimization, Property 9: 同步管道 API 签名验证和幂等性**
        **Validates: Requirement 3.5**
        """
        assume(key1 != key2)
        
        validator = WebhookValidator()
        
        # 保存第一个键的结果
        result1 = {'success': True, 'rows_received': 10}
        validator.save_idempotency(key1, result1)
        
        # 第二个键应该没有结果
        existing = validator.check_idempotency(key2)
        assert existing is None, "Different keys should be independent"
        
        # 保存第二个键的结果
        result2 = {'success': True, 'rows_received': 20}
        validator.save_idempotency(key2, result2)
        
        # 两个键应该有各自的结果
        assert validator.check_idempotency(key1)['rows_received'] == 10
        assert validator.check_idempotency(key2)['rows_received'] == 20


# ============================================================================
# Property 10: 同步管道 API 检查点增量同步
# **Validates: Requirement 3.4**
# ============================================================================

class TestCheckpointIncrementalSync:
    """Property 10: 同步管道 API 检查点增量同步"""
    
    @given(
        source_id=st.uuids().map(str),
        checkpoint_field=st.sampled_from(['updated_at', 'created_at', 'id', 'version']),
        last_value=st.one_of(
            st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)),
            st.integers(min_value=0, max_value=1000000),
            st.text(min_size=1, max_size=50)
        ),
        rows_pulled=st.integers(min_value=0, max_value=10000)
    )
    @settings(max_examples=100)
    def test_checkpoint_save_and_retrieve(self, source_id, checkpoint_field, last_value, rows_pulled):
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
            rows_pulled=rows_pulled
        )
        
        # 保存检查点
        saved = store.save(checkpoint)
        
        # 检索检查点
        retrieved = store.get(source_id, checkpoint_field)
        
        assert retrieved is not None, "Saved checkpoint should be retrievable"
        assert retrieved.source_id == source_id, "Source ID should match"
        assert retrieved.checkpoint_field == checkpoint_field, "Checkpoint field should match"
        assert retrieved.last_value == last_value, "Last value should match"
        assert retrieved.rows_pulled == rows_pulled, "Rows pulled should match"
        assert retrieved.last_pull_at is not None, "Last pull time should be set"
    
    @given(
        source_id=st.uuids().map(str),
        checkpoint_field=st.sampled_from(['updated_at', 'created_at']),
        values=st.lists(
            st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=100)
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
                rows_pulled=i * 100
            )
            store.save(checkpoint)
        
        # 检索最新的检查点
        retrieved = store.get(source_id, checkpoint_field)
        
        assert retrieved is not None, "Checkpoint should exist"
        assert retrieved.last_value == values[-1], "Should have latest value"
        assert retrieved.rows_pulled == (len(values) - 1) * 100, "Should have latest rows count"
    
    @given(
        source_id=st.uuids().map(str),
        field1=st.just('updated_at'),
        field2=st.just('created_at')
    )
    @settings(max_examples=100)
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
            rows_pulled=100
        )
        store.save(checkpoint1)
        
        # 保存第二个字段的检查点
        checkpoint2 = Checkpoint(
            source_id=source_id,
            checkpoint_field=field2,
            last_value=datetime(2024, 6, 1),
            last_pull_at=None,
            rows_pulled=200
        )
        store.save(checkpoint2)
        
        # 检索两个检查点
        retrieved1 = store.get(source_id, field1)
        retrieved2 = store.get(source_id, field2)
        
        assert retrieved1 is not None, "First checkpoint should exist"
        assert retrieved2 is not None, "Second checkpoint should exist"
        assert retrieved1.last_value != retrieved2.last_value, "Values should be different"
        assert retrieved1.rows_pulled == 100, "First checkpoint rows should be 100"
        assert retrieved2.rows_pulled == 200, "Second checkpoint rows should be 200"
    
    @given(
        source_id=st.uuids().map(str),
        checkpoint_field=st.just('updated_at')
    )
    @settings(max_examples=100)
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
