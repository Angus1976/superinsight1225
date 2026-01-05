#!/usr/bin/env python3
"""
业务逻辑API端点
提供业务逻辑分析、规则提取、模式识别等API服务

实现需求 13: 客户业务逻辑提炼与智能化
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import uuid
import json

from .extractor import BusinessLogicExtractor
from .models import (
    BusinessRule, BusinessPattern, BusinessInsight,
    PatternAnalysisRequest, PatternAnalysisResponse,
    RuleExtractionRequest, RuleExtractionResponse,
    RuleApplicationRequest, RuleApplicationResponse,
    BusinessLogicExportRequest, BusinessLogicExportResponse,
    VisualizationRequest, VisualizationResponse,
    ChangeDetectionRequest, ChangeDetectionResponse,
    BusinessLogicStats
)
from .service import BusinessLogicService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/business-logic", tags=["business-logic"])

# 依赖注入
def get_business_logic_service() -> BusinessLogicService:
    """获取业务逻辑服务实例"""
    return BusinessLogicService()

@router.post("/analyze", response_model=PatternAnalysisResponse)
async def analyze_patterns(
    request: PatternAnalysisRequest,
    background_tasks: BackgroundTasks,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    分析项目标注数据中的业务模式和规律
    
    实现需求 13.1: 分析标注数据中的业务模式和规律
    """
    try:
        logger.info(f"开始分析项目 {request.project_id} 的业务模式")
        
        # 执行模式分析
        result = await service.analyze_patterns(request)
        
        # 异步保存分析结果
        background_tasks.add_task(
            service.save_pattern_analysis,
            request.project_id,
            result
        )
        
        logger.info(f"项目 {request.project_id} 模式分析完成，识别出 {len(result.patterns)} 个模式")
        return result
        
    except Exception as e:
        logger.error(f"模式分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"模式分析失败: {str(e)}")

@router.get("/rules/{project_id}", response_model=List[BusinessRule])
async def get_business_rules(
    project_id: str,
    rule_type: Optional[str] = None,
    active_only: bool = True,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    获取项目的业务规则列表
    
    实现需求 13.2: 自动识别业务规则
    """
    try:
        logger.info(f"获取项目 {project_id} 的业务规则")
        
        rules = await service.get_business_rules(
            project_id=project_id,
            rule_type=rule_type,
            active_only=active_only
        )
        
        logger.info(f"项目 {project_id} 共有 {len(rules)} 个业务规则")
        return rules
        
    except Exception as e:
        logger.error(f"获取业务规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取业务规则失败: {str(e)}")

@router.post("/rules/extract", response_model=RuleExtractionResponse)
async def extract_business_rules(
    request: RuleExtractionRequest,
    background_tasks: BackgroundTasks,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    从标注数据中提取业务规则
    
    实现需求 13.2: 自动识别业务规则
    """
    try:
        logger.info(f"开始为项目 {request.project_id} 提取业务规则")
        
        # 执行规则提取
        result = await service.extract_business_rules(request)
        
        # 异步保存提取结果
        background_tasks.add_task(
            service.save_extracted_rules,
            request.project_id,
            result.rules
        )
        
        logger.info(f"项目 {request.project_id} 规则提取完成，提取出 {len(result.rules)} 个规则")
        return result
        
    except Exception as e:
        logger.error(f"规则提取失败: {e}")
        raise HTTPException(status_code=500, detail=f"规则提取失败: {str(e)}")

@router.get("/patterns/{project_id}", response_model=List[BusinessPattern])
async def get_business_patterns(
    project_id: str,
    pattern_type: Optional[str] = None,
    min_strength: float = 0.0,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    获取项目的业务模式列表
    
    实现需求 13.1: 分析标注数据中的业务模式和规律
    """
    try:
        logger.info(f"获取项目 {project_id} 的业务模式")
        
        patterns = await service.get_business_patterns(
            project_id=project_id,
            pattern_type=pattern_type,
            min_strength=min_strength
        )
        
        logger.info(f"项目 {project_id} 共有 {len(patterns)} 个业务模式")
        return patterns
        
    except Exception as e:
        logger.error(f"获取业务模式失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取业务模式失败: {str(e)}")

@router.post("/visualization", response_model=VisualizationResponse)
async def generate_visualization(
    request: VisualizationRequest,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    生成业务逻辑可视化图表
    
    实现需求 13.3: 生成可视化的业务逻辑图表和报告
    """
    try:
        logger.info(f"为项目 {request.project_id} 生成 {request.visualization_type} 可视化")
        
        result = await service.generate_visualization(request)
        
        logger.info(f"项目 {request.project_id} 可视化生成完成")
        return result
        
    except Exception as e:
        logger.error(f"可视化生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"可视化生成失败: {str(e)}")

@router.post("/export", response_model=BusinessLogicExportResponse)
async def export_business_logic(
    request: BusinessLogicExportRequest,
    background_tasks: BackgroundTasks,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    导出业务逻辑数据
    
    实现需求 13.5: 支持业务规则的导出和应用
    """
    try:
        logger.info(f"开始导出项目 {request.project_id} 的业务逻辑数据")
        
        # 生成导出任务
        result = await service.export_business_logic(request)
        
        # 异步执行导出
        background_tasks.add_task(
            service.execute_export,
            request.project_id,
            request
        )
        
        logger.info(f"项目 {request.project_id} 导出任务已创建")
        return result
        
    except Exception as e:
        logger.error(f"业务逻辑导出失败: {e}")
        raise HTTPException(status_code=500, detail=f"业务逻辑导出失败: {str(e)}")

@router.post("/apply", response_model=RuleApplicationResponse)
async def apply_business_rules(
    request: RuleApplicationRequest,
    background_tasks: BackgroundTasks,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    应用业务规则到目标项目
    
    实现需求 13.5: 支持业务规则的导出和应用
    """
    try:
        logger.info(f"开始将项目 {request.source_project_id} 的规则应用到项目 {request.target_project_id}")
        
        # 执行规则应用
        result = await service.apply_business_rules(request)
        
        # 异步更新应用结果
        background_tasks.add_task(
            service.update_rule_application,
            request.target_project_id,
            result
        )
        
        logger.info(f"规则应用完成，成功应用 {result.success_count} 个规则")
        return result
        
    except Exception as e:
        logger.error(f"规则应用失败: {e}")
        raise HTTPException(status_code=500, detail=f"规则应用失败: {str(e)}")

@router.post("/detect-changes", response_model=ChangeDetectionResponse)
async def detect_pattern_changes(
    request: ChangeDetectionRequest,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    检测业务逻辑变化
    
    实现需求 13.7: 跟踪和记录变化趋势
    """
    try:
        logger.info(f"开始检测项目 {request.project_id} 的业务逻辑变化")
        
        result = await service.detect_pattern_changes(request)
        
        logger.info(f"项目 {request.project_id} 变化检测完成，发现 {len(result.changes_detected)} 个变化")
        return result
        
    except Exception as e:
        logger.error(f"变化检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"变化检测失败: {str(e)}")

@router.get("/insights/{project_id}", response_model=List[BusinessInsight])
async def get_business_insights(
    project_id: str,
    insight_type: Optional[str] = None,
    unacknowledged_only: bool = False,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    获取业务洞察列表
    
    实现需求 13.4: 通知相关业务专家
    """
    try:
        logger.info(f"获取项目 {project_id} 的业务洞察")
        
        insights = await service.get_business_insights(
            project_id=project_id,
            insight_type=insight_type,
            unacknowledged_only=unacknowledged_only
        )
        
        logger.info(f"项目 {project_id} 共有 {len(insights)} 个业务洞察")
        return insights
        
    except Exception as e:
        logger.error(f"获取业务洞察失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取业务洞察失败: {str(e)}")

@router.post("/insights/{insight_id}/acknowledge")
async def acknowledge_insight(
    insight_id: str,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    确认业务洞察
    
    实现需求 13.4: 通知相关业务专家
    """
    try:
        logger.info(f"确认业务洞察 {insight_id}")
        
        result = await service.acknowledge_insight(insight_id)
        
        if result:
            logger.info(f"业务洞察 {insight_id} 已确认")
            return {"message": "洞察已确认", "insight_id": insight_id}
        else:
            raise HTTPException(status_code=404, detail="洞察不存在")
            
    except Exception as e:
        logger.error(f"确认洞察失败: {e}")
        raise HTTPException(status_code=500, detail=f"确认洞察失败: {str(e)}")

@router.get("/stats/{project_id}", response_model=BusinessLogicStats)
async def get_business_logic_stats(
    project_id: str,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    获取业务逻辑统计信息
    
    实现需求 13.6: 提供业务逻辑的置信度评分
    """
    try:
        logger.info(f"获取项目 {project_id} 的业务逻辑统计")
        
        stats = await service.get_business_logic_stats(project_id)
        
        logger.info(f"项目 {project_id} 统计信息获取完成")
        return stats
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.put("/rules/{rule_id}/confidence")
async def update_rule_confidence(
    rule_id: str,
    confidence: float,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    更新规则置信度
    
    实现需求 13.6: 提供业务逻辑的置信度评分
    """
    try:
        if not 0.0 <= confidence <= 1.0:
            raise HTTPException(status_code=400, detail="置信度必须在0.0-1.0之间")
            
        logger.info(f"更新规则 {rule_id} 的置信度为 {confidence}")
        
        result = await service.update_rule_confidence(rule_id, confidence)
        
        if result:
            logger.info(f"规则 {rule_id} 置信度已更新")
            return {"message": "置信度已更新", "rule_id": rule_id, "confidence": confidence}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")
            
    except Exception as e:
        logger.error(f"更新置信度失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新置信度失败: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_business_rule(
    rule_id: str,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    删除业务规则
    """
    try:
        logger.info(f"删除业务规则 {rule_id}")
        
        result = await service.delete_business_rule(rule_id)
        
        if result:
            logger.info(f"业务规则 {rule_id} 已删除")
            return {"message": "规则已删除", "rule_id": rule_id}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")
            
    except Exception as e:
        logger.error(f"删除规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除规则失败: {str(e)}")

@router.post("/rules/{rule_id}/toggle")
async def toggle_rule_status(
    rule_id: str,
    service: BusinessLogicService = Depends(get_business_logic_service)
):
    """
    切换规则激活状态
    """
    try:
        logger.info(f"切换规则 {rule_id} 的激活状态")
        
        result = await service.toggle_rule_status(rule_id)
        
        if result:
            logger.info(f"规则 {rule_id} 状态已切换")
            return {"message": "规则状态已切换", "rule_id": rule_id, "is_active": result.is_active}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")
            
    except Exception as e:
        logger.error(f"切换规则状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换规则状态失败: {str(e)}")

# 健康检查端点
@router.get("/health")
async def health_check():
    """业务逻辑服务健康检查"""
    return {
        "status": "healthy",
        "service": "business-logic",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# 导入测试和监控模块
from .testing_framework import TestingFrameworkManager
from .data_validator import data_quality_manager
from .monitoring_system import monitoring_system