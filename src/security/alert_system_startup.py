"""
Real-time Alert System Startup and Configuration.

Handles initialization, configuration loading, and startup of the real-time
alert system for SuperInsight platform.
"""

import asyncio
import logging
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional

from src.security.real_time_alert_system import (
    RealTimeAlertSystem, AlertRule, AlertChannel, AlertPriority,
    SecurityEventType, ThreatLevel, real_time_alert_system
)


logger = logging.getLogger(__name__)


class AlertSystemManager:
    """管理实时告警系统的启动和配置"""
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.alert_system: Optional[RealTimeAlertSystem] = None
        self.initialized = False
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载告警系统配置"""
        
        if config_path is None:
            # 尝试多个配置文件路径
            possible_paths = [
                "config/real_time_alerts.yaml",
                "config/real_time_alerts.yml",
                ".kiro/config/real_time_alerts.yaml",
                "real_time_alerts.yaml"
            ]
            
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded alert system config from {config_path}")
                return config
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
        
        # 返回默认配置
        logger.info("Using default alert system configuration")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'email': {
                'enabled': False,
                'smtp_server': 'localhost',
                'smtp_port': 587
            },
            'slack': {
                'enabled': False
            },
            'webhook': {
                'enabled': False
            },
            'recipients': {
                'critical_alert_recipients': ['admin@localhost'],
                'security_alert_recipients': ['security@localhost'],
                'auth_alert_recipients': ['admin@localhost']
            },
            'processing': {
                'processing_interval': 5,
                'max_pending_notifications': 10000,
                'max_retries': 3,
                'retry_delay_minutes': 5,
                'notification_retention_days': 30,
                'cooldown_retention_days': 7
            },
            'default_rules': {
                'critical_threats': {
                    'enabled': True,
                    'cooldown_minutes': 1,
                    'escalation_minutes': 15,
                    'channels': ['system_log'],
                    'priority': 'critical'
                },
                'anomalous_behavior': {
                    'enabled': True,
                    'cooldown_minutes': 10,
                    'escalation_minutes': 60,
                    'channels': ['system_log'],
                    'priority': 'medium'
                },
                'authentication_failures': {
                    'enabled': True,
                    'cooldown_minutes': 15,
                    'escalation_minutes': 120,
                    'channels': ['system_log'],
                    'priority': 'low'
                }
            }
        }
    
    def initialize_alert_system(self, config: Optional[Dict[str, Any]] = None) -> RealTimeAlertSystem:
        """初始化告警系统"""
        
        if config is None:
            config = self.load_config()
        
        self.config = config
        
        # 创建告警系统实例
        self.alert_system = RealTimeAlertSystem(config)
        
        # 加载自定义规则
        self._load_custom_rules(config)
        
        self.initialized = True
        logger.info("Real-time alert system initialized successfully")
        
        return self.alert_system
    
    def _load_custom_rules(self, config: Dict[str, Any]):
        """加载自定义告警规则"""
        
        custom_rules = config.get('custom_rules', [])
        
        for rule_config in custom_rules:
            try:
                # 转换配置为AlertRule对象
                rule = self._create_alert_rule_from_config(rule_config)
                self.alert_system.add_alert_rule(rule)
                logger.info(f"Added custom alert rule: {rule.name}")
                
            except Exception as e:
                logger.error(f"Failed to load custom rule {rule_config.get('rule_id', 'unknown')}: {e}")
    
    def _create_alert_rule_from_config(self, rule_config: Dict[str, Any]) -> AlertRule:
        """从配置创建告警规则"""
        
        # 转换事件类型
        event_types = []
        for event_type_str in rule_config.get('event_types', []):
            try:
                event_types.append(SecurityEventType(event_type_str))
            except ValueError:
                logger.warning(f"Unknown event type: {event_type_str}")
        
        # 转换威胁等级
        threat_levels = []
        for threat_level_str in rule_config.get('threat_levels', []):
            try:
                threat_levels.append(ThreatLevel(threat_level_str))
            except ValueError:
                logger.warning(f"Unknown threat level: {threat_level_str}")
        
        # 转换通道
        channels = []
        for channel_str in rule_config.get('channels', []):
            try:
                channels.append(AlertChannel(channel_str))
            except ValueError:
                logger.warning(f"Unknown alert channel: {channel_str}")
        
        # 转换优先级
        try:
            priority = AlertPriority(rule_config.get('priority', 'medium'))
        except ValueError:
            priority = AlertPriority.MEDIUM
            logger.warning(f"Unknown priority, using default: medium")
        
        return AlertRule(
            rule_id=rule_config['rule_id'],
            name=rule_config['name'],
            description=rule_config.get('description', ''),
            event_types=event_types,
            threat_levels=threat_levels,
            channels=channels,
            priority=priority,
            enabled=rule_config.get('enabled', True),
            cooldown_minutes=rule_config.get('cooldown_minutes', 5),
            escalation_minutes=rule_config.get('escalation_minutes', 30),
            recipients=rule_config.get('recipients', []),
            conditions=rule_config.get('conditions', {})
        )
    
    async def start_alert_system(self) -> bool:
        """启动告警系统"""
        
        if not self.initialized:
            self.initialize_alert_system()
        
        try:
            await self.alert_system.start_notification_processing()
            logger.info("Real-time alert system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start alert system: {e}")
            return False
    
    async def stop_alert_system(self) -> bool:
        """停止告警系统"""
        
        if not self.alert_system or not self.alert_system.running:
            logger.info("Alert system is not running")
            return True
        
        try:
            await self.alert_system.stop_notification_processing()
            logger.info("Real-time alert system stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop alert system: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        
        if not self.initialized or not self.alert_system:
            return {
                'initialized': False,
                'running': False,
                'error': 'Alert system not initialized'
            }
        
        stats = self.alert_system.get_alert_statistics()
        
        return {
            'initialized': self.initialized,
            'running': self.alert_system.running,
            'configuration_loaded': self.config is not None,
            'total_rules': stats['total_rules'],
            'active_rules': stats['active_rules'],
            'available_channels': len(self.alert_system.channel_handlers),
            'pending_notifications': stats['pending_notifications'],
            'total_notifications_sent': stats['total_notifications'],
            'success_rate': stats['success_rate'],
            'statistics': stats
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 验证邮件配置
        email_config = config.get('email', {})
        if email_config.get('enabled', False):
            required_fields = ['smtp_server', 'smtp_port']
            for field in required_fields:
                if not email_config.get(field):
                    validation_result['errors'].append(f"Email configuration missing required field: {field}")
                    validation_result['valid'] = False
        
        # 验证Slack配置
        slack_config = config.get('slack', {})
        if slack_config.get('enabled', False):
            if not slack_config.get('webhook_url'):
                validation_result['errors'].append("Slack configuration missing webhook_url")
                validation_result['valid'] = False
        
        # 验证接收者配置
        recipients = config.get('recipients', {})
        if not recipients.get('critical_alert_recipients'):
            validation_result['warnings'].append("No critical alert recipients configured")
        
        # 验证自定义规则
        custom_rules = config.get('custom_rules', [])
        for i, rule in enumerate(custom_rules):
            if not rule.get('rule_id'):
                validation_result['errors'].append(f"Custom rule {i} missing rule_id")
                validation_result['valid'] = False
            
            if not rule.get('name'):
                validation_result['errors'].append(f"Custom rule {i} missing name")
                validation_result['valid'] = False
        
        return validation_result


# 全局管理器实例
alert_system_manager = AlertSystemManager()


# 便捷函数
async def initialize_real_time_alerts(config_path: Optional[str] = None) -> bool:
    """初始化并启动实时告警系统"""
    
    try:
        # 加载配置
        config = alert_system_manager.load_config(config_path)
        
        # 验证配置
        validation = alert_system_manager.validate_configuration(config)
        if not validation['valid']:
            logger.error(f"Invalid alert configuration: {validation['errors']}")
            return False
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"Alert configuration warning: {warning}")
        
        # 初始化系统
        alert_system_manager.initialize_alert_system(config)
        
        # 启动系统
        success = await alert_system_manager.start_alert_system()
        
        if success:
            logger.info("Real-time alert system initialization completed successfully")
        else:
            logger.error("Failed to start real-time alert system")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize real-time alerts: {e}")
        return False


async def shutdown_real_time_alerts() -> bool:
    """关闭实时告警系统"""
    
    try:
        success = await alert_system_manager.stop_alert_system()
        
        if success:
            logger.info("Real-time alert system shutdown completed")
        else:
            logger.error("Failed to shutdown real-time alert system")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to shutdown real-time alerts: {e}")
        return False


def get_alert_system_manager() -> AlertSystemManager:
    """获取告警系统管理器"""
    return alert_system_manager


def get_real_time_alert_system() -> Optional[RealTimeAlertSystem]:
    """获取实时告警系统实例"""
    return alert_system_manager.alert_system if alert_system_manager.initialized else None