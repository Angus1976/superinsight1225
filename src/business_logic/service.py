#!/usr/bin/env python3
"""
业务逻辑服务层
提供业务逻辑分析、规则提取、模式识别等核心服务

实现需求 13: 客户业务逻辑提炼与智能化
实现需求 5.1-5.9: 业务逻辑服务数据库操作
"""

import logging
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .extractor import BusinessLogicExtractor, PatternType, RuleType
from .models import (
    BusinessRule, BusinessPattern, BusinessInsight,
    BusinessRuleModel, BusinessPatternModel, BusinessInsightModel,
    PatternAnalysisRequest, PatternAnalysisResponse,
    RuleExtractionRequest, RuleExtractionResponse,
    RuleApplicationRequest, RuleApplicationResponse,
    BusinessLogicExportRequest, BusinessLogicExportResponse,
    VisualizationRequest, VisualizationResponse,
    ChangeDetectionRequest, ChangeDetectionResponse,
    BusinessLogicStats, RuleTypeEnum, PatternTypeEnum, InsightTypeEnum
)
from .repository import (
    BusinessRuleRepository,
    BusinessPatternRepository,
    BusinessInsightRepository
)
from src.i18n import get_translation

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BusinessLogicService:
    """业务逻辑服务类
    
    提供业务规则、模式和洞察的完整 CRUD 操作，
    支持数据库持久化和多租户隔离。
    
    Implements Requirements 5.1-5.9
    """
    
    def __init__(self, db: Optional[Session] = None, tenant_id: str = "default"):
        """初始化业务逻辑服务
        
        Args:
            db: SQLAlchemy 数据库会话（可选）
            tenant_id: 租户标识符（默认: "default"）
        """
        self.extractor = BusinessLogicExtractor()
        self.db = db
        self.tenant_id = tenant_id
        
        # 初始化仓库（如果提供了数据库会话）
        self._rule_repo: Optional[BusinessRuleRepository] = None
        self._pattern_repo: Optional[BusinessPatternRepository] = None
        self._insight_repo: Optional[BusinessInsightRepository] = None
        
        if db:
            self._rule_repo = BusinessRuleRepository(db)
            self._pattern_repo = BusinessPatternRepository(db)
            self._insight_repo = BusinessInsightRepository(db)
    
    def set_db_session(self, db: Session):
        """设置数据库会话
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db
        self._rule_repo = BusinessRuleRepository(db)
        self._pattern_repo = BusinessPatternRepository(db)
        self._insight_repo = BusinessInsightRepository(db)
    
    async def analyze_patterns(self, request: PatternAnalysisRequest) -> PatternAnalysisResponse:
        """
        分析项目标注数据中的业务模式
        
        Args:
            request: 模式分析请求
            
        Returns:
            PatternAnalysisResponse: 分析结果
        """
        try:
            # 获取项目标注数据
            annotations = await self._get_project_annotations(
                request.project_id,
                request.time_range_days
            )
            
            # 执行模式分析
            analysis = self.extractor.analyze_annotation_patterns(annotations)
            
            # 转换为API模型
            patterns = []
            for pattern in analysis.patterns:
                pattern_model = BusinessPattern(
                    id=str(uuid.uuid4()),
                    tenant_id=self.tenant_id,
                    project_id=request.project_id,
                    pattern_type=PatternTypeEnum(pattern.type.value),
                    description=pattern.description,
                    strength=pattern.strength,
                    evidence=pattern.evidence,
                    detected_at=datetime.now(),
                    last_seen=datetime.now()
                )
                patterns.append(pattern_model)
            
            return PatternAnalysisResponse(
                project_id=request.project_id,
                patterns=patterns,
                total_annotations=analysis.total_annotations,
                analysis_timestamp=analysis.analysis_timestamp,
                confidence_threshold=analysis.confidence_threshold
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.pattern_analysis_failed",
                    default=f"模式分析失败: {e}"
                )
            )
            raise
    
    async def extract_business_rules(self, request: RuleExtractionRequest) -> RuleExtractionResponse:
        """
        从标注数据中提取业务规则
        
        Args:
            request: 规则提取请求
            
        Returns:
            RuleExtractionResponse: 提取结果
        """
        try:
            # 执行规则提取
            extracted_rules = self.extractor.extract_business_rules(
                request.project_id,
                request.threshold
            )
            
            # 转换为API模型
            rules = []
            for rule in extracted_rules:
                rule_model = BusinessRule(
                    id=rule.id,
                    tenant_id=self.tenant_id,
                    project_id=request.project_id,
                    name=rule.name,
                    description=rule.description,
                    pattern=rule.pattern,
                    rule_type=RuleTypeEnum(rule.rule_type.value),
                    confidence=rule.confidence,
                    frequency=rule.frequency,
                    examples=rule.examples,
                    is_active=rule.is_active,
                    created_at=rule.created_at,
                    updated_at=rule.updated_at
                )
                rules.append(rule_model)
            
            return RuleExtractionResponse(
                project_id=request.project_id,
                rules=rules,
                extraction_timestamp=datetime.now(),
                threshold=request.threshold
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.rule_extraction_failed",
                    default=f"规则提取失败: {e}"
                )
            )
            raise
    
    async def get_business_rules(
        self,
        project_id: str,
        rule_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[BusinessRule]:
        """
        获取项目的业务规则列表
        
        Args:
            project_id: 项目ID
            rule_type: 规则类型过滤
            active_only: 是否只返回激活的规则
            
        Returns:
            List[BusinessRule]: 业务规则列表
            
        Implements Requirement 5.1: Query business rules from database with filtering
        """
        try:
            # 如果有数据库连接，从数据库查询
            if self._rule_repo:
                rule_dicts = await self._rule_repo.find_by_project(
                    project_id=project_id,
                    tenant_id=self.tenant_id,
                    rule_type=rule_type,
                    active_only=active_only
                )
                
                rules = []
                for rule_dict in rule_dicts:
                    rule = BusinessRule(
                        id=rule_dict['id'],
                        tenant_id=rule_dict['tenant_id'],
                        project_id=rule_dict['project_id'],
                        name=rule_dict['name'],
                        description=rule_dict.get('description'),
                        pattern=rule_dict['pattern'],
                        rule_type=RuleTypeEnum(rule_dict['rule_type']),
                        confidence=rule_dict['confidence'],
                        frequency=rule_dict['frequency'],
                        examples=rule_dict.get('examples', []),
                        is_active=rule_dict['is_active'],
                        created_at=datetime.fromisoformat(rule_dict['created_at']) if isinstance(rule_dict['created_at'], str) else rule_dict['created_at'],
                        updated_at=datetime.fromisoformat(rule_dict['updated_at']) if isinstance(rule_dict['updated_at'], str) else rule_dict['updated_at']
                    )
                    rules.append(rule)
                
                return rules
            
            # 如果没有数据库连接，返回空列表
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_connection",
                    default="No database connection, returning empty list"
                )
            )
            return []
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.get_rules_failed",
                    default=f"获取业务规则失败: {e}"
                )
            )
            raise
    
    async def get_business_patterns(
        self,
        project_id: str,
        pattern_type: Optional[str] = None,
        min_strength: float = 0.0
    ) -> List[BusinessPattern]:
        """
        获取项目的业务模式列表
        
        Args:
            project_id: 项目ID
            pattern_type: 模式类型过滤
            min_strength: 最小强度阈值
            
        Returns:
            List[BusinessPattern]: 业务模式列表
            
        Implements Requirement 5.2: Query business patterns from database with strength filtering
        """
        try:
            # 如果有数据库连接，从数据库查询
            if self._pattern_repo:
                pattern_dicts = await self._pattern_repo.find_by_project(
                    project_id=project_id,
                    tenant_id=self.tenant_id,
                    pattern_type=pattern_type,
                    min_strength=min_strength
                )
                
                patterns = []
                for pattern_dict in pattern_dicts:
                    pattern = BusinessPattern(
                        id=pattern_dict['id'],
                        tenant_id=pattern_dict['tenant_id'],
                        project_id=pattern_dict['project_id'],
                        pattern_type=PatternTypeEnum(pattern_dict['pattern_type']),
                        description=pattern_dict.get('description'),
                        strength=pattern_dict['strength'],
                        evidence=pattern_dict.get('evidence', []),
                        detected_at=datetime.fromisoformat(pattern_dict['detected_at']) if isinstance(pattern_dict['detected_at'], str) else pattern_dict['detected_at'],
                        last_seen=datetime.fromisoformat(pattern_dict['last_seen']) if isinstance(pattern_dict['last_seen'], str) else pattern_dict['last_seen']
                    )
                    patterns.append(pattern)
                
                return patterns
            
            # 如果没有数据库连接，返回空列表
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_connection",
                    default="No database connection, returning empty list"
                )
            )
            return []
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.get_patterns_failed",
                    default=f"获取业务模式失败: {e}"
                )
            )
            raise
    
    async def get_business_insights(
        self,
        project_id: str,
        insight_type: Optional[str] = None,
        unacknowledged_only: bool = False
    ) -> List[BusinessInsight]:
        """
        获取业务洞察列表
        
        Args:
            project_id: 项目ID
            insight_type: 洞察类型过滤
            unacknowledged_only: 是否只返回未确认的洞察
            
        Returns:
            List[BusinessInsight]: 业务洞察列表
            
        Implements Requirement 5.3: Query business insights from database
        """
        try:
            # 如果有数据库连接，从数据库查询
            if self._insight_repo:
                insight_dicts = await self._insight_repo.find_by_project(
                    project_id=project_id,
                    tenant_id=self.tenant_id,
                    insight_type=insight_type,
                    unacknowledged_only=unacknowledged_only
                )
                
                insights = []
                for insight_dict in insight_dicts:
                    insight = BusinessInsight(
                        id=insight_dict['id'],
                        tenant_id=insight_dict['tenant_id'],
                        project_id=insight_dict['project_id'],
                        insight_type=InsightTypeEnum(insight_dict['insight_type']),
                        title=insight_dict['title'],
                        description=insight_dict.get('description'),
                        impact_score=insight_dict['impact_score'],
                        recommendations=insight_dict.get('recommendations', []),
                        data_points=insight_dict.get('data_points', []),
                        created_at=datetime.fromisoformat(insight_dict['created_at']) if isinstance(insight_dict['created_at'], str) else insight_dict['created_at'],
                        acknowledged_at=datetime.fromisoformat(insight_dict['acknowledged_at']) if insight_dict.get('acknowledged_at') and isinstance(insight_dict['acknowledged_at'], str) else insight_dict.get('acknowledged_at')
                    )
                    insights.append(insight)
                
                return insights
            
            # 如果没有数据库连接，返回空列表
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_connection",
                    default="No database connection, returning empty list"
                )
            )
            return []
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.get_insights_failed",
                    default=f"获取业务洞察失败: {e}"
                )
            )
            raise

    
    async def save_pattern_analysis(self, project_id: str, analysis: PatternAnalysisResponse):
        """保存模式分析结果
        
        Args:
            project_id: 项目ID
            analysis: 模式分析响应
            
        Implements Requirement 5.4: Persist pattern analysis results to database
        """
        try:
            if self._pattern_repo:
                patterns_to_save = []
                for pattern in analysis.patterns:
                    pattern_dict = {
                        'id': pattern.id,
                        'tenant_id': self.tenant_id,
                        'project_id': project_id,
                        'pattern_type': pattern.pattern_type.value,
                        'description': pattern.description,
                        'strength': pattern.strength,
                        'evidence': pattern.evidence,
                        'detected_at': pattern.detected_at,
                        'last_seen': pattern.last_seen
                    }
                    patterns_to_save.append(pattern_dict)
                
                saved_count = await self._pattern_repo.save_batch(patterns_to_save)
                logger.info(
                    get_translation(
                        "business_logic.service.patterns_saved",
                        default=f"项目 {project_id} 的 {saved_count} 个模式分析结果已保存"
                    )
                )
            else:
                logger.warning(
                    get_translation(
                        "business_logic.service.no_db_save_patterns",
                        default="No database connection, patterns not saved"
                    )
                )
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.save_patterns_failed",
                    default=f"保存模式分析结果失败: {e}"
                )
            )
            raise
    
    async def save_extracted_rules(self, project_id: str, rules: List[BusinessRule]):
        """保存提取的规则
        
        Args:
            project_id: 项目ID
            rules: 业务规则列表
            
        Implements Requirement 5.5: Persist extracted rules to database
        """
        try:
            if self._rule_repo:
                saved_count = 0
                for rule in rules:
                    rule_dict = {
                        'id': rule.id,
                        'tenant_id': self.tenant_id,
                        'project_id': project_id,
                        'name': rule.name,
                        'description': rule.description,
                        'pattern': rule.pattern,
                        'rule_type': rule.rule_type.value,
                        'confidence': rule.confidence,
                        'frequency': rule.frequency,
                        'examples': rule.examples,
                        'is_active': rule.is_active,
                        'created_at': rule.created_at,
                        'updated_at': rule.updated_at
                    }
                    await self._rule_repo.save(rule_dict)
                    saved_count += 1
                
                logger.info(
                    get_translation(
                        "business_logic.service.rules_saved",
                        default=f"项目 {project_id} 的 {saved_count} 个提取规则已保存"
                    )
                )
            else:
                logger.warning(
                    get_translation(
                        "business_logic.service.no_db_save_rules",
                        default="No database connection, rules not saved"
                    )
                )
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.save_rules_failed",
                    default=f"保存提取规则失败: {e}"
                )
            )
            raise
    
    async def acknowledge_insight(self, insight_id: str) -> bool:
        """确认业务洞察
        
        Args:
            insight_id: 洞察ID
            
        Returns:
            bool: 是否成功确认
            
        Implements Requirement 5.6: Update acknowledged_at timestamp
        """
        try:
            if self._insight_repo:
                result = await self._insight_repo.acknowledge(insight_id)
                if result:
                    logger.info(
                        get_translation(
                            "business_logic.service.insight_acknowledged",
                            default=f"确认洞察 {insight_id}"
                        )
                    )
                return result
            
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_ack_insight",
                    default="No database connection, insight not acknowledged"
                )
            )
            return False
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.ack_insight_failed",
                    default=f"确认洞察失败: {e}"
                )
            )
            return False
    
    async def update_rule_confidence(self, rule_id: str, confidence: float) -> bool:
        """更新规则置信度
        
        Args:
            rule_id: 规则ID
            confidence: 新的置信度值 (0.0 到 1.0)
            
        Returns:
            bool: 是否成功更新
            
        Implements Requirement 5.7: Update rule confidence in database
        """
        try:
            if self._rule_repo:
                result = await self._rule_repo.update_confidence(rule_id, confidence)
                if result:
                    logger.info(
                        get_translation(
                            "business_logic.service.confidence_updated",
                            default=f"更新规则 {rule_id} 置信度为 {confidence}"
                        )
                    )
                return result
            
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_update_confidence",
                    default="No database connection, confidence not updated"
                )
            )
            return False
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.update_confidence_failed",
                    default=f"更新规则置信度失败: {e}"
                )
            )
            return False
    
    async def delete_business_rule(self, rule_id: str) -> bool:
        """删除业务规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功删除
            
        Implements Requirement 5.8: Delete rule from database
        """
        try:
            if self._rule_repo:
                result = await self._rule_repo.delete(rule_id)
                if result:
                    logger.info(
                        get_translation(
                            "business_logic.service.rule_deleted",
                            default=f"删除规则 {rule_id}"
                        )
                    )
                return result
            
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_delete_rule",
                    default="No database connection, rule not deleted"
                )
            )
            return False
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.delete_rule_failed",
                    default=f"删除规则失败: {e}"
                )
            )
            return False
    
    async def toggle_rule_status(self, rule_id: str) -> Optional[BusinessRule]:
        """切换规则激活状态
        
        Args:
            rule_id: 规则ID
            
        Returns:
            Optional[BusinessRule]: 更新后的规则，如果未找到则返回 None
            
        Implements Requirement 5.9: Update is_active field in database
        """
        try:
            if self._rule_repo:
                rule_dict = await self._rule_repo.toggle_active(rule_id)
                if rule_dict:
                    logger.info(
                        get_translation(
                            "business_logic.service.rule_status_toggled",
                            default=f"切换规则 {rule_id} 状态"
                        )
                    )
                    return BusinessRule(
                        id=rule_dict['id'],
                        tenant_id=rule_dict['tenant_id'],
                        project_id=rule_dict['project_id'],
                        name=rule_dict['name'],
                        description=rule_dict.get('description'),
                        pattern=rule_dict['pattern'],
                        rule_type=RuleTypeEnum(rule_dict['rule_type']),
                        confidence=rule_dict['confidence'],
                        frequency=rule_dict['frequency'],
                        examples=rule_dict.get('examples', []),
                        is_active=rule_dict['is_active'],
                        created_at=datetime.fromisoformat(rule_dict['created_at']) if isinstance(rule_dict['created_at'], str) else rule_dict['created_at'],
                        updated_at=datetime.fromisoformat(rule_dict['updated_at']) if isinstance(rule_dict['updated_at'], str) else rule_dict['updated_at']
                    )
                return None
            
            logger.warning(
                get_translation(
                    "business_logic.service.no_db_toggle_rule",
                    default="No database connection, rule status not toggled"
                )
            )
            return None
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.toggle_rule_failed",
                    default=f"切换规则状态失败: {e}"
                )
            )
            return None
    
    async def generate_visualization(self, request: VisualizationRequest) -> VisualizationResponse:
        """
        生成业务逻辑可视化图表
        
        Args:
            request: 可视化请求
            
        Returns:
            VisualizationResponse: 可视化结果
        """
        try:
            chart_data = {}
            chart_config = {}
            
            if request.visualization_type == "rule_network":
                # 从数据库获取规则数据
                rules = await self.get_business_rules(request.project_id, active_only=True)
                
                nodes = []
                for rule in rules:
                    nodes.append({
                        "id": rule.id,
                        "name": rule.name,
                        "type": rule.rule_type.value,
                        "confidence": rule.confidence
                    })
                
                # 简单的链接生成（基于规则类型相似性）
                links = []
                for i, rule1 in enumerate(rules):
                    for rule2 in rules[i+1:]:
                        if rule1.rule_type == rule2.rule_type:
                            links.append({
                                "source": rule1.id,
                                "target": rule2.id,
                                "strength": 0.5
                            })
                
                chart_data = {"nodes": nodes, "links": links}
                chart_config = {
                    "type": "network",
                    "layout": "force",
                    "node_size_field": "confidence",
                    "link_width_field": "strength"
                }
                
            elif request.visualization_type == "pattern_timeline":
                # 从数据库获取模式数据
                patterns = await self.get_business_patterns(request.project_id)
                
                # 按日期分组
                timeline = {}
                for pattern in patterns:
                    date_str = pattern.detected_at.strftime("%Y-%m-%d")
                    if date_str not in timeline:
                        timeline[date_str] = {"date": date_str, "pattern_count": 0, "total_strength": 0.0}
                    timeline[date_str]["pattern_count"] += 1
                    timeline[date_str]["total_strength"] += pattern.strength
                
                # 计算平均强度
                timeline_data = []
                for date_str, data in sorted(timeline.items()):
                    avg_strength = data["total_strength"] / data["pattern_count"] if data["pattern_count"] > 0 else 0
                    timeline_data.append({
                        "date": date_str,
                        "pattern_count": data["pattern_count"],
                        "avg_strength": round(avg_strength, 2)
                    })
                
                chart_data = {"timeline": timeline_data}
                chart_config = {
                    "type": "line",
                    "x_field": "date",
                    "y_fields": ["pattern_count", "avg_strength"],
                    "smooth": True
                }
                
            elif request.visualization_type == "insight_dashboard":
                # 从数据库获取统计数据
                stats = await self.get_business_logic_stats(request.project_id)
                
                chart_data = {
                    "metrics": {
                        "total_rules": stats.total_rules,
                        "active_rules": stats.active_rules,
                        "avg_confidence": stats.avg_rule_confidence,
                        "total_patterns": stats.total_patterns,
                        "new_insights": stats.total_insights
                    },
                    "rule_distribution": stats.top_pattern_types,
                    "confidence_distribution": []
                }
                chart_config = {
                    "type": "dashboard",
                    "layout": "grid",
                    "components": ["metrics", "pie_chart", "bar_chart"]
                }
            
            return VisualizationResponse(
                project_id=request.project_id,
                visualization_type=request.visualization_type,
                chart_data=chart_data,
                chart_config=chart_config,
                generation_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.visualization_failed",
                    default=f"可视化生成失败: {e}"
                )
            )
            raise
    
    async def export_business_logic(self, request: BusinessLogicExportRequest) -> BusinessLogicExportResponse:
        """
        导出业务逻辑数据
        
        Args:
            request: 导出请求
            
        Returns:
            BusinessLogicExportResponse: 导出结果
        """
        try:
            # 生成导出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"business_logic_{request.project_id}_{timestamp}.{request.export_format}"
            
            # 生成下载URL（实际实现中应该是真实的文件URL）
            download_url = f"/api/business-logic/download/{filename}"
            
            return BusinessLogicExportResponse(
                project_id=request.project_id,
                export_format=request.export_format,
                download_url=download_url,
                file_size=1024 * 50,  # 示例文件大小
                export_timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.export_failed",
                    default=f"业务逻辑导出失败: {e}"
                )
            )
            raise
    
    async def apply_business_rules(self, request: RuleApplicationRequest) -> RuleApplicationResponse:
        """
        应用业务规则到目标项目
        
        Args:
            request: 规则应用请求
            
        Returns:
            RuleApplicationResponse: 应用结果
        """
        try:
            # 获取源项目的规则
            source_rules = await self.get_business_rules(request.source_project_id)
            
            # 筛选要应用的规则
            rules_to_apply = [r for r in source_rules if r.id in request.rule_ids]
            
            applied_rules = []
            success_count = 0
            failure_count = 0
            
            for rule in rules_to_apply:
                try:
                    # 创建新规则（复制到目标项目）
                    new_rule = BusinessRule(
                        id=f"rule_{request.target_project_id}_{uuid.uuid4().hex[:8]}",
                        tenant_id=self.tenant_id,
                        project_id=request.target_project_id,
                        name=f"{rule.name} (应用自 {request.source_project_id})",
                        description=rule.description,
                        pattern=rule.pattern,
                        rule_type=rule.rule_type,
                        confidence=rule.confidence * 0.9,  # 应用时降低置信度
                        frequency=0,  # 重置频率
                        examples=[],  # 清空示例
                        is_active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    # 保存到数据库
                    if self._rule_repo:
                        await self._rule_repo.save({
                            'id': new_rule.id,
                            'tenant_id': new_rule.tenant_id,
                            'project_id': new_rule.project_id,
                            'name': new_rule.name,
                            'description': new_rule.description,
                            'pattern': new_rule.pattern,
                            'rule_type': new_rule.rule_type.value,
                            'confidence': new_rule.confidence,
                            'frequency': new_rule.frequency,
                            'examples': new_rule.examples,
                            'is_active': new_rule.is_active,
                            'created_at': new_rule.created_at,
                            'updated_at': new_rule.updated_at
                        })
                    
                    applied_rules.append(new_rule)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(
                        get_translation(
                            "business_logic.service.apply_rule_failed",
                            default=f"应用规则 {rule.id} 失败: {e}"
                        )
                    )
                    failure_count += 1
            
            return RuleApplicationResponse(
                source_project_id=request.source_project_id,
                target_project_id=request.target_project_id,
                applied_rules=applied_rules,
                application_timestamp=datetime.now(),
                success_count=success_count,
                failure_count=failure_count
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.apply_rules_failed",
                    default=f"规则应用失败: {e}"
                )
            )
            raise
    
    async def detect_pattern_changes(self, request: ChangeDetectionRequest) -> ChangeDetectionResponse:
        """
        检测业务逻辑变化
        
        Args:
            request: 变化检测请求
            
        Returns:
            ChangeDetectionResponse: 检测结果
        """
        try:
            # 获取时间窗口内的数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=request.time_window_days)
            
            # 从数据库获取模式和规则
            patterns = await self.get_business_patterns(request.project_id)
            rules = await self.get_business_rules(request.project_id)
            
            changes_detected = []
            
            # 检测模式强度变化
            for pattern in patterns:
                if pattern.detected_at >= start_date:
                    changes_detected.append({
                        "type": "new_pattern_detected",
                        "pattern_id": pattern.id,
                        "description": f"检测到新模式: {pattern.description}",
                        "strength": pattern.strength,
                        "detected_at": pattern.detected_at.isoformat()
                    })
            
            # 检测新规则
            for rule in rules:
                if rule.created_at >= start_date:
                    changes_detected.append({
                        "type": "new_rule_discovered",
                        "rule_id": rule.id,
                        "description": f"发现新规则: {rule.name}",
                        "confidence": rule.confidence,
                        "detected_at": rule.created_at.isoformat()
                    })
            
            change_summary = {
                "total_changes": len(changes_detected),
                "pattern_changes": len([c for c in changes_detected if "pattern" in c["type"]]),
                "rule_changes": len([c for c in changes_detected if "rule" in c["type"]]),
                "significant_changes": len([c for c in changes_detected if c.get("confidence", c.get("strength", 0)) > request.change_threshold]),
                "change_trend": "increasing" if len(changes_detected) > 0 else "stable"
            }
            
            return ChangeDetectionResponse(
                project_id=request.project_id,
                changes_detected=changes_detected,
                change_summary=change_summary,
                detection_timestamp=datetime.now(),
                time_window_days=request.time_window_days
            )
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.change_detection_failed",
                    default=f"变化检测失败: {e}"
                )
            )
            raise
    
    async def get_business_logic_stats(self, project_id: str) -> BusinessLogicStats:
        """
        获取业务逻辑统计信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            BusinessLogicStats: 统计信息
        """
        try:
            # 从数据库获取统计数据
            rules = await self.get_business_rules(project_id, active_only=False)
            patterns = await self.get_business_patterns(project_id)
            insights = await self.get_business_insights(project_id)
            
            active_rules = [r for r in rules if r.is_active]
            
            # 计算平均置信度
            avg_confidence = 0.0
            if rules:
                avg_confidence = sum(r.confidence for r in rules) / len(rules)
            
            # 统计模式类型分布
            pattern_type_counts = {}
            for pattern in patterns:
                pattern_type = pattern.pattern_type.value
                if pattern_type not in pattern_type_counts:
                    pattern_type_counts[pattern_type] = 0
                pattern_type_counts[pattern_type] += 1
            
            top_pattern_types = [
                {"type": k, "count": v}
                for k, v in sorted(pattern_type_counts.items(), key=lambda x: x[1], reverse=True)
            ]
            
            # 获取最后分析时间
            last_analysis = None
            if patterns:
                last_analysis = max(p.detected_at for p in patterns)
            
            stats = BusinessLogicStats(
                project_id=project_id,
                total_rules=len(rules),
                active_rules=len(active_rules),
                total_patterns=len(patterns),
                total_insights=len(insights),
                last_analysis=last_analysis,
                avg_rule_confidence=round(avg_confidence, 2),
                top_pattern_types=top_pattern_types
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.get_stats_failed",
                    default=f"获取统计信息失败: {e}"
                )
            )
            raise
    
    async def _get_project_annotations(
        self,
        project_id: str,
        time_range_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取项目标注数据
        
        Args:
            project_id: 项目ID
            time_range_days: 时间范围（天数）
            
        Returns:
            List[Dict[str, Any]]: 标注数据列表
        """
        try:
            # TODO: 从标注数据库查询实际数据
            # 这里返回示例数据用于测试
            annotations = [
                {
                    "id": "ann_001",
                    "text": "This product is excellent and amazing!",
                    "sentiment": "positive",
                    "rating": 5,
                    "annotator": "user_001",
                    "created_at": datetime.now() - timedelta(days=1)
                },
                {
                    "id": "ann_002",
                    "text": "The service was terrible and disappointing.",
                    "sentiment": "negative",
                    "rating": 1,
                    "annotator": "user_002",
                    "created_at": datetime.now() - timedelta(days=2)
                },
                {
                    "id": "ann_003",
                    "text": "It's okay, nothing special.",
                    "sentiment": "neutral",
                    "rating": 3,
                    "annotator": "user_001",
                    "created_at": datetime.now() - timedelta(days=3)
                }
            ]
            
            # 应用时间范围过滤
            if time_range_days:
                cutoff_date = datetime.now() - timedelta(days=time_range_days)
                annotations = [a for a in annotations if a["created_at"] >= cutoff_date]
            
            return annotations
            
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.get_annotations_failed",
                    default=f"获取项目标注数据失败: {e}"
                )
            )
            raise
    
    async def execute_export(self, project_id: str, request: BusinessLogicExportRequest):
        """执行导出任务"""
        try:
            logger.info(
                get_translation(
                    "business_logic.service.export_started",
                    default=f"执行项目 {project_id} 的导出任务"
                )
            )
            # TODO: 实际导出逻辑
            await asyncio.sleep(2)  # 模拟导出过程
            logger.info(
                get_translation(
                    "business_logic.service.export_completed",
                    default=f"项目 {project_id} 导出任务完成"
                )
            )
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.export_task_failed",
                    default=f"执行导出任务失败: {e}"
                )
            )
    
    async def update_rule_application(self, project_id: str, result: RuleApplicationResponse):
        """更新规则应用结果"""
        try:
            logger.info(
                get_translation(
                    "business_logic.service.rule_application_updated",
                    default=f"更新项目 {project_id} 的规则应用结果"
                )
            )
            # TODO: 更新数据库
            await asyncio.sleep(0.1)  # 模拟异步操作
            logger.info(
                get_translation(
                    "business_logic.service.rule_application_saved",
                    default=f"项目 {project_id} 规则应用结果已更新"
                )
            )
        except Exception as e:
            logger.error(
                get_translation(
                    "business_logic.service.update_application_failed",
                    default=f"更新规则应用结果失败: {e}"
                )
            )
