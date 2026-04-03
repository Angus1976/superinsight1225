#!/usr/bin/env python3
"""
Test script for Label Studio synchronization.

This script tests:
1. Label Studio connection and authentication
2. Task creation with automatic sync
3. Manual sync retry
4. Project validation
"""

import asyncio
import httpx
import sys
from datetime import datetime


# Configuration
API_BASE_URL = "http://localhost:8000"
LABEL_STUDIO_URL = "http://localhost:8080"
API_TOKEN = "YOUR_LABEL_STUDIO_API_TOKEN_HERE"  # Get from Label Studio: Account & Settings > Legacy Tokens

# Test credentials (you need to get a valid JWT token from login)
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin"


async def login() -> str:
    """Login and get JWT token"""
    print("🔐 Logging in...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/auth/login",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ Login successful")
            return token
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)


async def label_studio_connection_check(token: str):
    """Test Label Studio connection (manual script helper; not a pytest case)."""
    print("\n📡 Testing Label Studio connection...")
    
    async with httpx.AsyncClient() as client:
        # Test direct Label Studio API
        print(f"   Testing direct API: {LABEL_STUDIO_URL}/api/current-user/whoami/")
        try:
            response = await client.get(
                f"{LABEL_STUDIO_URL}/api/current-user/whoami/",
                headers={"Authorization": f"Token {API_TOKEN}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                print(f"✅ Direct Label Studio API connection successful")
                user_data = response.json()
                print(f"   User: {user_data.get('email', 'N/A')}")
            else:
                print(f"❌ Direct Label Studio API failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Direct Label Studio API error: {str(e)}")
        
        # Test through SuperInsight API
        print(f"\n   Testing through SuperInsight API...")
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/tasks/label-studio/test-connection",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    print(f"✅ SuperInsight → Label Studio connection successful")
                    print(f"   Auth method: {data['details'].get('auth_method')}")
                    print(f"   Base URL: {data['details'].get('base_url')}")
                else:
                    print(f"❌ SuperInsight → Label Studio connection failed")
                    print(f"   Error: {data.get('message')}")
            else:
                print(f"❌ API request failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ API request error: {str(e)}")


async def create_test_task(token: str) -> str:
    """Create a test task"""
    print("\n📝 Creating test task...")
    
    task_data = {
        "name": f"Test Task {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Test task for Label Studio sync",
        "priority": "medium",
        "annotation_type": "text_classification",
        "total_items": 10,
        "tags": ["test", "sync"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json=task_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            task = response.json()
            task_id = task["id"]
            print(f"✅ Task created: {task_id}")
            print(f"   Name: {task['name']}")
            print(f"   Sync status: {task.get('label_studio_sync_status', 'unknown')}")
            return task_id
        else:
            print(f"❌ Task creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)


async def check_task_sync_status(token: str, task_id: str):
    """Check task sync status"""
    print(f"\n🔍 Checking sync status for task {task_id}...")
    
    # Wait a bit for background sync to complete
    print("   Waiting 3 seconds for background sync...")
    await asyncio.sleep(3)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        
        if response.status_code == 200:
            task = response.json()
            sync_status = task.get("label_studio_sync_status", "unknown")
            project_id = task.get("label_studio_project_id")
            last_sync = task.get("label_studio_last_sync")
            
            print(f"   Sync status: {sync_status}")
            print(f"   Project ID: {project_id or 'None'}")
            print(f"   Last sync: {last_sync or 'Never'}")
            
            if sync_status == "synced" and project_id:
                print(f"✅ Task successfully synced to Label Studio")
                print(f"   Project URL: {LABEL_STUDIO_URL}/projects/{project_id}")
                return True
            elif sync_status == "pending":
                print(f"⏳ Sync still pending (background task may still be running)")
                return False
            elif sync_status == "failed":
                print(f"❌ Sync failed")
                return False
            else:
                print(f"⚠️  Unknown sync status: {sync_status}")
                return False
        else:
            print(f"❌ Failed to get task: {response.status_code}")
            return False


async def manual_sync_task(token: str, task_id: str):
    """Manually sync a task"""
    print(f"\n🔄 Manually syncing task {task_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/tasks/{task_id}/sync-label-studio",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Manual sync successful")
            print(f"   Project ID: {data.get('project_id')}")
            print(f"   Project URL: {data.get('project_url')}")
            print(f"   Sync status: {data.get('sync_status')}")
            return True
        else:
            print(f"❌ Manual sync failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False


async def main():
    """Main test flow"""
    print("=" * 60)
    print("Label Studio Synchronization Test")
    print("=" * 60)
    
    try:
        # Step 1: Login
        token = await login()
        
        # Step 2: Test Label Studio connection
        await label_studio_connection_check(token)
        
        # Step 3: Create test task
        task_id = await create_test_task(token)
        
        # Step 4: Check sync status
        synced = await check_task_sync_status(token, task_id)
        
        # Step 5: If not synced, try manual sync
        if not synced:
            print("\n⚠️  Automatic sync didn't complete, trying manual sync...")
            await manual_sync_task(token, task_id)
            
            # Check again
            await check_task_sync_status(token, task_id)
        
        print("\n" + "=" * 60)
        print("✅ Test completed")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
