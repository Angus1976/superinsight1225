# Label Studio 快速开始指南

## 🚀 5分钟快速上手

### 方式 1: 使用测试脚本（最简单）⭐

```bash
# 运行测试脚本
python3 test_label_studio.py

# 按提示操作：
# 1. 自动登录（annotator_test）
# 2. 查看项目和任务
# 3. 选择标签进行标注
# 4. 查看标注结果
```

### 方式 2: 使用 curl 命令

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"annotator_test","password":"annotator123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. 查看项目
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/label-studio/projects | python3 -m json.tool

# 3. 查看任务
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/label-studio/projects/1/tasks | python3 -m json.tool

# 4. 创建标注
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": [{
      "value": {"choices": ["Positive"]},
      "from_name": "sentiment",
      "to_name": "text",
      "type": "choices"
    }],
    "task": 2
  }' \
  http://localhost:8000/api/label-studio/projects/1/tasks/2/annotations
```

### 方式 3: 使用 Python 代码

```python
import requests

# 1. 登录
response = requests.post(
    "http://localhost:8000/api/security/login",
    json={"username": "annotator_test", "password": "annotator123"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. 获取项目
projects = requests.get(
    "http://localhost:8000/api/label-studio/projects",
    headers=headers
).json()
print(f"找到 {projects['count']} 个项目")

# 3. 获取任务
tasks = requests.get(
    "http://localhost:8000/api/label-studio/projects/1/tasks",
    headers=headers
).json()
print(f"找到 {tasks['count']} 个任务")

# 4. 创建标注
annotation = requests.post(
    "http://localhost:8000/api/label-studio/projects/1/tasks/2/annotations",
    headers=headers,
    json={
        "result": [{
            "value": {"choices": ["Positive"]},
            "from_name": "sentiment",
            "to_name": "text",
            "type": "choices"
        }],
        "task": 2
    }
).json()
print(f"标注创建成功: {annotation['id']}")
```

## 📋 测试账号

| 角色 | 账号 | 密码 | 推荐度 |
|------|------|------|--------|
| 数据标注员 | annotator_test | annotator123 | ⭐⭐⭐ 最推荐 |
| 系统管理员 | admin_test | admin123 | ⭐⭐ |
| 业务专家 | expert_test | expert123 | ⭐⭐ |
| 报表查看者 | viewer_test | viewer123 | ⭐ |

## 🎯 示例数据

### 项目
- **ID**: 1
- **名称**: 客户评论情感分析
- **类型**: 文本分类
- **标签**: Positive, Negative, Neutral

### 任务
1. "这个产品非常好用，我很满意！" → Positive ✅
2. "质量太差了，完全不值这个价格。" → Negative ✅
3. "还可以吧，没有特别惊艳也没有特别失望。" → Neutral ✅

## 🔗 API 端点

| 功能 | 方法 | 端点 |
|------|------|------|
| 获取项目 | GET | `/api/label-studio/projects` |
| 创建项目 | POST | `/api/label-studio/projects` |
| 获取任务 | GET | `/api/label-studio/projects/{id}/tasks` |
| 创建任务 | POST | `/api/label-studio/projects/{id}/tasks` |
| 创建标注 | POST | `/api/label-studio/projects/{pid}/tasks/{tid}/annotations` |

## 📊 服务状态

```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查 Label Studio API
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/label-studio/projects
```

## 💡 常用操作

### 创建新项目

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新项目",
    "description": "项目描述",
    "label_config": "<View><Text name=\"text\" value=\"$text\"/><Choices name=\"label\" toName=\"text\" choice=\"single\"><Choice value=\"A\"/><Choice value=\"B\"/></Choices></View>"
  }' \
  http://localhost:8000/api/label-studio/projects
```

### 添加任务

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"text": "待标注的文本"},
    "project": 1
  }' \
  http://localhost:8000/api/label-studio/projects/1/tasks
```

### 查看统计

```bash
# 查看项目统计
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/label-studio/projects/1 \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"任务: {d['task_number']}, 已标注: {d['total_annotations_number']}\")"
```

## 🆘 常见问题

**Q: 如何获取 token？**
```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"annotator_test","password":"annotator123"}'
```

**Q: 如何查看所有标注？**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/label-studio/projects/1/tasks/1/annotations
```

**Q: 如何更新标注？**
```bash
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"result": [...]}' \
  http://localhost:8000/api/label-studio/annotations/1
```

**Q: 如何删除标注？**
```bash
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/label-studio/annotations/1
```

## 📚 更多文档

- `LABEL_STUDIO_部署完成_最终报告.md` - 完整部署报告
- `LABEL_STUDIO_集成完成.md` - 详细集成文档
- `LABEL_STUDIO_角色权限说明.md` - 角色权限说明
- `test_label_studio.py` - 测试脚本源码

## 🎊 开始使用

```bash
# 最简单的方式 - 运行测试脚本
python3 test_label_studio.py

# 按提示操作即可！
```

---

**提示**: 推荐使用 `annotator_test` 账号体验标注功能！
