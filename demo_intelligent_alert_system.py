#!/usr/bin/env python3
"""
智能告警系统演示脚本

演示多维度告警规则、告警聚合、通知处理等功能。
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.quality_billing.intelligent_alert_system import (
    IntelligentAlertSystem,
    AlertDimension,
    AlertLevel,
    AlertRuleType,
    AlertPriority
)
from src.quality_billing.alert_notification_system import (
    AlertNotificationSystem,
    NotificationChannel
)


async def demo_alert_rules():
    """演示告警规则创建和管理"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 告警规则管理")
    print("="*60)
    
    # 创建告警系统
    alert_system = IntelligentAlertSystem()
    
    print("\n1. 创建自定义告警规则")
    
    # 创建质量告警规则
    quality_rule = alert_system.rule_engine.create_quality_alert_rule(
        name="数据标注质量监控",
        quality_threshold=0.85,
        trend_window=15,
        level=AlertLevel.WARNING
    )
    print(f"✓ 创建质量告警规则: {quality_rule.name}")
    
    # 创建效率告警规则
    efficiency_rule = alert_system.rule_engine.create_efficiency_alert_rule(
        name="标注效率监控",
        efficiency_threshold=0.75,
        workload_threshold=80,
        level=AlertLevel.HIGH
    )
    print(f"✓ 创建效率告警规则: {efficiency_rule.name}")
    
    # 创建成本告警规则
    cost_rule = alert_system.rule_engine.create_cost_alert_rule(
        name="项目成本监控",
        cost_threshold=5000.0,
        budget_percentage=0.9,
        level=AlertLevel.CRITICAL
    )
    print(f"✓ 创建成本告警规则: {cost_rule.name}")
    
    # 创建异常检测规则
    anomaly_rule = alert_system.rule_engine.create_anomaly_detection_rule(
        name="质量异常检测",
        metric_name="quality_score",
        dimension=AlertDimension.QUALITY,
        sensitivity=2.5,
        level=AlertLevel.WARNING
    )
    print(f"✓ 创建异常检测规则: {anomaly_rule.name}")
    
    print(f"\n2. 规则列表 (共 {len(alert_system.rule_engine.rules)} 个规则)")
    rules = alert_system.rule_engine.list_rules()
    for rule in rules:
        print(f"   - {rule['name']} ({rule['dimension']}, {rule['level']})")
    
    return alert_system


async def demo_metric_processing():
    """演示指标处理和告警生成"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 指标处理和告警生成")
    print("="*60)
    
    alert_system = IntelligentAlertSystem()
    
    print("\n1. 模拟指标数据")
    
    # 模拟正常指标
    normal_metrics = {
        "quality_score": 0.92,
        "task_completion_rate": 0.88,
        "current_workload": 65,
        "daily_cost": 800.0,
        "budget_usage_percentage": 0.65,
        "annotation_accuracy": 0.94,
        "processing_speed": 120.5
    }
    print("正常指标数据:")
    for key, value in normal_metrics.items():
        print(f"   {key}: {value}")
    
    alerts = await alert_system.process_metrics(normal_metrics)
    print(f"\n✓ 处理正常指标: 生成 {len(alerts)} 个告警")
    
    print("\n2. 模拟异常指标")
    
    # 模拟异常指标
    abnormal_metrics = {
        "quality_score": 0.65,  # 低于阈值
        "task_completion_rate": 0.55,  # 低效率
        "current_workload": 150,  # 高负载
        "daily_cost": 6000.0,  # 超出成本
        "budget_usage_percentage": 0.95,  # 预算告急
        "annotation_accuracy": 0.60,  # 准确率低
        "processing_speed": 45.2  # 处理速度慢
    }
    print("异常指标数据:")
    for key, value in abnormal_metrics.items():
        print(f"   {key}: {value}")
    
    alerts = await alert_system.process_metrics(abnormal_metrics)
    print(f"\n✓ 处理异常指标: 生成 {len(alerts)} 个告警")
    
    if alerts:
        print("\n生成的告警:")
        for i, alert in enumerate(alerts, 1):
            print(f"   {i}. [{alert.level.value.upper()}] {alert.title}")
            print(f"      维度: {alert.dimension.value}")
            print(f"      消息: {alert.message}")
            print(f"      来源: {alert.source}")
            if alert.metric_name:
                print(f"      指标: {alert.metric_name} = {alert.metric_value}")
    
    return alert_system, alerts


async def demo_alert_aggregation():
    """演示告警聚合功能"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 告警聚合")
    print("="*60)
    
    alert_system = IntelligentAlertSystem()
    
    print("\n1. 生成多个相似告警")
    
    # 连续生成多个质量告警
    quality_metrics_series = [
        {"quality_score": 0.70, "annotation_accuracy": 0.68},
        {"quality_score": 0.65, "annotation_accuracy": 0.62},
        {"quality_score": 0.60, "annotation_accuracy": 0.58},
        {"quality_score": 0.55, "annotation_accuracy": 0.52},
        {"quality_score": 0.50, "annotation_accuracy": 0.48}
    ]
    
    all_alerts = []
    for i, metrics in enumerate(quality_metrics_series):
        print(f"   处理第 {i+1} 批指标: quality_score={metrics['quality_score']}")
        alerts = await alert_system.process_metrics(metrics)
        all_alerts.extend(alerts)
        await asyncio.sleep(0.1)  # 模拟时间间隔
    
    print(f"\n✓ 总共生成 {len(all_alerts)} 个告警")
    
    print("\n2. 查看聚合结果")
    active_alerts = alert_system.get_active_alerts()
    print(f"✓ 活跃告警数量: {len(active_alerts)}")
    
    for alert in active_alerts:
        if alert.get("context", {}).get("aggregated"):
            print(f"   [聚合告警] {alert['title']}")
            print(f"   包含 {alert['context']['alert_count']} 个原始告警")
            print(f"   维度: {', '.join(alert['context']['dimensions'])}")
        else:
            print(f"   [单独告警] {alert['title']}")
    
    return alert_system


async def demo_notification_system():
    """演示通知系统"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 通知系统")
    print("="*60)
    
    # 创建通知系统
    notification_system = AlertNotificationSystem()
    
    print("\n1. 配置通知渠道")
    
    # 配置邮件通知
    notification_system.configure_email_handler({
        "host": "smtp.example.com",
        "port": 587,
        "username": "alerts@superinsight.com",
        "password": "password",
        "use_tls": True,
        "from_email": "alerts@superinsight.com",
        "from_name": "SuperInsight Alert System"
    })
    print("✓ 配置邮件通知处理器")
    
    # 配置企业微信通知
    notification_system.configure_wechat_work_handler({
        "webhook_key": "your-wechat-work-webhook-key"
    })
    print("✓ 配置企业微信通知处理器")
    
    # 配置Webhook通知
    notification_system.configure_webhook_handler({
        "url": "https://your-webhook-endpoint.com/alerts",
        "headers": {"Authorization": "Bearer your-token"},
        "timeout": 30
    })
    print("✓ 配置Webhook通知处理器")
    
    print("\n2. 添加通知配置")
    
    # 添加邮件通知配置
    notification_system.add_notification_config(
        config_name="critical_email_alerts",
        channel=NotificationChannel.EMAIL,
        recipients=["admin@superinsight.com", "ops@superinsight.com"],
        alert_levels=[AlertLevel.CRITICAL, AlertLevel.EMERGENCY],
        alert_dimensions=[AlertDimension.QUALITY, AlertDimension.COST],
        enabled=True
    )
    print("✓ 添加严重告警邮件通知配置")
    
    # 添加企业微信通知配置
    notification_system.add_notification_config(
        config_name="all_wechat_alerts",
        channel=NotificationChannel.WECHAT_WORK,
        recipients=["@all"],
        alert_levels=[AlertLevel.WARNING, AlertLevel.HIGH, AlertLevel.CRITICAL],
        enabled=True
    )
    print("✓ 添加企业微信通知配置")
    
    # 设置限流
    notification_system.set_rate_limit(
        channel=NotificationChannel.EMAIL,
        max_notifications=10,
        time_window_minutes=60
    )
    print("✓ 设置邮件通知限流: 每小时最多10条")
    
    print("\n3. 模拟告警通知")
    
    # 创建模拟告警
    from src.quality_billing.intelligent_alert_system import Alert
    
    test_alert = Alert(
        id=uuid4(),
        rule_id="test_rule",
        dimension=AlertDimension.QUALITY,
        level=AlertLevel.CRITICAL,
        priority=AlertPriority.CRITICAL,
        title="数据质量严重下降",
        message="检测到数据标注质量从 0.92 下降到 0.65，低于阈值 0.8",
        source="quality_monitor",
        metric_name="quality_score",
        metric_value=0.65,
        threshold_value=0.8,
        context={"project_id": "proj_001", "dataset": "training_data_v2"}
    )
    
    # 发送通知
    notifications = await notification_system.send_alert_notifications(test_alert)
    print(f"✓ 发送告警通知: 生成 {len(notifications)} 条通知记录")
    
    for notification in notifications:
        print(f"   - {notification.channel.value}: {notification.recipient}")
        print(f"     主题: {notification.subject}")
        print(f"     状态: {notification.status.value}")
    
    return notification_system


async def demo_alert_management():
    """演示告警管理功能"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 告警管理")
    print("="*60)
    
    alert_system = IntelligentAlertSystem()
    
    # 生成一些测试告警
    test_metrics = {
        "quality_score": 0.60,
        "task_completion_rate": 0.50,
        "daily_cost": 8000.0
    }
    
    alerts = await alert_system.process_metrics(test_metrics)
    print(f"✓ 生成 {len(alerts)} 个测试告警")
    
    if alerts:
        test_alert = alerts[0]
        alert_id = test_alert.id
        
        print(f"\n1. 告警确认")
        success = await alert_system.acknowledge_alert(alert_id, "admin@superinsight.com")
        if success:
            print(f"✓ 告警 {alert_id} 已确认")
        
        print(f"\n2. 告警解决")
        success = await alert_system.resolve_alert(
            alert_id, 
            "admin@superinsight.com", 
            "已调整质量阈值并重新训练模型"
        )
        if success:
            print(f"✓ 告警 {alert_id} 已解决")
    
    print(f"\n3. 告警统计")
    stats = alert_system.get_alert_statistics(days=1)
    print(f"✓ 统计数据:")
    print(f"   总告警数: {stats['total_alerts']}")
    print(f"   活跃告警: {stats['active_alerts']}")
    print(f"   按维度分布: {stats['by_dimension']}")
    print(f"   按级别分布: {stats['by_level']}")
    print(f"   按状态分布: {stats['by_status']}")
    
    return alert_system


async def demo_escalation_system():
    """演示告警升级系统"""
    print("\n" + "="*60)
    print("智能告警系统演示 - 告警升级")
    print("="*60)
    
    alert_system = IntelligentAlertSystem()
    
    print("\n1. 生成严重告警")
    
    # 生成严重告警
    critical_metrics = {
        "quality_score": 0.45,  # 严重质量问题
        "daily_cost": 15000.0   # 严重成本超标
    }
    
    alerts = await alert_system.process_metrics(critical_metrics)
    print(f"✓ 生成 {len(alerts)} 个严重告警")
    
    if alerts:
        print("\n2. 模拟时间流逝 (告警未处理)")
        
        # 模拟告警创建时间为较早时间
        for alert in alerts:
            if alert.level == AlertLevel.CRITICAL:
                alert.created_at = datetime.now() - timedelta(minutes=10)
                print(f"   告警 {alert.id} 创建于 10 分钟前")
        
        print("\n3. 检查告警升级")
        escalations = await alert_system.escalation_manager.check_escalations(alerts)
        
        if escalations:
            print(f"✓ 检测到 {len(escalations)} 个告警需要升级")
            for escalation in escalations:
                print(f"   告警 {escalation['alert_id']} 升级到级别 {escalation['escalation_level']}")
                print(f"   升级原因: {escalation['escalation_reason']}")
                print(f"   升级动作: {', '.join(escalation['escalation_actions'])}")
        else:
            print("✓ 暂无告警需要升级")
    
    return alert_system


async def main():
    """主演示函数"""
    print("智能告警系统完整演示")
    print("="*80)
    
    try:
        # 1. 告警规则管理
        alert_system = await demo_alert_rules()
        
        # 2. 指标处理和告警生成
        alert_system, alerts = await demo_metric_processing()
        
        # 3. 告警聚合
        await demo_alert_aggregation()
        
        # 4. 通知系统
        await demo_notification_system()
        
        # 5. 告警管理
        await demo_alert_management()
        
        # 6. 告警升级
        await demo_escalation_system()
        
        print("\n" + "="*80)
        print("智能告警系统演示完成!")
        print("="*80)
        
        # 最终统计
        final_stats = alert_system.get_alert_statistics(days=1)
        print(f"\n最终统计:")
        print(f"- 总告警数: {final_stats['total_alerts']}")
        print(f"- 活跃告警: {final_stats['active_alerts']}")
        print(f"- 按维度分布: {json.dumps(final_stats['by_dimension'], ensure_ascii=False, indent=2)}")
        print(f"- 按级别分布: {json.dumps(final_stats['by_level'], ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())