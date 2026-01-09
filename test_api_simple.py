#!/usr/bin/env python3
"""Simple API test script."""

import requests
import time
import sys

def test_api():
    """Test API endpoints."""
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Wait for API to be ready
    for i in range(30):
        if test_api():
            print("✅ API is healthy!")
            sys.exit(0)
        print(f"Attempt {i+1}/30 - API not ready yet...")
        time.sleep(2)
    
    print("❌ API failed to become healthy")
    sys.exit(1)
