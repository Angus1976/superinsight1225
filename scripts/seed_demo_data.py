#!/usr/bin/env python3
"""
SuperInsight 演示数据生成脚本

生成用于本地调试的模拟数据，包括：
- 用户和角色
- 项目和数据集
- 标注任务
- 知识图谱数据
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import json

# 添加项目路径
sys.path.insert(0, '/app')

# 设置环境变量
os.environ['PYTHONUNBUFFERED'] = '1'

try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    from src.config.settings import settings
    print("✅ 成功导入 SQLAlchemy 和配置")
except ImportError as e:
    print(f"❌ 导入错误：{e}")
    print("请确保在 Docker 容器中运行此脚本")
    sys.exit(1)

# 数据库连接
DATABASE_URL = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')

async def init_db_session():
    """初始化数据库会话"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine

async def check_tables_exist(session: AsyncSession) -> bool:
    """检查数据库表是否存在"""
    try:
        result = await session.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name='users' LIMIT 1"))
        return result.fetchone() is not None
    except Exception as e:
        print(f"⚠️  检查表时出错：{e}")
        return False

async def create_demo_data_direct(session: AsyncSession):
    """直接使用 SQL 创建演示数据"""
    print("📝 使用 SQL 创建演示数据...\n")
    
    try:
        # 创建角色
        print("📝 创建角色...")
        roles_sql = """
        INSERT INTO roles (id, name, description, permissions, created_at, updated_at)
        VALUES 
            (:id1, 'admin', '系统管理员', :perms1, NOW(), NOW()),
            (:id2, 'business_expert', '业务专家', :perms2, NOW(), NOW()),
            (:id3, 'tech_expert', '技术专家', :perms3, NOW(), NOW()),
            (:id4, 'annotator', '数据标注员', :perms4, NOW(), NOW()),
            (:id5, 'reviewer', '质量审核员', :perms5, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
        """
        
        perms_admin = json.dumps({
            "users": ["create", "read", "update", "delete"],
            "projects": ["create", "read", "update", "delete"],
            "tasks": ["create", "read", "update", "delete"],
            "system": ["manage", "monitor"]
        })
        
        perms_business = json.dumps({
            "projects": ["create", "read", "update"],
            "tasks": ["create", "read", "update"],
            "datasets": ["read"]
        })
        
        perms_tech = json.dumps({
            "projects": ["read"],
            "tasks": ["read"],
            "ai_models": ["manage"],
            "system": ["monitor"]
        })
        
        perms_annotator = json.dumps({
            "tasks": ["read"],
            "annotations": ["create", "read", "update"]
        })
        
        perms_reviewer = json.dumps({
            "tasks": ["read"],
            "annotations": ["read", "update"],
            "quality": ["manage"]
        })
        
        await session.execute(text(roles_sql), {
            "id1": str(uuid.uuid4()),
            "id2": str(uuid.uuid4()),
            "id3": str(uuid.uuid4()),
            "id4": str(uuid.uuid4()),
            "id5": str(uuid.uuid4()),
            "perms1": perms_admin,
            "perms2": perms_business,
            "perms3": perms_tech,
            "perms4": perms_annotator,
            "perms5": perms_reviewer,
        })
        await session.commit()
        print("✅ 角色创建完成\n")
        
        # 获取角色 ID
        roles_result = await session.execute(text("SELECT id, name FROM roles"))
        roles = {row[1]: row[0] for row in roles_result.fetchall()}
        
        # 创建用户
        print("👥 创建测试用户...")
        users_data = [
            ("admin", "admin@superinsight.com", "系统管理员", roles["admin"]),
            ("business_expert", "business@superinsight.com", "业务专家 - 张三", roles["business_expert"]),
            ("tech_expert", "tech@superinsight.com", "技术专家 - 李四", roles["tech_expert"]),
            ("annotator1", "annotator1@superinsight.com", "标注员 - 王五", roles["annotator"]),
            ("annotator2", "annotator2@superinsight.com", "标注员 - 赵六", roles["annotator"]),
            ("reviewer", "reviewer@superinsight.com", "质量审核员 - 孙七", roles["reviewer"]),
        ]
        
        users_sql = """
        INSERT INTO users (id, username, email, full_name, role_id, is_active, created_at, updated_at)
        VALUES (:id, :username, :email, :full_name, :role_id, true, NOW(), NOW())
        ON CONFLICT (username) DO NOTHING
        """
        
        users = {}
        for username, email, full_name, role_id in users_data:
            user_id = str(uuid.uuid4())
            await session.execute(text(users_sql), {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "role_id": role_id,
            })
            users[username] = user_id
        
        await session.commit()
        print(f"✅ 创建了 {len(users)} 个用户\n")
        
        # 创建项目
        print("📊 创建项目...")
        projects_data = [
            ("电商商品分类", "电商平台商品自动分类项目", users["business_expert"], "active"),
            ("客服对话质量评估", "客服对话质量评估和改进项目", users["business_expert"], "active"),
            ("医疗文本挖掘", "医疗文本信息抽取和分类", users["tech_expert"], "planning"),
        ]
        
        projects_sql = """
        INSERT INTO projects (id, name, description, owner_id, status, created_at, updated_at)
        VALUES (:id, :name, :description, :owner_id, :status, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
        """
        
        projects = {}
        for name, description, owner_id, status in projects_data:
            project_id = str(uuid.uuid4())
            await session.execute(text(projects_sql), {
                "id": project_id,
                "name": name,
                "description": description,
                "owner_id": owner_id,
                "status": status,
            })
            projects[name] = project_id
        
        await session.commit()
        print(f"✅ 创建了 {len(projects)} 个项目\n")
        
        # 创建数据集
        print("📁 创建数据集...")
        datasets_data = [
            ("商品标题数据集 v1", projects["电商商品分类"], 5000, "包含 5000 条电商商品标题"),
            ("商品描述数据集 v1", projects["电商商品分类"], 3000, "包含 3000 条电商商品描述"),
            ("客服对话数据集 v1", projects["客服对话质量评估"], 2000, "包含 2000 条客服对话记录"),
        ]
        
        datasets_sql = """
        INSERT INTO datasets (id, name, project_id, size, description, created_at, updated_at)
        VALUES (:id, :name, :project_id, :size, :description, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
        """
        
        datasets = {}
        for name, project_id, size, description in datasets_data:
            dataset_id = str(uuid.uuid4())
            await session.execute(text(datasets_sql), {
                "id": dataset_id,
                "name": name,
                "project_id": project_id,
                "size": size,
                "description": description,
            })
            datasets[name] = dataset_id
        
        await session.commit()
        print(f"✅ 创建了 {len(datasets)} 个数据集\n")
        
        # 创建标注任务
        print("✏️  创建标注任务...")
        tasks_data = [
            ("商品分类标注 - 第一批", projects["电商商品分类"], "classification", "in_progress", users["annotator1"], 500, 150),
            ("商品分类标注 - 第二批", projects["电商商品分类"], "classification", "pending", users["annotator2"], 500, 0),
            ("客服对话质量评估", projects["客服对话质量评估"], "evaluation", "in_progress", users["annotator1"], 200, 80),
        ]
        
        tasks_sql = """
        INSERT INTO annotation_tasks (id, name, project_id, task_type, status, assigned_to_id, total_items, completed_items, created_at, updated_at)
        VALUES (:id, :name, :project_id, :task_type, :status, :assigned_to_id, :total_items, :completed_items, NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
        """
        
        tasks = {}
        for name, project_id, task_type, status, assigned_to_id, total_items, completed_items in tasks_data:
            task_id = str(uuid.uuid4())
            await session.execute(text(tasks_sql), {
                "id": task_id,
                "name": name,
                "project_id": project_id,
                "task_type": task_type,
                "status": status,
                "assigned_to_id": assigned_to_id,
                "total_items": total_items,
                "completed_items": completed_items,
            })
            tasks[name] = task_id
        
        await session.commit()
        print(f"✅ 创建了 {len(tasks)} 个标注任务\n")
        
        print("=" * 70)
        print("✅ 演示数据生成完成！")
        print("=" * 70)
        print("\n📝 测试账号信息：\n")
        print("| 用户名 | 密码 | 角色 | 邮箱 |")
        print("-" * 70)
        print("| admin | admin123 | 系统管理员 | admin@superinsight.com |")
        print("| business_expert | business123 | 业务专家 | business@superinsight.com |")
        print("| tech_expert | tech123 | 技术专家 | tech@superinsight.com |")
        print("| annotator1 | annotator123 | 标注员 | annotator1@superinsight.com |")
        print("| annotator2 | annotator123 | 标注员 | annotator2@superinsight.com |")
        print("| reviewer | reviewer123 | 质量审核员 | reviewer@superinsight.com |")
        print("-" * 70)
        print("\n🌐 访问地址：")
        print("- API 文档: http://localhost:8000/docs")
        print("- Label Studio: http://localhost:8080")
        print("- Neo4j 浏览器: http://localhost:7474")
        print("\n")
        
    except Exception as e:
        print(f"❌ 创建数据时出错：{e}")
        import traceback
        traceback.print_exc()
        raise

async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🚀 SuperInsight 演示数据生成脚本")
    print("=" * 70 + "\n")
    
    try:
        async_session, engine = await init_db_session()
        
        async with async_session() as session:
            # 检查表是否存在
            print("🔍 检查数据库表...")
            tables_exist = await check_tables_exist(session)
            
            if not tables_exist:
                print("❌ 数据库表不存在")
                print("💡 请先运行数据库迁移：")
                print("   docker compose exec superinsight-api alembic upgrade head")
                sys.exit(1)
            
            print("✅ 数据库表存在\n")
            
            # 创建演示数据
            await create_demo_data_direct(session)
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
