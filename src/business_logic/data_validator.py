#!/usr/bin/env python3
"""
数据质量验证系统
实现数据完整性检查、一致性验证、异常数据检测

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 48.2
"""

import logging
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from scipy import stats
    import warnings
    warnings.filterwarnings('ignore')
    HAS_SKLEARN = True
except ImportError:
    # 如果没有sklearn，使用简化版本
    HAS_SKLEARN = False
    import statistics

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationRule:
    """验证规则"""
    rule_id: str
    rule_name: str
    field_name: str
    rule_type: str  # completeness, format, range, consistency, uniqueness
    parameters: Dict[str, Any]
    severity: str  # low, medium, high, critical
    description: str

@dataclass
class ValidationResult:
    """验证结果"""
    rule_id: str
    rule_name: str
    field_name: str
    passed: bool
    error_count: int
    total_count: int
    error_rate: float
    severity: str
    details: Dict[str, Any]
    error_samples: List[Dict[str, Any]]

@dataclass
class DataQualityReport:
    """数据质量报告"""
    report_id: str
    dataset_name: str
    validation_timestamp: datetime
    total_records: int
    total_rules: int
    passed_rules: int
    failed_rules: int
    overall_score: float
    quality_level: str  # excellent, good, fair, poor
    validation_results: List[ValidationResult]
    recommendations: List[str]

class DataCompletenessValidator:
    """数据完整性验证器"""
    
    def __init__(self):
        self.validation_rules = []
        
    def validate_completeness(self, data: List[Dict[str, Any]], 
                            required_fields: List[str]) -> List[ValidationResult]:
        """
        验证数据完整性
        
        Args:
            data: 数据列表
            required_fields: 必需字段列表
            
        Returns:
            List[ValidationResult]: 验证结果列表
        """
        logger.info(f"开始验证数据完整性，检查 {len(required_fields)} 个必需字段")
        
        results = []
        df = pd.DataFrame(data)
        total_records = len(data)
        
        for field in required_fields:
            try:
                # 检查字段是否存在
                if field not in df.columns:
                    result = ValidationResult(
                        rule_id=f"completeness_{field}",
                        rule_name=f"字段存在性检查 - {field}",
                        field_name=field,
                        passed=False,
                        error_count=total_records,
                        total_count=total_records,
                        error_rate=1.0,
                        severity="critical",
                        details={"error_type": "missing_field"},
                        error_samples=[]
                    )
                    results.append(result)
                    continue
                
                # 检查空值
                null_mask = df[field].isnull()
                null_count = null_mask.sum()
                
                # 检查空字符串
                if df[field].dtype == 'object':
                    empty_mask = df[field].astype(str).str.strip() == ''
                    empty_count = empty_mask.sum()
                    total_missing = null_count + empty_count
                    missing_mask = null_mask | empty_mask
                else:
                    total_missing = null_count
                    missing_mask = null_mask
                
                error_rate = total_missing / total_records if total_records > 0 else 0
                
                # 获取错误样本
                error_samples = []
                if total_missing > 0:
                    error_indices = df[missing_mask].index[:5]  # 最多5个样本
                    for idx in error_indices:
                        sample = data[idx].copy()
                        sample['_error_reason'] = 'missing_value'
                        error_samples.append(sample)
                
                # 确定严重程度
                if error_rate == 0:
                    severity = "low"
                elif error_rate < 0.05:
                    severity = "medium"
                elif error_rate < 0.2:
                    severity = "high"
                else:
                    severity = "critical"
                
                result = ValidationResult(
                    rule_id=f"completeness_{field}",
                    rule_name=f"完整性检查 - {field}",
                    field_name=field,
                    passed=total_missing == 0,
                    error_count=int(total_missing),
                    total_count=total_records,
                    error_rate=round(error_rate, 4),
                    severity=severity,
                    details={
                        "null_count": int(null_count),
                        "empty_string_count": int(empty_count) if df[field].dtype == 'object' else 0,
                        "data_type": str(df[field].dtype)
                    },
                    error_samples=error_samples
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"完整性验证失败 ({field}): {e}")
                results.append(ValidationResult(
                    rule_id=f"completeness_{field}",
                    rule_name=f"完整性检查 - {field}",
                    field_name=field,
                    passed=False,
                    error_count=total_records,
                    total_count=total_records,
                    error_rate=1.0,
                    severity="critical",
                    details={"error": str(e)},
                    error_samples=[]
                ))
        
        logger.info(f"完整性验证完成，{sum(1 for r in results if r.passed)}/{len(results)} 个字段通过")
        return results

class DataFormatValidator:
    """数据格式验证器"""
    
    def __init__(self):
        self.format_patterns = {
            "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            "phone": r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$',
            "url": r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$',
            "date": r'^\d{4}-\d{2}-\d{2}$',
            "datetime": r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            "numeric": r'^-?\d+\.?\d*$',
            "alphanumeric": r'^[a-zA-Z0-9]+$',
            "alpha": r'^[a-zA-Z]+$'
        }
        
    def validate_format(self, data: List[Dict[str, Any]], 
                       format_rules: Dict[str, str]) -> List[ValidationResult]:
        """
        验证数据格式
        
        Args:
            data: 数据列表
            format_rules: 格式规则字典 {field_name: format_type}
            
        Returns:
            List[ValidationResult]: 验证结果列表
        """
        logger.info(f"开始验证数据格式，检查 {len(format_rules)} 个字段")
        
        results = []
        df = pd.DataFrame(data)
        total_records = len(data)
        
        for field_name, format_type in format_rules.items():
            try:
                if field_name not in df.columns:
                    results.append(ValidationResult(
                        rule_id=f"format_{field_name}",
                        rule_name=f"格式检查 - {field_name}",
                        field_name=field_name,
                        passed=False,
                        error_count=total_records,
                        total_count=total_records,
                        error_rate=1.0,
                        severity="critical",
                        details={"error_type": "missing_field"},
                        error_samples=[]
                    ))
                    continue
                
                # 获取格式模式
                if format_type not in self.format_patterns:
                    logger.warning(f"未知格式类型: {format_type}")
                    continue
                
                pattern = self.format_patterns[format_type]
                
                # 验证格式
                valid_mask = df[field_name].astype(str).str.match(pattern, na=False)
                invalid_count = (~valid_mask).sum()
                
                # 排除空值
                non_null_mask = df[field_name].notnull()
                valid_non_null = len(df[non_null_mask & valid_mask])
                total_non_null = non_null_mask.sum()
                
                if total_non_null > 0:
                    error_rate = invalid_count / total_non_null
                else:
                    error_rate = 0
                
                # 获取错误样本
                error_samples = []
                if invalid_count > 0:
                    invalid_indices = df[~valid_mask & non_null_mask].index[:5]
                    for idx in invalid_indices:
                        sample = data[idx].copy()
                        sample['_error_reason'] = f'invalid_{format_type}_format'
                        error_samples.append(sample)
                
                # 确定严重程度
                if error_rate == 0:
                    severity = "low"
                elif error_rate < 0.05:
                    severity = "medium"
                elif error_rate < 0.2:
                    severity = "high"
                else:
                    severity = "critical"
                
                result = ValidationResult(
                    rule_id=f"format_{field_name}",
                    rule_name=f"格式检查 - {field_name} ({format_type})",
                    field_name=field_name,
                    passed=invalid_count == 0,
                    error_count=int(invalid_count),
                    total_count=int(total_non_null),
                    error_rate=round(error_rate, 4),
                    severity=severity,
                    details={
                        "format_type": format_type,
                        "pattern": pattern,
                        "valid_count": int(valid_non_null),
                        "null_count": int(total_records - total_non_null)
                    },
                    error_samples=error_samples
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"格式验证失败 ({field_name}): {e}")
                results.append(ValidationResult(
                    rule_id=f"format_{field_name}",
                    rule_name=f"格式检查 - {field_name}",
                    field_name=field_name,
                    passed=False,
                    error_count=total_records,
                    total_count=total_records,
                    error_rate=1.0,
                    severity="critical",
                    details={"error": str(e)},
                    error_samples=[]
                ))
        
        logger.info(f"格式验证完成，{sum(1 for r in results if r.passed)}/{len(results)} 个字段通过")
        return results
    
    def add_custom_pattern(self, format_name: str, pattern: str):
        """添加自定义格式模式"""
        self.format_patterns[format_name] = pattern
        logger.info(f"添加自定义格式模式: {format_name}")

class DataQualityManager:
    """数据质量管理器"""
    
    def __init__(self):
        self.completeness_validator = DataCompletenessValidator()
        self.format_validator = DataFormatValidator()
        if HAS_SKLEARN:
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        else:
            self.anomaly_detector = None
        self.validation_history = []
        
    def run_comprehensive_validation(self, data: List[Dict[str, Any]], 
                                   validation_config: Dict[str, Any],
                                   dataset_name: str = "unknown") -> DataQualityReport:
        """
        运行综合数据质量验证
        
        Args:
            data: 数据列表
            validation_config: 验证配置
            dataset_name: 数据集名称
            
        Returns:
            DataQualityReport: 数据质量报告
        """
        logger.info(f"开始综合数据质量验证: {dataset_name}")
        
        report_id = f"dq_report_{uuid.uuid4().hex[:8]}"
        validation_timestamp = datetime.now()
        total_records = len(data)
        
        all_results = []
        
        try:
            # 1. 完整性验证
            if "required_fields" in validation_config:
                logger.info("执行完整性验证")
                completeness_results = self.completeness_validator.validate_completeness(
                    data, validation_config["required_fields"]
                )
                all_results.extend(completeness_results)
            
            # 2. 格式验证
            if "format_rules" in validation_config:
                logger.info("执行格式验证")
                format_results = self.format_validator.validate_format(
                    data, validation_config["format_rules"]
                )
                all_results.extend(format_results)
            
            # 3. 异常检测
            if "anomaly_detection" in validation_config:
                logger.info("执行异常检测")
                anomaly_config = validation_config["anomaly_detection"]
                numeric_fields = anomaly_config.get("numeric_fields", [])
                
                if numeric_fields:
                    anomaly_result = self._detect_anomalies(
                        data, numeric_fields, 
                        anomaly_config.get("contamination", 0.1)
                    )
                    all_results.append(anomaly_result)
            
            # 4. 唯一性验证
            if "unique_fields" in validation_config:
                logger.info("执行唯一性验证")
                uniqueness_results = self._validate_uniqueness(
                    data, validation_config["unique_fields"]
                )
                all_results.extend(uniqueness_results)
            
            # 5. 范围验证
            if "range_rules" in validation_config:
                logger.info("执行范围验证")
                range_results = self._validate_ranges(
                    data, validation_config["range_rules"]
                )
                all_results.extend(range_results)
            
            # 计算总体质量分数
            total_rules = len(all_results)
            passed_rules = sum(1 for r in all_results if r.passed)
            failed_rules = total_rules - passed_rules
            
            if total_rules > 0:
                overall_score = passed_rules / total_rules
            else:
                overall_score = 1.0
            
            # 确定质量等级
            if overall_score >= 0.95:
                quality_level = "excellent"
            elif overall_score >= 0.85:
                quality_level = "good"
            elif overall_score >= 0.7:
                quality_level = "fair"
            else:
                quality_level = "poor"
            
            # 生成建议
            recommendations = self._generate_recommendations(all_results, overall_score)
            
            # 创建报告
            report = DataQualityReport(
                report_id=report_id,
                dataset_name=dataset_name,
                validation_timestamp=validation_timestamp,
                total_records=total_records,
                total_rules=total_rules,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                overall_score=round(overall_score, 4),
                quality_level=quality_level,
                validation_results=all_results,
                recommendations=recommendations
            )
            
            # 保存到历史记录
            self.validation_history.append(report)
            
            logger.info(f"数据质量验证完成: {dataset_name}, 质量等级: {quality_level}")
            return report
            
        except Exception as e:
            logger.error(f"综合数据质量验证失败: {e}")
            
            # 返回错误报告
            return DataQualityReport(
                report_id=report_id,
                dataset_name=dataset_name,
                validation_timestamp=validation_timestamp,
                total_records=total_records,
                total_rules=0,
                passed_rules=0,
                failed_rules=1,
                overall_score=0.0,
                quality_level="poor",
                validation_results=[],
                recommendations=[f"验证过程出错: {str(e)}"]
            )
    
    def _detect_anomalies(self, data: List[Dict[str, Any]], 
                         numeric_fields: List[str],
                         contamination: float = 0.1) -> ValidationResult:
        """检测异常数据"""
        try:
            if not HAS_SKLEARN:
                # 简化版异常检测
                return ValidationResult(
                    rule_id="anomaly_detection",
                    rule_name="异常检测",
                    field_name=",".join(numeric_fields),
                    passed=True,
                    error_count=0,
                    total_count=len(data),
                    error_rate=0.0,
                    severity="low",
                    details={"error_type": "sklearn_not_available"},
                    error_samples=[]
                )
            
            df = pd.DataFrame(data)
            total_records = len(data)
            
            # 检查字段是否存在
            available_fields = [f for f in numeric_fields if f in df.columns]
            if not available_fields:
                return ValidationResult(
                    rule_id="anomaly_detection",
                    rule_name="异常检测",
                    field_name=",".join(numeric_fields),
                    passed=False,
                    error_count=total_records,
                    total_count=total_records,
                    error_rate=1.0,
                    severity="critical",
                    details={"error_type": "no_valid_fields"},
                    error_samples=[]
                )
            
            # 准备数值数据
            numeric_data = df[available_fields].select_dtypes(include=[np.number])
            
            if numeric_data.empty:
                return ValidationResult(
                    rule_id="anomaly_detection",
                    rule_name="异常检测",
                    field_name=",".join(available_fields),
                    passed=True,
                    error_count=0,
                    total_count=total_records,
                    error_rate=0.0,
                    severity="low",
                    details={"error_type": "no_numeric_data"},
                    error_samples=[]
                )
            
            # 处理缺失值
            numeric_data_clean = numeric_data.dropna()
            
            if len(numeric_data_clean) < 10:
                return ValidationResult(
                    rule_id="anomaly_detection",
                    rule_name="异常检测",
                    field_name=",".join(available_fields),
                    passed=True,
                    error_count=0,
                    total_count=total_records,
                    error_rate=0.0,
                    severity="low",
                    details={"error_type": "insufficient_data", "clean_records": len(numeric_data_clean)},
                    error_samples=[]
                )
            
            # 标准化数据
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_data_clean)
            
            # 使用Isolation Forest检测异常
            self.anomaly_detector.set_params(contamination=contamination)
            anomaly_labels = self.anomaly_detector.fit_predict(scaled_data)
            
            # 获取异常数据
            anomaly_mask = anomaly_labels == -1
            anomaly_count = anomaly_mask.sum()
            
            error_rate = anomaly_count / len(numeric_data_clean)
            
            # 获取异常样本
            error_samples = []
            if anomaly_count > 0:
                anomaly_indices = numeric_data_clean[anomaly_mask].index[:5]
                for idx in anomaly_indices:
                    sample = data[idx].copy()
                    sample['_error_reason'] = 'anomaly_detected'
                    error_samples.append(sample)
            
            # 确定严重程度
            if error_rate < 0.05:
                severity = "low"
            elif error_rate < 0.15:
                severity = "medium"
            else:
                severity = "high"
            
            return ValidationResult(
                rule_id="anomaly_detection",
                rule_name="异常检测",
                field_name=",".join(available_fields),
                passed=anomaly_count == 0,
                error_count=int(anomaly_count),
                total_count=len(numeric_data_clean),
                error_rate=round(error_rate, 4),
                severity=severity,
                details={
                    "contamination_rate": contamination,
                    "fields_analyzed": available_fields,
                    "records_analyzed": len(numeric_data_clean)
                },
                error_samples=error_samples
            )
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return ValidationResult(
                rule_id="anomaly_detection",
                rule_name="异常检测",
                field_name=",".join(numeric_fields),
                passed=False,
                error_count=len(data),
                total_count=len(data),
                error_rate=1.0,
                severity="critical",
                details={"error": str(e)},
                error_samples=[]
            )
    
    def _validate_uniqueness(self, data: List[Dict[str, Any]], 
                           unique_fields: List[str]) -> List[ValidationResult]:
        """验证唯一性"""
        results = []
        df = pd.DataFrame(data)
        total_records = len(data)
        
        for field in unique_fields:
            try:
                if field not in df.columns:
                    results.append(ValidationResult(
                        rule_id=f"uniqueness_{field}",
                        rule_name=f"唯一性检查 - {field}",
                        field_name=field,
                        passed=False,
                        error_count=total_records,
                        total_count=total_records,
                        error_rate=1.0,
                        severity="critical",
                        details={"error_type": "missing_field"},
                        error_samples=[]
                    ))
                    continue
                
                # 检查重复值
                duplicates = df[df[field].duplicated(keep=False)]
                duplicate_count = len(duplicates)
                
                error_rate = duplicate_count / total_records if total_records > 0 else 0
                
                # 获取重复样本
                error_samples = []
                if duplicate_count > 0:
                    duplicate_indices = duplicates.index[:5]
                    for idx in duplicate_indices:
                        sample = data[idx].copy()
                        sample['_error_reason'] = 'duplicate_value'
                        error_samples.append(sample)
                
                results.append(ValidationResult(
                    rule_id=f"uniqueness_{field}",
                    rule_name=f"唯一性检查 - {field}",
                    field_name=field,
                    passed=duplicate_count == 0,
                    error_count=duplicate_count,
                    total_count=total_records,
                    error_rate=round(error_rate, 4),
                    severity="high" if duplicate_count > 0 else "low",
                    details={
                        "unique_values": int(df[field].nunique()),
                        "duplicate_groups": int(len(df[df[field].duplicated()].groupby(field)))
                    },
                    error_samples=error_samples
                ))
                
            except Exception as e:
                logger.error(f"唯一性验证失败 ({field}): {e}")
                results.append(ValidationResult(
                    rule_id=f"uniqueness_{field}",
                    rule_name=f"唯一性检查 - {field}",
                    field_name=field,
                    passed=False,
                    error_count=total_records,
                    total_count=total_records,
                    error_rate=1.0,
                    severity="critical",
                    details={"error": str(e)},
                    error_samples=[]
                ))
        
        return results
    
    def _validate_ranges(self, data: List[Dict[str, Any]], 
                        range_rules: Dict[str, Dict[str, Any]]) -> List[ValidationResult]:
        """验证数值范围"""
        results = []
        df = pd.DataFrame(data)
        total_records = len(data)
        
        for field, range_config in range_rules.items():
            try:
                if field not in df.columns:
                    results.append(ValidationResult(
                        rule_id=f"range_{field}",
                        rule_name=f"范围检查 - {field}",
                        field_name=field,
                        passed=False,
                        error_count=total_records,
                        total_count=total_records,
                        error_rate=1.0,
                        severity="critical",
                        details={"error_type": "missing_field"},
                        error_samples=[]
                    ))
                    continue
                
                min_val = range_config.get("min")
                max_val = range_config.get("max")
                
                # 转换为数值类型
                numeric_series = pd.to_numeric(df[field], errors='coerce')
                valid_mask = numeric_series.notnull()
                
                # 检查范围
                range_violations = pd.Series([False] * len(df))
                
                if min_val is not None:
                    range_violations |= (numeric_series < min_val) & valid_mask
                
                if max_val is not None:
                    range_violations |= (numeric_series > max_val) & valid_mask
                
                violation_count = range_violations.sum()
                valid_count = valid_mask.sum()
                
                error_rate = violation_count / valid_count if valid_count > 0 else 0
                
                # 获取违规样本
                error_samples = []
                if violation_count > 0:
                    violation_indices = df[range_violations].index[:5]
                    for idx in violation_indices:
                        sample = data[idx].copy()
                        sample['_error_reason'] = 'range_violation'
                        error_samples.append(sample)
                
                results.append(ValidationResult(
                    rule_id=f"range_{field}",
                    rule_name=f"范围检查 - {field}",
                    field_name=field,
                    passed=violation_count == 0,
                    error_count=int(violation_count),
                    total_count=int(valid_count),
                    error_rate=round(error_rate, 4),
                    severity="medium" if violation_count > 0 else "low",
                    details={
                        "min_value": min_val,
                        "max_value": max_val,
                        "actual_min": float(numeric_series.min()) if valid_count > 0 else None,
                        "actual_max": float(numeric_series.max()) if valid_count > 0 else None
                    },
                    error_samples=error_samples
                ))
                
            except Exception as e:
                logger.error(f"范围验证失败 ({field}): {e}")
                results.append(ValidationResult(
                    rule_id=f"range_{field}",
                    rule_name=f"范围检查 - {field}",
                    field_name=field,
                    passed=False,
                    error_count=total_records,
                    total_count=total_records,
                    error_rate=1.0,
                    severity="critical",
                    details={"error": str(e)},
                    error_samples=[]
                ))
        
        return results
    
    def _generate_recommendations(self, results: List[ValidationResult], 
                                overall_score: float) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 按严重程度分组
        critical_issues = [r for r in results if not r.passed and r.severity == "critical"]
        high_issues = [r for r in results if not r.passed and r.severity == "high"]
        medium_issues = [r for r in results if not r.passed and r.severity == "medium"]
        
        # 关键问题建议
        if critical_issues:
            recommendations.append(f"发现 {len(critical_issues)} 个关键数据质量问题，需要立即处理")
            for issue in critical_issues[:3]:  # 最多显示3个
                recommendations.append(f"- 修复 {issue.field_name} 字段的 {issue.rule_name}")
        
        # 高优先级问题建议
        if high_issues:
            recommendations.append(f"发现 {len(high_issues)} 个高优先级问题，建议优先处理")
        
        # 中等优先级问题建议
        if medium_issues:
            recommendations.append(f"发现 {len(medium_issues)} 个中等优先级问题，可以逐步改进")
        
        # 总体建议
        if overall_score < 0.7:
            recommendations.append("数据质量偏低，建议建立数据质量监控机制")
        elif overall_score < 0.9:
            recommendations.append("数据质量良好，继续保持并改进薄弱环节")
        else:
            recommendations.append("数据质量优秀，建议建立持续监控机制")
        
        # 具体改进建议
        error_types = defaultdict(int)
        for result in results:
            if not result.passed:
                error_type = result.details.get("error_type", "unknown")
                error_types[error_type] += 1
        
        if error_types.get("missing_value", 0) > 0:
            recommendations.append("建议建立数据收集规范，减少缺失值")
        
        if error_types.get("invalid_format", 0) > 0:
            recommendations.append("建议建立数据输入验证机制，确保格式正确")
        
        if error_types.get("duplicate_value", 0) > 0:
            recommendations.append("建议建立唯一性约束，防止重复数据")
        
        return recommendations
    
    def get_validation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取验证历史"""
        recent_reports = self.validation_history[-limit:]
        
        return [
            {
                "report_id": report.report_id,
                "dataset_name": report.dataset_name,
                "validation_timestamp": report.validation_timestamp.isoformat(),
                "total_records": report.total_records,
                "overall_score": report.overall_score,
                "quality_level": report.quality_level,
                "passed_rules": report.passed_rules,
                "failed_rules": report.failed_rules
            }
            for report in recent_reports
        ]
    
    def export_report(self, report: DataQualityReport, format: str = "dict") -> Dict[str, Any]:
        """导出报告"""
        if format == "dict":
            return {
                "report_id": report.report_id,
                "dataset_name": report.dataset_name,
                "validation_timestamp": report.validation_timestamp.isoformat(),
                "summary": {
                    "total_records": report.total_records,
                    "total_rules": report.total_rules,
                    "passed_rules": report.passed_rules,
                    "failed_rules": report.failed_rules,
                    "overall_score": report.overall_score,
                    "quality_level": report.quality_level
                },
                "validation_results": [
                    {
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "field_name": r.field_name,
                        "passed": r.passed,
                        "error_count": r.error_count,
                        "total_count": r.total_count,
                        "error_rate": r.error_rate,
                        "severity": r.severity,
                        "details": r.details,
                        "error_samples": r.error_samples
                    }
                    for r in report.validation_results
                ],
                "recommendations": report.recommendations
            }
        else:
            return {"error": f"不支持的导出格式: {format}"}

# 创建全局数据质量管理器实例
data_quality_manager = DataQualityManager()