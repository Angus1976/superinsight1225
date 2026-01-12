#!/usr/bin/env python3
"""
Frontend Route Testing Script
Tests all frontend routes to identify 404 errors and routing issues.
"""

import requests
import json
import time
from typing import Dict, List, Tuple

# Test configuration
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"

# Routes to test (path, expected_status, description)
ROUTES_TO_TEST = [
    # Public routes
    ("/", 200, "Home page (should redirect to login)"),
    ("/login", 200, "Login page"),
    ("/register", 200, "Register page"),
    ("/forgot-password", 200, "Forgot password page"),
    
    # Protected routes (will redirect to login if not authenticated)
    ("/dashboard", 200, "Dashboard page"),
    ("/tasks", 200, "Tasks list page"),
    ("/tasks/1", 200, "Task detail page"),
    ("/tasks/1/annotate", 200, "Task annotation page"),
    ("/billing", 200, "Billing page"),
    ("/settings", 200, "Settings page"),
    ("/admin", 200, "Admin page"),
    ("/augmentation", 200, "Data augmentation page"),
    ("/quality", 200, "Quality management page"),
    ("/security", 200, "Security audit page"),
    ("/data-sync", 200, "Data sync page"),
    
    # Error pages
    ("/404", 200, "404 error page"),
    ("/403", 200, "403 error page"),
    ("/500", 200, "500 error page"),
    
    # Non-existent routes (should return 404 or redirect)
    ("/non-existent-page", 200, "Non-existent page (should show 404)"),
]

def test_backend_health() -> bool:
    """Test if backend is healthy"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend health: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_frontend_route(path: str, expected_status: int, description: str) -> Tuple[bool, str]:
    """Test a single frontend route"""
    try:
        url = f"{FRONTEND_URL}{path}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        
        # For React SPA, most routes should return 200 with HTML content
        # The actual routing is handled by React Router
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                # Check if it's the main React app HTML
                if 'id="root"' in response.text or 'react' in response.text.lower():
                    return True, f"✅ {path} - React app loaded successfully"
                else:
                    return False, f"❌ {path} - HTML returned but not React app"
            else:
                return False, f"❌ {path} - Wrong content type: {content_type}"
        else:
            return False, f"❌ {path} - HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, f"❌ {path} - Request timeout"
    except requests.exceptions.ConnectionError:
        return False, f"❌ {path} - Connection error"
    except Exception as e:
        return False, f"❌ {path} - Error: {e}"

def test_api_endpoints() -> Dict[str, bool]:
    """Test key API endpoints"""
    endpoints = {
        "/health": "Health check",
        "/api/v1/auth/me": "User info (should return 401 without auth)",
        "/api/v1/tasks": "Tasks API (should return 401 without auth)",
        "/docs": "API documentation",
    }
    
    results = {}
    print("\n🔍 Testing API endpoints...")
    
    for endpoint, description in endpoints.items():
        try:
            url = f"{BACKEND_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if endpoint == "/health":
                success = response.status_code == 200
            elif endpoint in ["/api/v1/auth/me", "/api/v1/tasks"]:
                # These should return 401 without authentication
                success = response.status_code == 401
            elif endpoint == "/docs":
                success = response.status_code == 200
            else:
                success = response.status_code in [200, 401]
            
            results[endpoint] = success
            status = "✅" if success else "❌"
            print(f"  {status} {endpoint} - {description} (HTTP {response.status_code})")
            
        except Exception as e:
            results[endpoint] = False
            print(f"  ❌ {endpoint} - Error: {e}")
    
    return results

def main():
    """Main test function"""
    print("🚀 SuperInsight Frontend Route Testing")
    print("=" * 50)
    
    # Test backend health first
    print("\n🏥 Testing backend health...")
    backend_healthy = test_backend_health()
    
    if not backend_healthy:
        print("⚠️  Backend is not healthy, but continuing with frontend tests...")
    
    # Test API endpoints
    api_results = test_api_endpoints()
    
    # Test frontend routes
    print(f"\n🌐 Testing frontend routes...")
    print(f"Frontend URL: {FRONTEND_URL}")
    print("-" * 50)
    
    passed = 0
    failed = 0
    results = []
    
    for path, expected_status, description in ROUTES_TO_TEST:
        success, message = test_frontend_route(path, expected_status, description)
        results.append((path, success, message, description))
        
        if success:
            passed += 1
        else:
            failed += 1
        
        print(f"  {message}")
        time.sleep(0.1)  # Small delay to avoid overwhelming the server
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    print(f"\n🌐 Frontend Routes:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total: {passed + failed}")
    
    api_passed = sum(1 for success in api_results.values() if success)
    api_failed = len(api_results) - api_passed
    print(f"\n🔌 API Endpoints:")
    print(f"  ✅ Passed: {api_passed}")
    print(f"  ❌ Failed: {api_failed}")
    print(f"  📊 Total: {len(api_results)}")
    
    # Detailed failure analysis
    if failed > 0:
        print(f"\n❌ FAILED ROUTES:")
        print("-" * 30)
        for path, success, message, description in results:
            if not success:
                print(f"  {path} - {description}")
                print(f"    Error: {message}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 20)
    
    if failed == 0:
        print("  🎉 All routes are working correctly!")
        print("  ✨ The frontend routing system is properly configured.")
    else:
        print("  🔧 Issues found with frontend routing:")
        if any("Connection error" in result[2] for result in results if not result[1]):
            print("    - Check if frontend server is running on port 5173")
        if any("timeout" in result[2].lower() for result in results if not result[1]):
            print("    - Frontend server may be overloaded or slow")
        if any("not React app" in result[2] for result in results if not result[1]):
            print("    - React app may not be building correctly")
        
        print("  📝 Next steps:")
        print("    1. Check browser developer console for JavaScript errors")
        print("    2. Verify React Router configuration in routes.tsx")
        print("    3. Check for missing component imports")
        print("    4. Test with different user roles and authentication states")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)