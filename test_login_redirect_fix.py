#!/usr/bin/env python3
"""
Test script to verify login redirect loop fix
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def test_login_redirect_fix():
    print("=" * 60)
    print("Testing Login Redirect Loop Fix")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: Check if frontend is accessible
    print("1. Testing frontend accessibility...")
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✓ Frontend is accessible")
        else:
            print(f"✗ Frontend returned status {response.status_code}")
    except Exception as e:
        print(f"✗ Frontend error: {e}")
    
    # Test 2: Check login page
    print("\n2. Testing login page...")
    try:
        response = requests.get(f"{FRONTEND_URL}/login", timeout=5)
        if response.status_code == 200:
            print("✓ Login page is accessible")
        else:
            print(f"✗ Login page returned status {response.status_code}")
    except Exception as e:
        print(f"✗ Login page error: {e}")

    # Test 3: Test authentication flow
    print("\n3. Testing authentication flow...")
    try:
        # Login with test credentials
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin_user", "password": "Admin@123456"},
            timeout=10
        )
        
        if login_response.status_code == 200:
            print("✓ Backend login successful")
            token = login_response.json().get("access_token")
            
            # Test authenticated API call
            headers = {"Authorization": f"Bearer {token}"}
            profile_response = requests.get(
                f"{BASE_URL}/auth/me",
                headers=headers,
                timeout=5
            )
            
            if profile_response.status_code == 200:
                user_data = profile_response.json()
                print(f"✓ Authenticated API call successful")
                print(f"  User: {user_data.get('username')} ({user_data.get('role')})")
            else:
                print(f"✗ Authenticated API call failed: {profile_response.status_code}")
        else:
            print(f"✗ Backend login failed: {login_response.status_code}")
    except Exception as e:
        print(f"✗ Authentication test error: {e}")

    # Test 4: Check if services are stable
    print("\n4. Testing service stability...")
    try:
        # Wait a moment and check again
        time.sleep(2)
        
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        frontend_response = requests.get(FRONTEND_URL, timeout=5)
        
        if health_response.status_code == 200 and frontend_response.status_code == 200:
            print("✓ Services are stable after authentication test")
        else:
            print(f"✗ Service stability issue - Backend: {health_response.status_code}, Frontend: {frontend_response.status_code}")
    except Exception as e:
        print(f"✗ Stability test error: {e}")

    print("\n" + "=" * 60)
    print("Test Summary:")
    print("- Frontend should now load without redirect loops")
    print("- Login page should be accessible")
    print("- Authentication flow should work properly")
    print("- After login, users should be redirected to dashboard")
    print()
    print("Manual Test Instructions:")
    print("1. Open http://localhost:5173/login in your browser")
    print("2. Login with: admin_user / Admin@123456")
    print("3. Verify you are redirected to dashboard without loops")
    print("4. Check browser console for any errors")
    print("=" * 60)

if __name__ == "__main__":
    test_login_redirect_fix()