# SuperInsight 本地调试指南

**Version**: 1.0  
**Last Updated**: 2026-01-20  
**Purpose**: 完整的本地开发调试指南，包含模拟数据、多角色测试和 Label Studio 集成

## 📋 目录

1. [快速启动](#快速启动)
2. [模拟数据设置](#模拟数据设置)
3. [多角色账号测试](#多角色账号测试)
4. [Label Studio 集成测试](#label-studio-集成测试)
5. [功能测试清单](#功能测试清单)
6. [常见问题](#常见问题)

---

## 快速启动

### 第一步：环境准备

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 编辑 .env 文件（可选，使用默认值也可以）
# 重要：确保以下配置
DEBUG=true
LOG_LEVEL=INFO
LABEL_STUDIO_LANGUAGE=zh

# 3. 创建必要目录
mkdir -p data/{postgres,redis,neo4j,label-studio}
mkdir -p logs/{api,postgres,redis,neo4j,label-studio}
mkdir -p uploads exports

# 4. 赋予脚本执行权限
chmod +x start-superinsight.sh stop-superinsight.sh
```

### 第二步：启动服务

```bash
# 方式一：使用启动脚本（推荐）
./start-superinsight.sh

# 方式二：手动启动
docker compose up -d

# 等待所有服务启动完成（约 30-60 秒）
docker compose ps
```

### 第三步：验证服务

```bash
# 检查所有服务是否运行
docker compose ps

# 检查 API 健康状态
curl http://localhost:8000/health

# 检查 Label Studio
curl http://localhost:8080/health

# 查看 API 文档
# 浏览器访问：http://localhost:8000/docs
```

---

## 模拟数据设置

### 创建模拟数据脚本

创建文件 `scripts/seed_demo_data.py`：

```python
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
from datetime import datetime, timedelta
from typing import List
import uuid

# 添加项目路径
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import (
    User, Role, Project, Dataset, Task, Annotation,
    AnnotationTask, QualityMetric, AuditLog
)
from src.config.settings import settings

# 数据库连接
DATABASE_URL = settings.database_url.replace('postgresql://', 'postgresql+asyncpg://')

async def init_db_session():
    """初始化数据库会话"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine

async def create_roles(session: AsyncSession) -> dict:
    """创建角色"""
    print("📝 创建角色...")
    
    roles_data = [
        {"name": "admin", "description": "系统管理员"},
        {"name": "business_expert", "description": "业务专家"},
        {"name": "tech_expert", "description": "技术专家"},
        {"name": "annotator", "description": "数据标注员"},
        {"name": "reviewer", "description": "质量审核员"},
    ]
    
    roles = {}
    for role_data in roles_data:
        role = Role(
            id=str(uuid.uuid4()),
            name=role_data["name"],
            description=role_data["description"],
            permissions=get_role_permissions(role_data["name"])
        )
        session.add(role)
        roles[role_data["name"]] = role
    
    await session.commit()
    print(f"✅ 创建了 {len(roles)} 个角色")
    return roles

async def create_users(session: AsyncSession, roles: dict) -> dict:
    """创建测试用户"""
    print("👥 创建测试用户...")
    
    users_data = [
        {
            "username": "admin",
            "email": "admin@superinsight.com",
            "full_name": "系统管理员",
            "role": "admin",
            "password": "admin123"
        },
        {
            "username": "business_expert",
            "email": "business@superinsight.com",
            "full_name": "业务专家 - 张三",
            "role": "business_expert",
            "password": "business123"
        },
        {
            "username": "tech_expert",
            "email": "tech@superinsight.com",
            "full_name": "技术专家 - 李四",
            "role": "tech_expert",
            "password": "tech123"
        },
        {
            "username": "annotator1",
            "email": "annotator1@superinsight.com",
            "full_name": "标注员 - 王五",
            "role": "annotator",
            "password": "annotator123"
        },
        {
            "username": "annotator2",
            "email": "annotator2@superinsight.com",
            "full_name": "标注员 - 赵六",
            "role": "annotator",
            "password": "annotator123"
        },
        {
            "username": "reviewer",
            "email": "reviewer@superinsight.com",
            "full_name": "质量审核员 - 孙七",
            "role": "reviewer",
            "password": "reviewer123"
        },
    ]
    
    users = {}
    for user_data in users_data:
        user = User(
            id=str(uuid.uuid4()),
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role_id=roles[user_data["role"]].id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        # 注意：实际应用中应该使用密码哈希
        user.set_password(user_data["password"])
        session.add(user)
        users[user_data["username"]] = user
    
    await session.commit()
    print(f"✅ 创建了 {len(users)} 个用户")
    return users

async def create_projects(session: AsyncSession, users: dict) -> dict:
    """创建项目"""
    print("📊 创建项目...")
    
    projects_data = [
        {
            "name": "电商商品分类",
            "description": "电商平台商品自动分类项目",
            "owner": "business_expert",
            "status": "active"
        },
        {
            "name": "客服对话质量评估",
            "description": "客服对话质量评估和改进项目",
            "owner": "business_expert",
            "status": "active"
        },
        {
            "name": "医疗文本挖掘",
            "description": "医疗文本信息抽取和分类",
            "owner": "tech_expert",
            "status": "planning"
        },
    ]
    
    projects = {}
    for project_data in projects_data:
        project = Project(
            id=str(uuid.uuid4()),
            name=project_data["name"],
            description=project_data["description"],
            owner_id=users[project_data["owner"]].id,
            status=project_data["status"],
            created_at=datetime.utcnow()
        )
        session.add(project)
        projects[project_data["name"]] = project
    
    await session.commit()
    print(f"✅ 创建了 {len(projects)} 个项目")
    return projects

async def create_datasets(session: AsyncSession, projects: dict) -> dict:
    """创建数据集"""
    print("📁 创建数据集...")
    
    datasets_data = [
        {
            "name": "商品标题数据集 v1",
            "project": "电商商品分类",
            "size": 5000,
            "description": "包含 5000 条电商商品标题"
        },
        {
            "name": "商品描述数据集 v1",
            "project": "电商商品分类",
            "size": 3000,
            "description": "包含 3000 条电商商品描述"
        },
        {
            "name": "客服对话数据集 v1",
            "project": "客服对话质量评估",
            "size": 2000,
            "description": "包含 2000 条客服对话记录"
        },
    ]
    
    datasets = {}
    for dataset_data in datasets_data:
        dataset = Dataset(
            id=str(uuid.uuid4()),
            name=dataset_data["name"],
            project_id=projects[dataset_data["project"]].id,
            size=dataset_data["size"],
            description=dataset_data["description"],
            created_at=datetime.utcnow()
        )
        session.add(dataset)
        datasets[dataset_data["name"]] = dataset
    
    await session.commit()
    print(f"✅ 创建了 {len(datasets)} 个数据集")
    return datasets

async def create_tasks(session: AsyncSession, projects: dict, users: dict) -> dict:
    """创建标注任务"""
    print("✏️  创建标注任务...")
    
    tasks_data = [
        {
            "name": "商品分类标注 - 第一批",
            "project": "电商商品分类",
            "task_type": "classification",
            "status": "in_progress",
            "assigned_to": "annotator1",
            "total_items": 500
        },
        {
            "name": "商品分类标注 - 第二批",
            "project": "电商商品分类",
            "task_type": "classification",
            "status": "pending",
            "assigned_to": "annotator2",
            "total_items": 500
        },
        {
            "name": "客服对话质量评估",
            "project": "客服对话质量评估",
            "task_type": "evaluation",
            "status": "in_progress",
            "assigned_to": "annotator1",
            "total_items": 200
        },
    ]
    
    tasks = {}
    for task_data in tasks_data:
        task = AnnotationTask(
            id=str(uuid.uuid4()),
            name=task_data["name"],
            project_id=projects[task_data["project"]].id,
            task_type=task_data["task_type"],
            status=task_data["status"],
            assigned_to_id=users[task_data["assigned_to"]].id,
            total_items=task_data["total_items"],
            completed_items=0 if task_data["status"] == "pending" else 150,
            created_at=datetime.utcnow()
        )
        session.add(task)
        tasks[task_data["name"]] = task
    
    await session.commit()
    print(f"✅ 创建了 {len(tasks)} 个标注任务")
    return tasks

def get_role_permissions(role_name: str) -> dict:
    """获取角色权限"""
    permissions_map = {
        "admin": {
            "users": ["create", "read", "update", "delete"],
            "projects": ["create", "read", "update", "delete"],
            "tasks": ["create", "read", "update", "delete"],
            "system": ["manage", "monitor"]
        },
        "business_expert": {
            "projects": ["create", "read", "update"],
            "tasks": ["create", "read", "update"],
            "datasets": ["read"]
        },
        "tech_expert": {
            "projects": ["read"],
            "tasks": ["read"],
            "ai_models": ["manage"],
            "system": ["monitor"]
        },
        "annotator": {
            "tasks": ["read"],
            "annotations": ["create", "read", "update"]
        },
        "reviewer": {
            "tasks": ["read"],
            "annotations": ["read", "update"],
            "quality": ["manage"]
        }
    }
    return permissions_map.get(role_name, {})

async def main():
    """主函数"""
    print("\n🚀 开始生成演示数据...\n")
    
    try:
        async_session, engine = await init_db_session()
        
        async with async_session() as session:
            # 创建数据
            roles = await create_roles(session)
            users = await create_users(session, roles)
            projects = await create_projects(session, users)
            datasets = await create_datasets(session, projects)
            tasks = await create_tasks(session, projects, users)
            
            print("\n✅ 演示数据生成完成！\n")
            print("📝 测试账号信息：")
            print("=" * 60)
            print("| 用户名 | 密码 | 角色 | 邮箱 |")
            print("=" * 60)
            print("| admin | admin123 | 系统管理员 | admin@superinsight.com |")
            print("| business_expert | business123 | 业务专家 | business@superinsight.com |")
            print("| tech_expert | tech123 | 技术专家 | tech@superinsight.com |")
            print("| annotator1 | annotator123 | 标注员 | annotator1@superinsight.com |")
            print("| annotator2 | annotator123 | 标注员 | annotator2@superinsight.com |")
            print("| reviewer | reviewer123 | 质量审核员 | reviewer@superinsight.com |")
            print("=" * 60)
            
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### 运行模拟数据脚本

```bash
# 进入 API 容器
docker compose exec superinsight-api bash

# 运行数据生成脚本
python scripts/seed_demo_data.py

# 或者从主机运行
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

---

## 多角色账号测试

### 测试账号信息

| 用户名 | 密码 | 角色 | 邮箱 | 权限 |
|--------|------|------|------|------|
| `admin` | `admin123` | 系统管理员 | admin@superinsight.com | 全部权限 |
| `business_expert` | `business123` | 业务专家 | business@superinsight.com | 项目管理、任务创建 |
| `tech_expert` | `tech123` | 技术专家 | tech@superinsight.com | AI 模型管理、系统监控 |
| `annotator1` | `annotator123` | 标注员 | annotator1@superinsight.com | 标注任务执行 |
| `annotator2` | `annotator123` | 标注员 | annotator2@superinsight.com | 标注任务执行 |
| `reviewer` | `reviewer123` | 质量审核员 | reviewer@superinsight.com | 质量审核、标注审核 |

### 使用 API 测试登录

```bash
# 1. 获取 JWT Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# 响应示例：
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "user": {
#     "id": "...",
#     "username": "admin",
#     "email": "admin@superinsight.com",
#     "role": "admin"
#   }
# }

# 2. 使用 Token 访问受保护的端点
TOKEN="your_token_here"
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# 3. 获取用户的项目列表
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"
```

### 使用 Swagger UI 测试

1. 打开浏览器访问：http://localhost:8000/docs
2. 点击右上角的 "Authorize" 按钮
3. 输入用户名和密码
4. 测试各个 API 端点

---

## Label Studio 集成测试

### 第一步：访问 Label Studio

1. 打开浏览器：http://localhost:8080
2. 默认登录信息：
   - 用户名：`admin@superinsight.com`
   - 密码：见 `.env` 文件中的 `LABEL_STUDIO_PASSWORD`

### 第二步：创建标注项目

#### 方式一：通过 Label Studio UI

1. 点击 "Create" 按钮
2. 输入项目名称：`电商商品分类演示`
3. 选择标注类型：`Classification`
4. 配置标签：
   - 电子产品
   - 服装鞋帽
   - 食品饮料
   - 家居用品
   - 其他

#### 方式二：通过 API

```bash
# 获取 Label Studio API Token
# 在 Label Studio UI 中：Settings > API Token

# 创建项目
curl -X POST http://localhost:8080/api/projects \
  -H "Authorization: Token YOUR_LABEL_STUDIO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "电商商品分类演示",
    "label_config": "<View><Text name=\"text\" value=\"$text\"/><Choices name=\"label\" toName=\"text\"><Choice value=\"电子产品\"/><Choice value=\"服装鞋帽\"/><Choice value=\"食品饮料\"/><Choice value=\"家居用品\"/><Choice value=\"其他\"/></Choices></View>"
  }'
```

### 第三步：导入数据

#### 创建示例数据文件

创建 `sample_data.csv`：

```csv
text
iPhone 13 Pro Max 256GB 深空黑色
Adidas 运动鞋 男款 黑色
有机咖啡豆 500g 中度烘焙
宜家 BILLY 书架 白色
小米 10000mAh 移动电源
```

#### 导入数据

```bash
# 通过 Label Studio UI
# 1. 进入项目
# 2. 点击 "Import" 按钮
# 3. 选择 CSV 文件
# 4. 配置映射关系

# 或通过 API
curl -X POST http://localhost:8080/api/projects/1/import \
  -H "Authorization: Token YOUR_LABEL_STUDIO_API_TOKEN" \
  -F "file=@sample_data.csv"
```

### 第四步：创建标注任务

1. 在 Label Studio 中创建标注任务
2. 分配给不同的标注员
3. 设置质量控制参数

### 第五步：测试标注工作流

#### 标注员视角

```bash
# 1. 以 annotator1 身份登录
# 用户名：annotator1
# 密码：annotator123

# 2. 查看分配的任务
curl -X GET http://localhost:8000/api/v1/tasks/assigned \
  -H "Authorization: Bearer $ANNOTATOR_TOKEN"

# 3. 获取待标注的数据
curl -X GET http://localhost:8000/api/v1/tasks/1/items \
  -H "Authorization: Bearer $ANNOTATOR_TOKEN"

# 4. 提交标注结果
curl -X POST http://localhost:8000/api/v1/annotations \
  -H "Authorization: Bearer $ANNOTATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "1",
    "item_id": "item_001",
    "label": "电子产品",
    "confidence": 0.95
  }'
```

#### 审核员视角

```bash
# 1. 以 reviewer 身份登录
# 用户名：reviewer
# 密码：reviewer123

# 2. 查看待审核的标注
curl -X GET http://localhost:8000/api/v1/annotations/pending-review \
  -H "Authorization: Bearer $REVIEWER_TOKEN"

# 3. 审核标注结果
curl -X POST http://localhost:8000/api/v1/annotations/1/review \
  -H "Authorization: Bearer $REVIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "comment": "标注正确"
  }'
```

---

## 功能测试清单

### 🔐 认证和授权

- [ ] 使用不同角色账号登录
- [ ] 验证 JWT Token 生成和验证
- [ ] 测试权限控制（不同角色访问不同资源）
- [ ] 测试 Token 过期和刷新
- [ ] 测试登出功能

### 📊 项目管理

- [ ] 创建新项目
- [ ] 编辑项目信息
- [ ] 删除项目
- [ ] 查看项目列表
- [ ] 查看项目详情
- [ ] 分配项目成员

### 📁 数据集管理

- [ ] 上传数据集
- [ ] 查看数据集列表
- [ ] 查看数据集详情
- [ ] 删除数据集
- [ ] 导出数据集

### ✏️ 标注任务

- [ ] 创建标注任务
- [ ] 分配任务给标注员
- [ ] 查看任务进度
- [ ] 更新任务状态
- [ ] 完成任务

### 🏷️ Label Studio 集成

- [ ] 创建 Label Studio 项目
- [ ] 导入数据到 Label Studio
- [ ] 执行标注操作
- [ ] 导出标注结果
- [ ] 同步标注数据到 SuperInsight

### 🤖 AI 预标注

- [ ] 配置 AI 模型
- [ ] 执行 AI 预标注
- [ ] 查看预标注结果
- [ ] 调整预标注参数
- [ ] 评估预标注质量

### 📈 质量管理

- [ ] 查看质量指标
- [ ] 生成质量报告
- [ ] 识别低质量标注
- [ ] 触发质量告警
- [ ] 查看质量趋势

### 💰 计费和统计

- [ ] 查看工作时间统计
- [ ] 查看标注数量统计
- [ ] 生成计费报告
- [ ] 导出统计数据
- [ ] 查看成本分析

### 🔍 监控和日志

- [ ] 查看系统健康状态
- [ ] 查看 API 性能指标
- [ ] 查看审计日志
- [ ] 查看错误日志
- [ ] 查看系统监控面板

---

## 常见问题

### Q1: 如何重置数据库？

```bash
# 停止服务并删除数据卷
docker compose down -v

# 重新启动
docker compose up -d

# 重新生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### Q2: 如何查看 API 日志？

```bash
# 实时查看日志
docker compose logs -f superinsight-api

# 查看最近 100 行
docker compose logs --tail=100 superinsight-api

# 查看特定时间范围的日志
docker compose logs --since 10m superinsight-api
```

### Q3: 如何连接到数据库进行调试？

```bash
# 进入 PostgreSQL 容器
docker compose exec postgres psql -U superinsight -d superinsight

# 常用命令
\dt                    # 列出所有表
\d table_name          # 查看表结构
SELECT * FROM users;   # 查询用户
\q                     # 退出
```

### Q4: 如何查看 Label Studio 的日志？

```bash
# 查看 Label Studio 日志
docker compose logs -f label-studio

# 进入 Label Studio 容器
docker compose exec label-studio bash
```

### Q5: 如何测试 AI 预标注功能？

```bash
# 1. 确保 Ollama 已启动
docker compose --profile ollama up -d

# 2. 下载模型
docker compose exec ollama ollama pull llama2

# 3. 测试 API
curl -X POST http://localhost:8000/api/v1/ai/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "iPhone 13 Pro Max",
    "model": "llama2"
  }'
```

### Q6: 如何导出标注数据？

```bash
# 导出为 JSON 格式
curl -X GET http://localhost:8000/api/v1/tasks/1/export?format=json \
  -H "Authorization: Bearer $TOKEN" \
  > annotations.json

# 导出为 CSV 格式
curl -X GET http://localhost:8000/api/v1/tasks/1/export?format=csv \
  -H "Authorization: Bearer $TOKEN" \
  > annotations.csv
```

### Q7: 如何处理 Label Studio 连接问题？

```bash
# 检查 Label Studio 是否运行
docker compose ps label-studio

# 检查 Label Studio 健康状态
curl http://localhost:8080/health

# 查看 Label Studio 日志
docker compose logs label-studio

# 重启 Label Studio
docker compose restart label-studio
```

### Q8: 如何调试异步问题？

```bash
# 启用 asyncio 调试模式
# 在 .env 中添加
DEBUG_ASYNCIO=true

# 查看详细的异步日志
docker compose logs -f superinsight-api | grep -i async
```

---

## 性能测试

### 负载测试

```bash
# 安装 locust
pip install locust

# 创建 locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class SuperInsightUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_projects(self):
        self.client.get("/api/v1/projects")
    
    @task
    def get_tasks(self):
        self.client.get("/api/v1/tasks")
EOF

# 运行负载测试
locust -f locustfile.py --host=http://localhost:8000
```

### 内存和 CPU 监控

```bash
# 实时监控容器资源使用
docker stats

# 查看特定容器的详细信息
docker stats superinsight-api
```

---

## 下一步

1. ✅ 启动本地环境
2. ✅ 生成演示数据
3. ✅ 使用不同角色账号测试
4. ✅ 测试 Label Studio 集成
5. ✅ 执行功能测试清单
6. ✅ 进行性能测试
7. 📝 记录测试结果
8. 🐛 报告发现的问题

---

**需要帮助？** 查看 [QUICK_START.md](./QUICK_START.md) 或 [README.md](./README.md)

