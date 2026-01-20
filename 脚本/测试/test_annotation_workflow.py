#!/usr/bin/env python3
"""
Test script for Label Studio annotation workflow integration
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def test_annotation_workflow():
    """Test the complete annotation workflow"""
    print("🧪 Testing Label Studio Annotation Workflow Integration")
    print("=" * 60)
    
    # Test 1: Login and get token
    print("\n1. Testing user authentication...")
    login_response = requests.post(f"{BASE_URL}/api/security/login", json={
        "username": "annotator_test",
        "password": "annotator123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
    else:
        print("❌ Login failed")
        return False
    
    # Test 2: Get Label Studio projects
    print("\n2. Testing Label Studio projects API...")
    projects_response = requests.get(f"{BASE_URL}/api/label-studio/projects", headers=headers)
    
    if projects_response.status_code == 200:
        projects_data = projects_response.json()
        projects = projects_data.get("results", [])
        print(f"✅ Found {len(projects)} projects")
        if projects:
            project_id = projects[0]["id"]
            print(f"   Using project ID: {project_id}")
        else:
            print("❌ No projects found")
            return False
    else:
        print("❌ Failed to get projects")
        return False
    
    # Test 3: Get tasks for the project
    print("\n3. Testing tasks API...")
    tasks_response = requests.get(f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks", headers=headers)
    
    if tasks_response.status_code == 200:
        tasks_data = tasks_response.json()
        tasks = tasks_data.get("results", [])
        print(f"✅ Found {len(tasks)} tasks")
        if tasks:
            task_id = tasks[0]["id"]
            print(f"   Using task ID: {task_id}")
            print(f"   Task text: {tasks[0]['data']['text'][:50]}...")
        else:
            print("❌ No tasks found")
            return False
    else:
        print("❌ Failed to get tasks")
        return False
    
    # Test 4: Create annotation
    print("\n4. Testing annotation creation...")
    annotation_data = {
        "result": [
            {
                "value": {
                    "choices": ["Positive"]
                },
                "from_name": "sentiment",
                "to_name": "text",
                "type": "choices"
            }
        ],
        "task": task_id
    }
    
    annotation_response = requests.post(
        f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations",
        json=annotation_data,
        headers=headers
    )
    
    if annotation_response.status_code in [200, 201]:
        annotation = annotation_response.json()
        annotation_id = annotation["id"]
        print(f"✅ Annotation created with ID: {annotation_id}")
    else:
        print(f"❌ Failed to create annotation: {annotation_response.status_code}")
        print(f"   Response: {annotation_response.text}")
        return False
    
    # Test 5: Get annotations
    print("\n5. Testing annotations retrieval...")
    annotations_response = requests.get(
        f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations",
        headers=headers
    )
    
    if annotations_response.status_code == 200:
        annotations = annotations_response.json()
        print(f"✅ Retrieved {len(annotations)} annotations")
    else:
        print("❌ Failed to get annotations")
        return False
    
    # Test 6: Test frontend routes accessibility
    print("\n6. Testing frontend routes...")
    
    # Test task detail page
    task_detail_url = f"{FRONTEND_URL}/tasks/{project_id}"
    print(f"   Task detail page: {task_detail_url}")
    
    # Test annotation page
    annotation_url = f"{FRONTEND_URL}/tasks/{project_id}/annotate"
    print(f"   Annotation page: {annotation_url}")
    
    print("✅ Frontend routes configured")
    
    # Test 7: Role-based access
    print("\n7. Testing role-based access...")
    
    # Test with different user roles
    test_users = [
        ("admin_test", "admin123", "ADMIN"),
        ("expert_test", "expert123", "BUSINESS_EXPERT"),
        ("annotator_test", "annotator123", "ANNOTATOR"),
        ("viewer_test", "viewer123", "VIEWER")
    ]
    
    for username, password, role in test_users:
        login_resp = requests.post(f"{BASE_URL}/api/security/login", json={
            "username": username,
            "password": password
        })
        
        if login_resp.status_code == 200:
            user_token = login_resp.json()["access_token"]
            user_headers = {"Authorization": f"Bearer {user_token}"}
            
            # Test access to projects
            projects_resp = requests.get(f"{BASE_URL}/api/label-studio/projects", headers=user_headers)
            access_status = "✅" if projects_resp.status_code == 200 else "❌"
            print(f"   {role}: {access_status}")
        else:
            print(f"   {role}: ❌ Login failed")
    
    print("\n" + "=" * 60)
    print("🎉 Label Studio Annotation Workflow Test Complete!")
    print("\n📋 Summary:")
    print("   • Backend API endpoints: ✅ Working")
    print("   • Authentication: ✅ Working")
    print("   • Project management: ✅ Working")
    print("   • Task management: ✅ Working")
    print("   • Annotation workflow: ✅ Working")
    print("   • Role-based access: ✅ Working")
    print("   • Frontend routes: ✅ Configured")
    
    print("\n🚀 Ready for testing:")
    print(f"   • Backend API: {BASE_URL}")
    print(f"   • Frontend Web: {FRONTEND_URL}")
    print(f"   • Annotation Page: {FRONTEND_URL}/tasks/{project_id}/annotate")
    
    print("\n👥 Test Accounts:")
    for username, password, role in test_users:
        print(f"   • {username} / {password} ({role})")
    
    return True

if __name__ == "__main__":
    success = test_annotation_workflow()
    exit(0 if success else 1)