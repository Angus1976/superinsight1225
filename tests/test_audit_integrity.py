"""
Tests for Audit Integrity and Anti-tampering System.

Comprehensive test suite for audit log integrity verification,
digital signatures, and tampering detection.
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.security.audit_integrity import AuditIntegrityService, audit_integrity_service
from src.security.audit_service_with_integrity import IntegrityProtectedAuditService
from src.security.models import AuditLogModel, AuditAction
from src.database.connection import get_db_session


class TestAuditIntegrityService:
    """测试审计完整性服务"""
    
    @pytest.fixture
    def integrity_service(self):
        """创建审计完整性服务实例"""
        return AuditIntegrityService()
    
    @pytest.fixture
    def sample_audit_log(self):
        """创建示例审计日志"""
        return AuditLogModel(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id="test_tenant",
            action=AuditAction.READ,
            resource_type="document",
            resource_id="doc_123",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            details={"test": "data"},
            timestamp=datetime.utcnow()
        )
    
    def test_calculate_audit_log_hash(self, integrity_service, sample_audit_log):
        """测试审计日志哈希计算"""
        
        # 计算哈希
        hash1 = integrity_service.calculate_audit_log_hash(sample_audit_log)
        
        # 验证哈希格式
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256哈希长度
        
        # 相同数据应产生相同哈希
        hash2 = integrity_service.calculate_audit_log_hash(sample_audit_log)
        assert hash1 == hash2
        
        # 修改数据应产生不同哈希
        sample_audit_log.details = {"modified": "data"}
        hash3 = integrity_service.calculate_audit_log_hash(sample_audit_log)
        assert hash1 != hash3
    
    def test_calculate_chain_hash(self, integrity_service):
        """测试链式哈希计算"""
        
        current_hash = "abc123"
        previous_hash = "def456"
        
        # 计算链式哈希
        chain_hash1 = integrity_service.calculate_chain_hash(current_hash, previous_hash)
        
        # 验证哈希格式
        assert isinstance(chain_hash1, str)
        assert len(chain_hash1) == 64
        
        # 相同输入应产生相同结果
        chain_hash2 = integrity_service.calculate_chain_hash(current_hash, previous_hash)
        assert chain_hash1 == chain_hash2
        
        # 不同输入应产生不同结果
        chain_hash3 = integrity_service.calculate_chain_hash(current_hash, "different")
        assert chain_hash1 != chain_hash3
    
    def test_sign_audit_log(self, integrity_service, sample_audit_log):
        """测试审计日志数字签名"""
        
        # 生成签名
        integrity_data = integrity_service.sign_audit_log(sample_audit_log)
        
        # 验证签名数据结构
        assert isinstance(integrity_data, dict)
        assert "hash" in integrity_data
        assert "signature" in integrity_data
        assert "algorithm" in integrity_data
        assert "signature_algorithm" in integrity_data
        assert "timestamp" in integrity_data
        
        # 验证哈希
        assert len(integrity_data["hash"]) == 64
        
        # 验证签名
        assert isinstance(integrity_data["signature"], str)
        assert len(integrity_data["signature"]) > 0
        
        # 验证算法信息
        assert integrity_data["algorithm"] == "sha256"
        assert integrity_data["signature_algorithm"] == "RSA-PSS-SHA256"
    
    def test_verify_audit_log_integrity_valid(self, integrity_service, sample_audit_log):
        """测试有效审计日志的完整性验证"""
        
        # 生成签名
        integrity_data = integrity_service.sign_audit_log(sample_audit_log)
        
        # 验证完整性
        verification_result = integrity_service.verify_audit_log_integrity(
            sample_audit_log, integrity_data
        )
        
        # 验证结果
        assert verification_result["is_valid"] is True
        assert verification_result["hash_valid"] is True
        assert verification_result["signature_valid"] is True
        assert verification_result["chain_valid"] is True
        assert len(verification_result["errors"]) == 0
    
    def test_verify_audit_log_integrity_tampered(self, integrity_service, sample_audit_log):
        """测试被篡改审计日志的完整性验证"""
        
        # 生成原始签名
        integrity_data = integrity_service.sign_audit_log(sample_audit_log)
        
        # 篡改审计日志
        sample_audit_log.details = {"tampered": "data"}
        
        # 验证完整性
        verification_result = integrity_service.verify_audit_log_integrity(
            sample_audit_log, integrity_data
        )
        
        # 验证结果
        assert verification_result["is_valid"] is False
        assert verification_result["hash_valid"] is False
        assert len(verification_result["errors"]) > 0
    
    def test_batch_verify_integrity(self, integrity_service):
        """测试批量完整性验证"""
        
        # 创建多个审计日志
        audit_logs = []
        for i in range(5):
            log = AuditLogModel(
                id=uuid4(),
                user_id=uuid4(),
                tenant_id="test_tenant",
                action=AuditAction.READ,
                resource_type="document",
                resource_id=f"doc_{i}",
                details={},
                timestamp=datetime.utcnow()
            )
            
            # 为前3个日志添加真实的完整性数据
            if i < 3:
                integrity_data = integrity_service.sign_audit_log(log)
                log.details["integrity"] = integrity_data
            
            audit_logs.append(log)
        
        # 模拟数据库会话
        mock_db = Mock()
        
        # 批量验证
        batch_result = integrity_service.batch_verify_integrity(audit_logs, mock_db)
        
        # 验证结果
        assert batch_result["total_logs"] == 5
        assert batch_result["valid_logs"] == 3
        assert batch_result["invalid_logs"] == 2
        assert batch_result["integrity_score"] == 60.0  # 3/5 * 100
    
    def test_detect_tampering_patterns(self, integrity_service):
        """测试篡改模式检测"""
        
        # 创建测试数据
        tenant_id = "test_tenant"
        
        # 模拟数据库查询
        mock_db = Mock()
        mock_audit_logs = []
        
        # 创建正常日志
        for i in range(10):
            log = AuditLogModel(
                id=uuid4(),
                user_id=uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.READ,
                resource_type="document",
                resource_id=f"doc_{i}",
                details={"integrity": {"hash": "test_hash", "signature": "test_sig"}},
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            mock_audit_logs.append(log)
        
        # 添加可疑的批量删除
        user_id = uuid4()
        for i in range(15):
            log = AuditLogModel(
                id=uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                action=AuditAction.DELETE,
                resource_type="document",
                resource_id=f"deleted_doc_{i}",
                details={},
                timestamp=datetime.utcnow() - timedelta(minutes=30)
            )
            mock_audit_logs.append(log)
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_audit_logs
        
        with patch.object(integrity_service, 'batch_verify_integrity') as mock_batch_verify:
            mock_batch_verify.return_value = {
                "total_logs": len(mock_audit_logs),
                "valid_logs": 20,
                "invalid_logs": 5,
                "integrity_score": 80.0,
                "verification_details": []
            }
            
            # 检测篡改模式
            detection_result = integrity_service.detect_tampering_patterns(tenant_id, mock_db, 30)
        
        # 验证结果
        assert detection_result["tenant_id"] == tenant_id
        assert detection_result["total_logs_analyzed"] == len(mock_audit_logs)
        assert len(detection_result["suspicious_patterns"]) > 0
        
        # 应该检测到批量删除模式
        bulk_deletion_detected = any(
            pattern["type"] == "bulk_deletion_pattern" 
            for pattern in detection_result["suspicious_patterns"]
        )
        assert bulk_deletion_detected
    
    def test_generate_integrity_report(self, integrity_service):
        """测试完整性报告生成"""
        
        tenant_id = "test_tenant"
        mock_db = Mock()
        
        with patch.object(integrity_service, 'detect_tampering_patterns') as mock_detect:
            mock_detect.return_value = {
                "tenant_id": tenant_id,
                "total_logs_analyzed": 100,
                "integrity_violations": [],
                "suspicious_patterns": [],
                "overall_risk_level": "low",
                "risk_score": 10
            }
            
            # 生成报告
            report = integrity_service.generate_integrity_report(tenant_id, mock_db, 30)
        
        # 验证报告结构
        assert "report_metadata" in report
        assert "executive_summary" in report
        assert "detailed_analysis" in report
        assert "recommendations" in report
        assert "compliance_status" in report
        
        # 验证元数据
        assert report["report_metadata"]["tenant_id"] == tenant_id
        assert report["report_metadata"]["report_type"] == "audit_integrity_report"
        
        # 验证执行摘要
        assert report["executive_summary"]["total_logs_analyzed"] == 100
        assert report["executive_summary"]["risk_level"] == "low"


class TestIntegrityProtectedAuditService:
    """测试完整性保护审计服务"""
    
    @pytest.fixture
    def audit_service(self):
        """创建完整性保护审计服务实例"""
        return IntegrityProtectedAuditService()
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = Mock(spec=Session)
        db.commit = Mock()
        db.rollback = Mock()
        db.execute = Mock()
        return db
    
    @pytest.mark.asyncio
    async def test_log_audit_event_with_integrity(self, audit_service, mock_db):
        """测试记录具有完整性保护的审计事件"""
        
        # 模拟基础审计服务返回
        mock_base_result = {
            "status": "success",
            "audit_log_id": uuid4()
        }
        
        # 创建模拟审计日志
        mock_audit_log = AuditLogModel(
            id=mock_base_result["audit_log_id"],
            user_id=uuid4(),
            tenant_id="test_tenant",
            action=AuditAction.CREATE,
            resource_type="document",
            resource_id="doc_123",
            details={},
            timestamp=datetime.utcnow()
        )
        
        # 模拟数据库查询
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_audit_log
        
        with patch.object(audit_service, 'log_enhanced_audit_event') as mock_log_enhanced:
            mock_log_enhanced.return_value = mock_base_result
            
            # 记录审计事件
            result = await audit_service.log_audit_event_with_integrity(
                user_id=uuid4(),
                tenant_id="test_tenant",
                action=AuditAction.CREATE,
                resource_type="document",
                resource_id="doc_123",
                db=mock_db
            )
        
        # 验证结果
        assert result["status"] == "success"
        assert result["integrity_protected"] is True
        assert "integrity_data" in result
        
        # 验证完整性数据结构
        integrity_data = result["integrity_data"]
        assert "hash" in integrity_data
        assert "signature" in integrity_data
        assert "algorithm" in integrity_data
    
    def test_verify_audit_log_integrity(self, audit_service, mock_db):
        """测试验证审计日志完整性"""
        
        audit_log_id = uuid4()
        
        # 创建模拟审计日志
        mock_audit_log = AuditLogModel(
            id=audit_log_id,
            user_id=uuid4(),
            tenant_id="test_tenant",
            action=AuditAction.READ,
            resource_type="document",
            details={
                "integrity": {
                    "hash": "test_hash",
                    "signature": "test_signature",
                    "algorithm": "sha256"
                }
            },
            timestamp=datetime.utcnow()
        )
        
        # 模拟数据库查询
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_audit_log
        
        # 模拟完整性验证结果
        mock_verification = {
            "is_valid": True,
            "hash_valid": True,
            "signature_valid": True,
            "chain_valid": True,
            "errors": [],
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        with patch.object(audit_service.integrity_service, 'verify_audit_log_integrity') as mock_verify:
            mock_verify.return_value = mock_verification
            
            # 验证完整性
            result = audit_service.verify_audit_log_integrity(audit_log_id, mock_db)
        
        # 验证结果
        assert result["status"] == "success"
        assert result["audit_log_id"] == str(audit_log_id)
        assert result["verification_result"]["is_valid"] is True
    
    def test_batch_verify_tenant_integrity(self, audit_service, mock_db):
        """测试批量验证租户完整性"""
        
        tenant_id = "test_tenant"
        
        # 创建模拟审计日志列表
        mock_audit_logs = [
            AuditLogModel(
                id=uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.READ,
                resource_type="document",
                details={},
                timestamp=datetime.utcnow()
            )
            for _ in range(5)
        ]
        
        # 模拟数据库查询
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_audit_logs
        
        # 模拟批量验证结果
        mock_batch_result = {
            "total_logs": 5,
            "valid_logs": 4,
            "invalid_logs": 1,
            "integrity_score": 80.0,
            "verification_timestamp": datetime.utcnow().isoformat()
        }
        
        with patch.object(audit_service.integrity_service, 'batch_verify_integrity') as mock_batch:
            mock_batch.return_value = mock_batch_result
            
            # 批量验证
            result = audit_service.batch_verify_tenant_integrity(tenant_id, mock_db, 30)
        
        # 验证结果
        assert result["status"] == "success"
        assert result["tenant_id"] == tenant_id
        assert result["total_logs"] == 5
        assert result["verification_result"]["integrity_score"] == 80.0
    
    def test_detect_audit_tampering(self, audit_service, mock_db):
        """测试检测审计篡改"""
        
        tenant_id = "test_tenant"
        
        # 模拟篡改检测结果
        mock_detection_result = {
            "tenant_id": tenant_id,
            "total_logs_analyzed": 100,
            "integrity_violations": [],
            "suspicious_patterns": [
                {
                    "type": "bulk_deletion_pattern",
                    "severity": "high",
                    "description": "检测到批量删除"
                }
            ],
            "overall_risk_level": "medium",
            "risk_score": 45,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        with patch.object(audit_service.integrity_service, 'detect_tampering_patterns') as mock_detect:
            mock_detect.return_value = mock_detection_result
            
            # 检测篡改
            result = audit_service.detect_audit_tampering(tenant_id, mock_db, 30)
        
        # 验证结果
        assert result["status"] == "success"
        assert result["detection_result"]["overall_risk_level"] == "medium"
        assert len(result["detection_result"]["suspicious_patterns"]) == 1
    
    def test_repair_integrity_violations(self, audit_service, mock_db):
        """测试修复完整性违规"""
        
        tenant_id = "test_tenant"
        
        # 创建需要修复的审计日志
        mock_audit_logs = [
            AuditLogModel(
                id=uuid4(),
                tenant_id=tenant_id,
                action=AuditAction.READ,
                resource_type="document",
                details={},  # 缺少完整性数据
                timestamp=datetime.utcnow()
            )
            for _ in range(3)
        ]
        
        # 模拟数据库查询
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_audit_logs
        
        # 模拟签名生成
        mock_integrity_data = {
            "hash": "new_hash",
            "signature": "new_signature",
            "algorithm": "sha256"
        }
        
        with patch.object(audit_service.integrity_service, 'sign_audit_log') as mock_sign:
            mock_sign.return_value = mock_integrity_data
            
            # 修复违规
            result = audit_service.repair_integrity_violations(tenant_id, mock_db)
        
        # 验证结果
        assert result["status"] == "success"
        assert result["tenant_id"] == tenant_id
        assert result["total_processed"] == 3
        assert len(result["repaired_logs"]) == 3
        assert len(result["failed_repairs"]) == 0
    
    def test_get_integrity_statistics(self, audit_service, mock_db):
        """测试获取完整性统计"""
        
        tenant_id = "test_tenant"
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar.side_effect = [100, 85]  # 总数和保护数
        
        # 模拟篡改检测结果
        mock_detection_result = {
            "status": "success",
            "detection_result": {
                "overall_risk_level": "low",
                "integrity_violations": [],
                "suspicious_patterns": [],
                "risk_score": 15
            }
        }
        
        with patch.object(audit_service, 'detect_audit_tampering') as mock_detect:
            mock_detect.return_value = mock_detection_result
            
            # 获取统计信息
            result = audit_service.get_integrity_statistics(tenant_id, mock_db, 30)
        
        # 验证结果
        assert result["status"] == "success"
        statistics = result["statistics"]
        assert statistics["tenant_id"] == tenant_id
        assert statistics["total_audit_logs"] == 100
        assert statistics["protected_logs"] == 85
        assert statistics["unprotected_logs"] == 15
        assert statistics["protection_rate_percent"] == 85.0
        assert statistics["integrity_status"] == "needs_attention"  # < 95%
        assert statistics["tampering_risk_level"] == "low"


class TestAuditIntegrityAPI:
    """测试审计完整性API"""
    
    def test_integrity_service_initialization(self):
        """测试完整性服务初始化"""
        
        # 验证全局服务实例
        assert audit_integrity_service is not None
        assert hasattr(audit_integrity_service, 'private_key')
        assert hasattr(audit_integrity_service, 'public_key')
        assert audit_integrity_service.hash_algorithm == "sha256"
        assert audit_integrity_service.chain_hash_enabled is True
    
    def test_key_generation_and_loading(self):
        """测试密钥生成和加载"""
        
        # 创建新的服务实例（应该生成新密钥）
        service = AuditIntegrityService()
        
        # 验证密钥存在
        assert service.private_key is not None
        assert service.public_key is not None
        
        # 验证密钥类型
        from cryptography.hazmat.primitives.asymmetric import rsa
        assert isinstance(service.private_key, rsa.RSAPrivateKey)
        assert isinstance(service.public_key, rsa.RSAPublicKey)
    
    def test_hash_consistency(self):
        """测试哈希一致性"""
        
        service = AuditIntegrityService()
        
        # 创建测试数据
        test_data = {
            "id": "test_id",
            "action": "read",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        # 多次计算应得到相同结果
        from src.utils.encryption import hash_data
        hash1 = hash_data(json.dumps(test_data, sort_keys=True), "sha256")
        hash2 = hash_data(json.dumps(test_data, sort_keys=True), "sha256")
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256长度
    
    def test_signature_verification_cycle(self):
        """测试签名验证周期"""
        
        service = AuditIntegrityService()
        
        # 创建测试审计日志
        audit_log = AuditLogModel(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id="test_tenant",
            action=AuditAction.CREATE,
            resource_type="test_resource",
            details={"test": "data"},
            timestamp=datetime.utcnow()
        )
        
        # 生成签名
        integrity_data = service.sign_audit_log(audit_log)
        
        # 验证签名
        verification_result = service.verify_audit_log_integrity(audit_log, integrity_data)
        
        # 应该验证成功
        assert verification_result["is_valid"] is True
        assert verification_result["hash_valid"] is True
        assert verification_result["signature_valid"] is True
        
        # 篡改数据后验证应该失败
        audit_log.details = {"tampered": "data"}
        verification_result_tampered = service.verify_audit_log_integrity(audit_log, integrity_data)
        
        assert verification_result_tampered["is_valid"] is False
        assert verification_result_tampered["hash_valid"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])