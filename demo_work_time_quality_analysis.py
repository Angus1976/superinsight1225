#!/usr/bin/env python3
"""
工时质量关联分析系统演示脚本

展示工时与质量分数关联分析、效率评估、基准制定和预测功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from src.quality_billing.work_time_manager import WorkTimeManager
from src.quality_billing.work_time_quality_analyzer import WorkTimeQualityAnalyzer
import json


def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title):
    """打印子章节标题"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def demo_quality_correlation_analysis():
    """演示工时质量关联分析"""
    print_section("工时质量关联分析演示")
    
    manager = WorkTimeManager()
    user_id = "demo_user_001"
    
    # 分析时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"分析用户: {user_id}")
    print(f"分析时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    # 执行关联分析
    result = manager.analyze_work_time_quality_correlation(user_id, start_date, end_date)
    
    if result['success']:
        print_subsection("关联分析结果")
        print(f"数据点数量: {result['data_points']}")
        
        # 显示相关性指标
        if 'correlation_metrics' in result:
            correlations = result['correlation_metrics'].get('correlations', {})
            print(f"\n相关性分析:")
            print(f"  工时与质量相关性: {correlations.get('hours_quality', 0):.3f}")
            print(f"  工时与效率相关性: {correlations.get('hours_efficiency', 0):.3f}")
            print(f"  质量与效率相关性: {correlations.get('quality_efficiency', 0):.3f}")
        
        # 显示效率模式
        if 'efficiency_patterns' in result:
            patterns = result['efficiency_patterns']
            print(f"\n效率模式分析:")
            print(f"  效率趋势: {patterns.get('efficiency_trend', 'N/A')}")
            print(f"  质量趋势: {patterns.get('quality_trend', 'N/A')}")
            
            optimal_hours = patterns.get('optimal_work_hours', {})
            if optimal_hours:
                print(f"  最优工时: {optimal_hours.get('optimal_hours', 0):.1f} 小时")
                print(f"  对应质量分数: {optimal_hours.get('max_quality', 0):.1f}")
        
        # 显示洞察和建议
        if 'insights' in result:
            insights = result['insights']
            if insights:
                print(f"\n关键洞察:")
                for i, insight in enumerate(insights, 1):
                    print(f"  {i}. {insight}")
        
        if 'recommendations' in result:
            recommendations = result['recommendations']
            if recommendations:
                print(f"\n改进建议:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")
    else:
        print(f"分析失败: {result.get('error', '未知错误')}")


def demo_efficiency_assessment():
    """演示效率评估和优化"""
    print_section("效率评估和优化演示")
    
    manager = WorkTimeManager()
    user_id = "demo_user_002"
    task_type = "annotation_task"
    project_id = "demo_project"
    
    print(f"评估用户: {user_id}")
    print(f"任务类型: {task_type}")
    print(f"项目ID: {project_id}")
    
    # 执行效率评估
    result = manager.assess_efficiency_and_optimization(user_id, task_type, project_id)
    
    if result['success']:
        print_subsection("效率评估结果")
        
        # 显示当前效率
        current_efficiency = result.get('current_efficiency', {})
        print(f"当前效率等级: {result.get('efficiency_level', 'N/A')}")
        print(f"综合效率分数: {current_efficiency.get('overall_score', 0):.1f}")
        
        # 显示基准对比
        if 'benchmark_comparison' in result:
            comparison = result['benchmark_comparison']
            print(f"\n基准对比:")
            print(f"  与基准差异: {comparison.get('deviation_from_benchmark', 'N/A')}")
            print(f"  排名百分位: {comparison.get('percentile_ranking', 'N/A')}")
        
        # 显示改进机会
        if 'improvement_opportunities' in result:
            opportunities = result['improvement_opportunities']
            if opportunities:
                print(f"\n改进机会:")
                for i, opp in enumerate(opportunities, 1):
                    print(f"  {i}. {opp.get('description', 'N/A')}")
                    print(f"     预期提升: {opp.get('potential_improvement', 'N/A')}")
        
        # 显示优化计划
        if 'optimization_plan' in result:
            plan = result['optimization_plan']
            print(f"\n优化计划:")
            print(f"  目标效率提升: {plan.get('target_improvement', 'N/A')}")
            print(f"  实施时间: {plan.get('timeline_weeks', 'N/A')} 周")
            
            actions = plan.get('priority_actions', [])
            if actions:
                print(f"  优先行动:")
                for i, action in enumerate(actions, 1):
                    print(f"    {i}. {action}")
    else:
        print(f"评估失败: {result.get('error', '未知错误')}")


def demo_benchmark_configuration():
    """演示基准配置"""
    print_section("工时基准配置演示")
    
    manager = WorkTimeManager()
    
    # 创建样本数据
    sample_data = [
        {'work_hours': 8.0, 'quality_score': 85.0, 'efficiency_ratio': 0.8},
        {'work_hours': 7.5, 'quality_score': 88.0, 'efficiency_ratio': 0.85},
        {'work_hours': 8.5, 'quality_score': 82.0, 'efficiency_ratio': 0.75},
        {'work_hours': 9.0, 'quality_score': 80.0, 'efficiency_ratio': 0.7},
        {'work_hours': 7.0, 'quality_score': 90.0, 'efficiency_ratio': 0.9},
        {'work_hours': 8.2, 'quality_score': 86.0, 'efficiency_ratio': 0.82},
        {'work_hours': 7.8, 'quality_score': 87.0, 'efficiency_ratio': 0.83},
        {'work_hours': 8.3, 'quality_score': 84.0, 'efficiency_ratio': 0.78},
        {'work_hours': 7.7, 'quality_score': 89.0, 'efficiency_ratio': 0.86},
        {'work_hours': 8.1, 'quality_score': 85.5, 'efficiency_ratio': 0.81},
        {'work_hours': 8.4, 'quality_score': 83.0, 'efficiency_ratio': 0.77},
        {'work_hours': 7.6, 'quality_score': 88.5, 'efficiency_ratio': 0.84},
        {'work_hours': 8.6, 'quality_score': 81.5, 'efficiency_ratio': 0.76},
        {'work_hours': 7.9, 'quality_score': 86.5, 'efficiency_ratio': 0.84},
        {'work_hours': 8.7, 'quality_score': 79.0, 'efficiency_ratio': 0.72}
    ]
    
    task_type = "annotation_task"
    project_type = "web_annotation"
    skill_level = "intermediate"
    
    print(f"任务类型: {task_type}")
    print(f"项目类型: {project_type}")
    print(f"技能水平: {skill_level}")
    print(f"样本数量: {len(sample_data)}")
    
    # 配置基准
    result = manager.configure_work_time_benchmarks(
        task_type, project_type, skill_level, sample_data
    )
    
    if result['success']:
        print_subsection("基准配置结果")
        
        benchmark = result['benchmark']
        print(f"基准ID: {result['benchmark_id']}")
        print(f"目标工时: {benchmark['target_hours_per_task']:.1f} 小时")
        print(f"目标质量分数: {benchmark['target_quality_score']:.1f}")
        print(f"目标效率比率: {benchmark['target_efficiency_ratio']:.2f}")
        
        # 显示百分位数
        percentiles = result['percentiles']
        print(f"\n工时百分位数:")
        print(f"  25%: {percentiles['hours']['25']:.1f} 小时")
        print(f"  50%: {percentiles['hours']['50']:.1f} 小时")
        print(f"  75%: {percentiles['hours']['75']:.1f} 小时")
        print(f"  90%: {percentiles['hours']['90']:.1f} 小时")
        
        # 显示统计信息
        statistics_data = result['statistics']
        print(f"\n统计信息:")
        print(f"  平均工时: {statistics_data['mean_hours']:.1f} 小时")
        print(f"  平均质量: {statistics_data['mean_quality']:.1f}")
        print(f"  工时质量相关性: {statistics_data['correlation_hours_quality']:.3f}")
        
        # 显示基准质量
        benchmark_quality = result.get('benchmark_quality', {})
        print(f"\n基准质量评估:")
        print(f"  质量等级: {benchmark_quality.get('quality_score', 'N/A')}")
        print(f"  样本充足性: {'是' if benchmark_quality.get('sample_size_adequate', False) else '否'}")
    else:
        print(f"配置失败: {result.get('error', '未知错误')}")


def demo_work_time_prediction():
    """演示工时和质量预测"""
    print_section("工时和质量预测演示")
    
    manager = WorkTimeManager()
    user_id = "demo_user_003"
    task_type = "annotation_task"
    task_complexity = 0.7  # 中等复杂度
    
    print(f"预测用户: {user_id}")
    print(f"任务类型: {task_type}")
    print(f"任务复杂度: {task_complexity}")
    
    # 执行预测
    result = manager.predict_work_time_and_quality(
        user_id, task_type, task_complexity
    )
    
    if result['success']:
        print_subsection("预测结果")
        
        predictions = result['predictions']
        
        # 工时预测
        work_hours_pred = predictions['work_hours']
        print(f"预测工时: {work_hours_pred['value']:.1f} 小时")
        print(f"置信区间: [{work_hours_pred['confidence_interval'][0]:.1f}, {work_hours_pred['confidence_interval'][1]:.1f}]")
        print(f"准确度等级: {work_hours_pred['accuracy_level']}")
        
        # 质量预测
        quality_pred = predictions['quality_score']
        print(f"\n预测质量分数: {quality_pred['value']:.1f}")
        print(f"置信区间: [{quality_pred['confidence_interval'][0]:.1f}, {quality_pred['confidence_interval'][1]:.1f}]")
        print(f"准确度等级: {quality_pred['accuracy_level']}")
        
        # 模型性能
        model_performance = result['model_performance']
        print(f"\n模型性能:")
        print(f"  工时模型 R²: {model_performance['time_model_r2']:.3f}")
        print(f"  质量模型 R²: {model_performance['quality_model_r2']:.3f}")
        
        # 考虑因素
        factors = result['factors_considered']
        print(f"\n考虑因素:")
        for i, factor in enumerate(factors, 1):
            print(f"  {i}. {factor}")
        
        # 预测建议
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n预测建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
    else:
        print(f"预测失败: {result.get('error', '未知错误')}")


def demo_efficiency_planning():
    """演示效率规划报告"""
    print_section("效率规划报告演示")
    
    manager = WorkTimeManager()
    team_ids = ["team_user_001", "team_user_002", "team_user_003"]
    project_id = "demo_project_planning"
    planning_horizon_weeks = 4
    
    print(f"团队成员: {', '.join(team_ids)}")
    print(f"项目ID: {project_id}")
    print(f"规划周期: {planning_horizon_weeks} 周")
    
    # 生成规划报告
    result = manager.generate_efficiency_planning_report(
        team_ids, project_id, planning_horizon_weeks
    )
    
    if result['success']:
        print_subsection("规划报告结果")
        
        print(f"团队规模: {result['team_size']} 人")
        
        # 团队分析
        team_analysis = result.get('team_analysis', {})
        print(f"\n团队效率分析:")
        print(f"  团队平均效率: {team_analysis.get('team_average_efficiency', 0):.1f}")
        print(f"  效率分布: {team_analysis.get('efficiency_distribution', 'N/A')}")
        
        # 资源分配
        resource_allocation = result.get('resource_allocation', {})
        print(f"\n资源分配策略:")
        print(f"  分配策略: {resource_allocation.get('allocation_strategy', 'N/A')}")
        
        bottlenecks = resource_allocation.get('bottlenecks', [])
        if bottlenecks:
            print(f"  识别瓶颈:")
            for i, bottleneck in enumerate(bottlenecks, 1):
                print(f"    {i}. {bottleneck}")
        
        # 风险评估
        risk_assessment = result.get('risk_assessment', {})
        print(f"\n风险评估:")
        print(f"  风险等级: {risk_assessment.get('risk_level', 'N/A')}")
        
        key_risks = risk_assessment.get('key_risks', [])
        if key_risks:
            print(f"  主要风险:")
            for i, risk in enumerate(key_risks, 1):
                print(f"    {i}. {risk}")
        
        # 规划建议
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n规划建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
    else:
        print(f"规划失败: {result.get('error', '未知错误')}")


def main():
    """主函数"""
    print("工时质量关联分析系统演示")
    print("=" * 60)
    print("本演示展示以下功能:")
    print("1. 工时与质量分数关联分析")
    print("2. 效率评估和优化建议")
    print("3. 工时基准配置")
    print("4. 工时和质量预测")
    print("5. 效率规划报告")
    
    try:
        # 演示各个功能
        demo_quality_correlation_analysis()
        demo_efficiency_assessment()
        demo_benchmark_configuration()
        demo_work_time_prediction()
        demo_efficiency_planning()
        
        print_section("演示完成")
        print("所有功能演示已完成！")
        print("\n主要特性:")
        print("✓ 工时质量关联分析 - 发现工时与质量的关系模式")
        print("✓ 效率评估优化 - 评估当前效率并提供改进建议")
        print("✓ 基准制定 - 建立行业和项目特定的效率基准")
        print("✓ 智能预测 - 基于历史数据预测工时和质量")
        print("✓ 规划支持 - 生成团队效率规划和资源分配建议")
        
    except Exception as e:
        print(f"\n演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()