"""
脱敏异常告警系统
基于现有告警机制，添加脱敏相关告警
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from src.desensitization.validator import ValidationResult

logger = logging.getLogger(__name__)

class DesensitizationAlertManager:
    """脱敏告警管理器"""
    
    def __init__(self):
        self.alert_thresholds = {
            "data_leakage": {
                "critical": 1,  # 任何数据泄露都是严重的
                "warning": 0
            },
            "success_rate": {
                "critical": 0.80,
                "warning": 0.90
            },
            "completeness": {
                "critical": 0.80,
                "warning": 0.90
            },
            "accuracy": {
                "critical": 0.75,
                "warning": 0.85
            },
            "processing_time": {
                "critical": 10.0,  # 10秒
                "warning": 5.0     # 5秒
            }
        }
    
    async def check_validation_result(self, result: ValidationResult, operation_context: Dict[str, Any]):
        """检查验证结果并发送告警"""
        
        alerts = []
        
        # 检查数据泄露
        leakage_issues = [issue for issue in result.issues if "leakage" in issue.lower()]
        if leakage_issues:
            alerts.append({
                "type": "data_leakage",
                "level": "critical",
                "title": "Data Leakage Detected",
                "message": f"Potential data leakage detected: {'; '.join(leakage_issues)}",
                "context": operation_context,
                "metadata": {
                    "leakage_count": len(leakage_issues),
                    "validation_result": result.__dict__
                }
            })
        
        # 检查完整性
        if result.completeness_score < self.alert_thresholds["completeness"]["critical"]:
            alerts.append({
                "type": "completeness",
                "level": "critical",
                "title": "Low Desensitization Completeness",
                "message": f"Completeness score {result.completeness_score:.1%} is critically low",
                "context": operation_context,
                "metadata": {
                    "completeness_score": result.completeness_score,
                    "threshold": self.alert_thresholds["completeness"]["critical"]
                }
            })
        elif result.completeness_score < self.alert_thresholds["completeness"]["warning"]:
            alerts.append({
                "type": "completeness",
                "level": "warning",
                "title": "Desensitization Completeness Warning",
                "message": f"Completeness score {result.completeness_score:.1%} below warning threshold",
                "context": operation_context,
                "metadata": {
                    "completeness_score": result.completeness_score,
                    "threshold": self.alert_thresholds["completeness"]["warning"]
                }
            })
        
        # 检查准确性
        if result.accuracy_score < self.alert_thresholds["accuracy"]["critical"]:
            alerts.append({
                "type": "accuracy",
                "level": "critical",
                "title": "Low Desensitization Accuracy",
                "message": f"Accuracy score {result.accuracy_score:.1%} is critically low",
                "context": operation_context,
                "metadata": {
                    "accuracy_score": result.accuracy_score,
                    "threshold": self.alert_thresholds["accuracy"]["critical"]
                }
            })
        elif result.accuracy_score < self.alert_thresholds["accuracy"]["warning"]:
            alerts.append({
                "type": "accuracy",
                "level": "warning",
                "title": "Desensitization Accuracy Warning",
                "message": f"Accuracy score {result.accuracy_score:.1%} below warning threshold",
                "context": operation_context,
                "metadata": {
                    "accuracy_score": result.accuracy_score,
                    "threshold": self.alert_thresholds["accuracy"]["warning"]
                }
            })
        
        # 发送所有告警
        for alert in alerts:
            await self.send_alert(alert)
    
    async def check_batch_results(self, results: List[ValidationResult], batch_context: Dict[str, Any]):
        """检查批量验证结果"""
        
        if not results:
            return
        
        # 计算批量指标
        total_results = len(results)
        valid_results = sum(1 for r in results if r.is_valid)
        success_rate = valid_results / total_results
        
        avg_completeness = sum(r.completeness_score for r in results) / total_results
        avg_accuracy = sum(r.accuracy_score for r in results) / total_results
        
        # 统计问题
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        
        leakage_count = sum(1 for issue in all_issues if "leakage" in issue.lower())
        
        alerts = []
        
        # 检查成功率
        if success_rate < self.alert_thresholds["success_rate"]["critical"]:
            alerts.append({
                "type": "success_rate",
                "level": "critical",
                "title": "Critical Desensitization Success Rate",
                "message": f"Batch success rate {success_rate:.1%} is critically low ({valid_results}/{total_results})",
                "context": batch_context,
                "metadata": {
                    "success_rate": success_rate,
                    "valid_results": valid_results,
                    "total_results": total_results
                }
            })
        elif success_rate < self.alert_thresholds["success_rate"]["warning"]:
            alerts.append({
                "type": "success_rate",
                "level": "warning",
                "title": "Low Desensitization Success Rate",
                "message": f"Batch success rate {success_rate:.1%} below warning threshold ({valid_results}/{total_results})",
                "context": batch_context,
                "metadata": {
                    "success_rate": success_rate,
                    "valid_results": valid_results,
                    "total_results": total_results
                }
            })
        
        # 检查数据泄露
        if leakage_count > 0:
            alerts.append({
                "type": "data_leakage",
                "level": "critical",
                "title": "Batch Data Leakage Detected",
                "message": f"Data leakage detected in {leakage_count} operations out of {total_results}",
                "context": batch_context,
                "metadata": {
                    "leakage_count": leakage_count,
                    "total_operations": total_results,
                    "leakage_rate": leakage_count / total_results
                }
            })
        
        # 检查平均完整性
        if avg_completeness < self.alert_thresholds["completeness"]["critical"]:
            alerts.append({
                "type": "completeness",
                "level": "critical",
                "title": "Critical Batch Completeness",
                "message": f"Average completeness {avg_completeness:.1%} is critically low",
                "context": batch_context,
                "metadata": {
                    "average_completeness": avg_completeness,
                    "threshold": self.alert_thresholds["completeness"]["critical"]
                }
            })
        
        # 检查平均准确性
        if avg_accuracy < self.alert_thresholds["accuracy"]["critical"]:
            alerts.append({
                "type": "accuracy",
                "level": "critical",
                "title": "Critical Batch Accuracy",
                "message": f"Average accuracy {avg_accuracy:.1%} is critically low",
                "context": batch_context,
                "metadata": {
                    "average_accuracy": avg_accuracy,
                    "threshold": self.alert_thresholds["accuracy"]["critical"]
                }
            })
        
        # 发送所有告警
        for alert in alerts:
            await self.send_alert(alert)
    
    async def check_processing_performance(self, processing_time: float, operation_context: Dict[str, Any]):
        """检查处理性能"""
        
        alerts = []
        
        if processing_time > self.alert_thresholds["processing_time"]["critical"]:
            alerts.append({
                "type": "processing_time",
                "level": "critical",
                "title": "Critical Processing Time",
                "message": f"Desensitization processing time {processing_time:.2f}s exceeds critical threshold",
                "context": operation_context,
                "metadata": {
                    "processing_time": processing_time,
                    "threshold": self.alert_thresholds["processing_time"]["critical"]
                }
            })
        elif processing_time > self.alert_thresholds["processing_time"]["warning"]:
            alerts.append({
                "type": "processing_time",
                "level": "warning",
                "title": "High Processing Time",
                "message": f"Desensitization processing time {processing_time:.2f}s exceeds warning threshold",
                "context": operation_context,
                "metadata": {
                    "processing_time": processing_time,
                    "threshold": self.alert_thresholds["processing_time"]["warning"]
                }
            })
        
        # 发送告警
        for alert in alerts:
            await self.send_alert(alert)
    
    async def send_alert(self, alert: Dict[str, Any]):
        """发送告警"""
        
        try:
            # 构建告警消息
            alert_message = {
                "title": alert["title"],
                "message": alert["message"],
                "level": alert["level"],
                "type": "desensitization",
                "subtype": alert["type"],
                "timestamp": datetime.utcnow().isoformat(),
                "context": alert.get("context", {}),
                "metadata": alert.get("metadata", {}),
                "tags": ["desensitization", "security", "data_protection", alert["type"]]
            }
            
            # 发送到告警系统
            await self._send_to_alert_system(alert_message)
            
            # 记录告警日志
            await self._log_alert(alert_message)
            
            # 如果是严重告警，发送紧急通知
            if alert["level"] == "critical":
                await self._send_emergency_notification(alert_message)
            
            logger.info(f"Desensitization alert sent: {alert['title']} - {alert['message']}")
            
        except Exception as e:
            logger.error(f"Failed to send desensitization alert: {e}")
    
    async def _send_to_alert_system(self, alert_message: Dict[str, Any]):
        """发送到告警系统"""
        
        # 集成现有告警系统
        from src.monitoring.alert_manager import AlertManager
        alert_manager = AlertManager()
        
        await alert_manager.send_alert(
            title=alert_message["title"],
            message=alert_message["message"],
            level=alert_message["level"],
            tags=alert_message["tags"],
            metadata=alert_message["metadata"]
        )
    
    async def _log_alert(self, alert_message: Dict[str, Any]):
        """记录告警日志"""
        
        try:
            from src.security.audit_service import EnhancedAuditService
            audit_service = EnhancedAuditService()
            
            await audit_service.log_event(
                event_type="desensitization_alert",
                user_id=alert_message.get("context", {}).get("user_id", "system"),
                resource="desensitization_alert",
                action="alert_sent",
                details={
                    "alert_type": alert_message["subtype"],
                    "alert_level": alert_message["level"],
                    "alert_title": alert_message["title"],
                    "alert_message": alert_message["message"],
                    "metadata": alert_message["metadata"]
                }
            )
        except Exception as e:
            logger.error(f"Failed to log desensitization alert: {e}")
    
    async def _send_emergency_notification(self, alert_message: Dict[str, Any]):
        """发送紧急通知"""
        
        try:
            # 发送邮件通知
            from src.notifications.email_service import EmailService
            email_service = EmailService()
            
            await email_service.send_emergency_alert(
                subject=f"CRITICAL: {alert_message['title']}",
                message=alert_message["message"],
                alert_data=alert_message
            )
            
            # 发送短信通知（如果配置了）
            from src.notifications.sms_service import SMSService
            sms_service = SMSService()
            
            await sms_service.send_emergency_alert(
                message=f"CRITICAL ALERT: {alert_message['title']} - {alert_message['message'][:100]}",
                alert_data=alert_message
            )
            
        except Exception as e:
            logger.error(f"Failed to send emergency notification: {e}")
    
    async def get_alert_statistics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """获取告警统计"""
        
        try:
            from src.security.audit_service import EnhancedAuditService
            audit_service = EnhancedAuditService()
            
            # 查询告警事件
            alert_events = await audit_service.query_audit_events(
                event_type="desensitization_alert",
                start_time=start_time,
                end_time=end_time
            )
            
            # 统计告警
            total_alerts = len(alert_events)
            critical_alerts = sum(1 for e in alert_events if e.get("details", {}).get("alert_level") == "critical")
            warning_alerts = sum(1 for e in alert_events if e.get("details", {}).get("alert_level") == "warning")
            
            # 按类型统计
            alert_types = {}
            for event in alert_events:
                alert_type = event.get("details", {}).get("alert_type", "unknown")
                alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            
            return {
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_alerts": total_alerts,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "alert_types": alert_types,
                "alert_rate": total_alerts / ((end_time - start_time).total_seconds() / 3600)  # 每小时告警数
            }
            
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {"error": str(e)}