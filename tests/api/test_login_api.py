#!/usr/bin/env python3
"""
Test login API endpoint directly
"""
import sys
sys.path.insert(0, '.')

import asyncio
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

print("🧪 Testing login API endpoint...")

# Test login
response = client.post(
    "/auth/login",
    json={"username": "admin", "password": "password"}
)

print(f"\n📊 Response Status: {response.status_code}")
print(f"📄 Response Body: {response.text}")

if response.status_code == 200:
    print("✅ Login successful!")
    data = response.json()
    print(f"   Token: {data.get('access_token', 'N/A')[:50]}...")
    print(f"   User: {data.get('user', {}).get('username', 'N/A')}")
else:
    print("❌ Login failed!")
    print(f"   Error: {response.json()}")
