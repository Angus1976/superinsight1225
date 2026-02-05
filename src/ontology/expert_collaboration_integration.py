"""
专家协作集成模块

将专家协作服务与企业本体管理器集成，提供统一的本体协作接口。

Validates: Task 27.1 - Integrate with existing ontology system
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.ontology.enterprise_ontology import (
    EnterpriseOntologyManager,
    OntologyEntity,
    OntologyRelation,
    ChineseEntityType,
    ChineseRelationType,
    DataClassification,
    SensitivityLevel,
    ComplianceResult,
)
from src.collaboration.expert_service import ExpertService
from src.collaboration.template_service import TemplateService
from src.collaboration.collaboration_service import CollaborationService
from src.collaboration.approval_service import ApprovalService
from src.collaboration.validation_service import ValidationService
from src.collaboration.impact_analysis_service import ImpactAnalysisService
from src.collaboration.ontology_i18n_service import OntologyI18nService
from src.collaboration.audit_service import AuditService
from src.collaboration.compliance_template_service import ComplianceTemplateService
from src.collaboration.best_practice_service import BestPracticeService
from src.collaboration.knowledge_contribution_service import KnowledgeContributionService

logger = logging.getLogger(__name__)


class ExpertCollaborationOntologyManager(EnterpriseOntologyManager):
    """
    专家协作本体管理器
    
    扩展 EnterpriseOntologyManager，集成专家协作功能：
    - 专家管理和推荐
    - 模板管理和实例化
    - 实时协作会话
    - 审批工作流
    - 验证规则
    - 影响分析
    - 国际化支持
    - 审计和回滚
    - 合规模板
    - 最佳实践
    - 知识贡献
    """
    
    def __init__(
        self,
        knowledge_graph_db=None,
        lineage_tracker=None,
        tenant_id: Optional[str] = None,
    ):
        """
        初始化专家协作本体管理器
        
        Args:
            knowledge_graph_db: Neo4j 数据库连接（可选）
            lineage_tracker: 血缘追踪器（可选）
            tenant_id: 租户ID（可选）
        """
        super().__init__(knowledge_graph_db, lineage_tracker)
        
        self.tenant_id = tenant_id
        
        # 初始化协作服务
        self.expert_service = ExpertService()
        self.template_service = TemplateService()
        self.collaboration_service = CollaborationService()
        self.approval_service = ApprovalService()
        self.validation_service = ValidationService()
        self.impact_analysis_service = ImpactAnalysisService()
        self.i18n_service = OntologyI18nService()
        self.audit_service = AuditService()
        self.compliance_service = ComplianceTemplateService()
        self.best_practice_service = BestPracticeService()
        self.contribution_service = KnowledgeContributionService()
        
        # 协作锁
        self._lock = asyncio.Lock()
        
        logger.info(f"ExpertCollaborationOntologyManager initialized for tenant: {tenant_id}")
    
    # ========================================================================
    # 模板集成方法
    # ========================================================================
    
    async def create_ontology_from_template(
        self,
        template_id: str,
        project_id: str,
        customizations: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从模板创建本体
        
        Args:
            template_id: 模板ID
            project_id: 项目ID
            customizations: 自定义配置
            created_by: 创建者ID
            
        Returns:
            创建结果，包含实例ID和创建的实体/关系
        """
        async with self._lock:
            # 实例化模板
            instance = await self.template_service.instantiate_template(
                template_id=template_id,
                project_id=project_id,
                customizations=customizations,
            )
            
            if not instance:
                return {"success": False, "error": "Template instantiation failed"}
            
            created_entities = []
            created_relations = []
            
            # 创建实体类型对应的本体实体
            for entity_type in instance.get("entity_types", []):
                ontology_entity = OntologyEntity(
                    id=uuid4(),
                    entity_type=self._map_entity_type(entity_type.get("name", "")),
                    name=entity_type.get("name_en", entity_type.get("name", "")),
                    name_zh=entity_type.get("name", ""),
                    description=entity_type.get("description", ""),
                    description_zh=entity_type.get("description", ""),
                    properties={
                        "template_id": template_id,
                        "instance_id": instance.get("instance_id"),
                        "is_core": entity_type.get("is_core", False),
                        "attributes": entity_type.get("attributes", []),
                    },
                    tenant_id=self.tenant_id,
                    created_by=created_by,
                )
                
                await self.create_entity(ontology_entity, track_lineage=True)
                created_entities.append(ontology_entity.to_dict())
            
            # 记录审计日志
            await self.audit_service.log_change(
                ontology_id=project_id,
                user_id=created_by or "system",
                change_type="CREATE",
                affected_elements=[e["id"] for e in created_entities],
                before_state=None,
                after_state={"template_id": template_id, "entities": len(created_entities)},
                description=f"Created ontology from template {template_id}",
            )
            
            return {
                "success": True,
                "instance_id": instance.get("instance_id"),
                "template_id": template_id,
                "project_id": project_id,
                "created_entities": created_entities,
                "created_relations": created_relations,
            }
    
    def _map_entity_type(self, type_name: str) -> ChineseEntityType:
        """映射实体类型名称到枚举"""
        type_mapping = {
            "合同": ChineseEntityType.CONTRACT,
            "contract": ChineseEntityType.CONTRACT,
            "部门": ChineseEntityType.DEPARTMENT,
            "department": ChineseEntityType.DEPARTMENT,
            "人员": ChineseEntityType.PERSON,
            "person": ChineseEntityType.PERSON,
            "组织": ChineseEntityType.ORGANIZATION,
            "organization": ChineseEntityType.ORGANIZATION,
            "项目": ChineseEntityType.PROJECT,
            "project": ChineseEntityType.PROJECT,
            "审批": ChineseEntityType.APPROVAL,
            "approval": ChineseEntityType.APPROVAL,
            "印章": ChineseEntityType.SEAL,
            "seal": ChineseEntityType.SEAL,
            "发票": ChineseEntityType.INVOICE,
            "invoice": ChineseEntityType.INVOICE,
            "证书": ChineseEntityType.CERTIFICATE,
            "certificate": ChineseEntityType.CERTIFICATE,
            "法规": ChineseEntityType.REGULATION,
            "regulation": ChineseEntityType.REGULATION,
            "政策": ChineseEntityType.POLICY,
            "policy": ChineseEntityType.POLICY,
        }
        return type_mapping.get(type_name.lower(), ChineseEntityType.DOCUMENT)
    
    # ========================================================================
    # 验证集成方法
    # ========================================================================
    
    async def validate_entity_with_rules(
        self,
        entity: OntologyEntity,
        region: str = "CN",
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        使用验证规则验证实体
        
        结合基础合规验证和自定义验证规则
        
        Args:
            entity: 本体实体
            region: 地区代码
            industry: 行业代码
            
        Returns:
            验证结果
        """
        # 基础合规验证
        compliance_result = await self.validate_compliance(entity)
        
        # 获取适用的验证规则
        rules = await self.validation_service.get_rules(
            entity_type=entity.entity_type.value,
            region=region,
            industry=industry,
        )
        
        # 应用自定义验证规则
        rule_errors = []
        for rule in rules:
            try:
                is_valid = await self.validation_service.validate(
                    entity=entity.to_dict(),
                    rule_id=rule.get("id"),
                )
                if not is_valid.get("is_valid", True):
                    rule_errors.extend(is_valid.get("errors", []))
            except Exception as e:
                logger.warning(f"Validation rule {rule.get('id')} failed: {e}")
        
        return {
            "entity_id": str(entity.id),
            "compliance_result": {
                "compliant": compliance_result.compliant,
                "issues": [
                    {
                        "type": issue.issue_type,
                        "message": issue.message,
                        "message_zh": issue.message_zh,
                        "severity": issue.severity,
                        "field": issue.field,
                        "suggestion": issue.suggestion,
                        "suggestion_zh": issue.suggestion_zh,
                    }
                    for issue in compliance_result.issues
                ],
            },
            "rule_validation": {
                "rules_applied": len(rules),
                "errors": rule_errors,
            },
            "is_valid": compliance_result.compliant and len(rule_errors) == 0,
            "validated_at": datetime.now().isoformat(),
        }
    
    # ========================================================================
    # 协作会话集成方法
    # ========================================================================
    
    async def start_collaboration_session(
        self,
        ontology_id: str,
        expert_id: str,
    ) -> Dict[str, Any]:
        """
        启动协作会话
        
        Args:
            ontology_id: 本体ID
            expert_id: 专家ID
            
        Returns:
            会话信息
        """
        # 验证专家存在
        expert = await self.expert_service.get_expert(expert_id)
        if not expert:
            return {"success": False, "error": "Expert not found"}
        
        # 创建或加入会话
        session = await self.collaboration_service.create_session(ontology_id)
        if session:
            await self.collaboration_service.join_session(
                session_id=session.get("id"),
                user_id=expert_id,
                user_name=expert.get("name", "Unknown"),
            )
        
        return {
            "success": True,
            "session_id": session.get("id") if session else None,
            "ontology_id": ontology_id,
            "expert_id": expert_id,
            "expert_name": expert.get("name"),
        }
    
    async def lock_element_for_editing(
        self,
        session_id: str,
        element_id: str,
        expert_id: str,
    ) -> Dict[str, Any]:
        """
        锁定元素进行编辑
        
        Args:
            session_id: 会话ID
            element_id: 元素ID
            expert_id: 专家ID
            
        Returns:
            锁定结果
        """
        lock_result = await self.collaboration_service.lock_element(
            session_id=session_id,
            element_id=element_id,
            user_id=expert_id,
        )
        
        return {
            "success": lock_result.get("success", False),
            "lock": lock_result.get("lock"),
            "error": lock_result.get("error"),
        }
    
    # ========================================================================
    # 审批工作流集成方法
    # ========================================================================
    
    async def submit_change_for_approval(
        self,
        ontology_id: str,
        element_id: str,
        change_type: str,
        proposed_changes: Dict[str, Any],
        requester_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        提交变更请求进行审批
        
        自动进行影响分析并路由到适当的审批链
        
        Args:
            ontology_id: 本体ID
            element_id: 元素ID
            change_type: 变更类型 (ADD/MODIFY/DELETE)
            proposed_changes: 提议的变更
            requester_id: 请求者ID
            description: 变更描述
            
        Returns:
            变更请求信息
        """
        # 进行影响分析
        impact_report = await self.impact_analysis_service.analyze_change(
            ontology_id=ontology_id,
            element_id=element_id,
            change_type=change_type,
            proposed_changes=proposed_changes,
        )
        
        # 创建变更请求
        change_request = await self.approval_service.create_change_request(
            ontology_id=ontology_id,
            requester_id=requester_id,
            change_type=change_type,
            target_element=element_id,
            proposed_changes=proposed_changes,
            description=description,
            impact_analysis=impact_report,
        )
        
        # 如果是高影响变更，自动提交审批
        if impact_report and impact_report.get("requires_high_impact_approval"):
            await self.approval_service.submit_change_request(
                change_request_id=change_request.get("id"),
            )
        
        return {
            "success": True,
            "change_request_id": change_request.get("id"),
            "impact_report": impact_report,
            "requires_approval": impact_report.get("requires_high_impact_approval", False) if impact_report else False,
            "status": change_request.get("status"),
        }
    
    # ========================================================================
    # 国际化集成方法
    # ========================================================================
    
    async def get_entity_with_translations(
        self,
        entity_id: UUID,
        language: str = "zh-CN",
    ) -> Optional[Dict[str, Any]]:
        """
        获取带翻译的实体
        
        Args:
            entity_id: 实体ID
            language: 语言代码
            
        Returns:
            带翻译的实体信息
        """
        entity = await self.get_entity(entity_id)
        if not entity:
            return None
        
        # 获取翻译
        translation = await self.i18n_service.get_translation(
            element_id=str(entity_id),
            language=language,
            fallback=True,
        )
        
        entity_dict = entity.to_dict()
        
        if translation:
            entity_dict["translated_name"] = translation.get("name", entity.name_zh)
            entity_dict["translated_description"] = translation.get("description", entity.description_zh)
            entity_dict["language"] = language
        
        return entity_dict
    
    # ========================================================================
    # 专家推荐集成方法
    # ========================================================================
    
    async def recommend_experts_for_ontology(
        self,
        ontology_area: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        为本体领域推荐专家
        
        Args:
            ontology_area: 本体领域
            limit: 返回数量限制
            
        Returns:
            推荐的专家列表
        """
        recommendations = await self.expert_service.recommend_experts(
            ontology_area=ontology_area,
            limit=limit,
        )
        
        return recommendations
    
    # ========================================================================
    # 合规模板集成方法
    # ========================================================================
    
    async def apply_compliance_template(
        self,
        ontology_id: str,
        template_type: str,
        applied_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        应用合规模板到本体
        
        Args:
            ontology_id: 本体ID
            template_type: 模板类型 (DSL/PIPL/CSL)
            applied_by: 应用者ID
            
        Returns:
            应用结果
        """
        # 获取合规模板
        template = await self.compliance_service.get_template(template_type)
        if not template:
            return {"success": False, "error": f"Compliance template {template_type} not found"}
        
        # 应用模板规则
        result = await self.compliance_service.apply_template(
            ontology_id=ontology_id,
            template_type=template_type,
        )
        
        # 记录审计日志
        await self.audit_service.log_change(
            ontology_id=ontology_id,
            user_id=applied_by or "system",
            change_type="MODIFY",
            affected_elements=[ontology_id],
            before_state=None,
            after_state={"compliance_template": template_type},
            description=f"Applied compliance template {template_type}",
        )
        
        return {
            "success": True,
            "template_type": template_type,
            "rules_applied": result.get("rules_applied", 0) if result else 0,
            "classifications_updated": result.get("classifications_updated", 0) if result else 0,
        }
    
    # ========================================================================
    # 知识贡献集成方法
    # ========================================================================
    
    async def add_expert_contribution(
        self,
        ontology_id: str,
        expert_id: str,
        contribution_type: str,
        content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        添加专家贡献
        
        Args:
            ontology_id: 本体ID
            expert_id: 专家ID
            contribution_type: 贡献类型 (comment/suggestion/document)
            content: 贡献内容
            
        Returns:
            贡献结果
        """
        if contribution_type == "comment":
            result = await self.contribution_service.add_comment(
                ontology_id=ontology_id,
                element_id=content.get("element_id"),
                expert_id=expert_id,
                content=content.get("text"),
                parent_comment_id=content.get("parent_comment_id"),
            )
        elif contribution_type == "entity_suggestion":
            result = await self.contribution_service.suggest_entity(
                ontology_id=ontology_id,
                expert_id=expert_id,
                entity_data=content,
            )
        elif contribution_type == "relation_suggestion":
            result = await self.contribution_service.suggest_relation(
                ontology_id=ontology_id,
                expert_id=expert_id,
                relation_data=content,
            )
        elif contribution_type == "document":
            result = await self.contribution_service.attach_document(
                ontology_id=ontology_id,
                element_id=content.get("element_id"),
                expert_id=expert_id,
                document_type=content.get("document_type"),
                url=content.get("url"),
                file_path=content.get("file_path"),
                description=content.get("description"),
            )
        else:
            return {"success": False, "error": f"Unknown contribution type: {contribution_type}"}
        
        return {
            "success": True,
            "contribution_id": result.get("id") if result else None,
            "contribution_type": contribution_type,
        }
    
    # ========================================================================
    # 最佳实践集成方法
    # ========================================================================
    
    async def apply_best_practice(
        self,
        ontology_id: str,
        best_practice_id: str,
        expert_id: str,
    ) -> Dict[str, Any]:
        """
        应用最佳实践到本体
        
        Args:
            ontology_id: 本体ID
            best_practice_id: 最佳实践ID
            expert_id: 专家ID
            
        Returns:
            应用会话信息
        """
        session = await self.best_practice_service.apply_best_practice(
            best_practice_id=best_practice_id,
            ontology_id=ontology_id,
            expert_id=expert_id,
        )
        
        return {
            "success": session is not None,
            "session_id": session.get("id") if session else None,
            "steps": session.get("steps", []) if session else [],
            "total_steps": session.get("total_steps", 0) if session else 0,
        }
    
    # ========================================================================
    # 审计和回滚集成方法
    # ========================================================================
    
    async def get_ontology_audit_history(
        self,
        ontology_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取本体审计历史
        
        Args:
            ontology_id: 本体ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            审计日志列表
        """
        logs = await self.audit_service.get_logs(
            ontology_id=ontology_id,
            limit=limit,
            offset=offset,
        )
        
        return {
            "ontology_id": ontology_id,
            "logs": logs,
            "total": len(logs),
            "limit": limit,
            "offset": offset,
        }
    
    async def rollback_ontology_changes(
        self,
        ontology_id: str,
        target_version: int,
        rolled_back_by: str,
    ) -> Dict[str, Any]:
        """
        回滚本体变更
        
        Args:
            ontology_id: 本体ID
            target_version: 目标版本
            rolled_back_by: 回滚操作者ID
            
        Returns:
            回滚结果
        """
        result = await self.audit_service.rollback_to_version(
            ontology_id=ontology_id,
            target_version=target_version,
            rolled_back_by=rolled_back_by,
        )
        
        return {
            "success": result.get("success", False) if result else False,
            "new_version": result.get("new_version") if result else None,
            "affected_users": result.get("affected_users", []) if result else [],
            "rolled_back_changes": result.get("rolled_back_changes", 0) if result else 0,
        }
    
    # ========================================================================
    # 统计信息
    # ========================================================================
    
    async def get_collaboration_stats(self) -> Dict[str, Any]:
        """获取协作统计信息"""
        base_stats = await self.get_stats()
        
        # 获取各服务的统计
        expert_count = len(self.expert_service._experts) if hasattr(self.expert_service, '_experts') else 0
        template_count = len(self.template_service._templates) if hasattr(self.template_service, '_templates') else 0
        session_count = len(self.collaboration_service._sessions) if hasattr(self.collaboration_service, '_sessions') else 0
        
        return {
            **base_stats,
            "expert_count": expert_count,
            "template_count": template_count,
            "active_sessions": session_count,
            "tenant_id": self.tenant_id,
        }


# 工厂函数
def create_expert_collaboration_manager(
    knowledge_graph_db=None,
    lineage_tracker=None,
    tenant_id: Optional[str] = None,
) -> ExpertCollaborationOntologyManager:
    """
    创建专家协作本体管理器实例
    
    Args:
        knowledge_graph_db: Neo4j 数据库连接
        lineage_tracker: 血缘追踪器
        tenant_id: 租户ID
        
    Returns:
        ExpertCollaborationOntologyManager 实例
    """
    return ExpertCollaborationOntologyManager(
        knowledge_graph_db=knowledge_graph_db,
        lineage_tracker=lineage_tracker,
        tenant_id=tenant_id,
    )
