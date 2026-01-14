"""
Quality Checker - 质量检查器
执行自动化质量检查
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.quality.quality_rule_engine import QualityRuleEngine, QualityRule, RuleResult


class QualityIssue(BaseModel):
    """质量问题"""
    rule_id: str
    rule_name: str
    severity: str  # critical, high, medium, low
    message: str
    field: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CheckResult(BaseModel):
    """检查结果"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str
    project_id: Optional[str] = None
    passed: bool
    issues: List[QualityIssue] = Field(default_factory=list)
    checked_rules: int = 0
    check_type: str = "realtime"  # realtime, batch, manual
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class BatchCheckResult(BaseModel):
    """批量检查结果"""
    project_id: str
    total_checked: int
    passed_count: int
    failed_count: int
    results: List[CheckResult] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class QualityChecker:
    """质量检查器"""
    
    def __init__(
        self,
        rule_engine: Optional[QualityRuleEngine] = None,
        alert_service: Optional[Any] = None
    ):
        """
        初始化质量检查器
        
        Args:
            rule_engine: 质量规则引擎
            alert_service: 预警服务 (可选)
        """
        self.rule_engine = rule_engine or QualityRuleEngine()
        self.alert_service = alert_service
        
        # 内存存储
        self._annotations: Dict[str, Dict[str, Any]] = {}
        self._check_results: Dict[str, CheckResult] = {}
    
    def add_annotation(self, annotation_id: str, data: Dict[str, Any], project_id: str = "default") -> None:
        """添加标注数据 (用于测试)"""
        self._annotations[annotation_id] = {
            "id": annotation_id,
            "data": data,
            "project_id": project_id
        }
    
    async def get_annotation(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """获取标注数据"""
        return self._annotations.get(annotation_id)
    
    async def check_annotation(
        self,
        annotation_id: str,
        annotation_data: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        check_type: str = "realtime"
    ) -> CheckResult:
        """
        检查单个标注
        
        Args:
            annotation_id: 标注ID
            annotation_data: 标注数据 (可选，如果不提供则从存储获取)
            project_id: 项目ID (可选)
            check_type: 检查类型
            
        Returns:
            检查结果
        """
        # 获取标注数据
        if annotation_data is None:
            annotation = await self.get_annotation(annotation_id)
            if annotation:
                annotation_data = annotation.get("data", {})
                project_id = project_id or annotation.get("project_id", "default")
            else:
                annotation_data = {}
        
        project_id = project_id or "default"
        
        # 获取活跃规则
        rules = await self.rule_engine.get_active_rules(project_id)
        
        issues: List[QualityIssue] = []
        
        for rule in rules:
            result = await self._execute_rule(annotation_data, rule)
            if not result.passed:
                issues.append(QualityIssue(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=result.message or f"Rule '{rule.name}' failed",
                    field=result.field,
                    details=result.details
                ))
        
        # 如果有严重问题，发送预警
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues and self.alert_service:
            await self.alert_service.send_alert(
                annotation_id=annotation_id,
                issues=critical_issues
            )
        
        check_result = CheckResult(
            annotation_id=annotation_id,
            project_id=project_id,
            passed=len(issues) == 0,
            issues=issues,
            checked_rules=len(rules),
            check_type=check_type
        )
        
        # 存储检查结果
        self._check_results[check_result.id] = check_result
        
        return check_result
    
    async def _execute_rule(
        self,
        annotation_data: Dict[str, Any],
        rule: QualityRule
    ) -> RuleResult:
        """
        执行单个规则
        
        Args:
            annotation_data: 标注数据
            rule: 规则对象
            
        Returns:
            规则执行结果
        """
        if rule.rule_type == "builtin":
            return await self._execute_builtin_rule(annotation_data, rule)
        elif rule.rule_type == "custom":
            return await self._execute_custom_rule(annotation_data, rule)
        else:
            return RuleResult(passed=True)
    
    async def _execute_builtin_rule(
        self,
        annotation_data: Dict[str, Any],
        rule: QualityRule
    ) -> RuleResult:
        """
        执行内置规则
        
        Args:
            annotation_data: 标注数据
            rule: 规则对象
            
        Returns:
            规则执行结果
        """
        rule_name = rule.name
        config = rule.config
        
        if rule_name == "required_fields":
            return self._check_required_fields(annotation_data, config)
        elif rule_name == "value_range":
            return self._check_value_range(annotation_data, config)
        elif rule_name == "format_validation":
            return self._check_format(annotation_data, config)
        elif rule_name == "length_limit":
            return self._check_length(annotation_data, config)
        elif rule_name == "text_length":
            return self._check_text_length(annotation_data, config)
        elif rule_name == "entity_overlap":
            return self._check_entity_overlap(annotation_data, config)
        elif rule_name == "allowed_values":
            return self._check_allowed_values(annotation_data, config)
        else:
            return RuleResult(passed=True)
    
    def _check_required_fields(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查必填字段"""
        required_fields = config.get("fields", [])
        missing_fields = []
        
        for field in required_fields:
            if field not in annotation_data:
                missing_fields.append(field)
            elif annotation_data[field] is None or annotation_data[field] == "":
                missing_fields.append(field)
        
        if missing_fields:
            return RuleResult(
                passed=False,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields}
            )
        
        return RuleResult(passed=True)
    
    def _check_value_range(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查值范围"""
        ranges = config.get("ranges", {})
        violations = []
        
        for field, range_config in ranges.items():
            if field not in annotation_data:
                continue
            
            value = annotation_data[field]
            if not isinstance(value, (int, float)):
                continue
            
            min_val = range_config.get("min")
            max_val = range_config.get("max")
            
            if min_val is not None and value < min_val:
                violations.append(f"{field} ({value}) is below minimum ({min_val})")
            if max_val is not None and value > max_val:
                violations.append(f"{field} ({value}) is above maximum ({max_val})")
        
        if violations:
            return RuleResult(
                passed=False,
                message="; ".join(violations),
                details={"violations": violations}
            )
        
        return RuleResult(passed=True)
    
    def _check_format(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查格式"""
        patterns = config.get("patterns", {})
        violations = []
        
        for field, pattern in patterns.items():
            if field not in annotation_data:
                continue
            
            value = annotation_data[field]
            if not isinstance(value, str):
                continue
            
            if not re.match(pattern, value):
                violations.append(f"{field} does not match pattern {pattern}")
        
        if violations:
            return RuleResult(
                passed=False,
                message="; ".join(violations),
                details={"violations": violations}
            )
        
        return RuleResult(passed=True)
    
    def _check_length(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查长度限制"""
        limits = config.get("limits", {})
        violations = []
        
        for field, limit_config in limits.items():
            if field not in annotation_data:
                continue
            
            value = annotation_data[field]
            if not isinstance(value, (str, list)):
                continue
            
            length = len(value)
            min_len = limit_config.get("min")
            max_len = limit_config.get("max")
            
            if min_len is not None and length < min_len:
                violations.append(f"{field} length ({length}) is below minimum ({min_len})")
            if max_len is not None and length > max_len:
                violations.append(f"{field} length ({length}) is above maximum ({max_len})")
        
        if violations:
            return RuleResult(
                passed=False,
                message="; ".join(violations),
                details={"violations": violations}
            )
        
        return RuleResult(passed=True)
    
    def _check_text_length(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查文本长度"""
        min_length = config.get("min_length", 0)
        max_length = config.get("max_length", float("inf"))
        field = config.get("field", "text")
        
        text = annotation_data.get(field, "")
        if not isinstance(text, str):
            text = str(text)
        
        length = len(text)
        
        if length < min_length:
            return RuleResult(
                passed=False,
                message=f"Text length ({length}) is below minimum ({min_length})",
                field=field
            )
        
        if length > max_length:
            return RuleResult(
                passed=False,
                message=f"Text length ({length}) is above maximum ({max_length})",
                field=field
            )
        
        return RuleResult(passed=True)
    
    def _check_entity_overlap(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查实体重叠"""
        allow_overlap = config.get("allow_overlap", False)
        entities_field = config.get("entities_field", "entities")
        
        entities = annotation_data.get(entities_field, [])
        if not isinstance(entities, list):
            return RuleResult(passed=True)
        
        if allow_overlap:
            return RuleResult(passed=True)
        
        # 检查重叠
        overlaps = []
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i >= j:
                    continue
                
                start1 = e1.get("start", 0)
                end1 = e1.get("end", 0)
                start2 = e2.get("start", 0)
                end2 = e2.get("end", 0)
                
                if start1 < end2 and start2 < end1:
                    overlaps.append((i, j))
        
        if overlaps:
            return RuleResult(
                passed=False,
                message=f"Found {len(overlaps)} overlapping entity pairs",
                details={"overlaps": overlaps}
            )
        
        return RuleResult(passed=True)
    
    def _check_allowed_values(
        self,
        annotation_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> RuleResult:
        """检查允许的值"""
        allowed = config.get("allowed", {})
        violations = []
        
        for field, allowed_values in allowed.items():
            if field not in annotation_data:
                continue
            
            value = annotation_data[field]
            if value not in allowed_values:
                violations.append(f"{field} value '{value}' is not in allowed values")
        
        if violations:
            return RuleResult(
                passed=False,
                message="; ".join(violations),
                details={"violations": violations}
            )
        
        return RuleResult(passed=True)
    
    async def _execute_custom_rule(
        self,
        annotation_data: Dict[str, Any],
        rule: QualityRule
    ) -> RuleResult:
        """
        执行自定义规则 (Python脚本)
        
        Args:
            annotation_data: 标注数据
            rule: 规则对象
            
        Returns:
            规则执行结果
        """
        if not rule.script:
            return RuleResult(passed=True)
        
        try:
            result = await self._safe_execute_script(rule.script, annotation_data)
            return RuleResult(
                passed=result.get("passed", True),
                message=result.get("message"),
                field=result.get("field"),
                details=result.get("details", {})
            )
        except Exception as e:
            return RuleResult(
                passed=False,
                message=f"Rule execution error: {str(e)}"
            )
    
    async def _safe_execute_script(
        self,
        script: str,
        annotation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        安全执行自定义脚本
        
        Args:
            script: Python脚本
            annotation_data: 标注数据
            
        Returns:
            执行结果
        """
        # 创建受限的执行环境
        safe_globals = {
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "any": any,
                "all": all,
                "isinstance": isinstance,
                "type": type,
            }
        }
        
        safe_locals = {
            "data": annotation_data,
            "result": {"passed": True}
        }
        
        try:
            exec(script, safe_globals, safe_locals)
            return safe_locals.get("result", {"passed": True})
        except Exception as e:
            return {"passed": False, "message": str(e)}
    
    async def batch_check(
        self,
        project_id: str,
        annotation_ids: Optional[List[str]] = None,
        annotations: Optional[List[Dict[str, Any]]] = None
    ) -> BatchCheckResult:
        """
        批量检查
        
        Args:
            project_id: 项目ID
            annotation_ids: 标注ID列表 (可选)
            annotations: 标注数据列表 (可选)
            
        Returns:
            批量检查结果
        """
        results: List[CheckResult] = []
        
        if annotations:
            # 直接使用提供的标注数据
            for ann in annotations:
                ann_id = ann.get("id", str(uuid4()))
                ann_data = ann.get("data", ann)
                result = await self.check_annotation(
                    annotation_id=ann_id,
                    annotation_data=ann_data,
                    project_id=project_id,
                    check_type="batch"
                )
                results.append(result)
        elif annotation_ids:
            # 根据ID获取标注数据
            for ann_id in annotation_ids:
                result = await self.check_annotation(
                    annotation_id=ann_id,
                    project_id=project_id,
                    check_type="batch"
                )
                results.append(result)
        else:
            # 获取项目所有未检查的标注
            for ann_id, ann in self._annotations.items():
                if ann.get("project_id") == project_id:
                    result = await self.check_annotation(
                        annotation_id=ann_id,
                        project_id=project_id,
                        check_type="batch"
                    )
                    results.append(result)
        
        passed_count = sum(1 for r in results if r.passed)
        
        return BatchCheckResult(
            project_id=project_id,
            total_checked=len(results),
            passed_count=passed_count,
            failed_count=len(results) - passed_count,
            results=results
        )
    
    async def get_check_results(
        self,
        project_id: Optional[str] = None,
        annotation_id: Optional[str] = None
    ) -> List[CheckResult]:
        """
        获取检查结果
        
        Args:
            project_id: 项目ID (可选)
            annotation_id: 标注ID (可选)
            
        Returns:
            检查结果列表
        """
        results = list(self._check_results.values())
        
        if project_id:
            results = [r for r in results if r.project_id == project_id]
        if annotation_id:
            results = [r for r in results if r.annotation_id == annotation_id]
        
        return results


# 独立函数 (用于属性测试)
def execute_rule(
    annotation_data: Dict[str, Any],
    rule_config: Dict[str, Any]
) -> RuleResult:
    """
    执行规则 (独立函数)
    
    Args:
        annotation_data: 标注数据
        rule_config: 规则配置
        
    Returns:
        规则执行结果
    """
    required_fields = rule_config.get("required_fields", [])
    missing_fields = []
    
    for field in required_fields:
        if field not in annotation_data:
            missing_fields.append(field)
        elif annotation_data[field] is None or annotation_data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        return RuleResult(
            passed=False,
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )
    
    return RuleResult(passed=True, details={"checked_fields": required_fields})
