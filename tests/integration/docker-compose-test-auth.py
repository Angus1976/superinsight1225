#!/usr/bin/env python3
"""
Docker Compose JWT and Label Studio Authentication Test Suite

This script provides comprehensive testing for:
1. JWT token generation and validation
2. Label Studio API Token authentication
3. Project creation and management
4. Task synchronization
5. Annotation sync
6. Language parameter handling
7. Error handling and recovery

Usage:
    docker-compose exec app python docker-compose-test-auth.py
    docker compose exec app python docker-compose-test-auth.py
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://label-studio:8080")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin")

# Colors
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

@dataclass
class TestResult:
    """Test result data class"""
    name: str
    passed: bool
    message: str
    details: Optional[str] = None
    duration: float = 0.0

class TestSuite:
    """JWT and Label Studio Authentication Test Suite"""
    
    def __init__(self):
        self.results: list[TestResult] = []
        self.jwt_token: Optional[str] = None
        self.task_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.api_token: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def log_header(self, title: str):
        """Log section header"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BLUE}{title:^70}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'='*70}{Colors.ENDC}\n")
    
    def log_test(self, name: str):
        """Log test start"""
        print(f"{Colors.CYAN}[TEST]{Colors.ENDC} {name}...", end=" ", flush=True)
    
    def log_pass(self, message: str, details: Optional[str] = None):
        """Log test pass"""
        print(f"{Colors.GREEN}✅ PASS{Colors.ENDC}")
        if details:
            print(f"  {Colors.GREEN}→{Colors.ENDC} {details}")
    
    def log_fail(self, message: str, details: Optional[str] = None):
        """Log test fail"""
        print(f"{Colors.RED}❌ FAIL{Colors.ENDC}")
        if details:
            print(f"  {Colors.RED}→{Colors.ENDC} {details}")
    
    def log_info(self, message: str):
        """Log info message"""
        print(f"{Colors.BLUE}ℹ️  INFO{Colors.ENDC}: {message}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        print(f"{Colors.YELLOW}⚠️  WARN{Colors.ENDC}: {message}")
    
    async def add_result(self, name: str, passed: bool, message: str, 
                        details: Optional[str] = None, duration: float = 0.0):
        """Add test result"""
        result = TestResult(name, passed, message, details, duration)
        self.results.append(result)
    
    async def wait_for_service(self, url: str, max_attempts: int = 30) -> bool:
        """Wait for service to be ready"""
        for attempt in range(max_attempts):
            try:
                response = await self.client.get(url)
                if response.status_code < 500:
                    return True
            except Exception:
                pass
            
            print(".", end="", flush=True)
            await asyncio.sleep(1)
        
        return False
    
    # ========================================================================
    # Section 1: Service Health Checks
    # ========================================================================
    
    async def test_service_health(self):
        """Test service health checks"""
        self.log_header("Section 1: Service Health Checks")
        
        # Test SuperInsight API
        self.log_test("SuperInsight API health check")
        if await self.wait_for_service(f"{API_BASE_URL}/health"):
            self.log_pass("SuperInsight API is ready")
            await self.add_result("SuperInsight API health", True, "API is ready")
        else:
            self.log_fail("SuperInsight API not responding")
            await self.add_result("SuperInsight API health", False, "API not responding")
            return False
        
        # Test Label Studio
        self.log_test("Label Studio health check")
        if await self.wait_for_service(f"{LABEL_STUDIO_URL}/health"):
            self.log_pass("Label Studio is ready")
            await self.add_result("Label Studio health", True, "Label Studio is ready")
        else:
            self.log_fail("Label Studio not responding")
            await self.add_result("Label Studio health", False, "Label Studio not responding")
            return False
        
        return True
    
    # ========================================================================
    # Section 2: JWT Authentication Tests
    # ========================================================================
    
    async def test_jwt_authentication(self):
        """Test JWT authentication"""
        self.log_header("Section 2: JWT Authentication Tests")
        
        # Test 2.1: Login with valid credentials
        self.log_test("Login with valid credentials")
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "admin@superinsight.local", "password": "admin123"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("access_token")
                
                if self.jwt_token:
                    self.log_pass("Login successful", f"Token: {self.jwt_token[:50]}...")
                    await self.add_result("JWT login", True, "Login successful")
                else:
                    self.log_fail("JWT token not found in response")
                    await self.add_result("JWT login", False, "Token not found")
                    return False
            else:
                error_detail = response.text if response.status_code != 200 else ""
                self.log_fail(f"Login failed with status {response.status_code}: {error_detail}")
                await self.add_result("JWT login", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            import traceback
            self.log_fail(f"Login error: {str(e)}")
            traceback.print_exc()
            await self.add_result("JWT login", False, str(e))
            return False
        
        # Test 2.2: Validate JWT token format
        self.log_test("Validate JWT token format")
        token_parts = self.jwt_token.split(".")
        if len(token_parts) == 3:
            self.log_pass("JWT token has valid format", f"Parts: {len(token_parts)}")
            await self.add_result("JWT format", True, "Valid format")
        else:
            self.log_fail(f"JWT token has invalid format (expected 3 parts, got {len(token_parts)})")
            await self.add_result("JWT format", False, f"Invalid format: {len(token_parts)} parts")
            return False
        
        # Test 2.3: Use JWT token to access protected endpoint
        self.log_test("Access protected endpoint with JWT token")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/users/me",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get("id")
                self.log_pass("Protected endpoint accessible", f"User ID: {user_id}")
                await self.add_result("JWT protected endpoint", True, "Accessible")
            else:
                self.log_fail(f"Protected endpoint returned {response.status_code}")
                await self.add_result("JWT protected endpoint", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_fail(f"Protected endpoint error: {str(e)}")
            await self.add_result("JWT protected endpoint", False, str(e))
            return False
        
        # Test 2.4: Reject invalid JWT token
        self.log_test("Reject invalid JWT token")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/users/me",
                headers={"Authorization": "Bearer invalid.token.here"}
            )
            
            if response.status_code in [401, 403]:
                self.log_pass("Invalid JWT token rejected", f"Status: {response.status_code}")
                await self.add_result("JWT invalid token", True, "Rejected")
            else:
                self.log_fail(f"Invalid JWT token not rejected (status {response.status_code})")
                await self.add_result("JWT invalid token", False, f"Not rejected: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Invalid token test error: {str(e)}")
            await self.add_result("JWT invalid token", False, str(e))
        
        # Test 2.5: Reject missing JWT token
        self.log_test("Reject missing JWT token")
        try:
            response = await self.client.get(f"{API_BASE_URL}/api/users/me")
            
            if response.status_code in [401, 403]:
                self.log_pass("Missing JWT token rejected", f"Status: {response.status_code}")
                await self.add_result("JWT missing token", True, "Rejected")
            else:
                self.log_fail(f"Missing JWT token not rejected (status {response.status_code})")
                await self.add_result("JWT missing token", False, f"Not rejected: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Missing token test error: {str(e)}")
            await self.add_result("JWT missing token", False, str(e))
        
        return True
    
    # ========================================================================
    # Section 3: Label Studio API Token Authentication
    # ========================================================================
    
    async def test_label_studio_authentication(self):
        """Test Label Studio API Token authentication"""
        self.log_header("Section 3: Label Studio API Token Authentication")
        
        # Get API Token from environment
        try:
            with open("/app/.env", "r") as f:
                for line in f:
                    if line.startswith("LABEL_STUDIO_API_TOKEN="):
                        self.api_token = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
        
        if not self.api_token:
            self.log_warning("LABEL_STUDIO_API_TOKEN not found in .env")
            return True
        
        self.log_info(f"Using API Token: {self.api_token[:50]}...")
        
        # Test 3.1: Test Label Studio connection
        self.log_test("Test Label Studio API connection")
        try:
            response = await self.client.get(
                f"{LABEL_STUDIO_URL}/api/current-user/whoami/",
                headers={"Authorization": f"Token {self.api_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                user_email = data.get("email", "N/A")
                self.log_pass("Label Studio API connection successful", f"User: {user_email}")
                await self.add_result("Label Studio connection", True, "Connected")
            else:
                self.log_fail(f"Label Studio API failed with status {response.status_code}")
                await self.add_result("Label Studio connection", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_fail(f"Label Studio connection error: {str(e)}")
            await self.add_result("Label Studio connection", False, str(e))
            return False
        
        # Test 3.2: List projects
        self.log_test("List Label Studio projects")
        try:
            response = await self.client.get(
                f"{LABEL_STUDIO_URL}/api/projects/",
                headers={"Authorization": f"Token {self.api_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                project_count = len(data.get("results", []))
                self.log_pass("List projects successful", f"Projects: {project_count}")
                await self.add_result("Label Studio list projects", True, f"{project_count} projects")
            else:
                self.log_fail(f"List projects failed with status {response.status_code}")
                await self.add_result("Label Studio list projects", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"List projects error: {str(e)}")
            await self.add_result("Label Studio list projects", False, str(e))
        
        # Test 3.3: Reject invalid API Token
        self.log_test("Reject invalid API Token")
        try:
            response = await self.client.get(
                f"{LABEL_STUDIO_URL}/api/current-user/whoami/",
                headers={"Authorization": "Token invalid_token_12345"}
            )
            
            if response.status_code in [401, 403]:
                self.log_pass("Invalid API Token rejected", f"Status: {response.status_code}")
                await self.add_result("Label Studio invalid token", True, "Rejected")
            else:
                self.log_fail(f"Invalid API Token not rejected (status {response.status_code})")
                await self.add_result("Label Studio invalid token", False, f"Not rejected: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Invalid token test error: {str(e)}")
            await self.add_result("Label Studio invalid token", False, str(e))
        
        return True
    
    # ========================================================================
    # Section 4: Project Management Tests
    # ========================================================================
    
    async def test_project_management(self):
        """Test project management"""
        self.log_header("Section 4: Project Management Tests")
        
        if not self.jwt_token:
            self.log_warning("JWT token not available")
            return True
        
        # Test 4.1: Create a test task
        self.log_test("Create test task")
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/api/tasks",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                json={
                    "name": "Test Task for Auth",
                    "description": "Testing JWT and Label Studio auth",
                    "priority": "medium",
                    "annotation_type": "text_classification",
                    "total_items": 10,
                    "tags": ["test", "auth"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.task_id = data.get("id")
                self.log_pass("Task created successfully", f"Task ID: {self.task_id}")
                await self.add_result("Create task", True, "Task created")
            else:
                self.log_fail(f"Task creation failed with status {response.status_code}")
                await self.add_result("Create task", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_fail(f"Task creation error: {str(e)}")
            await self.add_result("Create task", False, str(e))
            return False
        
        # Test 4.2: Verify task has sync status
        self.log_test("Verify task has Label Studio sync status")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/tasks/{self.task_id}",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                sync_status = data.get("label_studio_sync_status")
                
                if sync_status:
                    self.log_pass("Task has sync status", f"Status: {sync_status}")
                    await self.add_result("Task sync status", True, f"Status: {sync_status}")
                else:
                    self.log_warning("Task missing sync status field")
                    await self.add_result("Task sync status", False, "Missing field")
            else:
                self.log_fail(f"Task detail retrieval failed with status {response.status_code}")
                await self.add_result("Task sync status", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"Task detail error: {str(e)}")
            await self.add_result("Task sync status", False, str(e))
        
        return True
    
    # ========================================================================
    # Section 5: Label Studio Project Creation Tests
    # ========================================================================
    
    async def test_label_studio_project_creation(self):
        """Test Label Studio project creation"""
        self.log_header("Section 5: Label Studio Project Creation Tests")
        
        if not self.jwt_token or not self.task_id:
            self.log_warning("JWT token or Task ID not available")
            return True
        
        # Test 5.1: Test Label Studio connection endpoint
        self.log_test("Test Label Studio connection via API")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/tasks/label-studio/test-connection",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                self.log_pass("Label Studio connection test successful", f"Status: {status}")
                await self.add_result("Label Studio connection test", True, f"Status: {status}")
            else:
                self.log_fail(f"Connection test failed with status {response.status_code}")
                await self.add_result("Label Studio connection test", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"Connection test error: {str(e)}")
            await self.add_result("Label Studio connection test", False, str(e))
        
        # Test 5.2: Ensure project exists
        self.log_test("Ensure Label Studio project exists for task")
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/api/tasks/{self.task_id}/sync-label-studio",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.project_id = data.get("project_id")
                self.log_pass("Project sync initiated", f"Project ID: {self.project_id}")
                await self.add_result("Project sync", True, f"Project ID: {self.project_id}")
            else:
                self.log_fail(f"Project sync failed with status {response.status_code}")
                await self.add_result("Project sync", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"Project sync error: {str(e)}")
            await self.add_result("Project sync", False, str(e))
        
        # Test 5.3: Verify project exists in Label Studio
        if self.project_id and self.api_token:
            self.log_test("Verify project exists in Label Studio")
            try:
                response = await self.client.get(
                    f"{LABEL_STUDIO_URL}/api/projects/{self.project_id}/",
                    headers={"Authorization": f"Token {self.api_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    title = data.get("title")
                    self.log_pass("Project verified in Label Studio", f"Title: {title}")
                    await self.add_result("Project verification", True, f"Title: {title}")
                else:
                    self.log_fail(f"Project verification failed with status {response.status_code}")
                    await self.add_result("Project verification", False, f"Status {response.status_code}")
            except Exception as e:
                self.log_fail(f"Project verification error: {str(e)}")
                await self.add_result("Project verification", False, str(e))
        
        return True
    
    # ========================================================================
    # Section 6: Language Parameter Tests
    # ========================================================================
    
    async def test_language_parameters(self):
        """Test language parameter handling"""
        self.log_header("Section 6: Language Parameter Tests")
        
        if not self.jwt_token or not self.project_id:
            self.log_warning("JWT token or Project ID not available")
            return True
        
        # Test 6.1: Get authenticated URL with Chinese language
        self.log_test("Get authenticated URL with Chinese language")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/label-studio/projects/{self.project_id}/auth-url?language=zh",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                url = data.get("url", "")
                
                if "lang=zh" in url:
                    self.log_pass("Chinese language parameter included", f"URL: {url[:80]}...")
                    await self.add_result("Language parameter (zh)", True, "Included")
                else:
                    self.log_warning("Chinese language parameter not found in URL")
                    await self.add_result("Language parameter (zh)", False, "Not found")
            else:
                self.log_fail(f"URL generation failed with status {response.status_code}")
                await self.add_result("Language parameter (zh)", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"URL generation error: {str(e)}")
            await self.add_result("Language parameter (zh)", False, str(e))
        
        # Test 6.2: Get authenticated URL with English language
        self.log_test("Get authenticated URL with English language")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/label-studio/projects/{self.project_id}/auth-url?language=en",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                url = data.get("url", "")
                
                if "lang=en" in url:
                    self.log_pass("English language parameter included", f"URL: {url[:80]}...")
                    await self.add_result("Language parameter (en)", True, "Included")
                else:
                    self.log_warning("English language parameter not found in URL")
                    await self.add_result("Language parameter (en)", False, "Not found")
            else:
                self.log_fail(f"URL generation failed with status {response.status_code}")
                await self.add_result("Language parameter (en)", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_fail(f"URL generation error: {str(e)}")
            await self.add_result("Language parameter (en)", False, str(e))
        
        return True
    
    # ========================================================================
    # Section 7: Error Handling Tests
    # ========================================================================
    
    async def test_error_handling(self):
        """Test error handling"""
        self.log_header("Section 7: Error Handling Tests")
        
        if not self.jwt_token:
            self.log_warning("JWT token not available")
            return True
        
        # Test 7.1: Handle missing project
        self.log_test("Handle missing Label Studio project")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/label-studio/projects/99999/validate",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code in [404, 400]:
                self.log_pass("Missing project handled correctly", f"Status: {response.status_code}")
                await self.add_result("Missing project handling", True, f"Status: {response.status_code}")
            else:
                self.log_warning(f"Missing project returned unexpected status {response.status_code}")
                await self.add_result("Missing project handling", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Missing project test error: {str(e)}")
            await self.add_result("Missing project handling", False, str(e))
        
        # Test 7.2: Handle invalid task ID
        self.log_test("Handle invalid task ID")
        try:
            response = await self.client.get(
                f"{API_BASE_URL}/api/tasks/invalid-task-id",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            
            if response.status_code in [404, 400]:
                self.log_pass("Invalid task ID handled correctly", f"Status: {response.status_code}")
                await self.add_result("Invalid task ID handling", True, f"Status: {response.status_code}")
            else:
                self.log_warning(f"Invalid task ID returned unexpected status {response.status_code}")
                await self.add_result("Invalid task ID handling", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Invalid task ID test error: {str(e)}")
            await self.add_result("Invalid task ID handling", False, str(e))
        
        # Test 7.3: Handle unauthorized access
        self.log_test("Handle unauthorized access to task")
        try:
            response = await self.client.get(f"{API_BASE_URL}/api/tasks/{self.task_id}")
            
            if response.status_code in [401, 403]:
                self.log_pass("Unauthorized access rejected", f"Status: {response.status_code}")
                await self.add_result("Unauthorized access handling", True, f"Status: {response.status_code}")
            else:
                self.log_warning(f"Unauthorized access returned unexpected status {response.status_code}")
                await self.add_result("Unauthorized access handling", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_fail(f"Unauthorized access test error: {str(e)}")
            await self.add_result("Unauthorized access handling", False, str(e))
        
        return True
    
    # ========================================================================
    # Test Summary
    # ========================================================================
    
    def print_summary(self):
        """Print test summary"""
        self.log_header("Test Summary")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print(f"Total Tests:  {Colors.BLUE}{total}{Colors.ENDC}")
        print(f"Passed:       {Colors.GREEN}{passed}{Colors.ENDC}")
        print(f"Failed:       {Colors.RED}{failed}{Colors.ENDC}")
        print()
        
        if failed == 0:
            print(f"{Colors.GREEN}✅ All tests passed!{Colors.ENDC}\n")
            return 0
        else:
            print(f"{Colors.RED}❌ Some tests failed!{Colors.ENDC}\n")
            return 1

async def main():
    """Main test execution"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  Docker Compose JWT and Label Studio Authentication Test Suite ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    async with TestSuite() as suite:
        # Run all test sections
        await suite.test_service_health()
        await suite.test_jwt_authentication()
        await suite.test_label_studio_authentication()
        await suite.test_project_management()
        await suite.test_label_studio_project_creation()
        await suite.test_language_parameters()
        await suite.test_error_handling()
        
        # Print summary
        return suite.print_summary()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
