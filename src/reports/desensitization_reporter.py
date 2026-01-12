"""
脱敏效果报告生成器
基于现有报告生成模式，生成脱敏效果报告
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import logging

from src.desensitization.validator import DesensitizationValidator
from src.quality.desensitization_monitor import DesensitizationQualityMonitor
from src.reports.base_reporter import BaseReporter

logger = logging.getLogger(__name__)

class DesensitizationReporter(BaseReporter):
    """脱敏报告生成器"""
    
    def __init__(self):
        super().__init__()
        self.validator = DesensitizationValidator()
        self.quality_monitor = DesensitizationQualityMonitor()
    
    async def generate_daily_report(self, date: datetime, tenant_id: str = None) -> Dict[str, Any]:
        """生成日报"""
        
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        return await self._generate_report(
            start_time=start_time,
            end_time=end_time,
            tenant_id=tenant_id,
            report_type="daily"
        )
    
    async def generate_weekly_report(self, week_start: datetime, tenant_id: str = None) -> Dict[str, Any]:
        """生成周报"""
        
        start_time = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)
        
        return await self._generate_report(
            start_time=start_time,
            end_time=end_time,
            tenant_id=tenant_id,
            report_type="weekly"
        )
    
    async def generate_monthly_report(self, month_start: datetime, tenant_id: str = None) -> Dict[str, Any]:
        """生成月报"""
        
        start_time = month_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 计算下个月第一天
        if start_time.month == 12:
            end_time = start_time.replace(year=start_time.year + 1, month=1)
        else:
            end_time = start_time.replace(month=start_time.month + 1)
        
        return await self._generate_report(
            start_time=start_time,
            end_time=end_time,
            tenant_id=tenant_id,
            report_type="monthly"
        )
    
    async def _generate_report(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        tenant_id: str = None,
        report_type: str = "custom"
    ) -> Dict[str, Any]:
        """生成报告"""
        
        try:
            # 获取脱敏操作数据
            operations = await self._get_operations_data(start_time, end_time, tenant_id)
            
            # 生成验证结果
            validation_results = await self._validate_operations(operations)
            
            # 生成统计信息
            statistics = await self._generate_statistics(operations, validation_results)
            
            # 生成趋势分析
            trends = await self._analyze_trends(start_time, end_time, tenant_id)
            
            # 生成问题分析
            issues_analysis = await self._analyze_issues(validation_results)
            
            # 生成改进建议
            recommendations = await self._generate_recommendations(statistics, issues_analysis)
            
            report = {
                "report_info": {
                    "type": report_type,
                    "period": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "tenant_id": tenant_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "generator": "DesensitizationReporter"
                },
                "executive_summary": await self._generate_executive_summary(statistics),
                "statistics": statistics,
                "trends": trends,
                "quality_analysis": {
                    "validation_results": len(validation_results),
                    "success_rate": statistics.get("success_rate", 0.0),
                    "average_completeness": statistics.get("average_completeness", 0.0),
                    "average_accuracy": statistics.get("average_accuracy", 0.0),
                    "quality_grade": statistics.get("quality_grade", "N/A")
                },
                "issues_analysis": issues_analysis,
                "recommendations": recommendations,
                "detailed_results": [r.__dict__ for r in validation_results[:100]]  # 限制详细结果数量
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate desensitization report: {e}")
            return {
                "error": str(e),
                "report_info": {
                    "type": report_type,
                    "period": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat()
                    },
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
    
    async def _get_operations_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        tenant_id: str = None
    ) -> List[Dict[str, Any]]:
        """获取脱敏操作数据"""
        
        from src.security.audit_service import EnhancedAuditService
        audit_service = EnhancedAuditService()
        
        # 构建查询条件
        query_params = {
            "event_type": "desensitization_request",
            "start_time": start_time,
            "end_time": end_time
        }
        
        if tenant_id:
            query_params["tenant_id"] = tenant_id
        
        audit_events = await audit_service.query_audit_events(**query_params)
        
        operations = []
        for event in audit_events:
            details = event.get("details", {})
            operations.append({
                "id": event.get("id"),
                "tenant_id": event.get("tenant_id"),
                "user_id": event.get("user_id"),
                "timestamp": event.get("timestamp"),
                "data_type": details.get("data_type"),
                "original_length": len(details.get("original_text", "")),
                "masked_length": len(details.get("masked_text", "")),
                "entities_detected": len(details.get("detected_entities", [])),
                "processing_time": details.get("processing_time", 0),
                "original_text": details.get("original_text", ""),
                "masked_text": details.get("masked_text", ""),
                "detected_entities": details.get("detected_entities", [])
            })
        
        return operations
    
    async def _validate_operations(self, operations: List[Dict[str, Any]]) -> List:
        """验证脱敏操作"""
        
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
        
        return validation_results
    
    async def _generate_statistics(
        self, 
        operations: List[Dict[str, Any]], 
        validation_results: List
    ) -> Dict[str, Any]:
        """生成统计信息"""
        
        if not operations:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "average_completeness": 0.0,
                "average_accuracy": 0.0,
                "quality_grade": "N/A"
            }
        
        total_operations = len(operations)
        successful_validations = sum(1 for r in validation_results if r.is_valid)
        
        success_rate = successful_validations / len(validation_results) if validation_results else 0.0
        avg_completeness = sum(r.completeness_score for r in validation_results) / len(validation_results) if validation_results else 0.0
        avg_accuracy = sum(r.accuracy_score for r in validation_results) / len(validation_results) if validation_results else 0.0
        
        # 数据类型统计
        data_type_stats = {}
        for op in operations:
            data_type = op.get("data_type", "unknown")
            data_type_stats[data_type] = data_type_stats.get(data_type, 0) + 1
        
        # 处理时间统计
        processing_times = [op.get("processing_time", 0) for op in operations if op.get("processing_time")]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        
        # 实体检测统计
        total_entities = sum(op.get("entities_detected", 0) for op in operations)
        avg_entities_per_operation = total_entities / total_operations if total_operations > 0 else 0.0
        
        # 文本长度统计
        original_lengths = [op.get("original_length", 0) for op in operations]
        masked_lengths = [op.get("masked_length", 0) for op in operations]
        
        avg_original_length = sum(original_lengths) / len(original_lengths) if original_lengths else 0.0
        avg_masked_length = sum(masked_lengths) / len(masked_lengths) if masked_lengths else 0.0
        
        return {
            "total_operations": total_operations,
            "successful_validations": successful_validations,
            "success_rate": success_rate,
            "average_completeness": avg_completeness,
            "average_accuracy": avg_accuracy,
            "quality_grade": self._calculate_quality_grade((success_rate + avg_completeness + avg_accuracy) / 3),
            "data_type_distribution": data_type_stats,
            "performance": {
                "average_processing_time": avg_processing_time,
                "total_entities_detected": total_entities,
                "average_entities_per_operation": avg_entities_per_operation
            },
            "text_statistics": {
                "average_original_length": avg_original_length,
                "average_masked_length": avg_masked_length,
                "average_length_change": avg_masked_length - avg_original_length
            }
        }
    
    async def _analyze_trends(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        tenant_id: str = None
    ) -> Dict[str, Any]:
        """分析趋势"""
        
        # 按天分组统计
        daily_stats = {}
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            day_operations = await self._get_operations_data(day_start, day_end, tenant_id)
            day_validations = await self._validate_operations(day_operations)
            
            daily_stats[current_date.isoformat()] = {
                "operations_count": len(day_operations),
                "success_rate": sum(1 for r in day_validations if r.is_valid) / len(day_validations) if day_validations else 0.0,
                "avg_completeness": sum(r.completeness_score for r in day_validations) / len(day_validations) if day_validations else 0.0,
                "avg_accuracy": sum(r.accuracy_score for r in day_validations) / len(day_validations) if day_validations else 0.0
            }
            
            current_date += timedelta(days=1)
        
        # 计算趋势
        success_rates = [stats["success_rate"] for stats in daily_stats.values()]
        completeness_scores = [stats["avg_completeness"] for stats in daily_stats.values()]
        accuracy_scores = [stats["avg_accuracy"] for stats in daily_stats.values()]
        
        return {
            "daily_statistics": daily_stats,
            "trends": {
                "success_rate_trend": self._calculate_trend(success_rates),
                "completeness_trend": self._calculate_trend(completeness_scores),
                "accuracy_trend": self._calculate_trend(accuracy_scores)
            }
        }
    
    async def _analyze_issues(self, validation_results: List) -> Dict[str, Any]:
        """分析问题"""
        
        if not validation_results:
            return {"total_issues": 0, "issue_categories": {}}
        
        all_issues = []
        for result in validation_results:
            all_issues.extend(result.issues)
        
        # 分类问题
        issue_categories = {}
        for issue in all_issues:
            category = self._categorize_issue(issue)
            issue_categories[category] = issue_categories.get(category, 0) + 1
        
        # 找出最常见的问题
        common_issues = sorted(issue_categories.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_issues": len(all_issues),
            "issue_categories": issue_categories,
            "most_common_issues": common_issues,
            "issue_rate": len(all_issues) / len(validation_results) if validation_results else 0.0
        }
    
    async def _generate_recommendations(
        self, 
        statistics: Dict[str, Any], 
        issues_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # 基于成功率的建议
        success_rate = statistics.get("success_rate", 0.0)
        if success_rate < 0.8:
            recommendations.append("Success rate is below 80%. Consider reviewing detection algorithms and masking policies.")
        
        # 基于完整性的建议
        completeness = statistics.get("average_completeness", 0.0)
        if completeness < 0.9:
            recommendations.append("Completeness score is below 90%. Review detection patterns to ensure all sensitive data is identified.")
        
        # 基于准确性的建议
        accuracy = statistics.get("average_accuracy", 0.0)
        if accuracy < 0.85:
            recommendations.append("Accuracy score is below 85%. Fine-tune detection algorithms to reduce false positives.")
        
        # 基于问题分析的建议
        common_issues = issues_analysis.get("most_common_issues", [])
        for issue_type, count in common_issues:
            if issue_type == "data_leakage" and count > 0:
                recommendations.append("Data leakage detected. Review masking rules to ensure complete protection.")
            elif issue_type == "format_preservation" and count > 0:
                recommendations.append("Format preservation issues detected. Adjust masking techniques to maintain data structure.")
            elif issue_type == "completeness" and count > 0:
                recommendations.append("Completeness issues detected. Expand detection patterns and improve sensitivity.")
        
        # 性能建议
        avg_processing_time = statistics.get("performance", {}).get("average_processing_time", 0)
        if avg_processing_time > 5.0:  # 5秒
            recommendations.append("Processing time is high. Consider optimizing detection algorithms or implementing caching.")
        
        return recommendations
    
    async def _generate_executive_summary(self, statistics: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行摘要"""
        
        return {
            "overview": f"Processed {statistics.get('total_operations', 0)} desensitization operations with {statistics.get('success_rate', 0.0):.1%} success rate.",
            "quality_assessment": f"Overall quality grade: {statistics.get('quality_grade', 'N/A')}",
            "key_metrics": {
                "success_rate": f"{statistics.get('success_rate', 0.0):.1%}",
                "completeness": f"{statistics.get('average_completeness', 0.0):.1%}",
                "accuracy": f"{statistics.get('average_accuracy', 0.0):.1%}"
            },
            "performance": f"Average processing time: {statistics.get('performance', {}).get('average_processing_time', 0):.2f}s"
        }
    
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
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"
        
        # 简单的线性趋势计算
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        change = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
        
        if change > 0.05:
            return "improving"
        elif change < -0.05:
            return "declining"
        else:
            return "stable"
    
    def _categorize_issue(self, issue: str) -> str:
        """分类问题"""
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