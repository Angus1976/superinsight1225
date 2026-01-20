#!/usr/bin/env python3
"""
Frontend Verification Test Script
Tests all frontend functionality for different user roles to ensure no 404 errors.
"""

import requests
import json
import time
from typing import Dict, List, Optional

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Test users with different roles
TEST_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "manager", "password": "manager123", "role": "manager"},
    {"username": "annotator", "password": "annotator123", "role": "annotator"},
    {"username": "viewer", "password": "viewer123", "role": "viewer"}
]

class FrontendVerifier:
    def __init__(self):
        self.session = requests.Session()
        self.auth_tokens = {}
        
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return JWT token."""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                data={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    self.auth_tokens[username] = token
                    return token
            
            print(f"❌ Authentication failed for {username}: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"❌ Authentication error for {username}: {e}")
            return None
    
    def test_api_endpoint(self, endpoint: str, token: str, method: str = "GET") -> bool:
        """Test API endpoint with authentication."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            if method == "GET":
                response = self.session.get(f"{BASE_URL}{endpoint}", headers=headers)
            elif method == "POST":
                response = self.session.post(f"{BASE_URL}{endpoint}", headers=headers, json={})
            else:
                response = self.session.request(method, f"{BASE_URL}{endpoint}", headers=headers)
            
            if response.status_code in [200, 201]:
                print(f"✅ {endpoint} - {response.status_code}")
                return True
            elif response.status_code == 401:
                print(f"🔒 {endpoint} - Authentication required (expected)")
                return True
            elif response.status_code == 403:
                print(f"🚫 {endpoint} - Access forbidden (role-based)")
                return True
            else:
                print(f"❌ {endpoint} - {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            return False
    
    def test_frontend_route(self, route: str) -> bool:
        """Test frontend route accessibility."""
        try:
            response = self.session.get(f"{FRONTEND_URL}{route}")
            
            if response.status_code == 200:
                # Check if it's actually the React app (not a 404 page)
                if "<!DOCTYPE html>" in response.text and "root" in response.text:
                    print(f"✅ Frontend route {route} - 200 (React app loaded)")
                    return True
                else:
                    print(f"❌ Frontend route {route} - 200 but not React app")
                    return False
            else:
                print(f"❌ Frontend route {route} - {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Frontend route {route} - Error: {e}")
            return False
    
    def verify_user_role_functionality(self, user: Dict[str, str]) -> Dict[str, bool]:
        """Verify functionality for a specific user role."""
        username = user["username"]
        role = user["role"]
        
        print(f"\n🔍 Testing functionality for {username} ({role})")
        print("=" * 50)
        
        # Authenticate user
        token = self.authenticate_user(username, user["password"])
        if not token:
            return {"authentication": False}
        
        results = {"authentication": True}
        
        # Test core API endpoints
        api_endpoints = [
            "/auth/me",
            "/api/v1/tasks",
            "/api/v1/dashboard/metrics",
            "/health"
        ]
        
        print("\n📡 Testing API Endpoints:")
        for endpoint in api_endpoints:
            results[f"api_{endpoint.replace('/', '_')}"] = self.test_api_endpoint(endpoint, token)
        
        # Test role-specific endpoints based on user role
        if role == "admin":
            admin_endpoints = [
                "/api/v1/users",
                "/api/v1/tenants",
                "/api/v1/system/config"
            ]
            print("\n👑 Testing Admin-specific endpoints:")
            for endpoint in admin_endpoints:
                results[f"admin_{endpoint.replace('/', '_')}"] = self.test_api_endpoint(endpoint, token)
        
        elif role == "manager":
            manager_endpoints = [
                "/api/v1/projects",
                "/api/v1/reports",
                "/api/v1/quality/reports"
            ]
            print("\n📊 Testing Manager-specific endpoints:")
            for endpoint in manager_endpoints:
                results[f"manager_{endpoint.replace('/', '_')}"] = self.test_api_endpoint(endpoint, token)
        
        return results
    
    def verify_frontend_routes(self) -> Dict[str, bool]:
        """Verify all frontend routes are accessible."""
        print("\n🌐 Testing Frontend Routes:")
        print("=" * 30)
        
        # Core routes that should be accessible
        routes = [
            "/",
            "/login",
            "/dashboard",
            "/tasks",
            "/projects",
            "/users",
            "/settings",
            "/reports",
            "/quality",
            "/label-studio"
        ]
        
        results = {}
        for route in routes:
            results[f"route_{route.replace('/', '_') or 'root'}"] = self.test_frontend_route(route)
        
        return results
    
    def run_comprehensive_verification(self) -> Dict[str, Dict[str, bool]]:
        """Run comprehensive verification of all functionality."""
        print("🚀 Starting Comprehensive Frontend Verification")
        print("=" * 60)
        
        all_results = {}
        
        # Test frontend routes first
        all_results["frontend_routes"] = self.verify_frontend_routes()
        
        # Test each user role
        for user in TEST_USERS:
            role_key = f"user_{user['username']}"
            all_results[role_key] = self.verify_user_role_functionality(user)
        
        return all_results
    
    def generate_report(self, results: Dict[str, Dict[str, bool]]) -> None:
        """Generate a comprehensive test report."""
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE VERIFICATION REPORT")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in results.items():
            print(f"\n📂 {category.upper().replace('_', ' ')}")
            print("-" * 40)
            
            category_passed = 0
            category_total = 0
            
            for test_name, passed in tests.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {test_name.replace('_', ' ')}: {status}")
                
                category_total += 1
                total_tests += 1
                
                if passed:
                    category_passed += 1
                    passed_tests += 1
            
            success_rate = (category_passed / category_total * 100) if category_total > 0 else 0
            print(f"  📊 Category Success Rate: {success_rate:.1f}% ({category_passed}/{category_total})")
        
        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("🎯 OVERALL RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 90:
            print("🎉 EXCELLENT: System is working very well!")
        elif overall_success_rate >= 75:
            print("👍 GOOD: System is mostly functional with minor issues")
        elif overall_success_rate >= 50:
            print("⚠️  FAIR: System has significant issues that need attention")
        else:
            print("🚨 POOR: System has major issues requiring immediate attention")
        
        # Identify critical failures
        critical_failures = []
        for category, tests in results.items():
            for test_name, passed in tests.items():
                if not passed and any(critical in test_name for critical in ["authentication", "health", "route_root"]):
                    critical_failures.append(f"{category}.{test_name}")
        
        if critical_failures:
            print("\n🚨 CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  - {failure}")
        
        print("\n" + "=" * 60)

def main():
    """Main function to run the verification."""
    verifier = FrontendVerifier()
    
    print("🔧 Checking system availability...")
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not healthy: {response.status_code}")
            return
        print("✅ Backend is healthy")
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return
    
    # Check if frontend is running
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code != 200:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return
        print("✅ Frontend is accessible")
    except Exception as e:
        print(f"❌ Frontend not accessible: {e}")
        return
    
    # Run comprehensive verification
    results = verifier.run_comprehensive_verification()
    
    # Generate report
    verifier.generate_report(results)
    
    # Save results to file
    with open("frontend_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: frontend_verification_results.json")

if __name__ == "__main__":
    main()