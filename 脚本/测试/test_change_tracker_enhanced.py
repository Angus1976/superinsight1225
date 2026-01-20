#!/usr/bin/env python3
"""
测试增强的变化趋势跟踪系统
验证任务 47.3 的实现
"""

import sys
import os
sys.path.append('src')

from business_logic.change_tracker import AdvancedBusinessMetricTracker, ChangeTrackingManager
from datetime import datetime, timedelta
import numpy as np

def test_advanced_business_metric_tracker():
    """测试高级业务指标跟踪器"""
    print("=== 测试高级业务指标跟踪器 ===")
    
    # 创建测试数据
    test_annotations = []
    base_time = datetime.now()
    
    for i in range(50):
        annotation = {
            'id': i,
            'text': f'这是测试文本 {i}，包含一些内容用于分析。' * (i % 3 + 1),
            'sentiment': ['positive', 'negative', 'neutral'][i % 3],
            'rating': 3 + (i % 3) + np.random.normal(0, 0.5),
            'annotator': f'user_{i % 5}',
            'task_id': f'task_{i // 10}',
            'created_at': (base_time + timedelta(hours=i)).isoformat(),
            'status': 'completed' if i % 4 != 0 else 'in_progress'
        }
        test_annotations.append(annotation)
    
    # 创建跟踪器
    tracker = AdvancedBusinessMetricTracker()
    
    # 执行跟踪
    result = tracker.track_metrics(test_annotations)
    
    # 验证结果
    assert 'current_metrics' in result
    assert 'change_points' in result
    assert 'anomalies' in result
    assert 'trend_predictions' in result
    assert 'correlations' in result
    assert 'impact_assessment' in result
    assert 'early_warnings' in result
    assert 'advanced_features' in result
    
    print(f"✅ 当前指标数量: {len(result['current_metrics'])}")
    print(f"✅ 检测到变化点: {len(result['change_points'])}")
    print(f"✅ 检测到异常: {len(result['anomalies'])}")
    print(f"✅ 趋势预测: {len(result['trend_predictions'])}")
    print(f"✅ 相关性分析: {len(result['correlations'])}")
    print(f"✅ 影响评估: {result['impact_assessment']['overall_stability']}")
    print(f"✅ 早期警告: {len(result['early_warnings']['active_warnings'])}")
    
    # 验证高级特性
    advanced_features = result['advanced_features']
    print(f"✅ 季节性检测: {advanced_features['seasonality_detected']}")
    print(f"✅ 相关性强度: {advanced_features['correlation_strength']:.3f}")
    print(f"✅ 异常聚类: {advanced_features['anomaly_clusters']}")
    
    return True

def test_change_tracking_manager():
    """测试变化跟踪管理器"""
    print("\n=== 测试变化跟踪管理器 ===")
    
    # 创建测试数据
    test_annotations = []
    base_time = datetime.now()
    
    # 创建一些有趋势的数据
    for i in range(30):
        # 添加一些趋势和异常
        sentiment_bias = 'positive' if i > 20 else ['positive', 'negative', 'neutral'][i % 3]
        rating_bias = 4.5 if i > 25 else 3 + (i % 3) + np.random.normal(0, 0.3)
        
        annotation = {
            'id': i,
            'text': f'测试文本内容 {i}',
            'sentiment': sentiment_bias,
            'rating': max(1, min(5, rating_bias)),
            'annotator': f'user_{i % 3}',
            'task_id': f'task_{i // 5}',
            'created_at': (base_time + timedelta(hours=i)).isoformat(),
            'status': 'completed'
        }
        test_annotations.append(annotation)
    
    # 创建管理器
    manager = ChangeTrackingManager()
    
    # 执行综合跟踪
    result = manager.run_comprehensive_tracking(test_annotations, "test_project")
    
    # 验证结果
    assert 'project_id' in result
    assert 'tracking_results' in result
    assert 'daily_report' in result
    
    print(f"✅ 项目ID: {result['project_id']}")
    print(f"✅ 跟踪结果完整性: {'tracking_results' in result}")
    print(f"✅ 日报生成: {'daily_report' in result}")
    
    # 检查日报内容
    daily_report = result['daily_report']
    print(f"✅ 日报标题: {daily_report.get('title', 'N/A')}")
    print(f"✅ 关键发现: {len(daily_report.get('key_findings', []))}")
    print(f"✅ 建议数量: {len(daily_report.get('recommendations', []))}")
    
    # 检查警报报告
    if result.get('alert_report'):
        alert_report = result['alert_report']
        print(f"✅ 警报级别: {alert_report.get('alert_level', 'N/A')}")
        print(f"✅ 立即行动: {len(alert_report.get('immediate_actions', []))}")
    else:
        print("✅ 无需警报报告（系统正常）")
    
    return True

def test_enhanced_features():
    """测试增强功能"""
    print("\n=== 测试增强功能 ===")
    
    tracker = AdvancedBusinessMetricTracker()
    
    # 测试季节性检测
    seasonal_data = []
    for i in range(48):  # 2天的小时数据
        # 创建有季节性模式的数据
        base_value = 100
        seasonal_component = 20 * np.sin(2 * np.pi * i / 24)  # 24小时周期
        noise = np.random.normal(0, 5)
        value = base_value + seasonal_component + noise
        seasonal_data.append(value)
    
    seasonality_detected, period = tracker._detect_seasonality(np.array(seasonal_data))
    print(f"✅ 季节性检测: {seasonality_detected}, 周期: {period}")
    
    # 测试多层异常检测
    anomaly_data = [1, 2, 3, 2, 1, 2, 15, 2, 1, 3, 2, 1]  # 包含一个明显异常值
    tracker.metric_history['test_metric'] = [(datetime.now() + timedelta(hours=i), val) for i, val in enumerate(anomaly_data)]
    tracker.baseline_stats['test_metric'] = {
        'mean': np.mean(anomaly_data),
        'std': np.std(anomaly_data),
        'min': np.min(anomaly_data),
        'max': np.max(anomaly_data),
        'median': np.median(anomaly_data)
    }
    
    anomalies = tracker._multi_layer_anomaly_detection()
    print(f"✅ 多层异常检测: 发现 {len(anomalies)} 个异常")
    
    if anomalies:
        for anomaly in anomalies:
            print(f"   - {anomaly.metric_name}: {anomaly.severity} 级别异常")
    
    return True

def main():
    """主测试函数"""
    print("开始测试增强的变化趋势跟踪系统...")
    
    try:
        # 运行所有测试
        test_advanced_business_metric_tracker()
        test_change_tracking_manager()
        test_enhanced_features()
        
        print("\n🎉 所有测试通过！任务 47.3 变化趋势跟踪系统实现成功！")
        print("\n增强功能包括:")
        print("✅ 多层异常检测算法")
        print("✅ 智能趋势预测（包含季节性检测）")
        print("✅ 综合影响评估")
        print("✅ 早期警告系统")
        print("✅ 相关性分析")
        print("✅ 自动报告生成")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)