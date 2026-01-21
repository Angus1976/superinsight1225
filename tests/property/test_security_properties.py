"""
安全控制模块属性测试

测试加密、输入验证、速率限制和审计日志的正确性属性。

Validates: 需求 14.1-14.5
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

# 导入被测模块
from src.security.encryption import (
    AES256Encryption,
    EncryptionError,
    DecryptionError,
    encrypt,
    decrypt,
    generate_key
)
from src.security.input_validation import (
    InputValidationService,
    ValidationError,
    XSSDetectedError,
    SQLInjectionDetectedError,
    PathTraversalDetectedError,
    detect_xss,
    detect_sql_injection,
    detect_path_traversal,
    sanitize_string,
    validate_email,
    validate_phone,
    validate_url,
    validate_uuid,
    validate_ip_address
)
from src.security.rate_limiter import (
    RateLimitService,
    RateLimitConfig,
    RateLimitAlgorithm,
    InMemoryRateLimiter,
    rate_limit
)
from src.security.enhanced_audit import (
    EnhancedAuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity
)


# ============================================================================
# Property 23: AES-256 加密往返
# ============================================================================

class TestEncryptionRoundTrip:
    """
    Property 23: AES-256 加密往返
    
    对于任意明文和密钥，加密后解密应该返回原始明文。
    
    **Validates: Requirements 14.1**
    """
    
    @given(
        plaintext=st.text(min_size=1, max_size=1000),
        key=st.text(min_size=8, max_size=64)
    )
    @settings(max_examples=100, deadline=None)
    def test_encrypt_decrypt_roundtrip(self, plaintext: str, key: str):
        """加密后解密应返回原始明文"""
        # 跳过空字符串
        assume(len(plaintext.strip()) > 0)
        
        encryption = AES256Encryption()
        
        # 加密
        ciphertext = encryption.encrypt(plaintext, key)
        
        # 验证密文不等于明文
        assert ciphertext != plaintext
        
        # 解密
        decrypted = encryption.decrypt(ciphertext, key)
        
        # 验证解密结果等于原始明文
        assert decrypted == plaintext
    
    @given(
        plaintext=st.text(min_size=1, max_size=500),
        password=st.text(min_size=8, max_size=32)
    )
    @settings(max_examples=50, deadline=None)
    def test_encrypt_decrypt_with_salt_roundtrip(self, plaintext: str, password: str):
        """使用密码加密后解密应返回原始明文"""
        assume(len(plaintext.strip()) > 0)
        assume(len(password.strip()) >= 8)
        
        encryption = AES256Encryption()
        
        # 加密（包含盐值）
        ciphertext = encryption.encrypt_with_salt(plaintext, password)
        
        # 解密
        decrypted = encryption.decrypt_with_salt(ciphertext, password)
        
        # 验证
        assert decrypted == plaintext
    
    def test_different_keys_produce_different_ciphertext(self):
        """不同密钥应产生不同密文"""
        encryption = AES256Encryption()
        plaintext = "test message"
        key1 = "key1_secret_key"
        key2 = "key2_secret_key"
        
        ciphertext1 = encryption.encrypt(plaintext, key1)
        ciphertext2 = encryption.encrypt(plaintext, key2)
        
        # 不同密钥应产生不同密文
        assert ciphertext1 != ciphertext2
    
    def test_same_plaintext_different_nonce(self):
        """相同明文每次加密应产生不同密文（因为随机 nonce）"""
        encryption = AES256Encryption()
        plaintext = "test message"
        key = "test_secret_key"
        
        ciphertext1 = encryption.encrypt(plaintext, key)
        ciphertext2 = encryption.encrypt(plaintext, key)
        
        # 由于随机 nonce，密文应该不同
        assert ciphertext1 != ciphertext2
        
        # 但解密后应该相同
        assert encryption.decrypt(ciphertext1, key) == plaintext
        assert encryption.decrypt(ciphertext2, key) == plaintext
    
    def test_wrong_key_fails_decryption(self):
        """错误密钥应导致解密失败"""
        encryption = AES256Encryption()
        plaintext = "test message"
        correct_key = "correct_key"
        wrong_key = "wrong_key"
        
        ciphertext = encryption.encrypt(plaintext, correct_key)
        
        with pytest.raises(DecryptionError):
            encryption.decrypt(ciphertext, wrong_key)
    
    def test_generate_key_produces_valid_key(self):
        """生成的密钥应该可用于加密解密"""
        key = generate_key()
        encryption = AES256Encryption()
        plaintext = "test message"
        
        ciphertext = encryption.encrypt(plaintext, key)
        decrypted = encryption.decrypt(ciphertext, key)
        
        assert decrypted == plaintext


# ============================================================================
# Property 24: API 输入验证
# ============================================================================

class TestInputValidation:
    """
    Property 24: API 输入验证
    
    对于任意输入，验证器应正确检测恶意内容并拒绝。
    
    **Validates: Requirements 14.2**
    """
    
    @given(safe_text=st.text(alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'Z'),
        blacklist_characters='<>\'";'
    ), min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_safe_text_passes_validation(self, safe_text: str):
        """安全文本应通过验证"""
        assume(len(safe_text.strip()) > 0)
        
        # 安全文本不应触发 XSS 检测
        assert not detect_xss(safe_text)
        
        # 安全文本不应触发 SQL 注入检测
        assert not detect_sql_injection(safe_text)
    
    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "<img onerror=alert(1)>",
        "<iframe src='evil.com'>",
        "expression(alert(1))",
    ])
    def test_xss_detection(self, xss_payload: str):
        """XSS 攻击载荷应被检测"""
        assert detect_xss(xss_payload)
    
    @pytest.mark.parametrize("sql_payload", [
        "' OR '1'='1",
        "'; DROP TABLE users;--",
        "1; DELETE FROM users",
        "UNION SELECT * FROM passwords",
        "1' OR 1=1--",
    ])
    def test_sql_injection_detection(self, sql_payload: str):
        """SQL 注入载荷应被检测"""
        assert detect_sql_injection(sql_payload)
    
    @pytest.mark.parametrize("path_payload", [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "%2e%2e%2f%2e%2e%2f",
        "....//....//",
    ])
    def test_path_traversal_detection(self, path_payload: str):
        """路径遍历攻击应被检测"""
        assert detect_path_traversal(path_payload)
    
    @given(text=st.text(min_size=0, max_size=1000))
    @settings(max_examples=50, deadline=None)
    def test_sanitize_string_removes_control_chars(self, text: str):
        """清理后的字符串不应包含控制字符"""
        sanitized = sanitize_string(text)
        
        # 检查没有控制字符（除了换行和制表符）
        for char in sanitized:
            if char not in '\n\r\t':
                assert ord(char) >= 32 and ord(char) != 127
    
    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name@domain.co.uk", True),
        ("invalid-email", False),
        ("@nodomain.com", False),
        ("noat.com", False),
    ])
    def test_email_validation(self, email: str, expected: bool):
        """邮箱验证应正确识别有效和无效格式"""
        assert validate_email(email) == expected
    
    @pytest.mark.parametrize("phone,expected", [
        ("13812345678", True),
        ("+8613812345678", True),
        ("010-12345678", True),
        ("123", False),
        ("abcdefghijk", False),
    ])
    def test_phone_validation(self, phone: str, expected: bool):
        """电话验证应正确识别有效和无效格式"""
        assert validate_phone(phone) == expected
    
    @pytest.mark.parametrize("url,expected", [
        ("https://example.com", True),
        ("http://localhost:8080/path", True),
        ("ftp://invalid.com", False),
        ("not-a-url", False),
    ])
    def test_url_validation(self, url: str, expected: bool):
        """URL 验证应正确识别有效和无效格式"""
        assert validate_url(url) == expected
    
    @pytest.mark.parametrize("uuid_str,expected", [
        ("550e8400-e29b-41d4-a716-446655440000", True),
        ("550E8400-E29B-41D4-A716-446655440000", True),
        ("invalid-uuid", False),
        ("550e8400e29b41d4a716446655440000", False),
    ])
    def test_uuid_validation(self, uuid_str: str, expected: bool):
        """UUID 验证应正确识别有效和无效格式"""
        assert validate_uuid(uuid_str) == expected
    
    @pytest.mark.parametrize("ip,expected", [
        ("192.168.1.1", True),
        ("10.0.0.1", True),
        ("255.255.255.255", True),
        ("256.1.1.1", False),
        ("invalid", False),
    ])
    def test_ip_validation(self, ip: str, expected: bool):
        """IP 地址验证应正确识别有效和无效格式"""
        assert validate_ip_address(ip) == expected


# ============================================================================
# Property 25: 速率限制
# ============================================================================

class TestRateLimiting:
    """
    Property 25: 速率限制
    
    对于任意请求序列，速率限制器应正确限制超过阈值的请求。
    
    **Validates: Requirements 14.3**
    """
    
    @pytest.fixture
    def limiter(self):
        return InMemoryRateLimiter()
    
    @pytest.fixture
    def service(self, limiter):
        return RateLimitService(limiter)
    
    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, limiter):
        """在限制内的请求应被允许"""
        config = RateLimitConfig(requests=10, window=60)
        key = "test_user"
        
        # 发送 10 个请求（在限制内）
        for i in range(10):
            result = await limiter.check(key, config)
            assert result.allowed, f"Request {i+1} should be allowed"
            assert result.remaining == 10 - i - 1
    
    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, limiter):
        """超过限制的请求应被阻止"""
        config = RateLimitConfig(requests=5, window=60)
        key = "test_user"
        
        # 发送 5 个请求（达到限制）
        for i in range(5):
            result = await limiter.check(key, config)
            assert result.allowed
        
        # 第 6 个请求应被阻止
        result = await limiter.check(key, config)
        assert not result.allowed
        assert result.remaining == 0
        assert result.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter):
        """不同键的限制应独立"""
        config = RateLimitConfig(requests=2, window=60)
        
        # 用户 1 用完配额
        for _ in range(2):
            await limiter.check("user1", config)
        result1 = await limiter.check("user1", config)
        assert not result1.allowed
        
        # 用户 2 应该仍有配额
        result2 = await limiter.check("user2", config)
        assert result2.allowed
    
    @pytest.mark.asyncio
    async def test_service_endpoint_configs(self, service):
        """服务应支持不同端点的配置"""
        # 配置不同端点
        service.configure("auth", requests=5, window=60)
        service.configure("api", requests=100, window=60)
        
        # 验证配置
        auth_config = service.get_config("auth")
        api_config = service.get_config("api")
        
        assert auth_config.requests == 5
        assert api_config.requests == 100
    
    @pytest.mark.asyncio
    async def test_token_bucket_allows_burst(self, limiter):
        """令牌桶算法应允许突发请求"""
        config = RateLimitConfig(
            requests=10,
            window=60,
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            burst=5
        )
        key = "burst_test"
        
        # 应该允许 15 个请求（10 + 5 突发）
        allowed_count = 0
        for _ in range(20):
            result = await limiter.check(key, config)
            if result.allowed:
                allowed_count += 1
        
        # 至少应该允许 10 个请求
        assert allowed_count >= 10
    
    @given(
        requests=st.integers(min_value=1, max_value=100),
        window=st.integers(min_value=1, max_value=3600)
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_rate_limit_config_valid(self, requests: int, window: int):
        """速率限制配置应接受有效参数"""
        config = RateLimitConfig(requests=requests, window=window)
        assert config.requests == requests
        assert config.window == window
    
    def test_invalid_config_raises_error(self):
        """无效配置应抛出错误"""
        with pytest.raises(ValueError):
            RateLimitConfig(requests=0, window=60)
        
        with pytest.raises(ValueError):
            RateLimitConfig(requests=10, window=0)


# ============================================================================
# Property 26: 审计日志完整性
# ============================================================================

class TestAuditLogIntegrity:
    """
    Property 26: 审计日志完整性
    
    对于任意审计事件，日志应保持完整性并可验证。
    
    **Validates: Requirements 14.4, 14.5**
    """
    
    @pytest.fixture
    def audit_logger(self):
        return EnhancedAuditLogger()
    
    @pytest.mark.asyncio
    async def test_event_integrity_verification(self, audit_logger):
        """事件应通过完整性验证"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1"
        )
        
        # 验证完整性
        assert event.verify_integrity()
        
        # 记录事件
        event_id = await audit_logger.log(event)
        assert event_id == event.id
    
    @pytest.mark.asyncio
    async def test_tampered_event_fails_verification(self):
        """篡改的事件应验证失败"""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1"
        )
        
        # 保存原始校验和
        original_checksum = event.checksum
        
        # 篡改事件
        event.user_id = "hacker"
        
        # 验证应失败（因为校验和不匹配）
        assert not event.verify_integrity()
    
    @pytest.mark.asyncio
    async def test_login_events_logged(self, audit_logger):
        """登录事件应被正确记录"""
        # 记录成功登录
        event_id = await audit_logger.log_login_success(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1"
        )
        assert event_id is not None
        
        # 记录失败登录
        event_id = await audit_logger.log_login_failed(
            username="testuser",
            ip_address="192.168.1.1",
            reason="Invalid password"
        )
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_resource_events_logged(self, audit_logger):
        """资源事件应被正确记录"""
        # 创建
        await audit_logger.log_resource_created(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1",
            resource_type="document",
            resource_id="doc123"
        )
        
        # 更新
        await audit_logger.log_resource_updated(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1",
            resource_type="document",
            resource_id="doc123",
            old_value={"title": "Old"},
            new_value={"title": "New"}
        )
        
        # 删除
        await audit_logger.log_resource_deleted(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1",
            resource_type="document",
            resource_id="doc123"
        )
        
        # 验证统计
        stats = await audit_logger.get_stats()
        assert stats["total_events"] == 3
    
    @pytest.mark.asyncio
    async def test_failed_login_tracking(self, audit_logger):
        """失败登录应被追踪"""
        ip_address = "192.168.1.100"
        
        # 记录多次失败登录
        for i in range(5):
            await audit_logger.log_login_failed(
                username=f"user{i}",
                ip_address=ip_address
            )
        
        # 检查失败登录计数
        count = await audit_logger.get_failed_login_count(ip_address)
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_event_query(self, audit_logger):
        """事件查询应正确过滤"""
        # 记录不同类型的事件
        await audit_logger.log_login_success(
            user_id="user1",
            username="user1",
            ip_address="192.168.1.1"
        )
        await audit_logger.log_login_failed(
            username="user2",
            ip_address="192.168.1.2"
        )
        await audit_logger.log_resource_created(
            user_id="user1",
            username="user1",
            ip_address="192.168.1.1",
            resource_type="document",
            resource_id="doc1"
        )
        
        # 按类型查询
        login_events = await audit_logger.get_events(
            event_type=AuditEventType.LOGIN_SUCCESS
        )
        assert len(login_events) == 1
        
        # 按用户查询
        user1_events = await audit_logger.get_events(user_id="user1")
        assert len(user1_events) == 2
        
        # 按 IP 查询
        ip_events = await audit_logger.get_events(ip_address="192.168.1.1")
        assert len(ip_events) == 2
    
    @pytest.mark.asyncio
    async def test_all_events_integrity(self, audit_logger):
        """所有事件应通过完整性验证"""
        # 记录多个事件
        for i in range(10):
            await audit_logger.log_login_success(
                user_id=f"user{i}",
                username=f"user{i}",
                ip_address=f"192.168.1.{i}"
            )
        
        # 验证所有事件完整性
        result = await audit_logger.verify_all_integrity()
        assert result["total"] == 10
        assert result["valid"] == 10
        assert result["invalid"] == 0
        assert result["integrity_rate"] == 1.0
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N')
        )),
        ip_address=st.ip_addresses(v=4).map(str)
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_event_creation_with_various_inputs(
        self,
        user_id: str,
        ip_address: str
    ):
        """事件应能处理各种输入"""
        assume(len(user_id) > 0)
        
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address
        )
        
        # 验证事件创建成功
        assert event.id is not None
        assert event.checksum is not None
        assert event.verify_integrity()
        
        # 验证可以转换为字典
        event_dict = event.to_dict()
        assert event_dict["user_id"] == user_id
        assert event_dict["ip_address"] == ip_address


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
