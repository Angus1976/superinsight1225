#!/usr/bin/env python3
"""
Full-stack integration testing script for SuperInsight platform.

This script tests:
1. Database connectivity
2. Backend API endpoints
3. Authentication flow
4. Core functionality
5. Frontend integration
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess
import os

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Test accounts
TEST_ACCOUNTS = {
    "admin": {
        "username": "admin@superinsight.com",
        "password": "Admin@123456",
        "role": "admin",
        "language": "zh"
    },
    "analyst": {
        "username": "analyst@superinsight.com",
        "password": "Analyst@123456",
        "role": "analyst",
        "language": "en"
    },
    "editor": {
        "username": "editor@superinsight.com",
        "password": "Editor@123456",
        "role": "editor",
        "language": "zh"
    },
    "user": {
        "username": "user@superinsight.com",
        "password": "User@123456",
        "role": "user",
        "language": "en"
    },
    "guest": {
        "username": "guest@superinsight.com",
        "password": "Guest@123456",
        "role": "guest",
        "language": "zh"
    }
}

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
    
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"{Colors.GREEN}✓{Colors.RESET} {test_name}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"{Colors.RED}✗{Colors.RESET} {test_name}")
        print(f"  {Colors.RED}Error: {error}{Colors.RESET}")
    
    def add_skip(self, test_name: str, reason: str):
        self.skipped += 1
        print(f"{Colors.YELLOW}⊘{Colors.RESET} {test_name} (Skipped: {reason})")
    
    def print_summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}测试总结{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"总测试数: {total}")
        print(f"{Colors.GREEN}通过: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}失败: {self.failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}跳过: {self.skipped}{Colors.RESET}")
        
        if self.errors:
            print(f"\n{Colors.BOLD}失败详情:{Colors.RESET}")
            for error in self.errors:
                print(f"  - {error}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\n成功率: {success_rate:.1f}%")
        
        return self.failed == 0

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")

def test_backend_health(result: TestResult):
    """Test backend health check endpoint."""
    print_header("1. 后端健康检查")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            result.add_pass("后端服务运行正常")
        else:
            result.add_fail("后端服务", f"状态码: {response.status_code}")
    except requests.exceptions.ConnectionError:
        result.add_fail("后端服务", "无法连接到后端服务")
    except Exception as e:
        result.add_fail("后端服务", str(e))

def test_database_connection(result: TestResult):
    """Test database connectivity."""
    print_header("2. 数据库连接")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health/db", timeout=5)
        if response.status_code == 200:
            result.add_pass("数据库连接正常")
        else:
            result.add_fail("数据库连接", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("数据库连接", str(e))

def test_i18n_service(result: TestResult):
    """Test i18n service."""
    print_header("3. 国际化服务")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health/i18n", timeout=5)
        if response.status_code == 200:
            result.add_pass("i18n 服务运行正常")
        else:
            result.add_fail("i18n 服务", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("i18n 服务", str(e))

def test_authentication(result: TestResult) -> Optional[Dict[str, Any]]:
    """Test authentication flow."""
    print_header("4. 认证流程")
    
    tokens = {}
    
    for account_name, account_info in TEST_ACCOUNTS.items():
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/security/login",
                json={
                    "username": account_info["username"],
                    "password": account_info["password"]
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                tokens[account_name] = data.get("access_token")
                result.add_pass(f"登录成功: {account_info['username']}")
            else:
                result.add_fail(
                    f"登录失败: {account_info['username']}",
                    f"状态码: {response.status_code}"
                )
        except Exception as e:
            result.add_fail(f"登录异常: {account_info['username']}", str(e))
    
    return tokens if tokens else None

def test_user_endpoints(result: TestResult, tokens: Dict[str, str]):
    """Test user management endpoints."""
    print_header("5. 用户管理 API")
    
    if not tokens:
        result.add_skip("用户管理 API", "没有有效的认证令牌")
        return
    
    admin_token = tokens.get("admin")
    if not admin_token:
        result.add_skip("用户管理 API", "没有管理员令牌")
        return
    
    try:
        # Get current user
        response = requests.get(
            f"{API_BASE_URL}/api/security/users/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result.add_pass("获取当前用户信息")
        else:
            result.add_fail("获取当前用户信息", f"状态码: {response.status_code}")
        
        # Get users list
        response = requests.get(
            f"{API_BASE_URL}/api/security/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result.add_pass("获取用户列表")
        else:
            result.add_fail("获取用户列表", f"状态码: {response.status_code}")
    
    except Exception as e:
        result.add_fail("用户管理 API", str(e))

def test_billing_endpoints(result: TestResult, tokens: Dict[str, str]):
    """Test billing API endpoints."""
    print_header("6. 计费管理 API")
    
    if not tokens:
        result.add_skip("计费管理 API", "没有有效的认证令牌")
        return
    
    admin_token = tokens.get("admin")
    if not admin_token:
        result.add_skip("计费管理 API", "没有管理员令牌")
        return
    
    try:
        # Get billing report
        response = requests.get(
            f"{API_BASE_URL}/api/billing/enhanced-report",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result.add_pass("获取计费报表")
        else:
            result.add_fail("获取计费报表", f"状态码: {response.status_code}")
    
    except Exception as e:
        result.add_fail("计费管理 API", str(e))

def test_quality_endpoints(result: TestResult, tokens: Dict[str, str]):
    """Test quality management API endpoints."""
    print_header("7. 质量管理 API")
    
    if not tokens:
        result.add_skip("质量管理 API", "没有有效的认证令牌")
        return
    
    admin_token = tokens.get("admin")
    if not admin_token:
        result.add_skip("质量管理 API", "没有管理员令牌")
        return
    
    try:
        # Get quality report
        response = requests.get(
            f"{API_BASE_URL}/api/quality/report",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            result.add_pass("获取质量报表")
        else:
            result.add_fail("获取质量报表", f"状态码: {response.status_code}")
    
    except Exception as e:
        result.add_fail("质量管理 API", str(e))

def test_api_documentation(result: TestResult):
    """Test API documentation availability."""
    print_header("8. API 文档")
    
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            result.add_pass("Swagger API 文档可访问")
        else:
            result.add_fail("Swagger API 文档", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("Swagger API 文档", str(e))
    
    try:
        response = requests.get(f"{API_BASE_URL}/redoc", timeout=5)
        if response.status_code == 200:
            result.add_pass("ReDoc API 文档可访问")
        else:
            result.add_fail("ReDoc API 文档", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("ReDoc API 文档", str(e))

def test_frontend_availability(result: TestResult):
    """Test frontend availability."""
    print_header("9. 前端应用")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            result.add_pass("前端应用可访问")
        else:
            result.add_fail("前端应用", f"状态码: {response.status_code}")
    except requests.exceptions.ConnectionError:
        result.add_fail("前端应用", "无法连接到前端应用")
    except Exception as e:
        result.add_fail("前端应用", str(e))

def test_cors_configuration(result: TestResult):
    """Test CORS configuration."""
    print_header("10. CORS 配置")
    
    try:
        response = requests.options(
            f"{API_BASE_URL}/api/security/login",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "POST"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result.add_pass("CORS 配置正确")
        else:
            result.add_fail("CORS 配置", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("CORS 配置", str(e))

def test_error_handling(result: TestResult):
    """Test error handling."""
    print_header("11. 错误处理")
    
    try:
        # Test invalid login
        response = requests.post(
            f"{API_BASE_URL}/api/security/login",
            json={
                "username": "invalid@example.com",
                "password": "invalid"
            },
            timeout=5
        )
        
        if response.status_code == 401:
            result.add_pass("无效凭证返回 401")
        else:
            result.add_fail("无效凭证处理", f"预期 401，得到 {response.status_code}")
    
    except Exception as e:
        result.add_fail("错误处理", str(e))

def test_performance(result: TestResult):
    """Test API performance."""
    print_header("12. 性能测试")
    
    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        if elapsed < 100:
            result.add_pass(f"健康检查响应时间: {elapsed:.1f}ms")
        elif elapsed < 500:
            result.add_pass(f"健康检查响应时间: {elapsed:.1f}ms (可接受)")
        else:
            result.add_fail("健康检查性能", f"响应时间过长: {elapsed:.1f}ms")
    
    except Exception as e:
        result.add_fail("性能测试", str(e))

def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     SuperInsight 全栈集成测试                              ║")
    print("║     Full-Stack Integration Test                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    print(f"\n配置信息:")
    print(f"  后端 API: {API_BASE_URL}")
    print(f"  前端应用: {FRONTEND_URL}")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = TestResult()
    
    # Run tests
    test_backend_health(result)
    test_database_connection(result)
    test_i18n_service(result)
    tokens = test_authentication(result)
    
    if tokens:
        test_user_endpoints(result, tokens)
        test_billing_endpoints(result, tokens)
        test_quality_endpoints(result, tokens)
    
    test_api_documentation(result)
    test_frontend_availability(result)
    test_cors_configuration(result)
    test_error_handling(result)
    test_performance(result)
    
    # Print summary
    success = result.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
