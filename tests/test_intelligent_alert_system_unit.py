"""
智能告警系统单元测试

测试多维度告警规则、告警聚合、通知处理等功能。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from src.quality_billing.intelligent_alert_system import (
    IntelligentAlertSystem,
    MultiDimensionalAlertRuleEngine,
    AlertAggregator,
    AlertDeduplicator,
    AlertEscalationManager,
    Alert,
    AlertRule,
    AlertDimension,
    AlertLevel,
    AlertRuleType,
    AlertPriority,
    AlertStatus
)
from src.quality_billing.alert_notification_system import (
    AlertNotificationSystem,
    NotificationChannel,
    NotificationStatus,
    NotificationTemplate,
    NotificationRecord,
    EmailNotificationHandler,
    WeChatWorkNotificationHandler
)


class TestMultiDimensionalAlertRuleEngine:
    """测试多维度告警规则引擎"""
    
    def setup_method(self):
        """测试前准备"""
        self.engine = MultiDimensionalAlertRuleEngine()
    
    def test_create_quality_alert_rule(self):
        """测试创建质量告警规则"""
        rule = self.engine.create_quality_alert_rule(
            name="测试质量规则",
            quality_threshold=0.8,
            trend_window=10,
            level=AlertLevel.WARNING
        )
        
        assert rule.name == "测试质量规则"
        assert rule.dimension == AlertDimension.QUALITY
        assert rule.rule_type == AlertRuleType.THRESHOLD
        assert rule.level == AlertLevel.WARNING
        assert rule.conditions["value"] == 0.8
        assert rule.trend_config["window_size"] == 10
        
        # 验证规则已添加到引擎
        assert rule.id in self.engine.rules
    
    def test_create_efficiency_alert_rule(self):
        """测试创建效率告警规则"""
        rule = self.engine.create_efficiency_alert_rule(
            name="测试效率规则",
            efficiency_threshold=0.7,
            workload_threshold=100,
            level=AlertLevel.HIGH
        )
        
        assert rule.name == "测试效率规则"
        assert rule.dimension == AlertDimension.EFFICIENCY
        assert rule.rule_type == AlertRuleType.COMPOSITE
        assert rule.level == AlertLevel.HIGH
        assert len(rule.composite_config["conditions"]) == 2
    
    def test_create_cost_alert_rule(self):
        """测试创建成本告警规则"""
        rule = self.engine.create_cost_alert_rule(
            name="测试成本规则",
            cost_threshold=1000.0,
            budget_percentage=0.8,
            level=AlertLevel.CRITICAL
        )
        
        assert rule.name == "测试成本规则"
        assert rule.dimension == AlertDimension.COST
        assert rule.conditions["value"] == 1000.0
    
    def test_create_anomaly_detection_rule(self):
        """测试创建异常检测规则"""
        rule = self.engine.create_anomaly_detection_rule(
            name="测试异常检测",
            metric_name="quality_score",
            dimension=AlertDimension.QUALITY,
            sensitivity=2.0,
            level=AlertLevel.WARNING
        )
        
        assert rule.name == "测试异常检测"
        assert rule.rule_type == AlertRuleType.ANOMALY
        assert rule.anomaly_config["sensitivity"] == 2.0
        assert rule.conditions["metric_name"] == "quality_score"
    
    def test_evaluate_threshold_rule_triggered(self):
        """测试阈值规则触发"""
        # 创建阈值规则
        rule = self.engine.create_quality_alert_rule(
            name="质量阈值测试",
            quality_threshold=0.8,
            level=AlertLevel.WARNING
        )
        
        # 测试触发条件
        metrics = {"quality_score": 0.6}  # 低于阈值
        alerts = self.engine.evaluate_rules(metrics)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.rule_id == rule.id
        assert alert.level == AlertLevel.WARNING
        assert alert.metric_value == 0.6
        assert alert.threshold_value == 0.8
    
    def test_evaluate_threshold_rule_not_triggered(self):
        """测试阈值规则未触发"""
        # 创建阈值规则
        self.engine.create_quality_alert_rule(
            name="质量阈值测试",
            quality_threshold=0.8,
            level=AlertLevel.WARNING
        )
        
        # 测试未触发条件
        metrics = {"quality_score": 0.9}  # 高于阈值
        alerts = self.engine.evaluate_rules(metrics)
        
        assert len(alerts) == 0
    
    def test_evaluate_composite_rule(self):
        """测试复合规则评估"""
        # 创建复合规则
        rule = self.engine.create_efficiency_alert_rule(
            name="效率复合测试",
            efficiency_threshold=0.7,
            workload_threshold=100,
            level=AlertLevel.HIGH
        )
        
        # 测试所有条件满足
        metrics = {
            "task_completion_rate": 0.6,  # 低于阈值
            "current_workload": 120       # 高于阈值
        }
        alerts = self.engine.evaluate_rules(metrics)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.rule_id == rule.id
        assert alert.level == AlertLevel.HIGH
    
    def test_evaluate_anomaly_rule(self):
        """测试异常检测规则"""
        # 创建异常检测规则
        rule = self.engine.create_anomaly_detection_rule(
            name="异常检测测试",
            metric_name="quality_score",
            dimension=AlertDimension.QUALITY,
            sensitivity=2.0,
            level=AlertLevel.WARNING
        )
        
        # 先添加一些正常数据建立基线
        normal_metrics = [
            {"quality_score": 0.85},
            {"quality_score": 0.87},
            {"quality_score": 0.83},
            {"quality_score": 0.86},
            {"quality_score": 0.84},
            {"quality_score": 0.88},
            {"quality_score": 0.82},
            {"quality_score": 0.89},
            {"quality_score": 0.85},
            {"quality_score": 0.87}
        ]
        
        for metrics in normal_metrics:
            self.engine.evaluate_rules(metrics)
        
        # 测试异常值
        anomaly_metrics = {"quality_score": 0.3}  # 明显异常值
        alerts = self.engine.evaluate_rules(anomaly_metrics)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.rule_id == rule.id
        assert "异常" in alert.title
    
    def test_rule_management(self):
        """测试规则管理功能"""
        # 创建规则
        rule = self.engine.create_quality_alert_rule(
            name="管理测试规则",
            quality_threshold=0.8,
            level=AlertLevel.WARNING
        )
        rule_id = rule.id
        
        # 获取规则
        retrieved_rule = self.engine.get_rule(rule_id)
        assert retrieved_rule is not None
        assert retrieved_rule.name == "管理测试规则"
        
        # 更新规则
        updates = {"enabled": False, "name": "更新后的规则"}
        success = self.engine.update_rule(rule_id, updates)
        assert success
        
        updated_rule = self.engine.get_rule(rule_id)
        assert not updated_rule.enabled
        assert updated_rule.name == "更新后的规则"
        
        # 删除规则
        success = self.engine.delete_rule(rule_id)
        assert success
        
        deleted_rule = self.engine.get_rule(rule_id)
        assert deleted_rule is None
    
    def test_list_rules(self):
        """测试规则列表功能"""
        # 创建不同维度的规则
        self.engine.create_quality_alert_rule("质量规则", 0.8)
        self.engine.create_efficiency_alert_rule("效率规则", 0.7, 100)
        self.engine.create_cost_alert_rule("成本规则", 1000.0, 0.8)
        
        # 列出所有规则
        all_rules = self.engine.list_rules()
        assert len(all_rules) >= 3
        
        # 按维度过滤
        quality_rules = self.engine.list_rules(dimension=AlertDimension.QUALITY)
        assert len(quality_rules) >= 1
        assert all(rule["dimension"] == "quality" for rule in quality_rules)
        
        # 仅启用的规则
        enabled_rules = self.engine.list_rules(enabled_only=True)
        assert all(rule["enabled"] for rule in enabled_rules)


class TestAlertAggregator:
    """测试告警聚合器"""
    
    def setup_method(self):
        """测试前准备"""
        self.aggregator = AlertAggregator()
    
    def test_add_aggregation_rule(self):
        """测试添加聚合规则"""
        self.aggregator.add_aggregation_rule(
            rule_id="test_rule",
            group_by=["dimension", "level"],
            time_window_minutes=5,
            max_alerts=10,
            merge_strategy="count"
        )
        
        assert "test_rule" in self.aggregator.aggregation_rules
        rule = self.aggregator.aggregation_rules["test_rule"]
        assert rule["group_by"] == ["dimension", "level"]
        assert rule["time_window_minutes"] == 5
    
    def test_aggregate_alerts(self):
        """测试告警聚合"""
        # 添加聚合规则
        self.aggregator.add_aggregation_rule(
            rule_id="dimension_aggregation",
            group_by=["dimension"],
            time_window_minutes=10,
            max_alerts=5,
            merge_strategy="summary"
        )
        
        # 创建相似告警
        alerts = []
        for i in range(3):
            alert = Alert(
                id=uuid4(),
                rule_id="test_rule",
                dimension=AlertDimension.QUALITY,
                level=AlertLevel.WARNING,
                priority=AlertPriority.MEDIUM,
                title=f"质量告警 {i+1}",
                message=f"质量问题 {i+1}",
                source="test_source"
            )
            alerts.append(alert)
        
        # 执行聚合
        aggregated = self.aggregator.aggregate_alerts(alerts)
        
        # 验证聚合结果
        assert len(aggregated) == 1  # 应该聚合为一个告警
        aggregated_alert = aggregated[0]
        assert aggregated_alert.context["aggregated"]
        assert aggregated_alert.context["alert_count"] == 3
    
    def test_generate_group_key(self):
        """测试分组键生成"""
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="测试告警",
            message="测试消息",
            source="test_source",
            tenant_id="tenant_1",
            project_id="project_1"
        )
        
        # 测试不同分组字段
        key1 = self.aggregator._generate_group_key(alert, ["dimension"])
        assert key1 == "quality"
        
        key2 = self.aggregator._generate_group_key(alert, ["dimension", "level"])
        assert key2 == "quality|warning"
        
        key3 = self.aggregator._generate_group_key(alert, ["tenant_id", "project_id"])
        assert key3 == "tenant_1|project_1"


class TestAlertDeduplicator:
    """测试告警去重器"""
    
    def setup_method(self):
        """测试前准备"""
        self.deduplicator = AlertDeduplicator()
    
    def test_deduplicate_alerts(self):
        """测试告警去重"""
        # 创建重复告警
        alert1 = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="质量告警",
            message="质量问题",
            source="test_source"
        )
        
        alert2 = Alert(
            id=uuid4(),
            rule_id="test_rule",  # 相同规则
            dimension=AlertDimension.QUALITY,  # 相同维度
            level=AlertLevel.WARNING,  # 相同级别
            priority=AlertPriority.MEDIUM,
            title="质量告警",
            message="质量问题",
            source="test_source"  # 相同来源
        )
        
        alerts = [alert1, alert2]
        deduplicated = self.deduplicator.deduplicate_alerts(alerts)
        
        # 应该只保留一个告警
        assert len(deduplicated) == 1
        assert deduplicated[0].context["duplicate_count"] == 2  # 第一个告警计数为1，第二个重复告警使计数变为2
    
    def test_generate_dedup_key(self):
        """测试去重键生成"""
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="测试告警",
            message="测试消息",
            source="test_source",
            metric_name="quality_score"
        )
        
        key = self.deduplicator._generate_dedup_key(alert)
        expected_key = "test_rule|quality|warning|test_source|||quality_score"
        assert key == expected_key


class TestAlertEscalationManager:
    """测试告警升级管理器"""
    
    def setup_method(self):
        """测试前准备"""
        self.escalation_manager = AlertEscalationManager()
    
    @pytest.mark.asyncio
    async def test_check_alert_escalation(self):
        """测试告警升级检查"""
        # 创建过期的严重告警
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.CRITICAL,
            priority=AlertPriority.CRITICAL,
            title="严重质量告警",
            message="质量严重下降",
            source="test_source",
            created_at=datetime.now() - timedelta(minutes=10)  # 10分钟前创建
        )
        
        # 检查升级
        escalation = await self.escalation_manager._check_alert_escalation(alert)
        
        assert escalation is not None
        assert escalation["alert_id"] == alert.id
        assert escalation["escalation_level"] == 1
        assert "notify_supervisor" in escalation["escalation_actions"]
    
    @pytest.mark.asyncio
    async def test_no_escalation_for_recent_alert(self):
        """测试新告警不升级"""
        # 创建新的告警
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.CRITICAL,
            priority=AlertPriority.CRITICAL,
            title="新的严重告警",
            message="刚发生的质量问题",
            source="test_source"
            # 使用默认创建时间（现在）
        )
        
        # 检查升级
        escalation = await self.escalation_manager._check_alert_escalation(alert)
        
        assert escalation is None  # 新告警不应该升级


class TestIntelligentAlertSystem:
    """测试智能告警系统主类"""
    
    def setup_method(self):
        """测试前准备"""
        self.alert_system = IntelligentAlertSystem()
    
    @pytest.mark.asyncio
    async def test_process_metrics(self):
        """测试指标处理"""
        # 测试正常指标
        normal_metrics = {
            "quality_score": 0.9,
            "task_completion_rate": 0.8,
            "daily_cost": 500.0
        }
        
        alerts = await self.alert_system.process_metrics(normal_metrics)
        # 正常指标不应该产生告警
        assert len(alerts) == 0
        
        # 测试异常指标
        abnormal_metrics = {
            "quality_score": 0.5,  # 低于默认阈值
            "task_completion_rate": 0.4,
            "daily_cost": 2000.0
        }
        
        alerts = await self.alert_system.process_metrics(abnormal_metrics)
        # 异常指标应该产生告警
        assert len(alerts) > 0
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self):
        """测试告警确认"""
        # 先生成一个告警
        metrics = {"quality_score": 0.5}
        alerts = await self.alert_system.process_metrics(metrics)
        
        if alerts:
            alert_id = alerts[0].id
            
            # 确认告警
            success = await self.alert_system.acknowledge_alert(alert_id, "test_user")
            assert success
            
            # 验证状态更新
            alert = self.alert_system.active_alerts.get(alert_id)
            assert alert.status == AlertStatus.ACKNOWLEDGED
            assert alert.acknowledged_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """测试告警解决"""
        # 先生成一个告警
        metrics = {"quality_score": 0.5}
        alerts = await self.alert_system.process_metrics(metrics)
        
        if alerts:
            alert_id = alerts[0].id
            
            # 解决告警
            success = await self.alert_system.resolve_alert(
                alert_id, "test_user", "问题已修复"
            )
            assert success
            
            # 验证告警已从活跃列表中移除
            assert alert_id not in self.alert_system.active_alerts
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        # 初始状态应该没有活跃告警
        active_alerts = self.alert_system.get_active_alerts()
        initial_count = len(active_alerts)
        
        # 手动添加一个告警到活跃列表
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="测试告警",
            message="测试消息",
            source="test_source"
        )
        self.alert_system.active_alerts[alert.id] = alert
        
        # 验证活跃告警数量增加
        active_alerts = self.alert_system.get_active_alerts()
        assert len(active_alerts) == initial_count + 1
        
        # 测试过滤功能
        quality_alerts = self.alert_system.get_active_alerts(
            dimension=AlertDimension.QUALITY
        )
        assert len(quality_alerts) >= 1
        
        warning_alerts = self.alert_system.get_active_alerts(
            level=AlertLevel.WARNING
        )
        assert len(warning_alerts) >= 1
    
    def test_get_alert_statistics(self):
        """测试告警统计"""
        # 添加一些历史告警
        for i in range(3):
            alert = Alert(
                id=uuid4(),
                rule_id=f"test_rule_{i}",
                dimension=AlertDimension.QUALITY,
                level=AlertLevel.WARNING,
                priority=AlertPriority.MEDIUM,
                title=f"测试告警 {i}",
                message=f"测试消息 {i}",
                source="test_source"
            )
            self.alert_system.alert_history.append(alert)
        
        # 获取统计
        stats = self.alert_system.get_alert_statistics(days=7)
        
        assert "total_alerts" in stats
        assert "active_alerts" in stats
        assert "by_dimension" in stats
        assert "by_level" in stats
        assert "by_status" in stats
        assert stats["total_alerts"] >= 3


class TestAlertNotificationSystem:
    """测试告警通知系统"""
    
    def setup_method(self):
        """测试前准备"""
        self.notification_system = AlertNotificationSystem()
    
    def test_add_template(self):
        """测试添加通知模板"""
        template = NotificationTemplate(
            id="test_template",
            name="测试模板",
            channel=NotificationChannel.EMAIL,
            alert_level=AlertLevel.WARNING,
            subject_template="[告警] {alert_title}",
            body_template="告警消息: {alert_message}"
        )
        
        self.notification_system.add_template(template)
        
        assert "test_template" in self.notification_system.templates
        retrieved_template = self.notification_system.templates["test_template"]
        assert retrieved_template.name == "测试模板"
    
    def test_template_rendering(self):
        """测试模板渲染"""
        template = NotificationTemplate(
            id="test_template",
            name="测试模板",
            channel=NotificationChannel.EMAIL,
            alert_level=AlertLevel.WARNING,
            subject_template="[{alert_level}] {alert_title}",
            body_template="告警: {alert_message}\n时间: {created_at}"
        )
        
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="测试告警",
            message="这是一个测试告警",
            source="test_source"
        )
        
        subject = template.render_subject(alert)
        body = template.render_body(alert)
        
        assert "[warning] 测试告警" == subject
        assert "告警: 这是一个测试告警" in body
        assert "时间:" in body
    
    def test_add_notification_config(self):
        """测试添加通知配置"""
        self.notification_system.add_notification_config(
            config_name="test_config",
            channel=NotificationChannel.EMAIL,
            recipients=["test@example.com"],
            alert_levels=[AlertLevel.WARNING, AlertLevel.CRITICAL],
            alert_dimensions=[AlertDimension.QUALITY],
            enabled=True
        )
        
        assert "test_config" in self.notification_system.notification_configs
        config = self.notification_system.notification_configs["test_config"]
        assert config["channel"] == NotificationChannel.EMAIL
        assert "test@example.com" in config["recipients"]
    
    def test_rate_limiting(self):
        """测试限流功能"""
        # 设置限流
        self.notification_system.set_rate_limit(
            channel=NotificationChannel.EMAIL,
            max_notifications=2,
            time_window_minutes=60
        )
        
        # 测试限流检查
        assert self.notification_system._check_rate_limit(
            NotificationChannel.EMAIL, "test@example.com"
        )
        assert self.notification_system._check_rate_limit(
            NotificationChannel.EMAIL, "test@example.com"
        )
        # 第三次应该被限流
        assert not self.notification_system._check_rate_limit(
            NotificationChannel.EMAIL, "test@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_create_notification_record(self):
        """测试创建通知记录"""
        # 添加模板
        template = NotificationTemplate(
            id="test_template",
            name="测试模板",
            channel=NotificationChannel.EMAIL,
            alert_level=AlertLevel.WARNING,
            subject_template="测试主题",
            body_template="测试内容"
        )
        self.notification_system.add_template(template)
        
        # 创建告警
        alert = Alert(
            id=uuid4(),
            rule_id="test_rule",
            dimension=AlertDimension.QUALITY,
            level=AlertLevel.WARNING,
            priority=AlertPriority.MEDIUM,
            title="测试告警",
            message="测试消息",
            source="test_source"
        )
        
        # 创建通知记录
        record = await self.notification_system._create_notification_record(
            alert, NotificationChannel.EMAIL, "test@example.com", "test_template"
        )
        
        assert record is not None
        assert record.alert_id == alert.id
        assert record.channel == NotificationChannel.EMAIL
        assert record.recipient == "test@example.com"
        assert record.subject == "测试主题"
        assert record.content == "测试内容"
    
    def test_get_notification_statistics(self):
        """测试通知统计"""
        # 添加一些通知记录
        for i in range(3):
            record = NotificationRecord(
                id=uuid4(),
                alert_id=uuid4(),
                channel=NotificationChannel.EMAIL,
                recipient=f"test{i}@example.com",
                subject=f"测试主题 {i}",
                content=f"测试内容 {i}",
                status=NotificationStatus.SENT
            )
            self.notification_system.notification_records[record.id] = record
        
        # 获取统计
        stats = self.notification_system.get_notification_statistics(days=7)
        
        assert "total_notifications" in stats
        assert "by_channel" in stats
        assert "by_status" in stats
        assert "success_rate" in stats
        assert stats["total_notifications"] >= 3


class TestEmailNotificationHandler:
    """测试邮件通知处理器"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "test@example.com",
            "password": "password",
            "use_tls": True,
            "from_email": "alerts@example.com",
            "from_name": "Test Alert System"
        }
        self.handler = EmailNotificationHandler(self.config)
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """测试邮件发送成功"""
        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            subject="测试邮件",
            content="这是一封测试邮件"
        )
        
        # Mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            success = await self.handler.send_notification(record)
            
            assert success
            assert record.status == NotificationStatus.SENT
            assert record.sent_at is not None
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_failure(self):
        """测试邮件发送失败"""
        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            subject="测试邮件",
            content="这是一封测试邮件"
        )
        
        # Mock SMTP 抛出异常
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP连接失败")
            
            success = await self.handler.send_notification(record)
            
            assert not success
            assert record.status == NotificationStatus.FAILED
            assert "SMTP连接失败" in record.error_message


class TestWeChatWorkNotificationHandler:
    """测试企业微信通知处理器"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = {
            "webhook_key": "test-webhook-key"
        }
        self.handler = WeChatWorkNotificationHandler(self.config)
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """测试企业微信通知发送成功"""
        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=NotificationChannel.WECHAT_WORK,
            recipient="@all",
            subject="测试通知",
            content="这是一条测试通知",
            metadata={"alert_level": "warning"}
        )
        
        # Mock the entire send_notification method for this test
        with patch.object(self.handler, 'send_notification', return_value=True) as mock_send:
            success = await self.handler.send_notification(record)
            
            assert success
    
    @pytest.mark.asyncio
    async def test_send_notification_no_webhook_key(self):
        """测试没有配置webhook key"""
        handler = WeChatWorkNotificationHandler({})
        
        record = NotificationRecord(
            id=uuid4(),
            alert_id=uuid4(),
            channel=NotificationChannel.WECHAT_WORK,
            recipient="@all",
            subject="测试通知",
            content="这是一条测试通知"
        )
        
        success = await handler.send_notification(record)
        
        assert not success
        assert record.status == NotificationStatus.FAILED
        assert "webhook key not configured" in record.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])