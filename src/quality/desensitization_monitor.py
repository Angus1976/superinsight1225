"""
脱敏质量监控
基于现有质量管理系统，添加脱敏质量指标
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from src.desensitization.validator import DesensitizationValidator, ValidationResult

logger = logging.getLogger(__name__)

class DesensitizationQualityMonitor:
    """脱敏质量监控器"""
    
    def __init__(self):
        self.validator = DesensitizationValidator()
        self.monitoring_interval = 300  # 5分钟
        self.quality_thresholds = {
            "completeness_warning": 0.90,
            "completeness_critical": 0.80,
            "accuracy_warning": 0.85,
            "accuracy_critical": 0.75,
            "success_rate_warning": 0.90,
            "success_rate_critical": 0.80
        }
    
    async def start_monitoring(self):
        """开始监控"""
        logger.info("Starting desensitization quality monitoring")
        
        while True:
            try:
                await self.run_quality_check()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Quality monitoring error: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟后重试
    
    async def run_quality_check(self):
        """运行质量检查"""
        
        # 获取最近的脱敏操作
        recent_operations = await self.get_recent_desensitization_operations()
        
        if not recent_operations:
            return
        
        # 验证脱敏质量
        validation_results = []
        for operation in recent_operations:
            try:
                result = await self.validator.validate_desensitization(
                    original_text=operation.get("original_text", ""),
                    masked_text=operation.get("masked_text", ""),
                    detected_entities=operation.get("detected_entities", [])
                )
                validation_results.append(result)
            except Exception as e:
                logger.error(f"Validation failed for operation {operation.get('id')}: {e}")
        
        # 分析质量指标
        quality_metrics = await self.analyze_quality_metrics(validation_results)
        
        # 检查告警条件
        await self.check_quality_alerts(quality_metrics)
        
        # 更新质量指标
        await self.update_quality_metrics(quality_metrics)
    
    async def get_recent_desensitization_operations(self) -> List[Dict[str, Any]]:
        """获取最近的脱敏操作"""
        
        # 从审计日志中获取脱敏操作
        from src.security.audit_service import EnhancedAuditService
        audit_service = EnhancedAuditService()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=self.monitoring_interval // 60)
        
        audit_events = await audit_service.query_audit_events(
            event_type="desensitization_request",
            start_time=start_time,
            end_time=end_time
        )
        
        operations = []
        for event in audit_events:
            details = event.get("details", {})
            if details.get("original_text") and details.get("masked_text"):
                operations.append({
                    "id": event.get("id"),
                    "tenant_id": event.get("tenant_id"),
                    "user_id": event.get("user_id"),
                    "timestamp": event.get("timestamp"),
                    "original_text": details.get("original_text"),
                    "masked_text": details.get("masked_text"),
                    "detected_entities": details.get("detected_entities", [])
                })
        
        return operations
    
    async def analyze_quality_metrics(
        self, 
        validation_results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """分析质量指标"""
        
        if not validation_results:
            return {
                "total_validations": 0,
                "success_rate": 0.0,
                "average_completeness": 0.0,
                "average_accuracy": 0.0,
                "quality_grade": "N/A"
            }
        
        total_validations = len(validation_results)
        successful_validations = sum(1 for r in validation_results if r.is_valid)
        
        success_rate = successful_validations / total_validations
        avg_completeness = sum(r.completeness_score for r in validation_results) / total_validations
        avg_accuracy = sum(r.accuracy_score for r in validation_results) / total_validations
        
        # 计算综合质量评分
        overall_score = (success_rate + avg_completeness + avg_accuracy) / 3
        quality_grade = self._calculate_quality_grade(overall_score)
        
        # 统计问题类型
        issue_types = {}
        for result in validation_results:
            for issue in result.issues:
                issue_type = self._categorize_issue(issue)
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "success_rate": success_rate,
            "average_completeness": avg_completeness,
            "average_accuracy": avg_accuracy,
            "overall_score": overall_score,
            "quality_grade": quality_grade,
            "issue_types": issue_types,
            "validation_results": [r.__dict__ for r in validation_results]
        }
    
    async def check_quality_alerts(self, quality_metrics: Dict[str, Any]):
        """检查质量告警"""
        
        alerts = []
        
        # 检查成功率
        success_rate = quality_metrics.get("success_rate", 0.0)
        if success_rate < self.quality_thresholds["success_rate_critical"]:
            alerts.append({
                "level": "critical",
                "type": "success_rate",
                "message": f"Desensitization success rate critically low: {success_rate:.1%}",
                "value": success_rate,
                "threshold": self.quality_thresholds["success_rate_critical"]
            })
        elif success_rate < self.quality_thresholds["success_rate_warning"]:
            alerts.append({
                "level": "warning",
                "type": "success_rate",
                "message": f"Desensitization success rate below warning threshold: {success_rate:.1%}",
                "value": success_rate,
                "threshold": self.quality_thresholds["success_rate_warning"]
            })
        
        # 检查完整性
        completeness = quality_metrics.get("average_completeness", 0.0)
        if completeness < self.quality_thresholds["completeness_critical"]:
            alerts.append({
                "level": "critical",
                "type": "completeness",
                "message": f"Desensitization completeness critically low: {completeness:.1%}",
                "value": completeness,
                "threshold": self.quality_thresholds["completeness_critical"]
            })
        elif completeness < self.quality_thresholds["completeness_warning"]:
            alerts.append({
                "level": "warning",
                "type": "completeness",
                "message": f"Desensitization completeness below warning threshold: {completeness:.1%}",
                "value": completeness,
                "threshold": self.quality_thresholds["completeness_warning"]
            })
        
        # 检查准确性
        accuracy = quality_metrics.get("average_accuracy", 0.0)
        if accuracy < self.quality_thresholds["accuracy_critical"]:
            alerts.append({
                "level": "critical",
                "type": "accuracy",
                "message": f"Desensitization accuracy critically low: {accuracy:.1%}",
                "value": accuracy,
                "threshold": self.quality_thresholds["accuracy_critical"]
            })
        elif accuracy < self.quality_thresholds["accuracy_warning"]:
            alerts.append({
                "level": "warning",
                "type": "accuracy",
                "message": f"Desensitization accuracy below warning threshold: {accuracy:.1%}",
                "value": accuracy,
                "threshold": self.quality_thresholds["accuracy_warning"]
            })
        
        # 发送告警
        for alert in alerts:
            await self.send_quality_alert(alert)
    
    async def send_quality_alert(self, alert: Dict[str, Any]):
        """发送质量告警"""
        try:
            # 集成现有告警系统
            from src.monitoring.alert_manager import AlertManager
            alert_manager = AlertManager()
            
            await alert_manager.send_alert(
                title=f"Desensitization Quality Alert - {alert['type'].title()}",
                message=alert["message"],
                level=alert["level"],
                tags=["desensitization", "quality", alert["type"]],
                metadata=alert
            )
            
            logger.warning(f"Quality alert sent: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Failed to send quality alert: {e}")
    
    async def update_quality_metrics(self, quality_metrics: Dict[str, Any]):
        """更新质量指标"""
        try:
            # 存储到时序数据库或指标系统
            from src.monitoring.metrics_collector import MetricsCollector
            metrics_collector = MetricsCollector()
            
            await metrics_collector.record_metrics("desensitization_quality", {
                "success_rate": quality_metrics.get("success_rate", 0.0),
                "completeness": quality_metrics.get("average_completeness", 0.0),
                "accuracy": quality_metrics.get("average_accuracy", 0.0),
                "overall_score": quality_metrics.get("overall_score", 0.0),
                "total_validations": quality_metrics.get("total_validations", 0)
            })
            
        except Exception as e:
            logger.error(f"Failed to update quality metrics: {e}")
    
    def _calculate_quality_grade(self, score: float) -> str:
        """计算质量等级"""
        if score >= 0.95:
            return "A+"
        elif score >= 0.90:
            return "A"
        elif score >= 0.85:
            return "B+"
        elif score >= 0.80:
            return "B"
        elif score >= 0.70:
            return "C"
        else:
            return "D"
    
    def _categorize_issue(self, issue: str) -> str:
        """分类问题类型"""
        issue_lower = issue.lower()
        
        if "completeness" in issue_lower:
            return "completeness"
        elif "accuracy" in issue_lower:
            return "accuracy"
        elif "leakage" in issue_lower:
            return "data_leakage"
        elif "format" in issue_lower:
            return "format_preservation"
        elif "length" in issue_lower:
            return "length_change"
        else:
            return "other"
    
    async def generate_quality_report(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, Any]:
        """生成脱敏质量报告"""
        
        # 获取时间范围内的所有验证结果
        operations = await self.get_desensitization_operations_in_range(start_time, end_time)
        
        validation_results = []
        for operation in operations:
            try:
                result = await self.validator.validate_desensitization(
                    original_text=operation.get("original_text", ""),
                    masked_text=operation.get("masked_text", ""),
                    detected_entities=operation.get("detected_entities", [])
                )
                validation_results.append(result)
            except Exception as e:
                logger.error(f"Validation failed for operation {operation.get('id')}: {e}")
        
        # 生成报告
        report = await self.validator.generate_validation_report(validation_results)
        
        # 添加时间范围信息
        report["report_period"] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_hours": (end_time - start_time).total_seconds() / 3600
        }
        
        return report
    
    async def get_desensitization_operations_in_range(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """获取时间范围内的脱敏操作"""
        
        from src.security.audit_service import EnhancedAuditService
        audit_service = EnhancedAuditService()
        
        audit_events = await audit_service.query_audit_events(
            event_type="desensitization_request",
            start_time=start_time,
            end_time=end_time
        )
        
        operations = []
        for event in audit_events:
            details = event.get("details", {})
            if details.get("original_text") and details.get("masked_text"):
                operations.append({
                    "id": event.get("id"),
                    "tenant_id": event.get("tenant_id"),
                    "user_id": event.get("user_id"),
                    "timestamp": event.get("timestamp"),
                    "original_text": details.get("original_text"),
                    "masked_text": details.get("masked_text"),
                    "detected_entities": details.get("detected_entities", [])
                })
        
        return operations