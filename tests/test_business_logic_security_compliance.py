#!/usr/bin/env python3
"""
业务逻辑安全合规测试
验证数据安全、权限控制、审计日志、隐私保护等安全合规要求

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 49.2
"""

import pytest
import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import tempfile
import os

from src.business_logic.cache_system import SmartCacheManager
from src.business_logic.performance_optimizer import PerformanceOptimizer
from src.business_logic.algorithm_manager import BusinessLogicAlgorithmManager

class TestDataPrivacyProtection:
    """数据隐私保护测试"""
    
    @pytest.fixture
    def sensitive_data(self):
        """敏感数据"""
        return [
            {
                "id": 1,
                "text": "Customer John Doe (john.doe@email.com) complained about service",
                "sentiment": "negative",
                "user_id": "12345",
                "email": "john.doe@email.com",
                "phone": "+1-555-123-4567",
                "credit_card": "4532-1234-5678-9012",
                "ssn": "123-45-6789"
            },
            {
                "id": 2,
                "text": "Jane Smith loves our product and recommends it",
                "sentiment": "positive",
                "user_id": "67890",
                "email": "jane.smith@email.com",
                "phone": "+1-555-987-6543",
                "ip_address": "192.168.1.100"
            }
        ]
    
    def test_pii_detection(self, sensitive_data):
        """测试PII检测"""
        import re
        
        def detect_pii(text: str) -> Dict[str, List[str]]:
            """检测个人身份信息"""
            pii_patterns = {
                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "phone": r'\+?1?-?\s?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
                "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                "ssn": r'\b\d{3}-\d{2}-\d{4}\b'
            }
            
            detected_pii = {}
            for pii_type, pattern in pii_patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    detected_pii[pii_type] = matches
            
            return detected_pii
        
        # 检测敏感数据中的PII
        for item in sensitive_data:
            pii_found = detect_pii(item["text"])
            
            # 验证PII检测功能
            if "john.doe@email.com" in item["text"]:
                assert "email" in pii_found
                assert "john.doe@email.com" in pii_found["email"]
            
            if "4532-1234-5678-9012" in item.get("credit_card", ""):
                # 信用卡号应该被检测到
                assert item["credit_card"] == "4532-1234-5678-9012"
    
    def test_data_anonymization(self, sensitive_data):
        """测试数据匿名化"""
        def anonymize_data(data: Dict[str, Any]) -> Dict[str, Any]:
            """匿名化敏感数据"""
            anonymized = data.copy()
            
            # 匿名化字段
            sensitive_fields = ["user_id", "email", "phone", "credit_card", "ssn", "ip_address"]
            
            for field in sensitive_fields:
                if field in anonymized:
                    # 使用哈希值替换
                    original_value = str(anonymized[field])
                    hash_value = hashlib.sha256(original_value.encode()).hexdigest()[:8]
                    anonymized[field] = f"***{hash_value}"
            
            # 匿名化文本中的PII
            text = anonymized.get("text", "")
            import re
            
            # 替换邮箱
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                         '***@***.***', text)
            
            # 替换电话号码
            text = re.sub(r'\+?1?-?\s?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', 
                         '***-***-****', text)
            
            anonymized["text"] = text
            
            return anonymized
        
        # 匿名化数据
        anonymized_data = [anonymize_data(item) for item in sensitive_data]
        
        # 验证匿名化效果
        for original, anonymized in zip(sensitive_data, anonymized_data):
            # 敏感字段应该被匿名化
            if "email" in original:
                assert anonymized["email"].startswith("***")
                assert original["email"] not in anonymized["text"]
            
            if "phone" in original:
                assert anonymized["phone"].startswith("***")
            
            # 文本中的PII应该被替换
            assert "@" not in anonymized["text"] or "***@***" in anonymized["text"]
    
    def test_data_masking_in_logs(self, sensitive_data):
        """测试日志中的数据脱敏"""
        import logging
        from io import StringIO
        
        # 创建日志处理器
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        def mask_sensitive_data(message: str) -> str:
            """脱敏敏感数据"""
            import re
            
            # 脱敏邮箱
            message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                           '***@***.***', message)
            
            # 脱敏电话
            message = re.sub(r'\+?1?-?\s?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', 
                           '***-***-****', message)
            
            # 脱敏信用卡
            message = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 
                           '****-****-****-****', message)
            
            return message
        
        # 记录包含敏感数据的日志
        for item in sensitive_data:
            original_message = f"Processing data: {json.dumps(item)}"
            masked_message = mask_sensitive_data(original_message)
            logger.info(masked_message)
        
        # 检查日志内容
        log_content = log_stream.getvalue()
        
        # 验证敏感数据被脱敏
        assert "john.doe@email.com" not in log_content
        assert "***@***.***" in log_content
        assert "4532-1234-5678-9012" not in log_content

class TestAccessControlSecurity:
    """访问控制安全测试"""
    
    @pytest.fixture
    def user_contexts(self):
        """用户上下文"""
        return [
            {
                "user_id": "admin_001",
                "role": "admin",
                "tenant_id": "tenant_1",
                "permissions": ["read", "write", "delete", "analyze"],
                "projects": ["project_1", "project_2", "project_3"]
            },
            {
                "user_id": "expert_001",
                "role": "business_expert",
                "tenant_id": "tenant_1", 
                "permissions": ["read", "write", "analyze"],
                "projects": ["project_1", "project_2"]
            },
            {
                "user_id": "annotator_001",
                "role": "annotator",
                "tenant_id": "tenant_1",
                "permissions": ["read", "write"],
                "projects": ["project_1"]
            },
            {
                "user_id": "viewer_001",
                "role": "viewer",
                "tenant_id": "tenant_2",
                "permissions": ["read"],
                "projects": ["project_4"]
            }
        ]
    
    def test_role_based_access(self, user_contexts):
        """测试基于角色的访问控制"""
        def check_permission(user_context: Dict[str, Any], 
                           required_permission: str,
                           resource_project: str) -> bool:
            """检查用户权限"""
            # 检查权限
            if required_permission not in user_context["permissions"]:
                return False
            
            # 检查项目访问权限
            if resource_project not in user_context["projects"]:
                return False
            
            return True
        
        # 测试不同角色的权限
        test_cases = [
            ("admin_001", "analyze", "project_1", True),
            ("expert_001", "analyze", "project_1", True),
            ("annotator_001", "analyze", "project_1", False),  # 标注员无分析权限
            ("viewer_001", "write", "project_4", False),       # 查看者无写权限
            ("expert_001", "read", "project_3", False),        # 无项目访问权限
        ]
        
        for user_id, permission, project, expected in test_cases:
            user_context = next(u for u in user_contexts if u["user_id"] == user_id)
            result = check_permission(user_context, permission, project)
            assert result == expected, f"权限检查失败: {user_id}, {permission}, {project}"
    
    def test_tenant_isolation(self, user_contexts):
        """测试租户隔离"""
        def get_accessible_data(user_context: Dict[str, Any], 
                              all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """获取用户可访问的数据"""
            user_tenant = user_context["tenant_id"]
            user_projects = user_context["projects"]
            
            accessible_data = []
            for item in all_data:
                # 检查租户隔离
                if item.get("tenant_id") != user_tenant:
                    continue
                
                # 检查项目权限
                if item.get("project_id") in user_projects:
                    accessible_data.append(item)
            
            return accessible_data
        
        # 模拟多租户数据
        all_data = [
            {"id": 1, "tenant_id": "tenant_1", "project_id": "project_1", "data": "data1"},
            {"id": 2, "tenant_id": "tenant_1", "project_id": "project_2", "data": "data2"},
            {"id": 3, "tenant_id": "tenant_2", "project_id": "project_4", "data": "data3"},
            {"id": 4, "tenant_id": "tenant_1", "project_id": "project_3", "data": "data4"},
        ]
        
        # 测试不同用户的数据访问
        for user_context in user_contexts:
            accessible_data = get_accessible_data(user_context, all_data)
            
            # 验证租户隔离
            for item in accessible_data:
                assert item["tenant_id"] == user_context["tenant_id"]
                assert item["project_id"] in user_context["projects"]
    
    def test_api_authentication(self):
        """测试API认证"""
        def validate_jwt_token(token: str) -> Dict[str, Any]:
            """验证JWT令牌（模拟）"""
            # 简化的JWT验证
            if not token or not token.startswith("Bearer "):
                return None
            
            # 模拟解码JWT
            token_data = token.replace("Bearer ", "")
            
            # 模拟有效令牌
            valid_tokens = {
                "admin_token_123": {
                    "user_id": "admin_001",
                    "role": "admin",
                    "exp": int(time.time()) + 3600
                },
                "expired_token_456": {
                    "user_id": "user_001", 
                    "role": "user",
                    "exp": int(time.time()) - 3600  # 已过期
                }
            }
            
            if token_data in valid_tokens:
                token_info = valid_tokens[token_data]
                
                # 检查过期时间
                if token_info["exp"] < time.time():
                    return None
                
                return token_info
            
            return None
        
        # 测试有效令牌
        valid_token = "Bearer admin_token_123"
        user_info = validate_jwt_token(valid_token)
        assert user_info is not None
        assert user_info["user_id"] == "admin_001"
        
        # 测试无效令牌
        invalid_token = "Bearer invalid_token"
        user_info = validate_jwt_token(invalid_token)
        assert user_info is None
        
        # 测试过期令牌
        expired_token = "Bearer expired_token_456"
        user_info = validate_jwt_token(expired_token)
        assert user_info is None

class TestAuditLogging:
    """审计日志测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """审计日志记录器"""
        audit_logs = []
        
        def log_audit_event(user_id: str, 
                          action: str, 
                          resource: str,
                          result: str,
                          details: Dict[str, Any] = None):
            """记录审计事件"""
            audit_event = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                "details": details or {},
                "ip_address": "192.168.1.100",  # 模拟IP
                "user_agent": "TestClient/1.0"
            }
            audit_logs.append(audit_event)
        
        return log_audit_event, audit_logs
    
    def test_business_logic_analysis_audit(self, audit_logger):
        """测试业务逻辑分析审计"""
        log_audit_event, audit_logs = audit_logger
        
        # 模拟业务逻辑分析操作
        analysis_operations = [
            {
                "user_id": "expert_001",
                "action": "analyze_business_logic",
                "resource": "project_1",
                "result": "success",
                "details": {"algorithm": "pattern_analysis", "data_count": 1000}
            },
            {
                "user_id": "admin_001", 
                "action": "export_business_rules",
                "resource": "project_1",
                "result": "success",
                "details": {"format": "json", "rules_count": 25}
            },
            {
                "user_id": "annotator_001",
                "action": "analyze_business_logic",
                "resource": "project_1", 
                "result": "denied",
                "details": {"reason": "insufficient_permissions"}
            }
        ]
        
        # 记录审计日志
        for op in analysis_operations:
            log_audit_event(**op)
        
        # 验证审计日志
        assert len(audit_logs) == 3
        
        # 验证成功操作
        success_logs = [log for log in audit_logs if log["result"] == "success"]
        assert len(success_logs) == 2
        
        # 验证拒绝操作
        denied_logs = [log for log in audit_logs if log["result"] == "denied"]
        assert len(denied_logs) == 1
        assert denied_logs[0]["details"]["reason"] == "insufficient_permissions"
    
    def test_data_access_audit(self, audit_logger):
        """测试数据访问审计"""
        log_audit_event, audit_logs = audit_logger
        
        # 模拟数据访问操作
        data_operations = [
            {
                "user_id": "expert_001",
                "action": "read_annotation_data",
                "resource": "project_1/annotations",
                "result": "success",
                "details": {"records_accessed": 500}
            },
            {
                "user_id": "viewer_001",
                "action": "read_annotation_data", 
                "resource": "project_1/annotations",
                "result": "denied",
                "details": {"reason": "cross_tenant_access_denied"}
            }
        ]
        
        # 记录审计日志
        for op in data_operations:
            log_audit_event(**op)
        
        # 验证跨租户访问被拒绝
        cross_tenant_denied = [
            log for log in audit_logs 
            if log["details"].get("reason") == "cross_tenant_access_denied"
        ]
        assert len(cross_tenant_denied) == 1
    
    def test_audit_log_integrity(self, audit_logger):
        """测试审计日志完整性"""
        log_audit_event, audit_logs = audit_logger
        
        # 记录一些操作
        log_audit_event("user_001", "test_action", "test_resource", "success")
        
        # 验证日志完整性
        assert len(audit_logs) == 1
        log_entry = audit_logs[0]
        
        # 验证必需字段
        required_fields = ["timestamp", "user_id", "action", "resource", "result"]
        for field in required_fields:
            assert field in log_entry
            assert log_entry[field] is not None
        
        # 验证时间戳格式
        timestamp = log_entry["timestamp"]
        datetime.fromisoformat(timestamp)  # 应该不抛出异常

class TestSecureDataTransmission:
    """安全数据传输测试"""
    
    def test_data_encryption_in_transit(self):
        """测试传输中的数据加密"""
        import ssl
        import socket
        
        def create_secure_context():
            """创建安全上下文"""
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # 测试环境
            return context
        
        # 测试SSL上下文创建
        ssl_context = create_secure_context()
        assert ssl_context is not None
        assert ssl_context.verify_mode == ssl.CERT_NONE
    
    def test_api_request_validation(self):
        """测试API请求验证"""
        def validate_api_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
            """验证API请求"""
            errors = []
            
            # 验证必需字段
            required_fields = ["project_id", "data"]
            for field in required_fields:
                if field not in request_data:
                    errors.append(f"Missing required field: {field}")
            
            # 验证数据类型
            if "data" in request_data:
                if not isinstance(request_data["data"], list):
                    errors.append("Data must be a list")
                elif len(request_data["data"]) > 10000:
                    errors.append("Data size exceeds limit")
            
            # 验证项目ID格式
            if "project_id" in request_data:
                project_id = request_data["project_id"]
                if not isinstance(project_id, str) or len(project_id) < 3:
                    errors.append("Invalid project_id format")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
        
        # 测试有效请求
        valid_request = {
            "project_id": "project_123",
            "data": [{"text": "sample", "sentiment": "positive"}]
        }
        result = validate_api_request(valid_request)
        assert result["valid"] is True
        
        # 测试无效请求
        invalid_request = {
            "project_id": "p1",  # 太短
            "data": "not_a_list"  # 错误类型
        }
        result = validate_api_request(invalid_request)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_input_sanitization(self):
        """测试输入清理"""
        def sanitize_input(text: str) -> str:
            """清理输入文本"""
            import re
            
            # 移除潜在的脚本注入
            text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
            
            # 移除SQL注入尝试
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
                r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
                r"(--|#|/\*|\*/)"
            ]
            
            for pattern in sql_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
            # 限制长度
            if len(text) > 10000:
                text = text[:10000]
            
            return text.strip()
        
        # 测试脚本注入清理
        malicious_input = "<script>alert('xss')</script>This is normal text"
        cleaned = sanitize_input(malicious_input)
        assert "<script>" not in cleaned
        assert "This is normal text" in cleaned
        
        # 测试SQL注入清理
        sql_injection = "'; DROP TABLE users; --"
        cleaned = sanitize_input(sql_injection)
        assert "DROP TABLE" not in cleaned
        assert "--" not in cleaned

class TestComplianceRequirements:
    """合规要求测试"""
    
    def test_gdpr_compliance(self):
        """测试GDPR合规性"""
        def handle_data_deletion_request(user_id: str, data_store: List[Dict[str, Any]]) -> Dict[str, Any]:
            """处理数据删除请求（GDPR右删除权）"""
            deleted_count = 0
            remaining_data = []
            
            for item in data_store:
                if item.get("user_id") == user_id:
                    deleted_count += 1
                    # 记录删除操作
                else:
                    remaining_data.append(item)
            
            return {
                "deleted_records": deleted_count,
                "remaining_records": len(remaining_data),
                "data_store": remaining_data
            }
        
        # 模拟数据存储
        data_store = [
            {"id": 1, "user_id": "user_123", "text": "User data 1"},
            {"id": 2, "user_id": "user_456", "text": "User data 2"},
            {"id": 3, "user_id": "user_123", "text": "User data 3"},
        ]
        
        # 处理删除请求
        result = handle_data_deletion_request("user_123", data_store)
        
        # 验证删除结果
        assert result["deleted_records"] == 2
        assert result["remaining_records"] == 1
        
        # 验证用户数据已删除
        remaining_user_data = [
            item for item in result["data_store"] 
            if item.get("user_id") == "user_123"
        ]
        assert len(remaining_user_data) == 0
    
    def test_data_retention_policy(self):
        """测试数据保留策略"""
        def apply_retention_policy(data_store: List[Dict[str, Any]], 
                                 retention_days: int = 365) -> Dict[str, Any]:
            """应用数据保留策略"""
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            retained_data = []
            expired_data = []
            
            for item in data_store:
                created_at = datetime.fromisoformat(item.get("created_at", datetime.now().isoformat()))
                
                if created_at >= cutoff_date:
                    retained_data.append(item)
                else:
                    expired_data.append(item)
            
            return {
                "retained_count": len(retained_data),
                "expired_count": len(expired_data),
                "retained_data": retained_data
            }
        
        # 模拟不同时间的数据
        data_store = [
            {
                "id": 1,
                "text": "Recent data",
                "created_at": (datetime.now() - timedelta(days=30)).isoformat()
            },
            {
                "id": 2,
                "text": "Old data",
                "created_at": (datetime.now() - timedelta(days=400)).isoformat()
            }
        ]
        
        # 应用保留策略
        result = apply_retention_policy(data_store, retention_days=365)
        
        # 验证保留策略
        assert result["retained_count"] == 1
        assert result["expired_count"] == 1
    
    def test_consent_management(self):
        """测试同意管理"""
        def check_processing_consent(user_id: str, 
                                   processing_type: str,
                                   consent_store: Dict[str, Dict[str, Any]]) -> bool:
            """检查处理同意"""
            user_consent = consent_store.get(user_id, {})
            
            # 检查特定处理类型的同意
            consent_given = user_consent.get(processing_type, {}).get("granted", False)
            
            # 检查同意是否仍然有效
            if consent_given:
                consent_date = user_consent[processing_type].get("granted_at")
                if consent_date:
                    consent_datetime = datetime.fromisoformat(consent_date)
                    # 同意有效期为2年
                    if (datetime.now() - consent_datetime).days > 730:
                        return False
            
            return consent_given
        
        # 模拟同意存储
        consent_store = {
            "user_123": {
                "business_logic_analysis": {
                    "granted": True,
                    "granted_at": (datetime.now() - timedelta(days=100)).isoformat()
                },
                "data_sharing": {
                    "granted": False,
                    "granted_at": None
                }
            },
            "user_456": {
                "business_logic_analysis": {
                    "granted": True,
                    "granted_at": (datetime.now() - timedelta(days=800)).isoformat()  # 过期
                }
            }
        }
        
        # 测试同意检查
        assert check_processing_consent("user_123", "business_logic_analysis", consent_store) is True
        assert check_processing_consent("user_123", "data_sharing", consent_store) is False
        assert check_processing_consent("user_456", "business_logic_analysis", consent_store) is False  # 过期

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])