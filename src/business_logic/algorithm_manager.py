#!/usr/bin/env python3
"""
高级算法管理器
集成所有智能分析算法，提供统一的算法调用接口

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 47 完成
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from .advanced_algorithms import AdvancedAlgorithmManager
from .rule_generator import (
    FrequencyBasedRuleGenerator, 
    EnhancedRuleConflictDetector, 
    IntelligentRuleOptimizer, 
    RuleValidationEngine
)
from .change_tracker import ChangeTrackingManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AlgorithmResult:
    """算法执行结果"""
    algorithm_name: str
    success: bool
    result_data: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None

class BusinessLogicAlgorithmManager:
    """业务逻辑算法管理器"""
    
    def __init__(self):
        """初始化算法管理器"""
        self.advanced_algorithms = AdvancedAlgorithmManager()
        self.rule_generator = FrequencyBasedRuleGenerator()
        self.conflict_detector = EnhancedRuleConflictDetector()
        self.rule_optimizer = IntelligentRuleOptimizer()
        self.rule_validator = RuleValidationEngine()
        self.change_tracker = ChangeTrackingManager()
        
        # 算法注册表
        self.algorithms = {
            "pattern_analysis": self._run_pattern_analysis,
            "rule_generation": self._run_rule_generation,
            "rule_optimization": self._run_rule_optimization,
            "conflict_detection": self._run_conflict_detection,
            "rule_validation": self._run_rule_validation,
            "change_tracking": self._run_change_tracking,
            "comprehensive_analysis": self._run_comprehensive_analysis
        }
        
    async def execute_algorithm(self, algorithm_name: str, 
                              annotations: List[Dict[str, Any]], 
                              project_id: str,
                              **kwargs) -> AlgorithmResult:
        """
        执行指定算法
        
        Args:
            algorithm_name: 算法名称
            annotations: 标注数据
            project_id: 项目ID
            **kwargs: 算法参数
            
        Returns:
            AlgorithmResult: 算法执行结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行算法: {algorithm_name}")
            
            if algorithm_name not in self.algorithms:
                return AlgorithmResult(
                    algorithm_name=algorithm_name,
                    success=False,
                    result_data={},
                    execution_time=0.0,
                    error_message=f"未知算法: {algorithm_name}"
                )
            
            # 执行算法
            algorithm_func = self.algorithms[algorithm_name]
            result_data = await algorithm_func(annotations, project_id, **kwargs)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"算法 {algorithm_name} 执行完成，耗时 {execution_time:.2f}s")
            
            return AlgorithmResult(
                algorithm_name=algorithm_name,
                success=True,
                result_data=result_data,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"算法 {algorithm_name} 执行失败: {e}")
            
            return AlgorithmResult(
                algorithm_name=algorithm_name,
                success=False,
                result_data={},
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def execute_multiple_algorithms(self, algorithm_names: List[str],
                                        annotations: List[Dict[str, Any]],
                                        project_id: str,
                                        **kwargs) -> List[AlgorithmResult]:
        """
        并行执行多个算法
        
        Args:
            algorithm_names: 算法名称列表
            annotations: 标注数据
            project_id: 项目ID
            **kwargs: 算法参数
            
        Returns:
            List[AlgorithmResult]: 算法执行结果列表
        """
        logger.info(f"开始并行执行 {len(algorithm_names)} 个算法")
        
        # 创建并行任务
        tasks = []
        for algorithm_name in algorithm_names:
            task = self.execute_algorithm(algorithm_name, annotations, project_id, **kwargs)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AlgorithmResult(
                    algorithm_name=algorithm_names[i],
                    success=False,
                    result_data={},
                    execution_time=0.0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.success)
        logger.info(f"并行算法执行完成: {successful_count}/{len(algorithm_names)} 成功")
        
        return processed_results
    
    # 具体算法实现方法
    async def _run_pattern_analysis(self, annotations: List[Dict[str, Any]], 
                                  project_id: str, **kwargs) -> Dict[str, Any]:
        """运行模式分析算法"""
        return self.advanced_algorithms.run_comprehensive_analysis(annotations)
    
    async def _run_rule_generation(self, annotations: List[Dict[str, Any]], 
                                 project_id: str, **kwargs) -> Dict[str, Any]:
        """运行规则生成算法"""
        min_support = kwargs.get("min_support", 3)
        min_confidence = kwargs.get("min_confidence", 0.6)
        
        # 更新生成器参数
        self.rule_generator.min_support = min_support
        self.rule_generator.min_confidence = min_confidence
        
        # 生成规则
        rules = self.rule_generator.generate_rules_from_annotations(annotations)
        
        return {
            "generated_rules": [self._rule_to_dict(rule) for rule in rules],
            "total_rules": len(rules),
            "generation_parameters": {
                "min_support": min_support,
                "min_confidence": min_confidence
            },
            "generation_timestamp": datetime.now().isoformat()
        }
    
    async def _run_rule_optimization(self, annotations: List[Dict[str, Any]], 
                                   project_id: str, **kwargs) -> Dict[str, Any]:
        """运行规则优化算法"""
        # 首先生成规则
        rules = self.rule_generator.generate_rules_from_annotations(annotations)
        
        if not rules:
            return {
                "optimized_rules": [],
                "optimization_summary": "没有规则需要优化",
                "original_count": 0,
                "optimized_count": 0
            }
        
        # 优化规则
        optimized_rules = self.rule_optimizer.optimize_rules(rules)
        
        return {
            "optimized_rules": [self._rule_to_dict(rule) for rule in optimized_rules],
            "optimization_summary": f"从 {len(rules)} 个规则优化为 {len(optimized_rules)} 个规则",
            "original_count": len(rules),
            "optimized_count": len(optimized_rules),
            "optimization_ratio": len(optimized_rules) / len(rules) if rules else 0,
            "optimization_timestamp": datetime.now().isoformat()
        }
    
    async def _run_conflict_detection(self, annotations: List[Dict[str, Any]], 
                                    project_id: str, **kwargs) -> Dict[str, Any]:
        """运行冲突检测算法"""
        # 生成规则
        rules = self.rule_generator.generate_rules_from_annotations(annotations)
        
        if not rules:
            return {
                "conflicts": {},
                "conflict_summary": "没有规则，无冲突",
                "total_rules": 0,
                "conflicting_rules": 0
            }
        
        # 检测冲突
        conflicts = self.conflict_detector.detect_comprehensive_conflicts(rules)
        
        return {
            "conflicts": conflicts,
            "conflict_summary": f"在 {len(rules)} 个规则中发现 {len(conflicts)} 个冲突",
            "total_rules": len(rules),
            "conflicting_rules": len(conflicts),
            "conflict_rate": len(conflicts) / len(rules) if rules else 0,
            "detection_timestamp": datetime.now().isoformat()
        }
    
    async def _run_rule_validation(self, annotations: List[Dict[str, Any]], 
                                 project_id: str, **kwargs) -> Dict[str, Any]:
        """运行规则验证算法"""
        # 生成规则
        rules = self.rule_generator.generate_rules_from_annotations(annotations)
        
        if not rules:
            return {
                "validation_results": [],
                "validation_summary": "没有规则需要验证",
                "total_rules": 0,
                "valid_rules": 0
            }
        
        # 使用部分数据作为测试集
        test_size = min(len(annotations) // 3, 100)  # 最多100条作为测试
        test_data = annotations[-test_size:] if test_size > 0 else annotations
        
        # 验证规则
        validation_results = self.rule_validator.validate_rules(rules, test_data)
        
        return {
            "validation_results": validation_results,
            "validation_summary": f"验证了 {len(rules)} 个规则",
            "total_rules": len(rules),
            "valid_rules": validation_results.get("valid_rules", 0),
            "validation_rate": validation_results.get("validation_rate", 0),
            "test_data_size": len(test_data),
            "validation_timestamp": datetime.now().isoformat()
        }
    
    async def _run_change_tracking(self, annotations: List[Dict[str, Any]], 
                                 project_id: str, **kwargs) -> Dict[str, Any]:
        """运行变化跟踪算法"""
        return self.change_tracker.run_comprehensive_tracking(annotations, project_id)
    
    async def _run_comprehensive_analysis(self, annotations: List[Dict[str, Any]], 
                                        project_id: str, **kwargs) -> Dict[str, Any]:
        """运行综合分析"""
        logger.info("开始运行综合业务逻辑分析")
        
        # 并行执行多个核心算法
        core_algorithms = [
            "pattern_analysis",
            "rule_generation", 
            "rule_optimization",
            "change_tracking"
        ]
        
        results = await self.execute_multiple_algorithms(
            core_algorithms, annotations, project_id, **kwargs
        )
        
        # 整合结果
        comprehensive_result = {
            "project_id": project_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_annotations": len(annotations),
            "algorithms_executed": len(core_algorithms),
            "successful_algorithms": sum(1 for r in results if r.success),
            "algorithm_results": {}
        }
        
        # 组织各算法结果
        for result in results:
            comprehensive_result["algorithm_results"][result.algorithm_name] = {
                "success": result.success,
                "execution_time": result.execution_time,
                "data": result.result_data,
                "error": result.error_message
            }
        
        # 生成综合洞察
        insights = self._generate_comprehensive_insights(results)
        comprehensive_result["comprehensive_insights"] = insights
        
        logger.info("综合业务逻辑分析完成")
        return comprehensive_result
    
    def _generate_comprehensive_insights(self, results: List[AlgorithmResult]) -> List[str]:
        """生成综合洞察"""
        insights = []
        
        # 分析模式识别结果
        pattern_result = next((r for r in results if r.algorithm_name == "pattern_analysis"), None)
        if pattern_result and pattern_result.success:
            algorithms_used = pattern_result.result_data.get("algorithms_used", [])
            insights.append(f"成功运行了 {len(algorithms_used)} 个模式识别算法")
        
        # 分析规则生成结果
        rule_result = next((r for r in results if r.algorithm_name == "rule_generation"), None)
        if rule_result and rule_result.success:
            total_rules = rule_result.result_data.get("total_rules", 0)
            if total_rules > 0:
                insights.append(f"生成了 {total_rules} 个业务规则")
            else:
                insights.append("未能生成有效的业务规则，可能需要更多数据")
        
        # 分析优化结果
        opt_result = next((r for r in results if r.algorithm_name == "rule_optimization"), None)
        if opt_result and opt_result.success:
            optimization_ratio = opt_result.result_data.get("optimization_ratio", 1)
            if optimization_ratio < 0.8:
                insights.append(f"规则优化效果显著，压缩率达到 {(1-optimization_ratio)*100:.1f}%")
        
        # 分析变化跟踪结果
        change_result = next((r for r in results if r.algorithm_name == "change_tracking"), None)
        if change_result and change_result.success:
            tracking_results = change_result.result_data.get("tracking_results", {})
            risk_level = tracking_results.get("impact_assessment", {}).get("risk_level", "low")
            if risk_level != "low":
                insights.append(f"检测到 {risk_level} 风险级别的变化，需要关注")
        
        if not insights:
            insights.append("系统运行正常，各项指标稳定")
        
        return insights
    
    def _rule_to_dict(self, rule) -> Dict[str, Any]:
        """将规则对象转换为字典"""
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "pattern": rule.pattern,
            "rule_type": rule.rule_type.value if hasattr(rule.rule_type, 'value') else str(rule.rule_type),
            "confidence": rule.confidence,
            "frequency": rule.frequency,
            "support": rule.support,
            "lift": rule.lift,
            "conviction": rule.conviction,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat()
        }
    
    def get_available_algorithms(self) -> List[Dict[str, str]]:
        """获取可用算法列表"""
        return [
            {
                "name": "pattern_analysis",
                "description": "高级模式识别分析，包括情感关联、关键词共现、时间趋势、用户行为分析"
            },
            {
                "name": "rule_generation", 
                "description": "基于频率和置信度的业务规则自动生成"
            },
            {
                "name": "rule_optimization",
                "description": "业务规则优化，包括合并相似规则、移除冗余规则"
            },
            {
                "name": "conflict_detection",
                "description": "检测业务规则间的冲突和矛盾"
            },
            {
                "name": "rule_validation",
                "description": "验证业务规则的有效性和准确性"
            },
            {
                "name": "change_tracking",
                "description": "业务指标变化跟踪和趋势分析"
            },
            {
                "name": "comprehensive_analysis",
                "description": "综合分析，并行执行多个核心算法并生成综合洞察"
            }
        ]
    
    async def get_algorithm_status(self) -> Dict[str, Any]:
        """获取算法管理器状态"""
        return {
            "manager_status": "active",
            "available_algorithms": len(self.algorithms),
            "algorithm_list": list(self.algorithms.keys()),
            "last_updated": datetime.now().isoformat(),
            "components": {
                "advanced_algorithms": "loaded",
                "rule_generator": "loaded", 
                "conflict_detector": "loaded",
                "rule_optimizer": "loaded",
                "rule_validator": "loaded",
                "change_tracker": "loaded"
            }
        }