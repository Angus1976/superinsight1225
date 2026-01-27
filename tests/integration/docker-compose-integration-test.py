#!/usr/bin/env python3
"""
Simplified Docker Compose Integration Test Suite

Tests core functionality:
1. Service health
2. JWT authentication
3. Task creation
4. Label Studio integration
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://label-studio:8080")

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_header(title):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{title:^70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.ENDC}\n")

def print_test(name):
    print(f"[TEST] {name}...", end=" ", flush=True)

def print_pass(msg=""):
    print(f"{Colors.GREEN}✅ PASS{Colors.ENDC}")
    if msg:
        print(f"       {msg}")

def print_fail(msg=""):
    print(f"{Colors.RED}❌ FAIL{Colors.ENDC}")
    if msg:
        print(f"       {msg}")

def print_warn(msg=""):
    print(f"{Colors.YELLOW}⚠️  WARN{Colors.ENDC}: {msg}")

async def main():
    print(f"\n{Colors.BLUE}Docker Compose Integration Test Suite{Colors.ENDC}\n")
    
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # ====================================================================
        # Section 1: Service Health
        # ====================================================================
        print_header("Section 1: Service Health Checks")
        
        # Test API health
        print_test("SuperInsight API health")
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print_pass()
                passed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        # Test Label Studio health
        print_test("Label Studio health")
        try:
            response = await client.get(f"{LABEL_STUDIO_URL}/health")
            if response.status_code == 200:
                print_pass()
                passed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        # ====================================================================
        # Section 2: JWT Authentication
        # ====================================================================
        print_header("Section 2: JWT Authentication")
        
        jwt_token = None
        
        # Test login
        print_test("Login with valid credentials")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "admin@superinsight.local", "password": "admin123"}
            )
            
            if response.status_code == 200:
                data = response.json()
                jwt_token = data.get("access_token")
                if jwt_token:
                    print_pass(f"Token: {jwt_token[:40]}...")
                    passed += 1
                else:
                    print_fail("No token in response")
                    failed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                print(f"       Response: {response.text[:200]}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        if not jwt_token:
            print_warn("Cannot continue without JWT token")
            print_header("Test Summary")
            print(f"Passed: {Colors.GREEN}{passed}{Colors.ENDC}")
            print(f"Failed: {Colors.RED}{failed}{Colors.ENDC}")
            return 1
        
        # Test JWT token format
        print_test("JWT token format validation")
        parts = jwt_token.split(".")
        if len(parts) == 3:
            print_pass(f"Parts: {len(parts)}")
            passed += 1
        else:
            print_fail(f"Expected 3 parts, got {len(parts)}")
            failed += 1
        
        # Test protected endpoint
        print_test("Access protected endpoint")
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                user_email = data.get("email")
                print_pass(f"User: {user_email}")
                passed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        # ====================================================================
        # Section 3: Task Management
        # ====================================================================
        print_header("Section 3: Task Management")
        
        task_id = None
        
        # Test task creation
        print_test("Create task")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/tasks",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "name": "Integration Test Task",
                    "description": "Testing Docker Compose integration",
                    "priority": "medium",
                    "annotation_type": "text_classification",
                    "total_items": 10,
                    "tags": ["test", "integration"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("id")
                print_pass(f"Task ID: {task_id}")
                passed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                print(f"       Response: {response.text[:200]}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        if task_id:
            # Test task retrieval
            print_test("Retrieve task")
            try:
                response = await client.get(
                    f"{API_BASE_URL}/api/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {jwt_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    task_name = data.get("name")
                    print_pass(f"Name: {task_name}")
                    passed += 1
                else:
                    print_fail(f"Status: {response.status_code}")
                    failed += 1
            except Exception as e:
                print_fail(f"Error: {e}")
                failed += 1
        
        # ====================================================================
        # Section 4: Label Studio Integration
        # ====================================================================
        print_header("Section 4: Label Studio Integration")
        
        # Test Label Studio connection
        print_test("Test Label Studio connection")
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/tasks/label-studio/test-connection",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                print_pass(f"Status: {status}")
                passed += 1
            else:
                print_fail(f"Status: {response.status_code}")
                failed += 1
        except Exception as e:
            print_fail(f"Error: {e}")
            failed += 1
        
        # Test Label Studio project sync
        if task_id:
            print_test("Sync task to Label Studio")
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/tasks/{task_id}/sync-label-studio",
                    headers={"Authorization": f"Bearer {jwt_token}"},
                    json={}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    project_id = data.get("project_id")
                    print_pass(f"Project ID: {project_id}")
                    passed += 1
                else:
                    print_fail(f"Status: {response.status_code}")
                    print(f"       Response: {response.text[:200]}")
                    failed += 1
            except Exception as e:
                print_fail(f"Error: {e}")
                failed += 1
    
    # ========================================================================
    # Summary
    # ========================================================================
    print_header("Test Summary")
    total = passed + failed
    print(f"Total:  {total}")
    print(f"Passed: {Colors.GREEN}{passed}{Colors.ENDC}")
    print(f"Failed: {Colors.RED}{failed}{Colors.ENDC}")
    print()
    
    if failed == 0:
        print(f"{Colors.GREEN}✅ All tests passed!{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.RED}❌ Some tests failed!{Colors.ENDC}\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
