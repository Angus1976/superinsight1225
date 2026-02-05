# SuperInsight 与 Label Studio 集成说明

## 🎯 两个系统的关系

### Label Studio (http://localhost:8080/)
- **独立的标注系统**
- 用于创建项目、配置标注界面、管理数据
- 需要在这里导入数据和配置标注模板

### SuperInsight 前端 (http://localhost:5173/)
- **集成了 Label Studio 的企业级平台**
- 通过 iframe 嵌入 Label Studio 标注界面
- 提供额外的任务管理、权限控制、数据统计等功能

## 📋 完整工作流程

### 步骤 1: 在 Label Studio 中准备数据

1. **访问 Label Studio**
   ```
   http://localhost:8080/
   ```

2. **登录**
   - 用户名: `admin@example.com`
   - 密码: `admin`

3. **创建项目**
   - 点击 "Create Project"
   - 设置项目名称和描述
   - 配置标注界面（XML 配置）

4. **导入数据**
   - 在项目页面点击 "Import"
   - 上传 JSON 文件（如 `simple_test.json`）
   - 确认数据导入成功

5. **记录项目 ID**
   - 在项目 URL 中可以看到项目 ID
   - 例如: `http://localhost:8080/projects/1/` → 项目 ID 是 `1`

### 步骤 2: 在 SuperInsight 中使用

1. **访问 SuperInsight**
   ```
   http://localhost:5173/
   ```

2. **登录 SuperInsight**
   - 使用您的 SuperInsight 账号登录
   - 例如: `admin_user` / `password`

3. **访问任务页面**
   ```
   http://localhost:5173/tasks/
   ```

4. **查看或创建任务**
   - SuperInsight 的任务会关联到 Label Studio 项目
   - 任务详情中会显示 `label_studio_project_id`

5. **开始标注**
   - 点击任务进入标注页面
   - SuperInsight 会通过 iframe 嵌入 Label Studio
   - 在 SuperInsight 界面中直接进行标注

## 🔄 两种标注方式

### 方式 1: 直接在 Label Studio 标注（推荐用于测试）

**优点**:
- 直接访问，无需额外配置
- 适合快速测试和熟悉 Label Studio

**步骤**:
1. 访问 http://localhost:8080/
2. 选择项目
3. 点击任务开始标注

### 方式 2: 在 SuperInsight 中标注（推荐用于生产）

**优点**:
- 统一的用户界面
- 集成的权限管理
- 任务分配和进度跟踪
- 数据统计和报表
- 多语言同步

**步骤**:
1. 访问 http://localhost:5173/tasks/
2. 选择任务
3. 在嵌入的 Label Studio 界面中标注

## 🔗 集成功能

SuperInsight 集成了以下 Label Studio 功能：

### 1. iframe 嵌入
- 完整的 Label Studio 标注界面
- 无缝集成到 SuperInsight 页面

### 2. 双向通信
- 标注创建/更新事件同步
- 任务完成状态同步
- 进度更新实时反馈

### 3. 语言同步
- SuperInsight 切换语言时，Label Studio 自动切换
- 支持中文/英文

### 4. 连接状态监控
- 实时显示连接状态
- 自动健康检查
- 断线重连

### 5. 增强功能
- 全屏模式
- 重新加载
- 状态同步
- 错误处理

## 📊 当前状态检查

### 检查 Label Studio 是否有数据

```bash
# 访问 Label Studio API
curl -H "Authorization: Token f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17" \
  http://localhost:8080/api/projects
```

### 检查 SuperInsight 任务

访问: http://localhost:5173/tasks/

如果看到任务列表，说明 SuperInsight 已经配置了任务。

## 🚀 快速开始

### 场景 1: 我只想测试 Label Studio

1. 访问 http://localhost:8080/
2. 登录后创建项目
3. 导入 `data/demo_datasets/simple_test.json`
4. 开始标注

### 场景 2: 我想在 SuperInsight 中标注

**前提条件**:
- Label Studio 中已有项目和数据
- SuperInsight 中已创建关联任务

**步骤**:
1. 在 Label Studio 创建项目并导入数据（步骤 1）
2. 在 SuperInsight 中创建任务，关联 Label Studio 项目 ID
3. 访问 http://localhost:5173/tasks/annotate/{task_id}
4. 在嵌入的界面中标注

## 🔧 常见问题

### Q1: SuperInsight 任务页面为空？
**A**: 这是正常的，SuperInsight 的任务需要通过后端 API 创建。您可以：
- 选项 1: 直接使用 Label Studio (http://localhost:8080/)
- 选项 2: 通过 SuperInsight API 创建任务

### Q2: 如何在 SuperInsight 中创建任务？
**A**: 需要调用 SuperInsight 后端 API：

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试标注任务",
    "label_studio_project_id": "1",
    "annotation_type": "text_classification"
  }'
```

### Q3: Label Studio 和 SuperInsight 的数据是同步的吗？
**A**: 是的，SuperInsight 通过 API 和 iframe 通信与 Label Studio 同步：
- 标注数据存储在 Label Studio
- SuperInsight 记录任务元数据和进度
- 两者通过 project_id 关联

### Q4: 我应该用哪个系统？
**A**: 
- **测试/学习**: 直接使用 Label Studio (http://localhost:8080/)
- **生产环境**: 使用 SuperInsight (http://localhost:5173/)，它提供更多企业级功能

## 📝 推荐工作流

### 对于演示和测试

1. ✅ 使用 Label Studio (http://localhost:8080/)
2. ✅ 创建项目并导入演示数据
3. ✅ 熟悉标注界面和功能
4. ✅ 导出标注结果

### 对于生产使用

1. ✅ 在 Label Studio 创建项目模板
2. ✅ 在 SuperInsight 中创建任务
3. ✅ 分配任务给标注人员
4. ✅ 在 SuperInsight 中跟踪进度
5. ✅ 通过 SuperInsight 导出结果

## 🎉 下一步

**现在您可以**:

1. **立即开始**: 访问 http://localhost:8080/ 并导入演示数据
2. **查看集成**: 访问 http://localhost:5173/tasks/ 查看 SuperInsight 界面
3. **阅读文档**: 查看 `QUICK_START.md` 了解详细步骤

**推荐顺序**:
1. 先在 Label Studio 中熟悉标注功能
2. 再探索 SuperInsight 的企业级功能
3. 最后根据需求选择合适的工作流程

---

**总结**: 
- Label Studio = 标注引擎（核心功能）
- SuperInsight = 企业级平台（Label Studio + 任务管理 + 权限控制 + 数据统计）
