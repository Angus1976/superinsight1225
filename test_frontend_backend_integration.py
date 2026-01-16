#!/usr/bin/env python3
"""
前后端集成测试脚本
测试所有关键API端点和功能
"""

import requests
import json
import os
from typing import Dict, Any, Optional

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# 配置
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# 创建session并禁用代理
session = requests.Session()
session.trust_env = False

# 测试账号
TEST_ACCOUNTS = {
    "admin": {"username": "admin_user", "password": "Admin@123456"},
    "business": {"username": "business_expert", "password": "Business@123456"},
    "tech": {"username": "tech_expert", "password": "Tech@123456"}
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def test_endpoint(method: str, url: str, description: str, 
                  headers: Optional[Dict] = None, 
                  data: Optional[Dict] = None,
                  expected_status: int = 200) -> bool:
    """测试单个API端点"""
    try:
        if method.upper() == "GET":
            response = session.get(url, headers=headers, timeout=5)
        elif method.upper() == "POST":
            response = session.post(url, headers=headers, json=data, timeout=5)
        else:
            print_error(f"不支持的HTTP方法: {method}")
            return False
        
        if response.status_code == expected_status:
            print_success(f"{description} - 状态码: {response.status_code}")
            return True
        else:
            print_error(f"{description} - 期望状态码: {expected_status}, 实际: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"{description} - 请求失败: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("SuperInsight 前后端集成测试")
    print("="*60 + "\n")
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0
    }
    
    # 1. 测试前端服务
    print_info("1. 测试前端服务...")
    if test_endpoint("GET", FRONTEND_URL, "前端页面访问"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # 2. 测试后端健康检查
    print_info("2. 测试后端健康检查...")
    endpoints = [
        ("GET", f"{BASE_URL}/health", "健康检查"),
        ("GET", f"{BASE_URL}/health/live", "存活探针"),
        ("GET", f"{BASE_URL}/health/ready", "就绪探针"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 3. 测试系统状态API
    print_info("3. 测试系统状态API...")
    endpoints = [
        ("GET", f"{BASE_URL}/system/status", "系统状态"),
        ("GET", f"{BASE_URL}/system/metrics", "系统指标"),
        ("GET", f"{BASE_URL}/system/services", "服务状态"),
        ("GET", f"{BASE_URL}/api/info", "API信息"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 4. 测试认证API
    print_info("4. 测试认证API...")
    token = None
    
    # 测试登录
    login_data = TEST_ACCOUNTS["admin"]
    try:
        response = session.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            timeout=5
        )
        if response.status_code == 200:
            print_success(f"管理员登录成功")
            token = response.json().get("access_token")
            results["passed"] += 1
        else:
            print_error(f"管理员登录失败 - 状态码: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        print_error(f"管理员登录失败 - {str(e)}")
        results["failed"] += 1
    results["total"] += 1
    print()
    
    if not token:
        print_warning("未获取到认证令牌，跳过需要认证的测试")
        print("\n" + "="*60)
        print(f"测试完成: {results['passed']}/{results['total']} 通过")
        print("="*60 + "\n")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 5. 测试租户和工作空间API
    print_info("5. 测试租户和工作空间API...")
    endpoints = [
        ("GET", f"{BASE_URL}/auth/tenants", "获取租户列表"),
        ("GET", f"{BASE_URL}/api/workspaces/my", "获取我的工作空间"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc, headers=headers):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 6. 测试业务指标API
    print_info("6. 测试业务指标API...")
    endpoints = [
        ("GET", f"{BASE_URL}/api/business-metrics/summary", "业务指标摘要"),
        ("GET", f"{BASE_URL}/api/business-metrics/annotation-efficiency", "标注效率"),
        ("GET", f"{BASE_URL}/api/business-metrics/user-activity", "用户活动"),
        ("GET", f"{BASE_URL}/api/business-metrics/ai-models", "AI模型指标"),
        ("GET", f"{BASE_URL}/api/business-metrics/projects", "项目指标"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc, headers=headers):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 7. 测试任务API
    print_info("7. 测试任务API...")
    endpoints = [
        ("GET", f"{BASE_URL}/api/tasks", "获取任务列表"),
        ("GET", f"{BASE_URL}/api/tasks/stats", "任务统计"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc, headers=headers):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 8. 测试安全审计API
    print_info("8. 测试安全审计API...")
    endpoints = [
        ("GET", f"{BASE_URL}/api/security/audit-logs", "审计日志"),
        ("GET", f"{BASE_URL}/api/security/audit/summary", "审计摘要"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc, headers=headers):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 9. 测试质量管理API
    print_info("9. 测试质量管理API...")
    endpoints = [
        ("GET", f"{BASE_URL}/api/quality/dashboard/summary", "质量仪表板"),
        ("GET", f"{BASE_URL}/api/quality/rules", "质量规则"),
        ("GET", f"{BASE_URL}/api/quality/stats", "质量统计"),
    ]
    for method, url, desc in endpoints:
        if test_endpoint(method, url, desc, headers=headers):
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 10. 测试其他角色登录
    print_info("10. 测试其他角色登录...")
    for role, credentials in [("业务专家", TEST_ACCOUNTS["business"]), 
                               ("技术专家", TEST_ACCOUNTS["tech"])]:
        try:
            response = session.post(
                f"{BASE_URL}/auth/login",
                json=credentials,
                timeout=5
            )
            if response.status_code == 200:
                print_success(f"{role}登录成功")
                results["passed"] += 1
            else:
                print_error(f"{role}登录失败 - 状态码: {response.status_code}")
                results["failed"] += 1
        except Exception as e:
            print_error(f"{role}登录失败 - {str(e)}")
            results["failed"] += 1
        results["total"] += 1
    print()
    
    # 输出测试结果
    print("="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"总测试数: {results['total']}")
    print(f"{Colors.GREEN}通过: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}失败: {results['failed']}{Colors.END}")
    
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    print(f"成功率: {success_rate:.1f}%")
    print("="*60 + "\n")
    
    if results['failed'] == 0:
        print_success("所有测试通过！系统运行正常。")
    else:
        print_warning(f"有 {results['failed']} 个测试失败，请检查相关服务。")

if __name__ == "__main__":
    main()
