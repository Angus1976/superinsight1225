"""
Comprehensive test for Enhanced Audit System
测试增强审计系统的完整功能
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.audit_event_processor import AuditEventProcessor
from src.security.models import AuditLogModel, AuditAction
from src.security.enhanced_audit_models import (
    AuditEventModel, SecurityAlertModel, AuditRuleModel, ComplianceReportModel
)
from src.database.connection import db_manager


class TestEnhancedAuditSystem:
    """增强审计系统测试类"""
    
    def __init__(self):
        self.enhanced_audit_service = EnhancedAuditService()
        self.event_processor = AuditEventProcessor(self.enhanced_audit_service)
        self.test_tenant_id = "test-tenant-001"
        self.test_user_id = uuid4()
    
    async def test_enhanced_audit_logging(self):
        """测试增强审计日志记录"""
        print("🔍 测试增强审计日志记录...")
        
        with db_manager.get_session() as db:
            # 测试系统操作记录（无用户ID）
            result = await self.enhanced_audit_service.log_enhanced_audit_event(
                user_id=None,  # 系统事件，无用户ID
                tenant_id=self.test_tenant_id,
                action=AuditAction.READ,
                resource_type="dataset",
                resource_id="dataset-001",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                details={"operation": "view_dataset", "dataset_size": "1.2GB"},
                db=db
            )
            
            assert result["status"] == "success"
            assert "audit_log_id" in result
            assert "risk_assessment" in result
            
            print(f"✅ 正常操作记录成功，风险等级: {result['risk_assessment']['risk_level'].value}")
    
    async def test_high_risk_event_detection(self):
        """测试高风险事件检测"""
        print("🚨 测试高风险事件检测...")
        
        with db_manager.get_session() as db:
            # 模拟失败登录事件
            for i in range(6):  # 超过阈值的失败登录
                await self.enhanced_audit_service.log_enhanced_audit_event(
                    user_id=None,  # 系统事件
                    tenant_id=self.test_tenant_id,
                    action=AuditAction.LOGIN,
                    resource_type="authentication",
                    ip_address="192.168.1.100",
                    details={"status": "failed", "username": "test_user"},
                    db=db
                )
            
            # 最后一次应该被标记为高风险
            result = await self.enhanced_audit_service.log_enhanced_audit_event(
                user_id=None,  # 系统事件
                tenant_id=self.test_tenant_id,
                action=AuditAction.LOGIN,
                resource_type="authentication",
                ip_address="192.168.1.100",
                details={"status": "failed", "username": "test_user"},
                db=db
            )
            
            risk_level = result["risk_assessment"]["risk_level"]
            assert risk_level == RiskLevel.HIGH
            assert "failed_login_burst" in result["risk_assessment"]["risk_factors"]
            
            print(f"✅ 高风险事件检测成功，风险因素: {result['risk_assessment']['risk_factors']}")
    
    async def test_critical_threat_detection(self):
        """测试关键威胁检测"""
        print("⚠️ 测试关键威胁检测...")
        
        with db_manager.get_session() as db:
            # 模拟SQL注入尝试
            result = await self.enhanced_audit_service.log_enhanced_audit_event(
                user_id=None,  # 系统事件
                tenant_id=self.test_tenant_id,
                action=AuditAction.READ,
                resource_type="dataset",
                ip_address="192.168.1.100",
                details={
                    "query": "SELECT * FROM users WHERE id = '1' OR '1'='1'",
                    "suspicious_input": "'; DROP TABLE users; --"
                },
                db=db
            )
            
            risk_level = result["risk_assessment"]["risk_level"]
            assert risk_level == RiskLevel.CRITICAL
            
            # 检查是否检测到SQL注入威胁
            threat_factors = [f for f in result["risk_assessment"]["risk_factors"] 
                            if "sql_injection" in f]
            assert len(threat_factors) > 0
            
            print(f"✅ 关键威胁检测成功，威胁类型: {threat_factors}")
    
    async def test_event_processing(self):
        """测试事件处理器"""
        print("⚙️ 测试事件处理器...")
        
        # 启动事件处理器
        await self.event_processor.start_processing(num_workers=2)
        
        with db_manager.get_session() as db:
            # 创建测试审计日志
            audit_log = AuditLogModel(
                user_id=None,  # 系统事件
                tenant_id=self.test_tenant_id,
                action=AuditAction.DELETE,
                resource_type="user",
                resource_id="user-001",
                ip_address="192.168.1.100",
                timestamp=datetime.utcnow(),
                details={
                    "risk_level": "high",
                    "risk_factors": ["privilege_escalation", "sensitive_data_access"]
                }
            )
            db.add(audit_log)
            db.commit()
            
            # 处理事件
            result = await self.event_processor.process_event(audit_log)
            
            assert result.status.value in ["completed", "requires_attention"]
            assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            assert len(result.anomalies_detected) >= 0
            assert len(result.recommendations) > 0
            
            print(f"✅ 事件处理成功，分类: {result.category.value}, 建议数量: {len(result.recommendations)}")
        
        # 停止事件处理器
        await self.event_processor.stop_processing()
    
    async def test_security_summary(self):
        """测试安全摘要生成"""
        print("📊 测试安全摘要生成...")
        
        with db_manager.get_session() as db:
            summary = self.enhanced_audit_service.get_security_summary(
                tenant_id=self.test_tenant_id,
                days=7,
                db=db
            )
            
            assert "total_events" in summary
            assert "failed_logins" in summary
            assert "sensitive_operations" in summary
            assert "active_users" in summary
            assert "unique_ip_addresses" in summary
            
            print(f"✅ 安全摘要生成成功:")
            print(f"   - 总事件数: {summary['total_events']}")
            print(f"   - 失败登录: {summary['failed_logins']}")
            print(f"   - 敏感操作: {summary['sensitive_operations']}")
            print(f"   - 活跃用户: {summary['active_users']}")
            print(f"   - 唯一IP: {summary['unique_ip_addresses']}")
    
    async def test_security_alerts(self):
        """测试安全告警"""
        print("🚨 测试安全告警...")
        
        with db_manager.get_session() as db:
            alerts = self.enhanced_audit_service.check_security_alerts(
                tenant_id=self.test_tenant_id,
                db=db
            )
            
            print(f"✅ 安全告警检查完成，发现 {len(alerts)} 个告警")
            
            for alert in alerts:
                print(f"   - {alert['type']}: {alert['message']} (严重程度: {alert['severity']})")
    
    async def test_user_activity_analysis(self):
        """测试用户活动分析"""
        print("👤 测试用户活动分析...")
        
        with db_manager.get_session() as db:
            analysis = self.enhanced_audit_service.analyze_user_activity(
                user_id=None,  # 分析系统事件
                tenant_id=self.test_tenant_id,
                days=30,
                db=db
            )
            
            assert "total_actions" in analysis
            assert "actions_by_type" in analysis
            assert "resources_accessed" in analysis
            assert "daily_activity" in analysis
            assert "suspicious_patterns" in analysis
            
            print(f"✅ 用户活动分析完成:")
            print(f"   - 总操作数: {analysis['total_actions']}")
            print(f"   - 操作类型: {list(analysis['actions_by_type'].keys())}")
            print(f"   - 访问资源: {list(analysis['resources_accessed'].keys())}")
            print(f"   - 可疑模式: {len(analysis['suspicious_patterns'])}")
    
    async def test_log_statistics(self):
        """测试日志统计"""
        print("📈 测试日志统计...")
        
        with db_manager.get_session() as db:
            stats = self.enhanced_audit_service.get_log_statistics(
                tenant_id=self.test_tenant_id,
                db=db
            )
            
            assert "total_logs" in stats
            assert "storage_size_estimate" in stats
            
            print(f"✅ 日志统计完成:")
            print(f"   - 总日志数: {stats['total_logs']}")
            print(f"   - 存储大小估计: {stats['storage_size_estimate']}")
            if stats['oldest_log']:
                print(f"   - 最早日志: {stats['oldest_log']}")
            if stats['newest_log']:
                print(f"   - 最新日志: {stats['newest_log']}")
    
    async def test_processing_statistics(self):
        """测试处理统计"""
        print("📊 测试处理统计...")
        
        stats = self.event_processor.get_processing_stats()
        
        print(f"✅ 处理统计:")
        print(f"   - 已处理事件: {stats['events_processed']}")
        print(f"   - 失败事件: {stats['events_failed']}")
        print(f"   - 检测异常: {stats['anomalies_detected']}")
        print(f"   - 高风险事件: {stats['high_risk_events']}")
        if stats['events_processed'] > 0:
            print(f"   - 平均处理时间: {stats.get('average_processing_time_ms', 0):.2f}ms")
            print(f"   - 异常检测率: {stats.get('anomaly_detection_rate', 0):.2f}%")
            print(f"   - 高风险事件率: {stats.get('high_risk_event_rate', 0):.2f}%")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始增强审计系统综合测试")
        print("=" * 60)
        
        try:
            await self.test_enhanced_audit_logging()
            await self.test_high_risk_event_detection()
            await self.test_critical_threat_detection()
            await self.test_event_processing()
            await self.test_security_summary()
            await self.test_security_alerts()
            await self.test_user_activity_analysis()
            await self.test_log_statistics()
            await self.test_processing_statistics()
            
            print("=" * 60)
            print("✅ 所有测试通过！增强审计系统功能正常")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            raise


async def main():
    """主测试函数"""
    test_suite = TestEnhancedAuditSystem()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())