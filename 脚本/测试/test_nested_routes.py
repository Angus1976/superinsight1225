#!/usr/bin/env python3
"""
Test script to verify all nested routes work correctly
"""
import requests
import json
from typing import Dict, List

# Base URL for the API
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Test routes
NESTED_ROUTES = [
    # Augmentation routes
    "/augmentation/samples",
    "/augmentation/config",
    
    # Quality routes
    "/quality/rules", 
    "/quality/reports",
    
    # Security routes
    "/security/audit",
    "/security/permissions",
    
    # Data Sync routes
    "/data-sync/sources",
    "/data-sync/security",
    
    # Admin routes
    "/admin/tenants",
    "/admin/users", 
    "/admin/system"
]

# API endpoints to test
API_ENDPOINTS = [
    # Augmentation APIs
    "/api/v1/augmentation/samples",
    "/api/v1/augmentation/config",
    
    # Quality APIs
    "/api/v1/quality/rules",
    "/api/v1/quality/metrics?start_date=2025-01-01&end_date=2025-01-31",
    "/api/v1/quality/reports?start_date=2025-01-01&end_date=2025-01-31",
    
    # Security APIs
    "/api/v1/security/audit?start_date=2025-01-01&end_date=2025-01-31",
    "/api/v1/security/permissions",
    "/api/v1/security/roles",
    "/api/v1/security/user-permissions",
    
    # Data Sync APIs
    "/api/v1/data-sync/sources",
    "/api/v1/data-sync/security/config",
    "/api/v1/data-sync/security/rules",
    
    # Admin APIs
    "/api/v1/admin/tenants",
    "/api/v1/admin/users",
    "/api/v1/admin/system/config",
    "/api/v1/admin/system/status"
]

def test_frontend_routes():
    """Test frontend nested routes"""
    print("🔍 Testing Frontend Routes...")
    print("=" * 50)
    
    for route in NESTED_ROUTES:
        try:
            url = f"{FRONTEND_URL}{route}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {route} - OK (200)")
            else:
                print(f"❌ {route} - Failed ({response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {route} - Connection Error: {e}")
    
    print()

def test_api_endpoints():
    """Test API endpoints"""
    print("🔍 Testing API Endpoints...")
    print("=" * 50)
    
    # First, try to get an auth token (this might fail if auth is not set up)
    auth_token = None
    try:
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "admin",
            "password": "admin123"
        }, timeout=5)
        
        if login_response.status_code == 200:
            auth_data = login_response.json()
            auth_token = auth_data.get("access_token")
            print(f"✅ Authentication successful")
        else:
            print(f"⚠️  Authentication failed, testing without auth")
    except:
        print(f"⚠️  Authentication service unavailable, testing without auth")
    
    # Set up headers
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    for endpoint in API_ENDPOINTS:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK (200)")
                # Try to parse JSON to verify it's valid
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   📊 Returned {len(data)} items")
                    elif isinstance(data, dict):
                        print(f"   📊 Returned object with {len(data)} keys")
                except:
                    print(f"   📊 Returned non-JSON response")
                    
            elif response.status_code == 401:
                print(f"🔒 {endpoint} - Unauthorized (401) - Auth required")
            elif response.status_code == 403:
                print(f"🔒 {endpoint} - Forbidden (403) - Insufficient permissions")
            elif response.status_code == 404:
                print(f"❌ {endpoint} - Not Found (404)")
            else:
                print(f"❌ {endpoint} - Failed ({response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Connection Error: {e}")
    
    print()

def test_health_endpoints():
    """Test basic health endpoints"""
    print("🔍 Testing Health Endpoints...")
    print("=" * 50)
    
    health_endpoints = [
        "/health",
        "/",
        "/api/info"
    ]
    
    for endpoint in health_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK (200)")
                try:
                    data = response.json()
                    if "status" in data:
                        print(f"   📊 Status: {data['status']}")
                    if "version" in data:
                        print(f"   📊 Version: {data['version']}")
                except:
                    pass
            else:
                print(f"❌ {endpoint} - Failed ({response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Connection Error: {e}")
    
    print()

def main():
    """Main test function"""
    print("🚀 SuperInsight Nested Routes Test")
    print("=" * 50)
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Backend URL: {BASE_URL}")
    print()
    
    # Test health endpoints first
    test_health_endpoints()
    
    # Test API endpoints
    test_api_endpoints()
    
    # Test frontend routes
    test_frontend_routes()
    
    print("✨ Test completed!")
    print()
    print("📝 Notes:")
    print("- Frontend routes may show 200 even if the React component has errors")
    print("- API endpoints may require authentication")
    print("- Make sure both frontend and backend services are running")
    print("- Frontend: npm run dev (port 5173)")
    print("- Backend: docker-compose up -d or python -m uvicorn src.app_auth:app --reload")

if __name__ == "__main__":
    main()