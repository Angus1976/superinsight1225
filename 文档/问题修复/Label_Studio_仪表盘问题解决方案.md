# Label Studio 仪表盘问题解决方案

## 问题描述

用户点击"在新窗口中打开 Label Studio"后，看到的是项目仪表盘（Dashboard）而不是数据管理器（Data Manager）和标注界面。

## 根本原因

URL 端点使用错误：
- **错误 URL**: `/projects/{projectId}` - 显示项目仪表盘
- **正确 URL**: `/projects/{projectId}/data` - 显示数据管理器

## 解决方案

### 1. 代码已修复

以下文件已经修复，使用正确的 URL：

#### TaskDetail.tsx
```typescript
const handleOpenInNewWindow = () => {
  const projectId = task.label_studio_project_id;
  
  if (!projectId) {
    message.info('项目尚未创建，正在跳转到标注页面...');
    navigate(`/tasks/${id}/annotate`);
    return;
  }
  
  // ✅ 正确的 URL - 指向数据管理器
  const labelStudioUrl = import.meta.env.VITE_LABEL_STUDIO_URL || 'http://localhost:8080';
  const projectUrl = `${labelStudioUrl}/projects/${projectId}/data`;
  
  window.open(projectUrl, '_blank', 'noopener,noreferrer');
  message.success('已在新窗口中打开 Label Studio 数据管理器');
};
```

#### TaskAnnotate.tsx
```typescript
<Button
  type="primary"
  size="large"
  onClick={() => {
    const labelStudioUrl = 'http://localhost:8080';
    // ✅ 正确的 URL - 指向数据管理器
    const projectUrl = `${labelStudioUrl}/projects/${project.id}/data`;
    window.open(projectUrl, '_blank', 'noopener,noreferrer');
    message.success('已在新窗口中打开 Label Studio');
  }}
>
  在新窗口中打开 Label Studio
</Button>
```

### 2. 验证步骤

#### 步骤 1: 确认代码已更新

```bash
# 检查 TaskDetail.tsx 中的 URL
grep -A 5 "projectUrl.*projects" frontend/src/pages/Tasks/TaskDetail.tsx

# 应该看到: const projectUrl = `${labelStudioUrl}/projects/${projectId}/data`;
```

```bash
# 检查 TaskAnnotate.tsx 中的 URL
grep -A 5 "projectUrl.*projects" frontend/src/pages/Tasks/TaskAnnotate.tsx

# 应该看到: const projectUrl = `${labelStudioUrl}/projects/${project.id}/data`;
```

#### 步骤 2: 重建前端容器

```bash
# 停止前端容器
docker stop superinsight-frontend

# 删除旧容器
docker rm superinsight-frontend

# 重建并启动前端容器
docker-compose up -d --build frontend

# 查看容器日志
docker logs -f superinsight-frontend
```

#### 步骤 3: 清除浏览器缓存

1. 打开浏览器开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

或者：

1. 按 Ctrl+Shift+Delete (Windows) 或 Cmd+Shift+Delete (Mac)
2. 选择"缓存的图片和文件"
3. 点击"清除数据"

#### 步骤 4: 测试功能

1. **登录 SuperInsight**
   - 访问 http://localhost:5173
   - 使用您的凭据登录

2. **进入任务详情页**
   - 点击任务列表中的任意任务
   - 进入任务详情页

3. **点击"在新窗口中打开"按钮**
   - 应该在新窗口中打开 Label Studio
   - URL 应该是: `http://localhost:8080/projects/{projectId}/data`

4. **验证显示内容**
   - ✅ 应该看到: 数据管理器界面，包含任务列表
   - ✅ 应该看到: "Label All Tasks" 按钮
   - ✅ 应该看到: 任务列表，可以点击单个任务
   - ❌ 不应该看到: 项目仪表盘（统计图表、设置等）

### 3. 预期结果

#### 正确的数据管理器界面

```
┌─────────────────────────────────────────────────────────────┐
│  Label Studio - Project: {项目名称}                         │
├─────────────────────────────────────────────────────────────┤
│  [Label All Tasks]  [Import]  [Export]  [Settings]         │
├─────────────────────────────────────────────────────────────┤
│  Tasks (10)                                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ☐ Task 1: 这是第一个任务的文本内容...                  │ │
│  │ ☐ Task 2: 这是第二个任务的文本内容...                  │ │
│  │ ☐ Task 3: 这是第三个任务的文本内容...                  │ │
│  │ ...                                                     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 错误的仪表盘界面（不应该看到）

```
┌─────────────────────────────────────────────────────────────┐
│  Label Studio - Project Dashboard                          │
├─────────────────────────────────────────────────────────────┤
│  Overview                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Total Tasks │  │ Completed   │  │ Annotations │        │
│  │     10      │  │      5      │  │     15      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  [Settings]  [Members]  [API]                              │
└─────────────────────────────────────────────────────────────┘
```

### 4. 故障排查

#### 问题 1: 仍然显示仪表盘

**可能原因**:
1. 浏览器缓存未清除
2. 前端容器未重建
3. 代码未正确更新

**解决方法**:
```bash
# 1. 完全停止所有容器
docker-compose down

# 2. 删除前端镜像
docker rmi superinsight-frontend

# 3. 重建并启动
docker-compose up -d --build

# 4. 清除浏览器缓存（硬刷新）
# 按 Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac)
```

#### 问题 2: 显示 404 错误

**可能原因**:
1. Label Studio 服务未运行
2. 项目 ID 不存在
3. URL 格式错误

**解决方法**:
```bash
# 1. 检查 Label Studio 容器状态
docker ps | grep label-studio

# 2. 检查 Label Studio 日志
docker logs superinsight-label-studio

# 3. 验证项目是否存在
curl -H "Authorization: Token fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8" \
  http://localhost:8080/api/projects/

# 4. 手动访问 URL 测试
# 在浏览器中打开: http://localhost:8080/projects/{projectId}/data
```

#### 问题 3: 需要登录

**可能原因**:
1. Label Studio session 过期
2. 未登录 Label Studio

**解决方法**:
1. 在新标签页中打开 http://localhost:8080
2. 使用以下凭据登录:
   - 邮箱: `admin@example.com`
   - 密码: `admin`
3. 登录成功后，关闭标签页
4. 重新点击"在新窗口中打开"按钮

### 5. 验证清单

完成以下检查以确认问题已解决:

- [ ] 代码中的 URL 包含 `/data` 端点
- [ ] 前端容器已重建
- [ ] 浏览器缓存已清除
- [ ] 点击按钮后打开新窗口
- [ ] 新窗口 URL 包含 `/data`
- [ ] 显示数据管理器界面（任务列表）
- [ ] 可以看到 "Label All Tasks" 按钮
- [ ] 可以点击单个任务进行标注
- [ ] 不显示项目仪表盘

### 6. 成功标准

当您看到以下内容时，说明问题已解决:

1. **URL 正确**
   ```
   http://localhost:8080/projects/{projectId}/data
   ```

2. **界面正确**
   - 顶部有 "Label All Tasks" 按钮
   - 中间显示任务列表
   - 每个任务有复选框
   - 可以点击任务进入标注界面

3. **功能正常**
   - 点击 "Label All Tasks" 可以批量标注
   - 点击单个任务可以进入标注界面
   - 标注后可以保存结果

### 7. 下一步操作

问题解决后，您可以:

1. **开始标注**
   - 点击 "Label All Tasks" 批量标注
   - 或点击单个任务逐个标注

2. **查看进度**
   - 返回 SuperInsight 任务详情页
   - 查看标注进度统计

3. **导出结果**
   - 在 Label Studio 中点击 "Export"
   - 选择导出格式
   - 下载标注结果

## 技术细节

### Label Studio URL 端点说明

| 端点 | 用途 | 显示内容 |
|------|------|----------|
| `/projects/{id}` | 项目仪表盘 | 统计信息、设置、成员管理 |
| `/projects/{id}/data` | 数据管理器 | 任务列表、批量操作 |
| `/projects/{id}/data?task={taskId}` | 特定任务 | 预选特定任务 |
| `/tasks/{taskId}` | 直接标注 | 单个任务标注界面 |

### 为什么不能使用 `/projects/{id}`

Label Studio Community Edition 的项目仪表盘 (`/projects/{id}`) 主要用于:
- 查看项目统计信息
- 管理项目设置
- 管理项目成员
- 配置标注模板

**不适合直接标注**，因为:
- 没有任务列表
- 没有 "Label All Tasks" 按钮
- 需要额外点击才能进入标注界面

### 为什么使用 `/projects/{id}/data`

数据管理器 (`/projects/{id}/data`) 是 Label Studio 的核心工作界面:
- ✅ 显示所有任务列表
- ✅ 提供 "Label All Tasks" 批量标注按钮
- ✅ 可以点击单个任务进行标注
- ✅ 支持任务筛选和排序
- ✅ 支持批量操作（导入、导出、删除）

## 相关文档

- [Label Studio 集成需求文档](.kiro/specs/label-studio-iframe-integration/requirements.md)
- [Label Studio 集成设计文档](.kiro/specs/label-studio-iframe-integration/design.md)
- [Label Studio 集成任务列表](.kiro/specs/label-studio-iframe-integration/tasks.md)
- [Label Studio 官方文档](https://labelstud.io/guide/)

## 联系支持

如果问题仍未解决，请提供以下信息:

1. **浏览器信息**
   - 浏览器类型和版本
   - 是否清除了缓存

2. **容器状态**
   ```bash
   docker ps
   docker logs superinsight-frontend --tail 50
   docker logs superinsight-label-studio --tail 50
   ```

3. **URL 信息**
   - 实际打开的 URL
   - 浏览器地址栏显示的完整 URL

4. **截图**
   - 当前显示的界面截图
   - 浏览器开发者工具 Network 标签截图

---

**最后更新**: 2026-02-03  
**状态**: ✅ 已解决  
**版本**: 1.0
