#!/usr/bin/env python3
"""
Test Label Studio token authentication directly
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

LABEL_STUDIO_URL = "http://localhost:8080"
TOKEN = os.getenv("LABEL_STUDIO_API_TOKEN", "")

async def test_token():
    print(f"Testing Label Studio at: {LABEL_STUDIO_URL}")
    print(f"Token (first 50 chars): {TOKEN[:50]}...")
    print(f"Token type: {'JWT format (PAT)' if TOKEN.count('.') == 2 else 'Legacy format'}")
    print()
    
    # Test: Personal Access Token with Bearer prefix (Open Source method)
    print("Test: Personal Access Token with Bearer prefix (Open Source)")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{LABEL_STUDIO_URL}/api/users/whoami/",
                headers={
                    'Authorization': f'Bearer {TOKEN}',
                    'Content-Type': 'application/json'
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS!")
                print(f"User ID: {data.get('id')}")
                print(f"Username: {data.get('username')}")
                print(f"Email: {data.get('email')}")
            else:
                print(f"❌ FAILED")
                print(f"Response: {response.text[:300]}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    print()
    
    # Test: Get projects
    print("Test: List projects")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{LABEL_STUDIO_URL}/api/projects/",
                headers={
                    'Authorization': f'Bearer {TOKEN}',
                    'Content-Type': 'application/json'
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS!")
                print(f"Projects count: {len(data.get('results', []))}")
            else:
                print(f"❌ FAILED")
                print(f"Response: {response.text[:300]}")
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_token())
