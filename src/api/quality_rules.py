"""
Quality Rules API - 质量规则管理 API
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.quality.quality_rule_engine import (
    QualityRuleEngine,
    QualityRule,
    CreateRuleRequest,
    UpdateRuleRequest,
    RuleTemplate,
    RuleVersion
)


router = APIRouter(prefix="/api/v1/quality-rules", tags=["Quality Rules"])


# 全局规则引擎实例
_rule_engine: Optional[QualityRuleEngine] = None


def get_rule_engine() -> QualityRuleEngine:
    """获取规则引擎实例"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = QualityRuleEngine()
    return _rule_engine


# Request/Response Models
class CreateRuleRequestAPI(BaseModel):
    """创建规则请求"""
    name: str
    description: Optional[str] = None
    rule_type: str = "builtin"
    config: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[str] = None
    severity: str = "medium"
    priority: int = 0
    project_id: str


class UpdateRuleRequestAPI(BaseModel):
    """更新规则请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    script: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class CreateFromTemplateRequest(BaseModel):
    """从模板创建规则请求"""
    template_id: str
    project_id: str


class RuleResponse(BaseModel):
    """规则响应"""
    id: str
    name: str
    description: Optional[str] = None
    rule_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[str] = None
    severity: str
    priority: int
    project_id: str
    enabled: bool
    version: int
    
    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    """规则列表响应"""
    rules: List[RuleResponse]
    total: int


class TemplateResponse(BaseModel):
    """模板响应"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    rules: List[Dict[str, Any]]
    is_system: bool


class TemplateListResponse(BaseModel):
    """模板列表响应"""
    templates: List[TemplateResponse]
    total: int


# API Endpoints
@router.post("", response_model=RuleResponse)
async def create_rule(
    request: CreateRuleRequestAPI,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> RuleResponse:
    """
    创建质量规则
    
    - **name**: 规则名称
    - **rule_type**: 规则类型 (builtin/custom)
    - **config**: 规则配置
    - **severity**: 严重程度 (critical/high/medium/low)
    - **priority**: 优先级
    - **project_id**: 项目ID
    """
    create_request = CreateRuleRequest(
        name=request.name,
        description=request.description,
        rule_type=request.rule_type,
        config=request.config,
        script=request.script,
        severity=request.severity,
        priority=request.priority,
        project_id=request.project_id
    )
    
    rule = await rule_engine.create_rule(create_request)
    
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        config=rule.config,
        script=rule.script,
        severity=rule.severity,
        priority=rule.priority,
        project_id=rule.project_id,
        enabled=rule.enabled,
        version=rule.version
    )


@router.get("", response_model=RuleListResponse)
async def list_rules(
    project_id: str = Query(..., description="项目ID"),
    enabled_only: bool = Query(False, description="仅返回启用的规则"),
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> RuleListResponse:
    """
    获取项目的质量规则列表
    
    - **project_id**: 项目ID
    - **enabled_only**: 是否仅返回启用的规则
    """
    if enabled_only:
        rules = await rule_engine.get_active_rules(project_id)
    else:
        rules = await rule_engine.get_all_rules(project_id)
    
    rule_responses = [
        RuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            config=r.config,
            script=r.script,
            severity=r.severity,
            priority=r.priority,
            project_id=r.project_id,
            enabled=r.enabled,
            version=r.version
        )
        for r in rules
    ]
    
    return RuleListResponse(rules=rule_responses, total=len(rule_responses))


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> RuleResponse:
    """
    获取单个质量规则
    
    - **rule_id**: 规则ID
    """
    rule = await rule_engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        config=rule.config,
        script=rule.script,
        severity=rule.severity,
        priority=rule.priority,
        project_id=rule.project_id,
        enabled=rule.enabled,
        version=rule.version
    )


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequestAPI,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> RuleResponse:
    """
    更新质量规则
    
    - **rule_id**: 规则ID
    """
    update_request = UpdateRuleRequest(
        name=request.name,
        description=request.description,
        config=request.config,
        script=request.script,
        severity=request.severity,
        priority=request.priority,
        enabled=request.enabled
    )
    
    try:
        rule = await rule_engine.update_rule(rule_id, update_request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        config=rule.config,
        script=rule.script,
        severity=rule.severity,
        priority=rule.priority,
        project_id=rule.project_id,
        enabled=rule.enabled,
        version=rule.version
    )


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> Dict[str, Any]:
    """
    删除质量规则
    
    - **rule_id**: 规则ID
    """
    success = await rule_engine.delete_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True, "message": "Rule deleted"}


@router.post("/from-template", response_model=RuleListResponse)
async def create_from_template(
    request: CreateFromTemplateRequest,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> RuleListResponse:
    """
    从模板创建规则
    
    - **template_id**: 模板ID
    - **project_id**: 项目ID
    """
    try:
        rules = await rule_engine.create_from_template(request.template_id, request.project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    rule_responses = [
        RuleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            config=r.config,
            script=r.script,
            severity=r.severity,
            priority=r.priority,
            project_id=r.project_id,
            enabled=r.enabled,
            version=r.version
        )
        for r in rules
    ]
    
    return RuleListResponse(rules=rule_responses, total=len(rule_responses))


@router.get("/templates/list", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="模板分类"),
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> TemplateListResponse:
    """
    获取规则模板列表
    
    - **category**: 模板分类 (可选)
    """
    templates = await rule_engine.get_templates(category)
    
    template_responses = [
        TemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            rules=t.rules,
            is_system=t.is_system
        )
        for t in templates
    ]
    
    return TemplateListResponse(templates=template_responses, total=len(template_responses))


@router.get("/{rule_id}/history", response_model=List[Dict[str, Any]])
async def get_rule_history(
    rule_id: str,
    rule_engine: QualityRuleEngine = Depends(get_rule_engine)
) -> List[Dict[str, Any]]:
    """
    获取规则版本历史
    
    - **rule_id**: 规则ID
    """
    history = await rule_engine.get_rule_history(rule_id)
    
    return [
        {
            "version": h.version,
            "config": h.config,
            "script": h.script,
            "updated_at": h.updated_at.isoformat(),
            "updated_by": h.updated_by
        }
        for h in history
    ]
