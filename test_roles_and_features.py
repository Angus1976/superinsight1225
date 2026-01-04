#!/usr/bin/env python3
"""
SuperInsight 平台角色和功能测试脚本

测试各个用户角色的权限和功能
"""

import requests
import json
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

# 配置
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 10

# 颜色定义
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 用户角色
class UserRole(Enum):
    ADMIN = "ADMIN"
    BUSINESS_EXPERT = "BUSINESS_EXPERT"
    ANNOTATOR = "ANNOTATOR"
    VIEWER = "VIEWER"

@dataclass
class TestUser:
    username: str
    email: str
    password: str
    full_name: str
    role: UserRole
    token: Optional[str] = None

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        self.tests.append((True, test_name, message))
        print(f"{Colors.GREEN}✓{Colors.ENDC} {test_name}")
        if message:
            print(f"  {message}")
    
    def add_fail(self, test_name: str, message: str = ""):
        self.failed += 1
        self.tests.append((False, test_name, message))
        print(f"{Colors.RED}✗{Colors.ENDC} {test_name}")
        if message:
            print(f"  {message}")
    
    def print_summary(self):
        total = self.passed + self.failed
        print(f"\n{Colors.BOLD}{self.name} 测试结果:{Colors.ENDC}")
        print(f"  总计: {total} | {Colors.GREEN}通过: {self.passed}{Colors.ENDC} | {Colors.RED}失败: {self.failed}{Colors.ENDC}")
        if self.failed == 0:
            print(f"  {Colors.GREEN}所有测试通过！{Colors.ENDC}")
        else:
            print(f"  {Colors.RED}有 {self.failed} 个测试失败{Colors.ENDC}")

class SuperInsightTester:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.users: Dict[str, TestUser] = {}
        self.results: Dict[str, TestResult] = {}
    
    def print_header(self, text: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    def print_section(self, text: str):
        print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'-'*len(text)}{Colors.ENDC}")
    
    def check_api_health(self) -> bool:
        """检查 API 是否可用"""
        self.print_header("检查 API 健康状态")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"{Colors.GREEN}✓ API 正在运行{Colors.ENDC}")
                health_data = response.json()
                print(f"  整体状态: {health_data.get('overall_status', 'unknown')}")
                return True
            else:
                print(f"{Colors.RED}✗ API 返回错误状态码: {response.status_code}{Colors.ENDC}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"{Colors.RED}✗ 无法连接到 API (http://localhost:8000){Colors.ENDC}")
            print(f"  请确保应用已启动: docker-compose up -d superinsight-api")
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ 检查 API 失败: {e}{Colors.ENDC}")
            return False
    
    def create_test_users(self) -> bool:
        """创建测试用户"""
        self.print_section("创建测试用户")
        
        test_users = [
            TestUser(
                username="admin_test",
                email="admin@test.com",
                password="admin123",
                full_name="系统管理员",
                role=UserRole.ADMIN
            ),
            TestUser(
                username="expert_test",
                email="expert@test.com",
                password="expert123",
                full_name="业务专家",
                role=UserRole.BUSINESS_EXPERT
            ),
            TestUser(
                username="annotator_test",
                email="annotator@test.com",
                password="annotator123",
                full_name="数据标注员",
                role=UserRole.ANNOTATOR
            ),
            TestUser(
                username="viewer_test",
                email="viewer@test.com",
                password="viewer123",
                full_name="报表查看者",
                role=UserRole.VIEWER
            ),
        ]
        
        for user in test_users:
            try:
                response = requests.post(
                    f"{self.base_url}/api/security/users",
                    json={
                        "username": user.username,
                        "email": user.email,
                        "password": user.password,
                        "full_name": user.full_name,
                        "role": user.role.value
                    },
                    timeout=TIMEOUT
                )
                
                if response.status_code in [200, 201]:
                    print(f"{Colors.GREEN}✓ 创建用户: {user.full_name} ({user.role.value}){Colors.ENDC}")
                    self.users[user.username] = user
                elif response.status_code == 409:
                    print(f"{Colors.YELLOW}⚠ 用户已存在: {user.full_name}{Colors.ENDC}")
                    self.users[user.username] = user
                else:
                    print(f"{Colors.RED}✗ 创建用户失败: {user.full_name} - {response.status_code}{Colors.ENDC}")
                    print(f"  响应: {response.text}")
            except Exception as e:
                print(f"{Colors.RED}✗ 创建用户异常: {user.full_name} - {e}{Colors.ENDC}")
        
        return len(self.users) > 0
    
    def login_users(self) -> bool:
        """用户登录"""
        self.print_section("用户登录")
        
        for username, user in self.users.items():
            try:
                response = requests.post(
                    f"{self.base_url}/api/security/login",
                    json={
                        "username": user.username,
                        "password": user.password
                    },
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    user.token = data.get("access_token")
                    print(f"{Colors.GREEN}✓ 登录成功: {user.full_name}{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}✗ 登录失败: {user.full_name} - {response.status_code}{Colors.ENDC}")
                    print(f"  响应: {response.text}")
            except Exception as e:
                print(f"{Colors.RED}✗ 登录异常: {user.full_name} - {e}{Colors.ENDC}")
        
        return all(user.token for user in self.users.values())
    
    def test_admin_features(self):
        """测试管理员功能"""
        self.print_section("测试管理员功能")
        
        result = TestResult("管理员功能")
        admin_user = self.users.get("admin_test")
        
        if not admin_user or not admin_user.token:
            result.add_fail("管理员登录", "管理员用户未登录")
            result.print_summary()
            return result
        
        headers = {"Authorization": f"Bearer {admin_user.token}"}
        
        # 测试 1: 查看系统状态
        try:
            response = requests.get(
                f"{self.base_url}/system/status",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看系统状态", "成功获取系统状态")
            else:
                result.add_fail("查看系统状态", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看系统状态", str(e))
        
        # 测试 2: 查看所有服务
        try:
            response = requests.get(
                f"{self.base_url}/system/services",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看所有服务", "成功获取服务列表")
            else:
                result.add_fail("查看所有服务", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看所有服务", str(e))
        
        # 测试 3: 查看系统指标
        try:
            response = requests.get(
                f"{self.base_url}/system/metrics",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看系统指标", "成功获取系统指标")
            else:
                result.add_fail("查看系统指标", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看系统指标", str(e))
        
        # 测试 4: 创建新用户
        try:
            response = requests.post(
                f"{self.base_url}/api/security/users",
                headers=headers,
                json={
                    "username": "new_user_test",
                    "email": "newuser@test.com",
                    "password": "newpass123",
                    "full_name": "新用户",
                    "role": "VIEWER"
                },
                timeout=TIMEOUT
            )
            if response.status_code in [200, 201, 409]:
                result.add_pass("创建新用户", "成功创建或用户已存在")
            else:
                result.add_fail("创建新用户", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("创建新用户", str(e))
        
        result.print_summary()
        self.results["admin"] = result
        return result
    
    def test_business_expert_features(self):
        """测试业务专家功能"""
        self.print_section("测试业务专家功能")
        
        result = TestResult("业务专家功能")
        expert_user = self.users.get("expert_test")
        
        if not expert_user or not expert_user.token:
            result.add_fail("业务专家登录", "业务专家用户未登录")
            result.print_summary()
            return result
        
        headers = {"Authorization": f"Bearer {expert_user.token}"}
        
        # 测试 1: 查看健康状态
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看健康状态", "成功获取健康状态")
            else:
                result.add_fail("查看健康状态", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看健康状态", str(e))
        
        # 测试 2: 查看 API 信息
        try:
            response = requests.get(
                f"{self.base_url}/api/info",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看 API 信息", "成功获取 API 信息")
            else:
                result.add_fail("查看 API 信息", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看 API 信息", str(e))
        
        # 测试 3: 尝试创建用户（应该失败）
        try:
            response = requests.post(
                f"{self.base_url}/api/security/users",
                headers=headers,
                json={
                    "username": "unauthorized_user",
                    "email": "unauthorized@test.com",
                    "password": "pass123",
                    "full_name": "未授权用户",
                    "role": "VIEWER"
                },
                timeout=TIMEOUT
            )
            if response.status_code == 403:
                result.add_pass("权限检查", "正确拒绝了未授权操作")
            elif response.status_code in [200, 201]:
                result.add_fail("权限检查", "不应该允许业务专家创建用户")
            else:
                result.add_fail("权限检查", f"意外状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("权限检查", str(e))
        
        result.print_summary()
        self.results["expert"] = result
        return result
    
    def test_annotator_features(self):
        """测试标注员功能"""
        self.print_section("测试标注员功能")
        
        result = TestResult("标注员功能")
        annotator_user = self.users.get("annotator_test")
        
        if not annotator_user or not annotator_user.token:
            result.add_fail("标注员登录", "标注员用户未登录")
            result.print_summary()
            return result
        
        headers = {"Authorization": f"Bearer {annotator_user.token}"}
        
        # 测试 1: 查看健康状态
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看健康状态", "成功获取健康状态")
            else:
                result.add_fail("查看健康状态", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看健康状态", str(e))
        
        # 测试 2: 尝试查看系统状态（可能被限制）
        try:
            response = requests.get(
                f"{self.base_url}/system/status",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code in [200, 403]:
                result.add_pass("系统状态访问", f"返回状态码: {response.status_code}")
            else:
                result.add_fail("系统状态访问", f"意外状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("系统状态访问", str(e))
        
        result.print_summary()
        self.results["annotator"] = result
        return result
    
    def test_viewer_features(self):
        """测试查看者功能"""
        self.print_section("测试查看者功能")
        
        result = TestResult("查看者功能")
        viewer_user = self.users.get("viewer_test")
        
        if not viewer_user or not viewer_user.token:
            result.add_fail("查看者登录", "查看者用户未登录")
            result.print_summary()
            return result
        
        headers = {"Authorization": f"Bearer {viewer_user.token}"}
        
        # 测试 1: 查看健康状态
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=headers,
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("查看健康状态", "成功获取健康状态")
            else:
                result.add_fail("查看健康状态", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("查看健康状态", str(e))
        
        # 测试 2: 尝试创建用户（应该失败）
        try:
            response = requests.post(
                f"{self.base_url}/api/security/users",
                headers=headers,
                json={
                    "username": "unauthorized_user2",
                    "email": "unauthorized2@test.com",
                    "password": "pass123",
                    "full_name": "未授权用户2",
                    "role": "VIEWER"
                },
                timeout=TIMEOUT
            )
            if response.status_code == 403:
                result.add_pass("权限检查", "正确拒绝了未授权操作")
            elif response.status_code in [200, 201]:
                result.add_fail("权限检查", "不应该允许查看者创建用户")
            else:
                result.add_fail("权限检查", f"意外状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("权限检查", str(e))
        
        result.print_summary()
        self.results["viewer"] = result
        return result
    
    def test_health_check_endpoints(self):
        """测试健康检查端点"""
        self.print_section("测试健康检查端点")
        
        result = TestResult("健康检查端点")
        
        # 测试 1: 主健康检查端点
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("overall_status")
                result.add_pass("主健康检查", f"状态: {status}")
            else:
                result.add_fail("主健康检查", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("主健康检查", str(e))
        
        # 测试 2: 存活探针
        try:
            response = requests.get(
                f"{self.base_url}/health/live",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result.add_pass("存活探针", "应用正在运行")
            else:
                result.add_fail("存活探针", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("存活探针", str(e))
        
        # 测试 3: 就绪探针
        try:
            response = requests.get(
                f"{self.base_url}/health/ready",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                result.add_pass("就绪探针", f"状态: {status}")
            else:
                result.add_fail("就绪探针", f"状态码: {response.status_code}")
        except Exception as e:
            result.add_fail("就绪探针", str(e))
        
        result.print_summary()
        self.results["health"] = result
        return result
    
    def print_final_summary(self):
        """打印最终总结"""
        self.print_header("测试总结")
        
        total_passed = sum(r.passed for r in self.results.values())
        total_failed = sum(r.failed for r in self.results.values())
        total_tests = total_passed + total_failed
        
        print(f"总计: {total_tests} 个测试")
        print(f"{Colors.GREEN}通过: {total_passed}{Colors.ENDC}")
        print(f"{Colors.RED}失败: {total_failed}{Colors.ENDC}")
        
        if total_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}所有测试通过！✓{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}有 {total_failed} 个测试失败{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}详细结果:{Colors.ENDC}")
        for name, result in self.results.items():
            status = f"{Colors.GREEN}✓{Colors.ENDC}" if result.failed == 0 else f"{Colors.RED}✗{Colors.ENDC}"
            print(f"  {status} {result.name}: {result.passed}/{result.passed + result.failed}")
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_header("SuperInsight 平台测试套件")
        
        # 检查 API 健康状态
        if not self.check_api_health():
            print(f"\n{Colors.RED}API 不可用，无法继续测试{Colors.ENDC}")
            return False
        
        # 创建测试用户
        if not self.create_test_users():
            print(f"\n{Colors.RED}创建测试用户失败{Colors.ENDC}")
            return False
        
        # 用户登录
        if not self.login_users():
            print(f"\n{Colors.RED}用户登录失败{Colors.ENDC}")
            return False
        
        # 测试各个角色的功能
        self.test_admin_features()
        self.test_business_expert_features()
        self.test_annotator_features()
        self.test_viewer_features()
        
        # 测试健康检查端点
        self.test_health_check_endpoints()
        
        # 打印最终总结
        self.print_final_summary()
        
        return True

def main():
    """主函数"""
    tester = SuperInsightTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
