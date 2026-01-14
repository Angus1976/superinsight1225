"""
Quality Rule Engine - 质量规则引擎
管理和执行质量规则
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    """规则执行结果"""
    passed: bool
    message: Optional[str] = None
    field: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityRule(BaseModel):
    """质量规则"""
    id: str
    name: str
    description: Optional[str] = None
    rule_type: str = "builtin"  # builtin, custom
    config: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[str] = None
    severity: str = "medium"  # critical, high, medium, low
    priority: int = 0
    project_id: str
    enabled: bool = True
    version: int = 1
    template_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreateRuleRequest(BaseModel):
    """创建规则请求"""
    name: str
    description: Optional[str] = None
    rule_type: str = "builtin"
    config: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[str] = None
    severity: str = "medium"
    priority: int = 0
    project_id: str


class UpdateRuleRequest(BaseModel):
    """更新规则请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    script: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class RuleTemplate(BaseModel):
    """规则模板"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    is_system: bool = False


class RuleVersion(BaseModel):
    """规则版本"""
    version: int
    config: Dict[str, Any]
    script: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None


class QualityRuleEngine:
    """质量规则引擎"""
    
    def __init__(self, cache: Optional[Any] = None):
        """
        初始化规则引擎
        
        Args:
            cache: Redis缓存客户端 (可选)
        """
        self.cache = cache
        # 内存规则存储 (用于无数据库场景)
        self._rules: Dict[str, QualityRule] = {}
        self._templates: Dict[str, RuleTemplate] = {}
        self._project_configs: Dict[str, Dict[str, Any]] = {}
        self._rule_history: Dict[str, List[RuleVersion]] = {}
        
        # 初始化内置规则模板
        self._init_builtin_templates()
    
    def _init_builtin_templates(self) -> None:
        """初始化内置规则模板"""
        # 基础质量检查模板
        basic_template = RuleTemplate(
            id="template_basic",
            name="基础质量检查",
            description="包含必填字段、格式验证等基础检查规则",
            category="basic",
            rules=[
                {
                    "name": "required_fields",
                    "rule_type": "builtin",
                    "config": {"fields": []},
                    "severity": "high",
                    "priority": 100
                },
                {
                    "name": "format_validation",
                    "rule_type": "builtin",
                    "config": {"patterns": {}},
                    "severity": "medium",
                    "priority": 80
                }
            ],
            is_system=True
        )
        self._templates[basic_template.id] = basic_template
        
        # NLP标注质量模板
        nlp_template = RuleTemplate(
            id="template_nlp",
            name="NLP标注质量检查",
            description="适用于NLP标注任务的质量检查规则",
            category="nlp",
            rules=[
                {
                    "name": "text_length",
                    "rule_type": "builtin",
                    "config": {"min_length": 1, "max_length": 10000},
                    "severity": "medium",
                    "priority": 90
                },
                {
                    "name": "entity_overlap",
                    "rule_type": "builtin",
                    "config": {"allow_overlap": False},
                    "severity": "high",
                    "priority": 85
                }
            ],
            is_system=True
        )
        self._templates[nlp_template.id] = nlp_template
    
    async def create_rule(self, rule: CreateRuleRequest) -> QualityRule:
        """
        创建规则
        
        Args:
            rule: 创建规则请求
            
        Returns:
            创建的规则
        """
        rule_id = str(uuid4())
        new_rule = QualityRule(
            id=rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            config=rule.config,
            script=rule.script,
            severity=rule.severity,
            priority=rule.priority,
            project_id=rule.project_id,
            enabled=True,
            version=1
        )
        
        self._rules[rule_id] = new_rule
        
        # 记录版本历史
        self._rule_history[rule_id] = [RuleVersion(
            version=1,
            config=rule.config,
            script=rule.script,
            updated_at=datetime.utcnow()
        )]
        
        # 清除缓存
        await self._invalidate_cache(rule.project_id)
        
        return new_rule
    
    async def update_rule(self, rule_id: str, updates: UpdateRuleRequest) -> QualityRule:
        """
        更新规则
        
        Args:
            rule_id: 规则ID
            updates: 更新内容
            
        Returns:
            更新后的规则
        """
        if rule_id not in self._rules:
            raise ValueError(f"Rule not found: {rule_id}")
        
        rule = self._rules[rule_id]
        update_dict = updates.dict(exclude_unset=True)
        
        for key, value in update_dict.items():
            setattr(rule, key, value)
        
        rule.version += 1
        rule.updated_at = datetime.utcnow()
        
        # 记录版本历史
        if rule_id not in self._rule_history:
            self._rule_history[rule_id] = []
        self._rule_history[rule_id].append(RuleVersion(
            version=rule.version,
            config=rule.config,
            script=rule.script,
            updated_at=rule.updated_at
        ))
        
        # 清除缓存
        await self._invalidate_cache(rule.project_id)
        
        return rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否删除成功
        """
        if rule_id not in self._rules:
            return False
        
        rule = self._rules[rule_id]
        project_id = rule.project_id
        
        del self._rules[rule_id]
        
        # 清除缓存
        await self._invalidate_cache(project_id)
        
        return True
    
    async def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """
        获取规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            规则对象
        """
        return self._rules.get(rule_id)
    
    async def get_active_rules(self, project_id: str) -> List[QualityRule]:
        """
        获取项目的活跃规则
        
        Args:
            project_id: 项目ID
            
        Returns:
            活跃规则列表 (按优先级降序排列)
        """
        # 尝试从缓存获取
        if self.cache:
            cache_key = f"quality_rules:{project_id}"
            cached = await self._get_from_cache(cache_key)
            if cached:
                return [QualityRule.parse_raw(r) for r in json.loads(cached)]
        
        # 从内存获取
        rules = [
            rule for rule in self._rules.values()
            if rule.project_id == project_id and rule.enabled
        ]
        
        # 按优先级降序排列
        rules.sort(key=lambda x: x.priority, reverse=True)
        
        # 缓存结果
        if self.cache:
            await self._set_cache(
                cache_key,
                json.dumps([r.json() for r in rules]),
                ex=3600
            )
        
        return rules
    
    async def get_all_rules(self, project_id: str) -> List[QualityRule]:
        """
        获取项目的所有规则
        
        Args:
            project_id: 项目ID
            
        Returns:
            所有规则列表
        """
        rules = [
            rule for rule in self._rules.values()
            if rule.project_id == project_id
        ]
        rules.sort(key=lambda x: x.priority, reverse=True)
        return rules
    
    async def get_score_weights(self, project_id: str) -> Dict[str, float]:
        """
        获取评分权重
        
        Args:
            project_id: 项目ID
            
        Returns:
            评分权重字典
        """
        config = self._project_configs.get(project_id, {})
        return config.get("score_weights", {
            "accuracy": 0.4,
            "completeness": 0.3,
            "timeliness": 0.2,
            "consistency": 0.1
        })
    
    async def set_score_weights(self, project_id: str, weights: Dict[str, float]) -> None:
        """
        设置评分权重
        
        Args:
            project_id: 项目ID
            weights: 权重字典
        """
        if project_id not in self._project_configs:
            self._project_configs[project_id] = {}
        self._project_configs[project_id]["score_weights"] = weights
    
    async def get_required_fields(self, project_id: str) -> List[str]:
        """
        获取必填字段
        
        Args:
            project_id: 项目ID
            
        Returns:
            必填字段列表
        """
        config = self._project_configs.get(project_id, {})
        return config.get("required_fields", [])
    
    async def set_required_fields(self, project_id: str, fields: List[str]) -> None:
        """
        设置必填字段
        
        Args:
            project_id: 项目ID
            fields: 字段列表
        """
        if project_id not in self._project_configs:
            self._project_configs[project_id] = {}
        self._project_configs[project_id]["required_fields"] = fields
    
    async def get_expected_duration(self, project_id: str) -> int:
        """
        获取预期标注时长 (秒)
        
        Args:
            project_id: 项目ID
            
        Returns:
            预期时长
        """
        config = self._project_configs.get(project_id, {})
        return config.get("expected_duration", 300)
    
    async def set_expected_duration(self, project_id: str, duration: int) -> None:
        """
        设置预期标注时长
        
        Args:
            project_id: 项目ID
            duration: 时长 (秒)
        """
        if project_id not in self._project_configs:
            self._project_configs[project_id] = {}
        self._project_configs[project_id]["expected_duration"] = duration
    
    async def create_from_template(
        self,
        template_id: str,
        project_id: str
    ) -> List[QualityRule]:
        """
        从模板创建规则
        
        Args:
            template_id: 模板ID
            project_id: 项目ID
            
        Returns:
            创建的规则列表
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        rules = []
        for rule_config in template.rules:
            request = CreateRuleRequest(
                name=rule_config.get("name", "Unnamed Rule"),
                description=rule_config.get("description"),
                rule_type=rule_config.get("rule_type", "builtin"),
                config=rule_config.get("config", {}),
                script=rule_config.get("script"),
                severity=rule_config.get("severity", "medium"),
                priority=rule_config.get("priority", 0),
                project_id=project_id
            )
            rule = await self.create_rule(request)
            rules.append(rule)
        
        return rules
    
    async def get_templates(self, category: Optional[str] = None) -> List[RuleTemplate]:
        """
        获取规则模板列表
        
        Args:
            category: 模板分类 (可选)
            
        Returns:
            模板列表
        """
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates
    
    async def get_rule_history(self, rule_id: str) -> List[RuleVersion]:
        """
        获取规则版本历史
        
        Args:
            rule_id: 规则ID
            
        Returns:
            版本历史列表
        """
        return self._rule_history.get(rule_id, [])
    
    async def _invalidate_cache(self, project_id: str) -> None:
        """清除项目规则缓存"""
        if self.cache:
            cache_key = f"quality_rules:{project_id}"
            try:
                await self.cache.delete(cache_key)
            except Exception:
                pass
    
    async def _get_from_cache(self, key: str) -> Optional[str]:
        """从缓存获取"""
        if not self.cache:
            return None
        try:
            return await self.cache.get(key)
        except Exception:
            return None
    
    async def _set_cache(self, key: str, value: str, ex: int = 3600) -> None:
        """设置缓存"""
        if not self.cache:
            return
        try:
            await self.cache.set(key, value, ex=ex)
        except Exception:
            pass
