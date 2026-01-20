#!/usr/bin/env python3
"""
Label Studio API 测试脚本
演示如何使用 Label Studio API 进行标注
"""

import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
# 使用真实的 JWT token（需要先登录获取）
TOKEN = None

def login():
    """登录获取 token"""
    response = requests.post(
        f"{BASE_URL}/api/security/login",
        json={
            "username": "annotator_test",
            "password": "annotator123"
        }
    )
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        print(f"登录失败: {response.status_code}")
        return None

def get_projects(token):
    """获取所有项目"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/label-studio/projects", headers=headers)
    return response.json()

def get_project_tasks(token, project_id):
    """获取项目的所有任务"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks",
        headers=headers
    )
    return response.json()

def create_annotation(token, project_id, task_id, sentiment):
    """创建标注"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "result": [
            {
                "value": {"choices": [sentiment]},
                "from_name": "sentiment",
                "to_name": "text",
                "type": "choices"
            }
        ],
        "task": task_id
    }
    response = requests.post(
        f"{BASE_URL}/api/label-studio/projects/{project_id}/tasks/{task_id}/annotations",
        headers=headers,
        json=data
    )
    return response.json()

def main():
    """主函数"""
    print("=" * 60)
    print("Label Studio API 测试")
    print("=" * 60)
    
    # 1. 登录
    print("\n1. 登录系统...")
    token = login()
    if not token:
        print("登录失败，退出")
        return
    print(f"✓ 登录成功，获取到 token")
    
    # 2. 获取项目列表
    print("\n2. 获取项目列表...")
    projects = get_projects(token)
    print(f"✓ 找到 {projects['count']} 个项目")
    for project in projects['results']:
        print(f"  - 项目 #{project['id']}: {project['title']}")
        print(f"    任务数: {project['task_number']}, 已标注: {project['total_annotations_number']}")
    
    # 3. 获取第一个项目的任务
    if projects['count'] > 0:
        project_id = projects['results'][0]['id']
        print(f"\n3. 获取项目 #{project_id} 的任务列表...")
        tasks = get_project_tasks(token, project_id)
        print(f"✓ 找到 {tasks['count']} 个任务")
        
        for task in tasks['results']:
            status = "✓ 已标注" if task['is_labeled'] else "○ 待标注"
            print(f"  {status} 任务 #{task['id']}: {task['data'].get('text', '')[:30]}...")
            if task['annotations']:
                for ann in task['annotations']:
                    result = ann['result'][0]['value']['choices'][0]
                    print(f"      标注结果: {result} (by {ann['created_username']})")
        
        # 4. 为未标注的任务创建标注
        print("\n4. 为未标注的任务创建标注...")
        unlabeled_tasks = [t for t in tasks['results'] if not t['is_labeled']]
        
        if unlabeled_tasks:
            task = unlabeled_tasks[0]
            task_id = task['id']
            text = task['data'].get('text', '')
            
            print(f"\n选择任务 #{task_id}: {text}")
            print("请选择情感标签:")
            print("  1. Positive (积极)")
            print("  2. Negative (消极)")
            print("  3. Neutral (中性)")
            
            choice = input("请输入选择 (1-3): ").strip()
            sentiment_map = {
                '1': 'Positive',
                '2': 'Negative',
                '3': 'Neutral'
            }
            
            if choice in sentiment_map:
                sentiment = sentiment_map[choice]
                print(f"\n创建标注: {sentiment}...")
                annotation = create_annotation(token, project_id, task_id, sentiment)
                print(f"✓ 标注创建成功！")
                print(f"  标注 ID: {annotation['id']}")
                print(f"  创建时间: {annotation['created_at']}")
                print(f"  创建者: {annotation['created_username']}")
                
                # 5. 再次获取任务列表，查看更新
                print("\n5. 查看更新后的任务列表...")
                tasks = get_project_tasks(token, project_id)
                labeled_count = sum(1 for t in tasks['results'] if t['is_labeled'])
                print(f"✓ 已标注任务: {labeled_count}/{tasks['count']}")
            else:
                print("无效的选择")
        else:
            print("所有任务都已标注！")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
