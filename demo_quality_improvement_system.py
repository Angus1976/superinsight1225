#!/usr/bin/env python3
"""
质量改进系统演示脚本

演示质量改进系统的完整功能，包括根因分析、模式识别、修复建议生成、
效果预测和个性化指导。
"""

import sys
import os
from datetime import datetime, timedelta
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.quality.quality_improvement_system import quality_improvement_system
from src.quality.root_cause_analyzer import QualityIssue, ProblemCategory, SeverityLevel


def create_sample_issues():
    """创建示例质量问题"""
    
    issues = [
        QualityIssue(
            id="issue_001",
            category=ProblemCategory.ACCURACY,
            description="数据标注中发现多个日期格式错误，影响时间序列分析准确性",
            affected_data=["data_001", "data_002", "data_003", "data_004", "data_005"],
            reporter="user_001",
            created_at=datetime.now() - timedelta(hours=2),
            severity=SeverityLevel.HIGH,
            context={
                "timestamp": datetime.now() - timedelta(hours=2),
                "user_id": "user_001",
                "session_id": "session_123"
            },
            metadata={
                "data_source": "external_api",
                "tool_version": "v2.1.0",
                "batch_id": "batch_001"
            }
        ),
        
        QualityIssue(
            id="issue_002",
            category=ProblemCategory.CONSISTENCY,
            description="不同标注员对同类实体使用了不同的标签，导致数据不一致",
            affected_data=[f"data_{i:03d}" for i in range(10, 25)],
            reporter="user_002",
            created_at=datetime.now() - timedelta(hours=6),
            severity=SeverityLevel.MEDIUM,
            context={
                "timestamp": datetime.now() - timedelta(hours=6),
                "user_id": "user_002",
                "project_id": "project_alpha"
            },
            metadata={
                "data_source": "internal_dataset",
                "tool_version": "v2.0.5",
                "annotator_count": 3
            }
        ),
        
        QualityIssue(
            id="issue_003",
            category=ProblemCategory.SYSTEM,
            description="系统在处理大批量数据时出现内存溢出，导致标注任务失败",
            affected_data=[f"batch_{i}" for i in range(1, 6)],
            reporter="system",
            created_at=datetime.now() - timedelta(minutes=30),
            severity=SeverityLevel.CRITICAL,
            context={
                "timestamp": datetime.now() - timedelta(minutes=30),
                "system_load": 0.95,
                "memory_usage": 0.98
            },
            metadata={
                "data_source": "large_dataset",
                "tool_version": "v2.1.0",
                "batch_size": 10000
            }
        )
    ]
    
    return issues


def demo_quality_improvement_system():
    """演示质量改进系统"""
    
    print("=" * 80)
    print("质量改进系统演示")
    print("=" * 80)
    
    # 创建示例问题
    issues = create_sample_issues()
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{'='*60}")
        print(f"处理问题 {i}: {issue.id}")
        print(f"{'='*60}")
        
        print(f"\n📋 问题详情:")
        print(f"  类别: {issue.category.value}")
        print(f"  严重程度: {issue.severity.value}")
        print(f"  描述: {issue.description}")
        print(f"  影响数据: {len(issue.affected_data)} 条记录")
        print(f"  报告时间: {issue.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 处理质量问题
        try:
            result = quality_improvement_system.process_quality_issue(
                issue, user_id=f"user_{i:03d}"
            )
            
            # 显示根因分析结果
            print(f"\n🔍 根因分析结果:")
            print(f"  主要原因: {result.root_cause_analysis.primary_cause.value}")
            print(f"  贡献因素: {[f.value for f in result.root_cause_analysis.contributing_factors]}")
            print(f"  置信度: {result.root_cause_analysis.confidence_score:.2f}")
            print(f"  证据:")
            for evidence in result.root_cause_analysis.evidence:
                print(f"    - {evidence}")
            
            # 显示匹配的模式
            print(f"\n🎯 匹配模式:")
            if result.matching_patterns:
                for pattern in result.matching_patterns:
                    print(f"  - {pattern.name} (置信度: {pattern.confidence_score:.2f})")
            else:
                print("  未发现匹配的历史模式")
            
            # 显示修复建议
            print(f"\n💡 修复建议 (共 {len(result.repair_suggestions)} 个):")
            for j, suggestion in enumerate(result.repair_suggestions[:3], 1):  # 只显示前3个
                print(f"  {j}. {suggestion.title}")
                print(f"     类型: {suggestion.suggestion_type.value}")
                print(f"     优先级: {suggestion.priority.value}")
                print(f"     预估工作量: {suggestion.estimated_effort}")
                print(f"     成功概率: {suggestion.success_probability:.2f}")
            
            # 显示修复计划
            print(f"\n📋 修复计划:")
            plan = result.repair_plan
            print(f"  计划ID: {plan.plan_id}")
            print(f"  立即行动: {len(plan.immediate_actions)} 项")
            print(f"  短期措施: {len(plan.short_term_actions)} 项")
            print(f"  长期改进: {len(plan.long_term_actions)} 项")
            print(f"  预防措施: {len(plan.preventive_actions)} 项")
            print(f"  总体成功概率: {plan.overall_success_probability:.2f}")
            
            # 显示效果预测
            print(f"\n📊 效果预测:")
            if result.effect_predictions:
                for prediction in result.effect_predictions[:2]:  # 只显示前2个
                    print(f"  建议: {prediction.suggestion_id}")
                    print(f"    成功概率: {prediction.success_probability:.2f}")
                    print(f"    效果等级: {prediction.effect_level.value}")
                    print(f"    置信度: {prediction.confidence.value}")
                    print(f"    预计解决时间: {prediction.time_to_resolution:.1f} 小时")
            
            # 显示个性化指导
            print(f"\n🎓 个性化指导:")
            if result.personalized_guidance:
                guidance = result.personalized_guidance
                print(f"  用户技能水平: {guidance.get('user_skill_level', 'unknown')}")
                print(f"  指导内容: {len(guidance.get('guidance_content', []))} 项")
                print(f"  培训推荐: {len(guidance.get('training_recommendations', []))} 项")
                print(f"  最佳实践: {len(guidance.get('best_practice_cases', []))} 项")
                
                # 显示个性化提示
                tips = guidance.get('personalized_tips', [])
                if tips:
                    print(f"  个性化提示:")
                    for tip in tips[:3]:  # 只显示前3个
                        print(f"    - {tip}")
            
            # 显示综合评估
            print(f"\n📈 综合评估:")
            print(f"  整体成功概率: {result.overall_success_probability:.2f}")
            print(f"  推荐方法: {result.recommended_approach}")
            print(f"  优先级: {result.priority_level}")
            print(f"  处理时间: {result.processing_time_seconds:.2f} 秒")
            
        except Exception as e:
            print(f"❌ 处理问题时发生错误: {str(e)}")
            continue
    
    # 显示系统洞察
    print(f"\n{'='*60}")
    print("系统洞察和统计")
    print(f"{'='*60}")
    
    try:
        insights = quality_improvement_system.get_quality_insights(7)  # 最近7天
        
        print(f"\n📊 根因分析统计:")
        root_cause_stats = insights.get('root_cause_analysis', {})
        if 'cause_frequency' in root_cause_stats:
            print("  常见根因:")
            for cause, count in list(root_cause_stats['cause_frequency'].items())[:5]:
                print(f"    - {cause}: {count} 次")
        
        print(f"\n🎯 模式识别统计:")
        pattern_stats = insights.get('pattern_recognition', {})
        print(f"  总模式数: {pattern_stats.get('total_patterns', 0)}")
        print(f"  活跃模式: {pattern_stats.get('active_patterns', 0)}")
        
        print(f"\n💡 建议生成统计:")
        suggestion_stats = insights.get('suggestion_generation', {})
        print(f"  总建议数: {suggestion_stats.get('total_suggestions_generated', 0)}")
        print(f"  总计划数: {suggestion_stats.get('total_plans_created', 0)}")
        
        print(f"\n🎓 指导系统统计:")
        guidance_stats = insights.get('guidance_system', {})
        print(f"  指导内容: {guidance_stats.get('guidance_content_count', 0)} 项")
        print(f"  培训资源: {guidance_stats.get('training_resources_count', 0)} 项")
        print(f"  最佳实践: {guidance_stats.get('best_practice_cases_count', 0)} 项")
        print(f"  用户档案: {guidance_stats.get('user_profiles_count', 0)} 个")
        
    except Exception as e:
        print(f"❌ 获取系统洞察时发生错误: {str(e)}")
    
    print(f"\n{'='*80}")
    print("演示完成")
    print(f"{'='*80}")


def demo_user_dashboard():
    """演示用户仪表板功能"""
    
    print(f"\n{'='*60}")
    print("用户仪表板演示")
    print(f"{'='*60}")
    
    user_id = "demo_user_001"
    
    try:
        dashboard = quality_improvement_system.get_user_dashboard(user_id)
        
        if 'error' in dashboard:
            print(f"⚠️  {dashboard['error']}")
            return
        
        print(f"\n👤 用户档案:")
        profile = dashboard.get('user_profile', {})
        print(f"  用户ID: {profile.get('user_id', 'unknown')}")
        print(f"  整体技能水平: {profile.get('overall_skill_level', 'unknown')}")
        print(f"  处理问题总数: {profile.get('total_issues_handled', 0)}")
        print(f"  成功解决率: {profile.get('success_rate', 0):.2f}")
        print(f"  培训时长: {profile.get('training_hours', 0):.1f} 小时")
        
        print(f"\n📚 学习路径推荐:")
        learning_paths = dashboard.get('learning_paths', {})
        for category, path in list(learning_paths.items())[:3]:  # 只显示前3个
            print(f"  {category}:")
            print(f"    当前技能: {path.get('current_skill_level', 'unknown')}")
            print(f"    推荐课程: {len(path.get('learning_path', []))} 个")
            print(f"    预估时长: {path.get('estimated_duration_hours', 0):.1f} 小时")
        
    except Exception as e:
        print(f"❌ 获取用户仪表板时发生错误: {str(e)}")


if __name__ == "__main__":
    print("🚀 启动质量改进系统演示...")
    
    try:
        # 主要演示
        demo_quality_improvement_system()
        
        # 用户仪表板演示
        demo_user_dashboard()
        
        print("\n✅ 演示成功完成！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()