"""
质量改进系统 API

提供质量改进系统的 REST API 接口。
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..quality.quality_improvement_system import quality_improvement_system
from ..quality.root_cause_analyzer import QualityIssue, ProblemCategory, SeverityLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality-improvement", tags=["quality-improvement"])


@router.post("/analyze-issue")
async def analyze_quality_issue(
    issue_data: Dict[str, Any],
    user_id: Optional[str] = None
):
    """分析质量问题"""
    try:
        # 构建质量问题对象
        issue = QualityIssue(
            id=issue_data['id'],
            category=ProblemCategory(issue_data['category']),
            description=issue_data['description'],
            affected_data=issue_data.get('affected_data', []),
            reporter=issue_data.get('reporter', 'system'),
            created_at=datetime.fromisoformat(issue_data.get('created_at', datetime.now().isoformat())),
            severity=SeverityLevel(issue_data.get('severity', 'medium')),
            context=issue_data.get('context', {}),
            metadata=issue_data.get('metadata', {})
        )
        
        # 处理质量问题
        result = quality_improvement_system.process_quality_issue(issue, user_id)
        
        # 转换结果为可序列化格式
        return {
            'issue_id': result.issue_id,
            'root_cause_analysis': {
                'primary_cause': result.root_cause_analysis.primary_cause.value,
                'contributing_factors': [f.value for f in result.root_cause_analysis.contributing_factors],
                'confidence_score': result.root_cause_analysis.confidence_score,
                'evidence': result.root_cause_analysis.evidence,
                'impact_assessment': result.root_cause_analysis.impact_assessment,
                'recommendations': result.root_cause_analysis.recommendations
            },
            'matching_patterns': [pattern.to_dict() for pattern in result.matching_patterns],
            'repair_suggestions': [suggestion.to_dict() for suggestion in result.repair_suggestions],
            'repair_plan': result.repair_plan.to_dict(),
            'effect_predictions': [prediction.to_dict() for prediction in result.effect_predictions],
            'personalized_guidance': result.personalized_guidance,
            'overall_assessment': {
                'success_probability': result.overall_success_probability,
                'recommended_approach': result.recommended_approach,
                'priority_level': result.priority_level
            },
            'processing_info': {
                'processed_at': result.processed_at.isoformat(),
                'processing_time_seconds': result.processing_time_seconds
            }
        }
        
    except Exception as e:
        logger.error(f"分析质量问题时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_quality_insights(time_period_days: int = 30):
    """获取质量洞察"""
    try:
        insights = quality_improvement_system.get_quality_insights(time_period_days)
        return insights
    except Exception as e:
        logger.error(f"获取质量洞察时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/dashboard")
async def get_user_dashboard(user_id: str):
    """获取用户仪表板"""
    try:
        dashboard = quality_improvement_system.get_user_dashboard(user_id)
        return dashboard
    except Exception as e:
        logger.error(f"获取用户仪表板时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/feedback")
async def update_user_feedback(user_id: str, feedback_data: Dict[str, Any]):
    """更新用户反馈"""
    try:
        issue_id = feedback_data.get('issue_id', 'unknown')
        quality_improvement_system.update_user_feedback(issue_id, user_id, feedback_data)
        return {"message": "反馈更新成功"}
    except Exception as e:
        logger.error(f"更新用户反馈时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base/export")
async def export_knowledge_base():
    """导出知识库"""
    try:
        knowledge_base = quality_improvement_system.export_knowledge_base()
        return knowledge_base
    except Exception as e:
        logger.error(f"导出知识库时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-base/import")
async def import_knowledge_base(knowledge_data: Dict[str, Any]):
    """导入知识库"""
    try:
        quality_improvement_system.import_knowledge_base(knowledge_data)
        return {"message": "知识库导入成功"}
    except Exception as e:
        logger.error(f"导入知识库时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_quality_patterns():
    """获取质量模式"""
    try:
        patterns = quality_improvement_system.pattern_classifier.export_patterns()
        return patterns
    except Exception as e:
        logger.error(f"获取质量模式时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/guidance/{content_id}")
async def get_guidance_content(content_id: str):
    """获取指导内容"""
    try:
        content = quality_improvement_system.guidance_system.guidance_content.get(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="指导内容不存在")
        
        return content.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指导内容时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-resources")
async def get_training_resources(
    skill_level: Optional[str] = None,
    category: Optional[str] = None
):
    """获取培训资源"""
    try:
        resources = quality_improvement_system.guidance_system.training_resources
        
        # 过滤条件
        filtered_resources = []
        for resource in resources.values():
            if skill_level and resource.target_skill_level.value != skill_level:
                continue
            if category and not any(cat.value == category for cat in resource.applicable_categories):
                continue
            filtered_resources.append(resource.to_dict())
        
        return {
            'resources': filtered_resources,
            'total_count': len(filtered_resources)
        }
    except Exception as e:
        logger.error(f"获取培训资源时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/best-practices")
async def get_best_practices(category: Optional[str] = None):
    """获取最佳实践案例"""
    try:
        cases = quality_improvement_system.guidance_system.best_practice_cases
        
        # 过滤条件
        filtered_cases = []
        for case in cases.values():
            if category and case.category.value != category:
                continue
            filtered_cases.append(case.to_dict())
        
        return {
            'cases': filtered_cases,
            'total_count': len(filtered_cases)
        }
    except Exception as e:
        logger.error(f"获取最佳实践案例时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_system_statistics():
    """获取系统统计信息"""
    try:
        # 汇总各子系统的统计信息
        stats = {
            'root_cause_analyzer': quality_improvement_system.root_cause_analyzer.get_analysis_statistics(),
            'pattern_classifier': quality_improvement_system.pattern_classifier.get_pattern_statistics(),
            'suggestion_generator': quality_improvement_system.suggestion_generator.get_suggestion_statistics(),
            'effect_predictor': quality_improvement_system.effect_predictor.get_prediction_statistics(),
            'guidance_system': quality_improvement_system.guidance_system.get_system_statistics(),
            'generated_at': datetime.now().isoformat()
        }
        
        return stats
    except Exception as e:
        logger.error(f"获取系统统计信息时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))