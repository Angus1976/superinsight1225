"""
脱敏效果验证服务
验证脱敏完整性和准确性
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    completeness_score: float  # 完整性评分 (0-1)
    accuracy_score: float      # 准确性评分 (0-1)
    issues: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]

@dataclass
class ValidationMetrics:
    """验证指标"""
    total_entities: int
    masked_entities: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float

class DesensitizationValidator:
    """脱敏验证器"""
    
    def __init__(self):
        self.validation_patterns = self._load_validation_patterns()
        self.quality_thresholds = {
            "completeness_min": 0.95,
            "accuracy_min": 0.90,
            "precision_min": 0.85,
            "recall_min": 0.90
        }
    
    def _load_validation_patterns(self) -> Dict[str, str]:
        """加载验证模式"""
        return {
            "phone": r'\b\d{3}-\d{3}-\d{4}\b|\b\d{11}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "id_card": r'\b\d{15}|\d{18}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "bank_account": r'\b\d{16,19}\b',
            "name": r'\b[A-Za-z\u4e00-\u9fff]{2,10}\b'
        }
    
    async def validate_desensitization(
        self, 
        original_text: str, 
        masked_text: str,
        detected_entities: List[Dict[str, Any]] = None,
        expected_entities: List[Dict[str, Any]] = None
    ) -> ValidationResult:
        """验证脱敏效果"""
        
        issues = []
        recommendations = []
        
        # 1. 完整性验证
        completeness_score = await self._validate_completeness(
            original_text, masked_text, detected_entities
        )
        
        if completeness_score < self.quality_thresholds["completeness_min"]:
            issues.append(f"Completeness score {completeness_score:.2f} below threshold")
            recommendations.append("Review detection patterns and increase sensitivity")
        
        # 2. 准确性验证
        accuracy_score = await self._validate_accuracy(
            original_text, masked_text, detected_entities, expected_entities
        )
        
        if accuracy_score < self.quality_thresholds["accuracy_min"]:
            issues.append(f"Accuracy score {accuracy_score:.2f} below threshold")
            recommendations.append("Fine-tune detection algorithms and reduce false positives")
        
        # 3. 数据泄露检查
        leakage_issues = await self._check_data_leakage(original_text, masked_text)
        issues.extend(leakage_issues)
        
        # 4. 格式保持验证
        format_issues = await self._validate_format_preservation(original_text, masked_text)
        issues.extend(format_issues)
        
        # 5. 计算验证指标
        metrics = await self._calculate_metrics(detected_entities, expected_entities)
        
        # 综合评估
        is_valid = (
            completeness_score >= self.quality_thresholds["completeness_min"] and
            accuracy_score >= self.quality_thresholds["accuracy_min"] and
            len(leakage_issues) == 0
        )
        
        return ValidationResult(
            is_valid=is_valid,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            issues=issues,
            recommendations=recommendations,
            metadata={
                "validation_timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics.__dict__ if metrics else None,
                "original_length": len(original_text),
                "masked_length": len(masked_text),
                "entities_detected": len(detected_entities) if detected_entities else 0
            }
        )
    
    async def _validate_completeness(
        self, 
        original_text: str, 
        masked_text: str, 
        detected_entities: List[Dict[str, Any]]
    ) -> float:
        """验证脱敏完整性"""
        
        # 使用验证模式检查原文中的敏感信息
        total_sensitive_items = 0
        masked_items = 0
        
        for entity_type, pattern in self.validation_patterns.items():
            # 在原文中查找敏感信息
            original_matches = re.findall(pattern, original_text, re.IGNORECASE)
            total_sensitive_items += len(original_matches)
            
            # 检查这些信息是否在脱敏文本中被处理
            for match in original_matches:
                if match not in masked_text:
                    masked_items += 1
        
        # 计算完整性评分
        if total_sensitive_items == 0:
            return 1.0  # 没有敏感信息，完整性为100%
        
        return masked_items / total_sensitive_items
    
    async def _validate_accuracy(
        self, 
        original_text: str, 
        masked_text: str,
        detected_entities: List[Dict[str, Any]],
        expected_entities: List[Dict[str, Any]]
    ) -> float:
        """验证脱敏准确性"""
        
        if not detected_entities and not expected_entities:
            return 1.0
        
        if not expected_entities:
            # 使用启发式方法评估准确性
            return await self._heuristic_accuracy_assessment(original_text, detected_entities)
        
        # 基于期望实体计算准确性
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        detected_set = {(e.get('start', 0), e.get('end', 0), e.get('entity_type', '')) for e in detected_entities}
        expected_set = {(e.get('start', 0), e.get('end', 0), e.get('entity_type', '')) for e in expected_entities}
        
        true_positives = len(detected_set.intersection(expected_set))
        false_positives = len(detected_set - expected_set)
        false_negatives = len(expected_set - detected_set)
        
        if true_positives + false_positives == 0:
            precision = 0.0
        else:
            precision = true_positives / (true_positives + false_positives)
        
        if true_positives + false_negatives == 0:
            recall = 0.0
        else:
            recall = true_positives / (true_positives + false_negatives)
        
        # 使用F1分数作为准确性指标
        if precision + recall == 0:
            return 0.0
        
        f1_score = 2 * (precision * recall) / (precision + recall)
        return f1_score
    
    async def _heuristic_accuracy_assessment(
        self, 
        original_text: str, 
        detected_entities: List[Dict[str, Any]]
    ) -> float:
        """启发式准确性评估"""
        
        if not detected_entities:
            return 1.0
        
        accurate_detections = 0
        total_detections = len(detected_entities)
        
        for entity in detected_entities:
            start = entity.get('start', 0)
            end = entity.get('end', 0)
            entity_type = entity.get('entity_type', '')
            
            if start < len(original_text) and end <= len(original_text):
                entity_text = original_text[start:end]
                
                # 检查检测是否合理
                if self._is_reasonable_detection(entity_text, entity_type):
                    accurate_detections += 1
        
        return accurate_detections / total_detections if total_detections > 0 else 1.0
    
    def _is_reasonable_detection(self, text: str, entity_type: str) -> bool:
        """检查检测是否合理"""
        
        if entity_type.lower() in self.validation_patterns:
            pattern = self.validation_patterns[entity_type.lower()]
            return bool(re.match(pattern, text, re.IGNORECASE))
        
        # 通用合理性检查
        if len(text.strip()) < 2:
            return False
        
        if entity_type.lower() in ['person', 'name'] and not re.match(r'^[A-Za-z\u4e00-\u9fff\s]+$', text):
            return False
        
        return True
    
    async def _check_data_leakage(self, original_text: str, masked_text: str) -> List[str]:
        """检查数据泄露"""
        
        issues = []
        
        # 检查明显的敏感信息泄露
        for entity_type, pattern in self.validation_patterns.items():
            matches = re.findall(pattern, masked_text, re.IGNORECASE)
            if matches:
                issues.append(f"Potential {entity_type} leakage detected: {len(matches)} instances")
        
        # 检查部分脱敏是否过于宽松
        common_sensitive_patterns = [
            r'\b\d{4}\*{4}\d{4}\b',  # 信用卡部分脱敏
            r'\b\d{3}\*{4}\d{4}\b',  # 手机号部分脱敏
        ]
        
        for pattern in common_sensitive_patterns:
            if re.search(pattern, masked_text):
                # 检查是否泄露过多信息
                matches = re.findall(pattern, masked_text)
                for match in matches:
                    visible_digits = len(re.findall(r'\d', match))
                    total_length = len(match.replace('*', ''))
                    if visible_digits / total_length > 0.5:  # 超过50%可见
                        issues.append(f"Excessive information exposure in partial masking: {match}")
        
        return issues
    
    async def _validate_format_preservation(self, original_text: str, masked_text: str) -> List[str]:
        """验证格式保持"""
        
        issues = []
        
        # 检查文本长度变化
        length_change = abs(len(masked_text) - len(original_text)) / len(original_text)
        if length_change > 0.2:  # 长度变化超过20%
            issues.append(f"Significant length change: {length_change:.1%}")
        
        # 检查结构保持
        original_lines = original_text.count('\n')
        masked_lines = masked_text.count('\n')
        if original_lines != masked_lines:
            issues.append("Line structure not preserved")
        
        # 检查特殊字符保持
        special_chars = set(re.findall(r'[^\w\s]', original_text))
        masked_special_chars = set(re.findall(r'[^\w\s]', masked_text))
        
        missing_chars = special_chars - masked_special_chars
        if missing_chars:
            issues.append(f"Special characters lost: {missing_chars}")
        
        return issues
    
    async def _calculate_metrics(
        self, 
        detected_entities: List[Dict[str, Any]], 
        expected_entities: List[Dict[str, Any]]
    ) -> Optional[ValidationMetrics]:
        """计算验证指标"""
        
        if not expected_entities:
            return None
        
        detected_set = {(e.get('start', 0), e.get('end', 0)) for e in detected_entities or []}
        expected_set = {(e.get('start', 0), e.get('end', 0)) for e in expected_entities}
        
        true_positives = len(detected_set.intersection(expected_set))
        false_positives = len(detected_set - expected_set)
        false_negatives = len(expected_set - detected_set)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return ValidationMetrics(
            total_entities=len(expected_entities),
            masked_entities=len(detected_entities or []),
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )
    
    async def generate_validation_report(
        self, 
        validation_results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """生成验证报告"""
        
        if not validation_results:
            return {"error": "No validation results provided"}
        
        total_validations = len(validation_results)
        valid_count = sum(1 for r in validation_results if r.is_valid)
        
        avg_completeness = sum(r.completeness_score for r in validation_results) / total_validations
        avg_accuracy = sum(r.accuracy_score for r in validation_results) / total_validations
        
        all_issues = []
        all_recommendations = []
        
        for result in validation_results:
            all_issues.extend(result.issues)
            all_recommendations.extend(result.recommendations)
        
        # 统计最常见的问题
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "summary": {
                "total_validations": total_validations,
                "valid_count": valid_count,
                "success_rate": valid_count / total_validations,
                "average_completeness": avg_completeness,
                "average_accuracy": avg_accuracy
            },
            "quality_assessment": {
                "completeness_grade": self._get_grade(avg_completeness),
                "accuracy_grade": self._get_grade(avg_accuracy),
                "overall_grade": self._get_grade((avg_completeness + avg_accuracy) / 2)
            },
            "common_issues": common_issues,
            "recommendations": list(set(all_recommendations)),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_grade(self, score: float) -> str:
        """获取评分等级"""
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