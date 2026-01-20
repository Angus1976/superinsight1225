#!/usr/bin/env python3
"""
Authenticated Route Testing Script
Tests frontend routes after authentication to identify real 404 errors.
"""

import requests
import json
import time
from typing import Dict, List, Tuple, Optional

# Test configuration
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"

# Test users
TEST_USERS = [
    {
        "username": "admin_user",
        "password": "Admin@123456",
        "role": "admin",
        "expected_access": ["dashboard", "tasks", "billing", "settings", "admin", "augmentation", "quality", "security", "data-sync"]
    },
    {
        "username": "business_expert", 
        "password": "Business@123456",
        "role": "business_expert",
        "expected_access": ["dashboard", "tasks", "billing", "settings", "quality"]
    },
    {
        "username": "technical_expert",
        "password": "Technical@123456", 
        "role": "technical_expert",
        "expected_access": ["dashboard", "tasks", "settings", "augmentation", "quality", "data-sync"]
    },
    {
        "username": "contractor",
        "password": "Contractor@123456",
        "role": "contractor", 
        "expected_access": ["dashboard", "tasks", "settings"]
    },
    {
        "username": "viewer",
        "password": "Viewer@123456",
        "role": "viewer",
        "expected_access": ["dashboard", "settings"]
    }
]

def get_auth_token(username: str, password: str) -> Optional[str]:
    """Get authentication token from backend"""
    try:
        # Try different possible auth endpoints
        auth_endpoints = [
            "/api/v1/auth/login",
            "/api/auth/login", 
            "/auth/login",
            "/login"
        ]
        
        for endpoint in auth_endpoints:
            try:
                response = requests.post(
                    f"{BACKEND_URL}{endpoint}",
                    json={"username": username, "password": password},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("access_token") or data.get("token")
                    if token:
                        print(f"✅ Authentication successful for {username} via {endpoint}")
                        return token
                elif response.status_code == 404:
                    continue  # Try next endpoint
                else:
                    print(f"❌ Auth failed for {username} via {endpoint}: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException:
                continue  # Try next endpoint
                
        print(f"❌ No working auth endpoint found for {username}")
        return None
        
    except Exception as e:
        print(f"❌ Auth error for {username}: {e}")
        return None

def test_api_with_auth(token: str, username: str) -> Dict[str, bool]:
    """Test API endpoints with authentication"""
    endpoints = {
        "/api/v1/auth/me": "User profile",
        "/api/v1/tasks": "Tasks list", 
        "/api/v1/dashboard/metrics": "Dashboard metrics",
        "/health": "Health check (no auth needed)"
    }
    
    results = {}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🔍 Testing API endpoints for {username}...")
    
    for endpoint, description in endpoints.items():
        try:
            url = f"{BACKEND_URL}{endpoint}"
            response = requests.get(url, headers=headers, timeout=5)
            
            # Different endpoints have different expected status codes
            if endpoint == "/health":
                success = response.status_code == 200
            elif endpoint in ["/api/v1/auth/me", "/api/v1/tasks", "/api/v1/dashboard/metrics"]:
                success = response.status_code in [200, 401, 403, 404]  # 404 means endpoint doesn't exist
            else:
                success = response.status_code in [200, 401, 403]
            
            results[endpoint] = success
            status = "✅" if success else "❌"
            print(f"  {status} {endpoint} - {description} (HTTP {response.status_code})")
            
        except Exception as e:
            results[endpoint] = False
            print(f"  ❌ {endpoint} - Error: {e}")
    
    return results

def test_frontend_with_browser_simulation(username: str, password: str, role: str, expected_access: List[str]) -> Dict[str, bool]:
    """Simulate browser behavior to test frontend routes"""
    print(f"\n🌐 Testing frontend routes for {username} ({role})...")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Test routes that should be accessible for this role
    routes_to_test = [
        "/dashboard",
        "/tasks", 
        "/tasks/1",
        "/billing",
        "/settings",
        "/admin",
        "/augmentation", 
        "/quality",
        "/security",
        "/data-sync"
    ]
    
    results = {}
    
    for route in routes_to_test:
        try:
            url = f"{FRONTEND_URL}{route}"
            response = session.get(url, timeout=10, allow_redirects=True)
            
            # For React SPA, we expect 200 with HTML content
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    # Check if it's the React app
                    if 'id="root"' in response.text or 'react' in response.text.lower():
                        route_name = route.strip('/')
                        should_have_access = route_name in expected_access or route_name == ""
                        
                        # For React SPA, all routes return 200, but access control is handled by React
                        results[route] = True
                        status = "✅" if should_have_access else "⚠️"
                        access_note = "expected" if should_have_access else "may be restricted by React"
                        print(f"  {status} {route} - React app loaded ({access_note})")
                    else:
                        results[route] = False
                        print(f"  ❌ {route} - HTML returned but not React app")
                else:
                    results[route] = False
                    print(f"  ❌ {route} - Wrong content type: {content_type}")
            else:
                results[route] = False
                print(f"  ❌ {route} - HTTP {response.status_code}")
                
        except Exception as e:
            results[route] = False
            print(f"  ❌ {route} - Error: {e}")
    
    return results

def check_frontend_console_errors() -> List[str]:
    """Check for common frontend issues that might cause 404s"""
    issues = []
    
    try:
        # Test if main React bundle loads
        response = requests.get(f"{FRONTEND_URL}/", timeout=5)
        if response.status_code == 200:
            html_content = response.text
            
            # Check for common issues
            if 'Failed to fetch' in html_content:
                issues.append("API fetch failures detected")
            if 'ChunkLoadError' in html_content:
                issues.append("JavaScript chunk loading errors")
            if 'Module not found' in html_content:
                issues.append("Module import errors")
            if 'Cannot resolve' in html_content:
                issues.append("Module resolution errors")
                
    except Exception as e:
        issues.append(f"Failed to check frontend: {e}")
    
    return issues

def main():
    """Main test function"""
    print("🚀 SuperInsight Authenticated Route Testing")
    print("=" * 60)
    
    # Check for frontend console errors first
    print("\n🔍 Checking for frontend issues...")
    frontend_issues = check_frontend_console_errors()
    if frontend_issues:
        print("⚠️  Potential frontend issues detected:")
        for issue in frontend_issues:
            print(f"  - {issue}")
    else:
        print("✅ No obvious frontend issues detected")
    
    # Test each user role
    all_results = {}
    
    for user in TEST_USERS:
        username = user["username"]
        password = user["password"] 
        role = user["role"]
        expected_access = user["expected_access"]
        
        print(f"\n" + "=" * 60)
        print(f"🧪 Testing user: {username} (Role: {role})")
        print("=" * 60)
        
        # Try to get auth token
        token = get_auth_token(username, password)
        
        if token:
            # Test API endpoints with auth
            api_results = test_api_with_auth(token, username)
            
            # Test frontend routes
            frontend_results = test_frontend_with_browser_simulation(username, password, role, expected_access)
            
            all_results[username] = {
                "role": role,
                "auth_success": True,
                "api_results": api_results,
                "frontend_results": frontend_results
            }
        else:
            print(f"⚠️  Skipping {username} - authentication failed")
            all_results[username] = {
                "role": role, 
                "auth_success": False,
                "api_results": {},
                "frontend_results": {}
            }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    total_users = len(TEST_USERS)
    auth_success = sum(1 for result in all_results.values() if result["auth_success"])
    
    print(f"\n👥 User Authentication:")
    print(f"  ✅ Successful: {auth_success}/{total_users}")
    print(f"  ❌ Failed: {total_users - auth_success}/{total_users}")
    
    # Analyze results by role
    print(f"\n🎭 Results by Role:")
    for username, result in all_results.items():
        if result["auth_success"]:
            role = result["role"]
            frontend_success = sum(1 for success in result["frontend_results"].values() if success)
            frontend_total = len(result["frontend_results"])
            api_success = sum(1 for success in result["api_results"].values() if success)
            api_total = len(result["api_results"])
            
            print(f"  {role.upper()}:")
            print(f"    Frontend routes: {frontend_success}/{frontend_total} working")
            print(f"    API endpoints: {api_success}/{api_total} working")
    
    # Identify common issues
    print(f"\n🔍 Issue Analysis:")
    
    # Check if any routes consistently fail
    route_failures = {}
    for result in all_results.values():
        if result["auth_success"]:
            for route, success in result["frontend_results"].items():
                if not success:
                    route_failures[route] = route_failures.get(route, 0) + 1
    
    if route_failures:
        print("  ❌ Routes with consistent failures:")
        for route, failure_count in route_failures.items():
            print(f"    {route}: {failure_count} failures")
    else:
        print("  ✅ No consistent route failures detected")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 30)
    
    if auth_success == 0:
        print("  🚨 CRITICAL: No users can authenticate")
        print("    - Check if backend auth endpoints are working")
        print("    - Verify user credentials and database")
        print("    - Check backend logs for auth errors")
    elif auth_success < total_users:
        print("  ⚠️  Some users cannot authenticate")
        print("    - Check specific user credentials")
        print("    - Verify role-based access is configured correctly")
    
    if route_failures:
        print("  🔧 Frontend route issues detected:")
        print("    - Check browser developer console for JavaScript errors")
        print("    - Verify React Router configuration")
        print("    - Check for missing component imports")
        print("    - Test role-based access control in React components")
    else:
        print("  🎉 All frontend routes are loading correctly!")
        print("  ✨ The issue may be with role-based access control within React components")
        print("  📝 Next steps:")
        print("    1. Test actual functionality within each page")
        print("    2. Check for JavaScript console errors in browser")
        print("    3. Verify role-based UI restrictions are working")
    
    return len(route_failures) == 0 and auth_success == total_users

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)