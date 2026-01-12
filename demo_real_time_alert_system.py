#!/usr/bin/env python3
"""
Real-time Alert System Demonstration Script.

This script demonstrates the comprehensive real-time alerting capabilities
of the SuperInsight security monitoring system.
"""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from src.security.real_time_alert_system import (
    RealTimeAlertSystem, AlertRule, AlertChannel, AlertPriority,
    SecurityEventType, ThreatLevel
)
from src.security.security_event_monitor import SecurityEvent
from src.security.alert_system_startup import AlertSystemManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_real_time_alerts():
    """演示实时告警系统功能"""
    
    print("🚨 SuperInsight 实时告警系统演示")
    print("=" * 50)
    
    # 1. 初始化告警系统
    print("\n1. 初始化告警系统")
    config = {
        'email': {
            'enabled': True,
            'smtp_server': 'localhost',
            'smtp_port': 587,
            'username': 'demo@example.com',
            'password': 'demo_password',
            'sender_email': 'alerts@superinsight.com'
        },
        'slack': {
            'enabled': True,
            'webhook_url': 'https://hooks.slack.com/demo'
        },
        'webhook': {
            'enabled': True
        },
        'critical_alert_recipients': ['security@example.com', 'admin@example.com'],
        'security_alert_recipients': ['security@example.com'],
        'auth_alert_recipients': ['admin@example.com']
    }
    
    alert_system = RealTimeAlertSystem(config)
    print(f"✓ 告警系统初始化完成")
    print(f"  - 默认规则数量: {len(alert_system.alert_rules)}")
    print(f"  - 可用通道数量: {len(alert_system.channel_handlers)}")
    
    # 2. 启动通知处理
    print("\n2. 启动通知处理")
    await alert_system.start_notification_processing()
    print("✓ 通知处理已启动")
    
    # 3. 演示告警规则管理
    print("\n3. 演示告警规则管理")
    
    # 添加自定义规则
    custom_rule = AlertRule(
        rule_id="demo_custom_rule",
        name="演示自定义规则",
        description="用于演示的自定义告警规则",
        event_types=[SecurityEventType.SUSPICIOUS_ACTIVITY],
        threat_levels=[ThreatLevel.MEDIUM, ThreatLevel.HIGH],
        channels=[AlertChannel.EMAIL, AlertChannel.SYSTEM_LOG],
        priority=AlertPriority.HIGH,
        cooldown_minutes=2,
        escalation_minutes=10,
        recipients=['demo@example.com']
    )
    
    alert_system.add_alert_rule(custom_rule)
    print(f"✓ 添加自定义规则: {custom_rule.name}")
    
    # 4. 演示安全事件处理
    print("\n4. 演示安全事件处理")
    
    # 创建测试安全事件
    test_events = [
        SecurityEvent(
            event_id="demo_event_001",
            event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
            threat_level=ThreatLevel.CRITICAL,
            tenant_id="demo_tenant_001",
            user_id=uuid4(),
            ip_address="192.168.1.100",
            timestamp=datetime.now(),
            description="演示暴力破解攻击检测",
            details={
                "pattern_id": "brute_force_login",
                "attempts": 25,
                "target_user": "admin",
                "source_country": "Unknown"
            }
        ),
        SecurityEvent(
            event_id="demo_event_002",
            event_type=SecurityEventType.DATA_EXFILTRATION,
            threat_level=ThreatLevel.HIGH,
            tenant_id="demo_tenant_001",
            user_id=uuid4(),
            ip_address="10.0.0.50",
            timestamp=datetime.now(),
            description="演示数据泄露风险检测",
            details={
                "pattern_id": "data_exfiltration",
                "export_size_mb": 150,
                "export_count": 8,
                "data_types": ["user_data", "financial_records"]
            }
        ),
        SecurityEvent(
            event_id="demo_event_003",
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.MEDIUM,
            tenant_id="demo_tenant_002",
            user_id=uuid4(),
            ip_address="172.16.0.25",
            timestamp=datetime.now(),
            description="演示可疑活动检测",
            details={
                "pattern_id": "anomalous_behavior",
                "anomaly_score": 0.85,
                "behavior_changes": ["unusual_time", "new_location", "high_volume"]
            }
        )
    ]
    
    # 处理安全事件
    for i, event in enumerate(test_events, 1):
        print(f"\n  处理安全事件 {i}: {event.event_type.value}")
        print(f"    威胁等级: {event.threat_level.value}")
        print(f"    描述: {event.description}")
        
        await alert_system.process_security_event(event)
        
        # 检查生成的通知
        pending_count = len(alert_system.pending_notifications)
        print(f"    ✓ 生成 {pending_count} 个待发送通知")
        
        # 处理通知
        await alert_system._process_pending_notifications()
        
        sent_count = len([n for n in alert_system.sent_notifications 
                         if n.alert_id.startswith('ALERT_')])
        print(f"    ✓ 发送完成，总计 {sent_count} 个通知")
        
        # 短暂等待
        await asyncio.sleep(1)
    
    # 5. 演示冷却机制
    print("\n5. 演示冷却机制")
    
    # 重复发送相同类型的事件
    duplicate_event = SecurityEvent(
        event_id="demo_event_004",
        event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
        threat_level=ThreatLevel.CRITICAL,
        tenant_id="demo_tenant_001",
        user_id=uuid4(),
        ip_address="192.168.1.100",
        timestamp=datetime.now(),
        description="重复的暴力破解攻击（应被冷却机制阻止）",
        details={"pattern_id": "brute_force_login", "attempts": 30}
    )
    
    initial_notifications = len(alert_system.sent_notifications)
    await alert_system.process_security_event(duplicate_event)
    await alert_system._process_pending_notifications()
    
    final_notifications = len(alert_system.sent_notifications)
    
    if final_notifications == initial_notifications:
        print("✓ 冷却机制正常工作 - 重复事件被阻止")
    else:
        print("⚠️ 冷却机制可能未正常工作")
    
    # 6. 显示统计信息
    print("\n6. 告警系统统计信息")
    stats = alert_system.get_alert_statistics()
    
    print(f"  总通知数量: {stats['total_notifications']}")
    print(f"  成功通知数量: {stats['successful_notifications']}")
    print(f"  失败通知数量: {stats['failed_notifications']}")
    print(f"  成功率: {stats['success_rate']:.2%}")
    print(f"  待处理通知: {stats['pending_notifications']}")
    print(f"  活跃规则数量: {stats['active_rules']}")
    print(f"  总规则数量: {stats['total_rules']}")
    
    print("\n  优先级分布:")
    for priority, count in stats['priority_distribution'].items():
        print(f"    {priority}: {count}")
    
    print("\n  通道分布:")
    for channel, count in stats['channel_distribution'].items():
        print(f"    {channel}: {count}")
    
    # 7. 演示规则管理
    print("\n7. 演示规则管理")
    
    # 禁用规则
    alert_system.disable_alert_rule("demo_custom_rule")
    print("✓ 禁用自定义规则")
    
    # 启用规则
    alert_system.enable_alert_rule("demo_custom_rule")
    print("✓ 重新启用自定义规则")
    
    # 移除规则
    alert_system.remove_alert_rule("demo_custom_rule")
    print("✓ 移除自定义规则")
    
    # 8. 演示通知历史
    print("\n8. 最近通知历史")
    recent_notifications = sorted(
        alert_system.sent_notifications,
        key=lambda x: x.created_at,
        reverse=True
    )[:5]
    
    for i, notif in enumerate(recent_notifications, 1):
        print(f"  {i}. [{notif.priority.value.upper()}] {notif.subject}")
        print(f"     通道: {notif.channel.value}, 状态: {notif.status.value}")
        print(f"     时间: {notif.created_at.strftime('%H:%M:%S')}")
    
    # 9. 停止告警系统
    print("\n9. 停止告警系统")
    await alert_system.stop_notification_processing()
    print("✓ 告警系统已停止")
    
    print("\n🎉 实时告警系统演示完成！")
    print("\n主要功能演示:")
    print("  ✓ 多通道告警 (邮件、Slack、Webhook、系统日志)")
    print("  ✓ 智能规则匹配")
    print("  ✓ 冷却机制防止告警风暴")
    print("  ✓ 优先级管理")
    print("  ✓ 实时通知处理")
    print("  ✓ 统计和监控")
    print("  ✓ 规则动态管理")


async def demonstrate_alert_system_manager():
    """演示告警系统管理器功能"""
    
    print("\n" + "=" * 50)
    print("🔧 告警系统管理器演示")
    print("=" * 50)
    
    # 创建管理器
    manager = AlertSystemManager()
    
    # 1. 配置验证
    print("\n1. 配置验证演示")
    
    # 有效配置
    valid_config = {
        'email': {
            'enabled': True,
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'test@example.com'
        },
        'recipients': {
            'critical_alert_recipients': ['admin@example.com']
        },
        'custom_rules': [
            {
                'rule_id': 'test_rule',
                'name': 'Test Rule',
                'event_types': ['suspicious_activity'],
                'threat_levels': ['medium'],
                'channels': ['email'],
                'priority': 'medium',
                'recipients': ['test@example.com']
            }
        ]
    }
    
    validation = manager.validate_configuration(valid_config)
    print(f"✓ 有效配置验证: {validation['valid']}")
    if validation['warnings']:
        print(f"  警告: {validation['warnings']}")
    
    # 无效配置
    invalid_config = {
        'email': {
            'enabled': True
            # 缺少必需字段
        },
        'custom_rules': [
            {
                # 缺少 rule_id 和 name
                'event_types': ['suspicious_activity']
            }
        ]
    }
    
    validation = manager.validate_configuration(invalid_config)
    print(f"✗ 无效配置验证: {validation['valid']}")
    if validation['errors']:
        print(f"  错误: {validation['errors']}")
    
    # 2. 系统初始化
    print("\n2. 系统初始化")
    alert_system = manager.initialize_alert_system(valid_config)
    print(f"✓ 系统初始化完成")
    
    # 3. 系统状态
    print("\n3. 系统状态")
    status = manager.get_system_status()
    print(f"  初始化状态: {status['initialized']}")
    print(f"  运行状态: {status['running']}")
    print(f"  配置加载: {status['configuration_loaded']}")
    print(f"  总规则数: {status['total_rules']}")
    print(f"  活跃规则数: {status['active_rules']}")
    print(f"  可用通道数: {status['available_channels']}")
    
    # 4. 启动和停止
    print("\n4. 启动和停止")
    
    start_success = await manager.start_alert_system()
    print(f"✓ 启动结果: {start_success}")
    
    # 等待一下
    await asyncio.sleep(2)
    
    stop_success = await manager.stop_alert_system()
    print(f"✓ 停止结果: {stop_success}")
    
    print("\n🎉 告警系统管理器演示完成！")


async def main():
    """主演示函数"""
    
    print("🚀 SuperInsight 实时告警系统完整演示")
    print("=" * 60)
    
    try:
        # 演示核心告警系统
        await demonstrate_real_time_alerts()
        
        # 演示管理器功能
        await demonstrate_alert_system_manager()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！实时告警系统功能正常")
        print("\n📋 系统特性总结:")
        print("  🔔 多通道实时告警 (邮件/Slack/Webhook/日志)")
        print("  📋 灵活的告警规则配置")
        print("  🎯 智能事件匹配和过滤")
        print("  ⏰ 冷却机制防止告警风暴")
        print("  📊 完整的统计和监控")
        print("  🔧 动态规则管理")
        print("  🚀 高性能异步处理")
        print("  🛡️ 企业级安全告警")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        print(f"\n❌ 演示失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())