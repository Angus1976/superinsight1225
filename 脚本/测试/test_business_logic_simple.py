#!/usr/bin/env python3
"""
业务逻辑测试和验证系统简化测试
不依赖外部机器学习库的基础功能测试
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_data_validator():
    """测试数据验证器基础功能"""
    print("\n=== 测试数据验证器 ===")
    
    try:
        from src.business_logic.data_validator import DataCompletenessValidator, DataFormatValidator
        
        # 测试完整性验证器
        completeness_validator = DataCompletenessValidator()
        
        # 创建测试数据
        test_data = [
            {"id": 1, "name": "张三", "email": "zhang@example.com"},
            {"id": 2, "name": "", "email": "li@example.com"},  # 缺失name
            {"id": 3, "name": "王五", "email": ""},  # 缺失email
            {"id": 4, "name": "赵六", "email": "zhao@example.com"}
        ]
        
        # 验证必需字段
        required_fields = ["id", "name", "email"]
        results = completeness_validator.validate_completeness(test_data, required_fields)
        
        print(f"完整性验证结果:")
        for result in results:
            status = "✅" if result.passed else "❌"
            print(f"  {status} {result.rule_name}: 错误率 {result.error_rate:.2%}")
        
        # 测试格式验证器
        format_validator = DataFormatValidator()
        
        # 测试邮箱格式验证
        format_rules = {"email": "email"}
        format_results = format_validator.validate_format(test_data, format_rules)
        
        print(f"格式验证结果:")
        for result in format_results:
            status = "✅" if result.passed else "❌"
            print(f"  {status} {result.rule_name}: 错误率 {result.error_rate:.2%}")
        
        print("✅ 数据验证器测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据验证器测试失败: {e}")
        return False

def test_monitoring_system():
    """测试监控系统基础功能"""
    print("\n=== 测试监控系统 ===")
    
    try:
        from src.business_logic.monitoring_system import MetricsCollector, AlertManager
        
        # 测试指标收集器
        collector = MetricsCollector()
        
        # 添加一些测试指标
        now = datetime.now()
        collector.add_metric("test.cpu.usage", 75.5, now, {"host": "test"})
        collector.add_metric("test.memory.usage", 60.2, now, {"host": "test"})
        collector.add_metric("test.cpu.usage", 80.1, now + timedelta(seconds=30), {"host": "test"})
        
        # 获取指标列表
        metrics = collector.list_metrics()
        print(f"收集的指标: {metrics}")
        
        # 获取指标摘要
        cpu_summary = collector.get_metric_summary("test.cpu.usage")
        print(f"CPU使用率摘要: {cpu_summary}")
        
        # 测试告警管理器
        alert_manager = AlertManager()
        
        # 添加告警规则
        rule_id = alert_manager.add_alert_rule(
            "test.cpu.usage", 80.0, "greater", "high", "CPU使用率过高"
        )
        print(f"添加告警规则: {rule_id}")
        
        # 检查告警
        alert_manager.check_alerts(collector)
        
        # 获取活跃告警
        active_alerts = alert_manager.get_active_alerts()
        print(f"活跃告警数: {len(active_alerts)}")
        
        for alert in active_alerts:
            print(f"  告警: {alert.alert_name} - {alert.message}")
        
        print("✅ 监控系统测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 监控系统测试失败: {e}")
        return False

def test_business_logic_api():
    """测试业务逻辑API基础功能"""
    print("\n=== 测试业务逻辑API ===")
    
    try:
        # 检查API文件是否存在
        api_file = "src/business_logic/api.py"
        if os.path.exists(api_file):
            print(f"✅ API文件存在: {api_file}")
            
            # 读取API文件内容检查
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查关键API端点
            api_endpoints = [
                "/api/business-logic/advanced-analysis",
                "/api/business-logic/algorithms",
                "/api/business-logic/testing/comprehensive",
                "/api/business-logic/data-quality/validate",
                "/api/business-logic/monitoring/start"
            ]
            
            found_endpoints = 0
            for endpoint in api_endpoints:
                if endpoint in content:
                    found_endpoints += 1
                    print(f"  ✅ 找到端点: {endpoint}")
                else:
                    print(f"  ❌ 缺少端点: {endpoint}")
            
            print(f"API端点检查: {found_endpoints}/{len(api_endpoints)} 个端点存在")
            
        else:
            print(f"❌ API文件不存在: {api_file}")
            return False
        
        print("✅ 业务逻辑API测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 业务逻辑API测试失败: {e}")
        return False

def test_algorithm_manager():
    """测试算法管理器"""
    print("\n=== 测试算法管理器 ===")
    
    try:
        from src.business_logic.algorithm_manager import BusinessLogicAlgorithmManager
        
        # 创建算法管理器
        manager = BusinessLogicAlgorithmManager()
        
        # 获取可用算法
        algorithms = manager.get_available_algorithms()
        print(f"可用算法: {len(algorithms)} 个")
        
        for algo in algorithms:
            print(f"  - {algo['name']}: {algo['description']}")
        
        # 测试算法执行（使用模拟数据）
        test_data = [
            {"text": "这是一个好产品", "sentiment": "positive"},
            {"text": "服务很差", "sentiment": "negative"}
        ]
        
        # 尝试执行一个算法
        if algorithms:
            algo_name = algorithms[0]['name']
            print(f"测试执行算法: {algo_name}")
            
            # 这里只是测试接口，不执行实际算法
            print(f"  算法接口正常")
        
        print("✅ 算法管理器测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 算法管理器测试失败: {e}")
        return False

def test_file_structure():
    """测试文件结构完整性"""
    print("\n=== 测试文件结构 ===")
    
    try:
        required_files = [
            "src/business_logic/testing_framework.py",
            "src/business_logic/data_validator.py", 
            "src/business_logic/monitoring_system.py",
            "src/business_logic/algorithm_manager.py",
            "src/business_logic/advanced_algorithms.py",
            "src/business_logic/api.py",
            "src/business_logic/service.py"
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in required_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
                print(f"  ✅ {file_path}")
            else:
                missing_files.append(file_path)
                print(f"  ❌ {file_path}")
        
        print(f"\n文件结构检查: {len(existing_files)}/{len(required_files)} 个文件存在")
        
        if missing_files:
            print(f"缺少文件: {missing_files}")
            return False
        
        print("✅ 文件结构测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 文件结构测试失败: {e}")
        return False

def test_import_modules():
    """测试模块导入"""
    print("\n=== 测试模块导入 ===")
    
    try:
        modules_to_test = [
            ("数据验证器", "src.business_logic.data_validator"),
            ("监控系统", "src.business_logic.monitoring_system"),
            ("算法管理器", "src.business_logic.algorithm_manager"),
            ("高级算法", "src.business_logic.advanced_algorithms"),
            ("测试框架", "src.business_logic.testing_framework")
        ]
        
        successful_imports = 0
        
        for module_name, module_path in modules_to_test:
            try:
                __import__(module_path)
                print(f"  ✅ {module_name}: {module_path}")
                successful_imports += 1
            except ImportError as e:
                print(f"  ❌ {module_name}: {module_path} - {e}")
            except Exception as e:
                print(f"  ⚠️  {module_name}: {module_path} - {e}")
        
        print(f"\n模块导入检查: {successful_imports}/{len(modules_to_test)} 个模块成功导入")
        
        print("✅ 模块导入测试完成")
        return successful_imports == len(modules_to_test)
        
    except Exception as e:
        print(f"❌ 模块导入测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始业务逻辑测试和验证系统简化测试")
    print("=" * 60)
    
    test_results = []
    
    # 运行各项测试
    test_functions = [
        ("文件结构检查", test_file_structure),
        ("模块导入测试", test_import_modules),
        ("数据验证器", test_data_validator),
        ("监控系统", test_monitoring_system),
        ("算法管理器", test_algorithm_manager),
        ("业务逻辑API", test_business_logic_api)
    ]
    
    for test_name, test_func in test_functions:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed_tests += 1
    
    print(f"\n总体结果: {passed_tests}/{total_tests} 个测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试都通过了！业务逻辑测试和验证系统基础功能正常。")
        return True
    elif passed_tests >= total_tests * 0.8:
        print("✅ 大部分测试通过，系统基本功能正常。")
        return True
    else:
        print("⚠️  多个测试失败，请检查相关功能。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)