#!/usr/bin/env python3
"""
API Endpoints Testing Script
Tests the newly created API endpoints to verify they're working correctly.
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
        "role": "admin"
    }
]

def get_auth_token(username: str, password: str) -> Optional[str]:
    """Get authentication token from backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"✅ Authentication successful for {username}")
                return token
        else:
            print(f"❌ Auth failed for {username}: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Auth error for {username}: {e}")
    
    return None

def test_api_endpoints(token: str, username: str) -> Dict[str, bool]:
    """Test API endpoints with authentication"""
    endpoints = [
        # Auth endpoints
        ("/auth/me", "GET", "User profile"),
        
        # Tasks endpoints  
        ("/api/v1/tasks", "GET", "Tasks list"),
        ("/api/v1/tasks/stats", "GET", "Task statistics"),
        
        # Dashboard endpoints
        ("/api/v1/dashboard/metrics", "GET", "Dashboard metrics"),
        ("/api/v1/dashboard/annotation-efficiency", "GET", "Annotation efficiency"),
        ("/api/v1/dashboard/real-time-metrics", "GET", "Real-time metrics"),
        ("/api/v1/dashboard/quality-reports", "GET", "Quality reports"),
        ("/api/v1/dashboard/knowledge-graph", "GET", "Knowledge graph data"),
        
        # System endpoints
        ("/health", "GET", "Health check"),
        ("/system/status", "GET", "System status"),
        ("/api/info", "GET", "API information"),
    ]
    
    results = {}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🔍 Testing API endpoints for {username}...")
    
    for endpoint, method, description in endpoints:
        try:
            url = f"{BACKEND_URL}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json={}, timeout=10)
            else:
                response = requests.request(method, url, headers=headers, timeout=10)
            
            success = response.status_code in [200, 201]
            results[endpoint] = success
            
            status = "✅" if success else "❌"
            print(f"  {status} {method} {endpoint} - {description} (HTTP {response.status_code})")
            
            # Show response preview for successful requests
            if success and response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        keys = list(data.keys())[:3]  # Show first 3 keys
                        print(f"      Response keys: {keys}")
                    elif isinstance(data, list):
                        print(f"      Response: list with {len(data)} items")
                except:
                    print(f"      Response: {response.text[:100]}...")
            
        except Exception as e:
            results[endpoint] = False
            print(f"  ❌ {method} {endpoint} - Error: {e}")
    
    return results

def test_tasks_crud_operations(token: str) -> bool:
    """Test CRUD operations for tasks"""
    print(f"\n🧪 Testing Tasks CRUD operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test creating a task
        create_data = {
            "name": "Test Task",
            "description": "This is a test task",
            "annotation_type": "text_classification",
            "priority": "high",
            "total_items": 100,
            "tags": ["test", "api"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/tasks",
            headers=headers,
            json=create_data,
            timeout=10
        )
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get("id")
            print(f"  ✅ Task created successfully: {task_id}")
            
            # Test getting the task
            response = requests.get(
                f"{BACKEND_URL}/api/v1/tasks/{task_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"  ✅ Task retrieved successfully")
                
                # Test updating the task
                update_data = {
                    "status": "in_progress",
                    "progress": 50
                }
                
                response = requests.put(
                    f"{BACKEND_URL}/api/v1/tasks/{task_id}",
                    headers=headers,
                    json=update_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"  ✅ Task updated successfully")
                    
                    # Test deleting the task
                    response = requests.delete(
                        f"{BACKEND_URL}/api/v1/tasks/{task_id}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        print(f"  ✅ Task deleted successfully")
                        return True
                    else:
                        print(f"  ❌ Task deletion failed: HTTP {response.status_code}")
                else:
                    print(f"  ❌ Task update failed: HTTP {response.status_code}")
            else:
                print(f"  ❌ Task retrieval failed: HTTP {response.status_code}")
        else:
            print(f"  ❌ Task creation failed: HTTP {response.status_code}")
            print(f"      Response: {response.text}")
            
    except Exception as e:
        print(f"  ❌ CRUD test error: {e}")
    
    return False

def main():
    """Main test function"""
    print("🚀 SuperInsight API Endpoints Testing")
    print("=" * 60)
    
    # Test authentication and API endpoints
    user = TEST_USERS[0]
    username = user["username"]
    password = user["password"]
    
    print(f"\n🔐 Testing authentication for {username}...")
    token = get_auth_token(username, password)
    
    if not token:
        print("❌ Authentication failed - cannot proceed with API tests")
        return False
    
    # Test API endpoints
    api_results = test_api_endpoints(token, username)
    
    # Test CRUD operations
    crud_success = test_tasks_crud_operations(token)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    api_passed = sum(1 for success in api_results.values() if success)
    api_total = len(api_results)
    
    print(f"\n🌐 API Endpoints:")
    print(f"  ✅ Passed: {api_passed}/{api_total}")
    print(f"  ❌ Failed: {api_total - api_passed}/{api_total}")
    
    print(f"\n🧪 CRUD Operations:")
    print(f"  {'✅ Passed' if crud_success else '❌ Failed'}")
    
    # Show failed endpoints
    failed_endpoints = [endpoint for endpoint, success in api_results.items() if not success]
    if failed_endpoints:
        print(f"\n❌ Failed endpoints:")
        for endpoint in failed_endpoints:
            print(f"  - {endpoint}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 30)
    
    if api_passed == api_total and crud_success:
        print("  🎉 All API endpoints are working correctly!")
        print("  ✨ The backend API is ready for frontend integration")
        print("  📝 Next steps:")
        print("    1. Test frontend integration with these endpoints")
        print("    2. Verify role-based access control")
        print("    3. Test error handling and edge cases")
    else:
        print("  🔧 Some API endpoints need attention:")
        if api_passed < api_total:
            print("    - Check failed endpoints for implementation issues")
            print("    - Verify authentication and authorization")
        if not crud_success:
            print("    - Fix CRUD operations for tasks")
        print("    - Check backend logs for detailed error information")
    
    return api_passed == api_total and crud_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)