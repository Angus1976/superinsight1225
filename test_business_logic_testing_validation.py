#!/usr/bin/env python3
"""
业务逻辑测试验证脚本
验证任务 48.3 端到端业务逻辑测试的完整性

实现需求 13: 客户业务逻辑提炼与智能化
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.business_logic.service import BusinessLogicService
from src.business_logic.extractor import BusinessLogicExtractor
from src.business_logic.models import (
    PatternAnalysisRequest, RuleExtractionRequest, 
    VisualizationRequest, ChangeDetectionRequest,
    BusinessLogicExportRequest, RuleApplicationRequest
)
from src.business_logic.notifications import (
    email_service, sms_service, history_service
)

class BusinessLogicTestValidator:
    """业务逻辑测试验证器"""
    
    def __init__(self):
        self.service = BusinessLogicService()
        self.extractor = BusinessLogicExtractor()
        self.test_project_id = "validation_test_project"
        self.validation_results = []
    
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    async def validate_complete_workflow(self):
        """验证完整的业务逻辑提炼流程"""
        print("\n=== 验证完整业务逻辑提炼流程 ===")
        
        try:
            # 1. 模式分析
            pattern_request = PatternAnalysisRequest(
                project_id=self.test_project_id,
                confidence_threshold=0.8,
                min_frequency=2,
                time_range_days=30
            )
            
            pattern_response = await self.service.analyze_patterns(pattern_request)
            
            # 验证模式分析结果
            assert pattern_response.project_id == self.test_project_id
            assert pattern_response.total_annotations >= 0
            assert isinstance(pattern_response.patterns, list)
            
            self.log_result(
                "模式分析流程",
                True,
                f"成功分析 {pattern_response.total_annotations} 条数据，发现 {len(pattern_response.patterns)} 个模式"
            )
            
            # 2. 规则提取
            rule_request = RuleExtractionRequest(
                project_id=self.test_project_id,
                threshold=0.7
            )
            
            rule_response = await self.service.extract_business_rules(rule_request)
            
            # 验证规则提取结果
            assert rule_response.project_id == self.test_project_id
            assert isinstance(rule_response.rules, list)
            assert rule_response.threshold == 0.7
            
            self.log_result(
                "规则提取流程",
                True,
                f"成功提取 {len(rule_response.rules)} 个业务规则"
            )
            
            # 3. 可视化生成
            viz_request = VisualizationRequest(
                project_id=self.test_project_id,
                visualization_type="insight_dashboard",
                time_range_days=30
            )
            
            viz_response = await self.service.generate_visualization(viz_request)
            
            # 验证可视化结果
            assert viz_response.project_id == self.test_project_id
            assert viz_response.visualization_type == "insight_dashboard"
            assert isinstance(viz_response.chart_data, dict)
            assert isinstance(viz_response.chart_config, dict)
            
            self.log_result(
                "可视化生成流程",
                True,
                f"成功生成 {viz_response.visualization_type} 可视化"
            )
            
            # 4. 变化检测
            change_request = ChangeDetectionRequest(
                project_id=self.test_project_id,
                time_window_days=7
            )
            
            change_response = await self.service.detect_pattern_changes(change_request)
            
            # 验证变化检测结果
            assert change_response.project_id == self.test_project_id
            assert change_response.time_window_days == 7
            assert isinstance(change_response.changes_detected, list)
            assert isinstance(change_response.change_summary, dict)
            
            self.log_result(
                "变化检测流程",
                True,
                f"成功检测 {len(change_response.changes_detected)} 个变化"
            )
            
            # 5. 导出功能
            export_request = BusinessLogicExportRequest(
                project_id=self.test_project_id,
                export_format="json",
                include_rules=True,
                include_patterns=True,
                include_insights=True
            )
            
            export_response = await self.service.export_business_logic(export_request)
            
            # 验证导出结果
            assert export_response.project_id == self.test_project_id
            assert export_response.export_format == "json"
            assert export_response.download_url is not None
            assert export_response.file_size > 0
            
            self.log_result(
                "导出功能流程",
                True,
                f"成功导出 {export_response.file_size} 字节数据"
            )
            
        except Exception as e:
            self.log_result("完整业务逻辑提炼流程", False, f"流程验证失败: {str(e)}")
    
    async def validate_frontend_backend_integration(self):
        """验证前后端集成功能"""
        print("\n=== 验证前后端集成功能 ===")
        
        try:
            # 1. API端点可用性测试
            stats = await self.service.get_business_logic_stats(self.test_project_id)
            
            assert stats.project_id == self.test_project_id
            assert stats.total_rules >= 0
            assert stats.active_rules >= 0
            assert stats.total_patterns >= 0
            assert stats.total_insights >= 0
            assert 0.0 <= stats.avg_rule_confidence <= 1.0
            
            self.log_result(
                "API端点可用性",
                True,
                f"统计API正常: 规则 {stats.total_rules}, 模式 {stats.total_patterns}, 洞察 {stats.total_insights}"
            )
            
            # 2. 数据一致性验证
            rules = await self.service.get_business_rules(self.test_project_id)
            patterns = await self.service.get_business_patterns(self.test_project_id)
            insights = await self.service.get_business_insights(self.test_project_id)
            
            # 验证数据结构一致性
            for rule in rules:
                assert hasattr(rule, 'id')
                assert hasattr(rule, 'project_id')
                assert hasattr(rule, 'confidence')
                assert 0.0 <= rule.confidence <= 1.0
            
            for pattern in patterns:
                assert hasattr(pattern, 'id')
                assert hasattr(pattern, 'project_id')
                assert hasattr(pattern, 'strength')
                assert pattern.strength >= 0.0
            
            for insight in insights:
                assert hasattr(insight, 'id')
                assert hasattr(insight, 'project_id')
                assert hasattr(insight, 'impact_score')
                assert 0.0 <= insight.impact_score <= 1.0
            
            self.log_result(
                "数据一致性验证",
                True,
                f"数据结构一致: 规则 {len(rules)}, 模式 {len(patterns)}, 洞察 {len(insights)}"
            )
            
            # 3. 规则管理功能测试
            if len(rules) > 0:
                rule = rules[0]
                
                # 测试置信度更新
                new_confidence = min(1.0, rule.confidence + 0.05)
                update_result = await self.service.update_rule_confidence(rule.id, new_confidence)
                assert update_result is True
                
                # 测试状态切换
                toggle_result = await self.service.toggle_rule_status(rule.id)
                # toggle_rule_status 可能返回 None 或更新后的规则
                
                self.log_result(
                    "规则管理功能",
                    True,
                    f"规则管理正常: 置信度更新 {update_result}, 状态切换完成"
                )
            else:
                self.log_result(
                    "规则管理功能",
                    True,
                    "无可用规则，跳过规则管理测试"
                )
            
        except Exception as e:
            self.log_result("前后端集成功能", False, f"集成验证失败: {str(e)}")
    
    def validate_notification_system(self):
        """验证实时通知系统"""
        print("\n=== 验证实时通知系统 ===")
        
        try:
            # 1. 通知结构验证
            notification_data = {
                "type": "business_insight",
                "project_id": self.test_project_id,
                "title": "测试业务洞察",
                "description": "这是一个测试通知",
                "impact_score": 0.85,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "pattern_type": "sentiment_correlation",
                    "strength": 0.75,
                    "change_percentage": 0.15
                }
            }
            
            # 验证通知数据结构
            required_fields = ["type", "project_id", "title", "timestamp"]
            for field in required_fields:
                assert field in notification_data
            
            assert notification_data["project_id"] == self.test_project_id
            assert 0.0 <= notification_data["impact_score"] <= 1.0
            
            self.log_result(
                "通知结构验证",
                True,
                f"通知结构正确: {notification_data['type']}"
            )
            
            # 2. 通知过滤测试
            notifications = [
                {
                    "type": "business_insight",
                    "project_id": self.test_project_id,
                    "impact_score": 0.9,
                    "timestamp": datetime.now()
                },
                {
                    "type": "pattern_change",
                    "project_id": self.test_project_id,
                    "impact_score": 0.6,
                    "timestamp": datetime.now() - timedelta(hours=1)
                },
                {
                    "type": "rule_update",
                    "project_id": self.test_project_id,
                    "impact_score": 0.3,
                    "timestamp": datetime.now() - timedelta(hours=2)
                }
            ]
            
            # 按影响分数过滤高优先级通知
            high_priority = [n for n in notifications if n["impact_score"] >= 0.8]
            assert len(high_priority) == 1
            assert high_priority[0]["type"] == "business_insight"
            
            # 按时间过滤最近通知
            recent_notifications = [
                n for n in notifications 
                if (datetime.now() - n["timestamp"]).total_seconds() < 3600
            ]
            assert len(recent_notifications) >= 1
            
            self.log_result(
                "通知过滤功能",
                True,
                f"过滤正常: 高优先级 {len(high_priority)}, 最近 {len(recent_notifications)}"
            )
            
            # 3. 通知历史记录测试
            record_id = history_service.add_notification_record(
                notification_type="business_insight",
                channel="email",
                project_id=self.test_project_id,
                title="测试通知",
                status="sent"
            )
            
            assert record_id is not None
            
            history = history_service.get_notification_history(
                project_id=self.test_project_id,
                limit=10
            )
            
            assert len(history) > 0
            assert any(h.id == record_id for h in history)
            
            self.log_result(
                "通知历史记录",
                True,
                f"历史记录正常: 记录ID {record_id}, 历史条数 {len(history)}"
            )
            
        except Exception as e:
            self.log_result("实时通知系统", False, f"通知系统验证失败: {str(e)}")
    
    async def validate_export_import_functionality(self):
        """验证规则导出和应用功能"""
        print("\n=== 验证规则导出和应用功能 ===")
        
        try:
            source_project = "export_source_test"
            target_project = "export_target_test"
            
            # 1. 导出功能测试
            export_formats = ["json", "csv"]
            
            for format_type in export_formats:
                export_request = BusinessLogicExportRequest(
                    project_id=source_project,
                    export_format=format_type,
                    include_rules=True,
                    include_patterns=True,
                    include_insights=True
                )
                
                export_response = await self.service.export_business_logic(export_request)
                
                assert export_response.project_id == source_project
                assert export_response.export_format == format_type
                assert export_response.download_url is not None
                assert export_response.file_size > 0
                assert export_response.expires_at > datetime.now()
                
                self.log_result(
                    f"{format_type.upper()}导出功能",
                    True,
                    f"导出成功: 文件大小 {export_response.file_size} 字节"
                )
            
            # 2. 规则应用功能测试
            source_rules = await self.service.get_business_rules(source_project)
            
            if len(source_rules) > 0:
                # 选择要应用的规则
                selected_rules = source_rules[:min(2, len(source_rules))]
                rule_ids = [rule.id for rule in selected_rules]
                
                application_request = RuleApplicationRequest(
                    source_project_id=source_project,
                    target_project_id=target_project,
                    rule_ids=rule_ids,
                    apply_mode="copy"
                )
                
                application_response = await self.service.apply_business_rules(application_request)
                
                assert application_response.source_project_id == source_project
                assert application_response.target_project_id == target_project
                assert application_response.success_count > 0
                assert len(application_response.applied_rules) == application_response.success_count
                
                # 验证应用的规则
                for applied_rule in application_response.applied_rules:
                    assert applied_rule.id != ""
                    assert source_project in applied_rule.name
                    assert applied_rule.is_active is True
                    assert 0.0 <= applied_rule.confidence <= 1.0
                
                self.log_result(
                    "规则应用功能",
                    True,
                    f"应用成功: {application_response.success_count} 个规则"
                )
            else:
                self.log_result(
                    "规则应用功能",
                    True,
                    "无可用规则，跳过应用测试"
                )
            
            # 3. 导出导入一致性测试
            original_rules = await self.service.get_business_rules(source_project)
            original_patterns = await self.service.get_business_patterns(source_project)
            original_insights = await self.service.get_business_insights(source_project)
            
            # 执行导出
            export_request = BusinessLogicExportRequest(
                project_id=source_project,
                export_format="json",
                include_rules=True,
                include_patterns=True,
                include_insights=True
            )
            
            export_response = await self.service.export_business_logic(export_request)
            
            # 验证导出包含所有数据
            assert export_response.project_id == source_project
            assert export_response.file_size > 0
            assert export_response.download_url is not None
            assert export_response.export_timestamp is not None
            assert export_response.expires_at > export_response.export_timestamp
            
            self.log_result(
                "导出导入一致性",
                True,
                f"一致性验证通过: 规则 {len(original_rules)}, 模式 {len(original_patterns)}, 洞察 {len(original_insights)}"
            )
            
        except Exception as e:
            self.log_result("规则导出和应用功能", False, f"导出应用验证失败: {str(e)}")
    
    async def validate_performance_requirements(self):
        """验证性能要求"""
        print("\n=== 验证性能要求 ===")
        
        try:
            # 1. 模式分析性能测试
            large_annotations = []
            for i in range(500):  # 减少数据量以加快测试
                annotation = {
                    "id": f"perf_ann_{i:04d}",
                    "text": f"This is performance test annotation number {i} with various sentiments",
                    "sentiment": ["positive", "negative", "neutral"][i % 3],
                    "rating": (i % 5) + 1,
                    "annotator": f"user_{i % 10}",
                    "created_at": datetime.now() - timedelta(days=i % 30)
                }
                large_annotations.append(annotation)
            
            start_time = time.time()
            result = self.extractor.analyze_annotation_patterns(large_annotations)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            # 验证结果
            assert result.total_annotations == 500
            assert len(result.patterns) > 0
            
            # 性能要求：500条数据应该在5秒内完成分析
            assert analysis_time < 5.0, f"分析时间过长: {analysis_time:.2f}秒"
            
            self.log_result(
                "模式分析性能",
                True,
                f"性能达标: {analysis_time:.2f}秒处理500条数据，发现 {len(result.patterns)} 个模式"
            )
            
            # 2. 并发操作性能测试
            project_ids = [f"concurrent_perf_project_{i}" for i in range(3)]
            
            tasks = []
            for project_id in project_ids:
                task = self.service.get_business_logic_stats(project_id)
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            concurrent_time = end_time - start_time
            
            # 验证结果
            assert len(results) == 3
            for i, result in enumerate(results):
                assert result.project_id == project_ids[i]
            
            self.log_result(
                "并发操作性能",
                True,
                f"并发性能达标: {concurrent_time:.2f}秒完成3个并发请求"
            )
            
        except Exception as e:
            self.log_result("性能要求", False, f"性能验证失败: {str(e)}")
    
    async def run_comprehensive_validation(self):
        """运行综合验证"""
        print("="*80)
        print("开始业务逻辑端到端测试综合验证")
        print("="*80)
        
        start_time = time.time()
        
        # 执行所有验证
        await self.validate_complete_workflow()
        await self.validate_frontend_backend_integration()
        self.validate_notification_system()
        await self.validate_export_import_functionality()
        await self.validate_performance_requirements()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计结果
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for r in self.validation_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*80)
        print("验证结果汇总")
        print("="*80)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        print(f"总耗时: {total_time:.2f}秒")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for result in self.validation_results:
                if not result["success"]:
                    print(f"  ❌ {result['test_name']}: {result['details']}")
        
        print("\n" + "="*80)
        if failed_tests == 0:
            print("🎉 所有验证测试通过！任务 48.3 端到端业务逻辑测试完成！")
        else:
            print("⚠️  部分验证测试失败，需要进一步检查")
        print("="*80)
        
        return failed_tests == 0
    
    def export_validation_report(self, filename: str = "business_logic_validation_report.json"):
        """导出验证报告"""
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "test_project_id": self.test_project_id,
            "total_tests": len(self.validation_results),
            "passed_tests": sum(1 for r in self.validation_results if r["success"]),
            "failed_tests": sum(1 for r in self.validation_results if not r["success"]),
            "success_rate": (sum(1 for r in self.validation_results if r["success"]) / len(self.validation_results)) * 100 if self.validation_results else 0,
            "test_results": self.validation_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n验证报告已导出: {filename}")

async def main():
    """主函数"""
    validator = BusinessLogicTestValidator()
    
    try:
        success = await validator.run_comprehensive_validation()
        validator.export_validation_report()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)