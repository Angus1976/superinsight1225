#!/usr/bin/env python3
"""
Direct API endpoint testing script.
Tests the API endpoints that the frontend expects without going through Docker.
"""

import requests
import json
from typing import Dict, Any

def test_endpoint(url: str, method: str = "GET", data: Dict[Any, Any] = None) -> Dict[str, Any]:
    """Test an API endpoint and return the result."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "error": None
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": None,
            "success": False,
            "data": None,
            "error": str(e)
        }

def main():
    """Test all the API endpoints that the frontend expects."""
    base_url = "http://localhost:8000"
    
    endpoints_to_test = [
        {"url": f"{base_url}/health", "name": "Health Check"},
        {"url": f"{base_url}/", "name": "Root Endpoint"},
        {"url": f"{base_url}/api/v1/tasks", "name": "Tasks List"},
        {"url": f"{base_url}/api/v1/dashboard/metrics", "name": "Dashboard Metrics"},
        {"url": f"{base_url}/auth/me", "name": "Current User"},
    ]
    
    print("🔍 Testing API Endpoints")
    print("=" * 50)
    
    all_passed = True
    
    for endpoint in endpoints_to_test:
        print(f"\n📡 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        result = test_endpoint(endpoint['url'])
        
        if result['success']:
            print(f"   ✅ Status: {result['status_code']} - SUCCESS")
            if isinstance(result['data'], dict):
                print(f"   📄 Response keys: {list(result['data'].keys())}")
            else:
                print(f"   📄 Response: {str(result['data'])[:100]}...")
        else:
            print(f"   ❌ Status: {result['status_code']} - FAILED")
            print(f"   🚨 Error: {result['error']}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All API endpoints are working correctly!")
        print("✅ The 404 errors reported by the user should be resolved.")
    else:
        print("⚠️  Some API endpoints are not working.")
        print("🔧 The backend needs to be fixed before the frontend will work properly.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)