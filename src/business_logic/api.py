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

# 创建测试框架管理器实例
testing_manager = TestingFrameworkManager()

# 测试框架API端点
@app.route('/api/business-logic/testing/comprehensive', methods=['POST'])
def run_comprehensive_testing():
    """运行综合测试"""
    try:
        data = request.get_json() or {}
        
        # 获取测试参数
        rules = data.get('rules', [])
        algorithms = data.get('algorithms', {})
        test_data = data.get('test_data', [])
        target_field = data.get('target_field', 'sentiment')
        
        if not test_data:
            return jsonify({
                "success": False,
                "error": "缺少测试数据"
            }), 400
        
        # 运行综合测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 转换算法函数（简化处理）
            algorithm_funcs = {}
            for name, config in algorithms.items():
                # 这里应该根据配置创建实际的算法函数
                # 为了演示，创建一个简单的模拟函数
                def mock_algorithm(data_list):
                    return {"score": 0.85, "processed": len(data_list)}
                algorithm_funcs[name] = mock_algorithm
            
            result = testing_manager.run_comprehensive_testing(
                rules, algorithm_funcs, test_data, target_field
            )
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "testing_results": result
        })
        
    except Exception as e:
        logger.error(f"综合测试API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/testing/ab-test', methods=['POST'])
def create_ab_test():
    """创建A/B测试"""
    try:
        data = request.get_json() or {}
        
        test_name = data.get('test_name', '未命名A/B测试')
        algorithm_a_config = data.get('algorithm_a', {})
        algorithm_b_config = data.get('algorithm_b', {})
        test_data = data.get('test_data', [])
        split_ratio = data.get('split_ratio', 0.5)
        
        if not test_data:
            return jsonify({
                "success": False,
                "error": "缺少测试数据"
            }), 400
        
        # 创建模拟算法函数
        def mock_algorithm_a(data_list):
            return {"score": 0.8, "algorithm": "A"}
        
        def mock_algorithm_b(data_list):
            return {"score": 0.85, "algorithm": "B"}
        
        # 创建A/B测试
        test_id = testing_manager.ab_framework.create_ab_test(
            test_name, mock_algorithm_a, mock_algorithm_b, 
            test_data, split_ratio
        )
        
        return jsonify({
            "success": True,
            "test_id": test_id,
            "message": f"A/B测试创建成功: {test_name}"
        })
        
    except Exception as e:
        logger.error(f"A/B测试创建API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/testing/ab-test/<test_id>/run', methods=['POST'])
def run_ab_test(test_id):
    """运行A/B测试"""
    try:
        result = testing_manager.ab_framework.run_ab_test(test_id)
        
        return jsonify({
            "success": result.success,
            "test_result": {
                "test_id": result.test_id,
                "test_name": result.test_name,
                "score": result.score,
                "metrics": result.metrics,
                "execution_time": result.execution_time,
                "error": result.error_message
            }
        })
        
    except Exception as e:
        logger.error(f"A/B测试运行API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/testing/ab-test/<test_id>/status', methods=['GET'])
def get_ab_test_status(test_id):
    """获取A/B测试状态"""
    try:
        status = testing_manager.ab_framework.get_test_status(test_id)
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"A/B测试状态API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/testing/ab-tests', methods=['GET'])
def list_ab_tests():
    """列出所有A/B测试"""
    try:
        tests = testing_manager.ab_framework.list_active_tests()
        
        return jsonify({
            "success": True,
            "tests": tests
        })
        
    except Exception as e:
        logger.error(f"A/B测试列表API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 数据质量验证API端点
@app.route('/api/business-logic/data-quality/validate', methods=['POST'])
def validate_data_quality():
    """验证数据质量"""
    try:
        data = request.get_json() or {}
        
        dataset = data.get('dataset', [])
        validation_config = data.get('validation_config', {})
        dataset_name = data.get('dataset_name', 'unknown')
        
        if not dataset:
            return jsonify({
                "success": False,
                "error": "缺少数据集"
            }), 400
        
        # 运行数据质量验证
        report = data_quality_manager.run_comprehensive_validation(
            dataset, validation_config, dataset_name
        )
        
        # 导出报告
        report_data = data_quality_manager.export_report(report)
        
        return jsonify({
            "success": True,
            "quality_report": report_data
        })
        
    except Exception as e:
        logger.error(f"数据质量验证API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/data-quality/history', methods=['GET'])
def get_data_quality_history():
    """获取数据质量验证历史"""
    try:
        limit = request.args.get('limit', 10, type=int)
        history = data_quality_manager.get_validation_history(limit)
        
        return jsonify({
            "success": True,
            "history": history
        })
        
    except Exception as e:
        logger.error(f"数据质量历史API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 监控系统API端点
@app.route('/api/business-logic/monitoring/start', methods=['POST'])
def start_monitoring():
    """启动监控系统"""
    try:
        monitoring_system.start_monitoring()
        
        return jsonify({
            "success": True,
            "message": "监控系统已启动"
        })
        
    except Exception as e:
        logger.error(f"启动监控API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """停止监控系统"""
    try:
        monitoring_system.stop_monitoring()
        
        return jsonify({
            "success": True,
            "message": "监控系统已停止"
        })
        
    except Exception as e:
        logger.error(f"停止监控API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """获取监控系统状态"""
    try:
        status = monitoring_system.get_system_status()
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        logger.error(f"监控状态API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/metrics', methods=['GET'])
def get_metrics():
    """获取监控指标"""
    try:
        metric_name = request.args.get('metric_name')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        time_range = None
        if start_time and end_time:
            time_range = {
                "start": datetime.fromisoformat(start_time),
                "end": datetime.fromisoformat(end_time)
            }
        
        if metric_name:
            # 获取特定指标
            metrics = monitoring_system.metrics_collector.get_metrics(metric_name, time_range)
            summary = monitoring_system.metrics_collector.get_metric_summary(metric_name, time_range)
            
            return jsonify({
                "success": True,
                "metric_name": metric_name,
                "data_points": len(metrics),
                "summary": summary,
                "latest_values": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value,
                        "tags": m.tags
                    } for m in metrics[-10:]  # 最近10个值
                ]
            })
        else:
            # 获取所有指标列表
            metric_names = monitoring_system.metrics_collector.list_metrics()
            
            return jsonify({
                "success": True,
                "metrics": metric_names,
                "total_metrics": len(metric_names)
            })
        
    except Exception as e:
        logger.error(f"获取指标API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/alerts', methods=['GET'])
def get_alerts():
    """获取告警信息"""
    try:
        alert_type = request.args.get('type', 'active')  # active, history
        
        if alert_type == 'active':
            alerts = monitoring_system.alert_manager.get_active_alerts()
        else:
            limit = request.args.get('limit', 100, type=int)
            alerts = monitoring_system.alert_manager.get_alert_history(limit)
        
        alert_data = [
            {
                "alert_id": alert.alert_id,
                "alert_name": alert.alert_name,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "status": alert.status
            } for alert in alerts
        ]
        
        return jsonify({
            "success": True,
            "alerts": alert_data,
            "total_alerts": len(alert_data)
        })
        
    except Exception as e:
        logger.error(f"获取告警API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/reports/daily', methods=['POST'])
def generate_daily_report():
    """生成日报"""
    try:
        report = monitoring_system.generate_daily_report()
        report_data = monitoring_system.report_generator.export_report(report)
        
        return jsonify({
            "success": True,
            "report": report_data
        })
        
    except Exception as e:
        logger.error(f"生成日报API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/reports/weekly', methods=['POST'])
def generate_weekly_report():
    """生成周报"""
    try:
        report = monitoring_system.generate_weekly_report()
        report_data = monitoring_system.report_generator.export_report(report)
        
        return jsonify({
            "success": True,
            "report": report_data
        })
        
    except Exception as e:
        logger.error(f"生成周报API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/reports/history', methods=['GET'])
def get_report_history():
    """获取报告历史"""
    try:
        limit = request.args.get('limit', 10, type=int)
        history = monitoring_system.report_generator.get_report_history(limit)
        
        return jsonify({
            "success": True,
            "reports": history
        })
        
    except Exception as e:
        logger.error(f"获取报告历史API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 添加自定义指标API端点
@app.route('/api/business-logic/monitoring/metrics/custom', methods=['POST'])
def add_custom_metric():
    """添加自定义指标"""
    try:
        data = request.get_json() or {}
        
        metric_name = data.get('metric_name')
        value = data.get('value')
        tags = data.get('tags', {})
        
        if not metric_name or value is None:
            return jsonify({
                "success": False,
                "error": "缺少指标名称或值"
            }), 400
        
        # 添加指标
        monitoring_system.metrics_collector.add_metric(
            metric_name, float(value), tags=tags
        )
        
        return jsonify({
            "success": True,
            "message": f"自定义指标已添加: {metric_name}"
        })
        
    except Exception as e:
        logger.error(f"添加自定义指标API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/business-logic/monitoring/alerts/rules', methods=['POST'])
def add_alert_rule():
    """添加告警规则"""
    try:
        data = request.get_json() or {}
        
        metric_name = data.get('metric_name')
        threshold = data.get('threshold')
        comparison = data.get('comparison', 'greater')
        severity = data.get('severity', 'medium')
        alert_name = data.get('alert_name')
        
        if not metric_name or threshold is None:
            return jsonify({
                "success": False,
                "error": "缺少指标名称或阈值"
            }), 400
        
        # 添加告警规则
        rule_id = monitoring_system.alert_manager.add_alert_rule(
            metric_name, float(threshold), comparison, severity, alert_name
        )
        
        return jsonify({
            "success": True,
            "rule_id": rule_id,
            "message": f"告警规则已添加: {alert_name or metric_name}"
        })
        
    except Exception as e:
        logger.error(f"添加告警规则API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500