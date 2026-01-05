#!/usr/bin/env python3
"""
测试不同角色的标注权限
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# 测试用户
TEST_USERS = [
    {
        "username": "admin_test",
        "password": "admin123",
        "role": "ADMIN",
        "display_name": "系统管理员",
        "expected_permissions": {
            "can_view_annotation": True,
            "can_create_annotation": True,
            "can_edit_annotation": True,
            "can_delete_annotation": True
        }
    },
    {
        "username": "expert_test", 
        "password": "expert123",
        "role": "BUSINESS_EXPERT",
        "display_name": "业务专家",
        "expected_permissions": {
            "can_view_annotation": True,
            "can_create_annotation": True,
            "can_edit_annotation": True,
            "can_delete_annotation": False
        }
    },
    {
        "username": "annotator_test",
        "password": "annotator123", 
        "role": "ANNOTATOR",
        "display_name": "数据标注员",
        "expected_permissions": {
            "can_view_annotation": True,
            "can_create_annotation": True,
            "can_edit_annotation": True,
            "can_delete_annotation": False
        }
    },
    {
        "username": "viewer_test",
        "password": "viewer123",
        "role": "VIEWER", 
        "display_name": "报表查看者",
        "expected_permissions": {
            "can_view_annotation": True,
            "can_create_annotation": False,
            "can_edit_annotation": False,
            "can_delete_annotation": False
        }
    }
]

def test_user_permissions():
    """测试各角色的标注权限"""
    print("🔐 测试角色权限系统")
    print("=" * 60)
    
    for user in TEST_USERS:
        print(f"\n👤 测试用户: {user['username']} ({user['display_name']})")
        print("-" * 40)
        
        # 1. 登录获取token
        login_response = requests.post(f"{BASE_URL}/api/security/login", json={
            "username": user["username"],
            "password": user["password"]
        })
        
        if login_response.status_code != 200:
            print(f"❌ 登录失败: {login_response.status_code}")
            continue
            
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_info = login_response.json().get("user", {})
        
        print(f"✅ 登录成功")
        print(f"   角色: {user_info.get('role', 'Unknown')}")
        print(f"   姓名: {user_info.get('full_name', 'Unknown')}")
        
        # 2. 测试查看标注项目权限
        projects_response = requests.get(f"{BASE_URL}/api/label-studio/projects", headers=headers)
        can_view_projects = projects_response.status_code == 200
        
        print(f"   查看项目: {'✅' if can_view_projects else '❌'}")
        
        if can_view_projects:
            projects_data = projects_response.json()
            projects = projects_data.get("results", [])
            print(f"   可访问项目数: {len(projects)}")
            
            if projects:
                project_id = projects[0]["id"]
                
                # 3. 测试查看任务权限
                tasks_response = requests.get(f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks", headers=headers)
                can_view_tasks = tasks_response.status_code == 200
                print(f"   查看任务: {'✅' if can_view_tasks else '❌'}")
                
                if can_view_tasks:
                    tasks_data = tasks_response.json()
                    tasks = tasks_data.get("results", [])
                    print(f"   可访问任务数: {len(tasks)}")
                    
                    if tasks:
                        task_id = tasks[0]["id"]
                        
                        # 4. 测试创建标注权限
                        annotation_data = {
                            "result": [
                                {
                                    "value": {"choices": ["Positive"]},
                                    "from_name": "sentiment",
                                    "to_name": "text",
                                    "type": "choices"
                                }
                            ],
                            "task": task_id
                        }
                        
                        create_response = requests.post(
                            f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations",
                            json=annotation_data,
                            headers=headers
                        )
                        can_create = create_response.status_code in [200, 201]
                        print(f"   创建标注: {'✅' if can_create else '❌'}")
                        
                        if can_create:
                            annotation_id = create_response.json().get("id")
                            
                            # 5. 测试编辑标注权限
                            update_data = {
                                "result": [
                                    {
                                        "value": {"choices": ["Negative"]},
                                        "from_name": "sentiment", 
                                        "to_name": "text",
                                        "type": "choices"
                                    }
                                ]
                            }
                            
                            update_response = requests.patch(
                                f"{BASE_URL}/api/label-studio/annotations/{annotation_id}",
                                json=update_data,
                                headers=headers
                            )
                            can_edit = update_response.status_code in [200, 201]
                            print(f"   编辑标注: {'✅' if can_edit else '❌'}")
                            
                            # 6. 测试删除标注权限
                            delete_response = requests.delete(
                                f"{BASE_URL}/api/label-studio/annotations/{annotation_id}",
                                headers=headers
                            )
                            can_delete = delete_response.status_code in [200, 204]
                            print(f"   删除标注: {'✅' if can_delete else '❌'}")
        
        # 7. 前端页面访问测试
        print(f"   前端页面访问:")
        print(f"     - 任务详情: {FRONTEND_URL}/tasks/1")
        print(f"     - 标注页面: {FRONTEND_URL}/tasks/1/annotate")
        
        # 8. 权限验证总结
        expected = user["expected_permissions"]
        print(f"   权限验证:")
        print(f"     - 查看权限: {'符合预期' if can_view_projects == expected['can_view_annotation'] else '不符合预期'}")
        if can_view_projects and projects:
            print(f"     - 创建权限: {'符合预期' if can_create == expected['can_create_annotation'] else '不符合预期'}")
            if can_create:
                print(f"     - 编辑权限: {'符合预期' if can_edit == expected['can_edit_annotation'] else '不符合预期'}")
                print(f"     - 删除权限: {'符合预期' if can_delete == expected['can_delete_annotation'] else '不符合预期'}")

def main():
    print("🧪 标注权限系统测试")
    print("=" * 60)
    
    # 检查服务状态
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ 后端服务正常")
        else:
            print("❌ 后端服务异常")
            return
    except:
        print("❌ 无法连接后端服务")
        return
    
    try:
        frontend_response = requests.get(FRONTEND_URL, timeout=5)
        if frontend_response.status_code == 200:
            print("✅ 前端服务正常")
        else:
            print("❌ 前端服务异常")
    except:
        print("❌ 无法连接前端服务")
    
    # 测试用户权限
    test_user_permissions()
    
    print("\n" + "=" * 60)
    print("🎉 权限测试完成!")
    print("\n📋 功能说明:")
    print("   • 系统管理员: 拥有所有权限，可以进行完整的标注管理")
    print("   • 业务专家: 可以查看、创建、编辑标注，但不能删除")
    print("   • 数据标注员: 可以查看、创建、编辑标注，专注于标注工作")
    print("   • 报表查看者: 只能查看标注结果，不能进行标注操作")
    
    print("\n🌐 访问地址:")
    print(f"   • 后端API: {BASE_URL}")
    print(f"   • 前端界面: {FRONTEND_URL}")
    print(f"   • 标注页面: {FRONTEND_URL}/tasks/1/annotate")

if __name__ == "__main__":
    main()