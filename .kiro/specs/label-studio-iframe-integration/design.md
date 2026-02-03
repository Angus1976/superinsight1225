# Label Studio 集成设计文档

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    SuperInsight Frontend                     │
│                                                              │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │  TaskDetail    │         │  TaskAnnotate    │           │
│  │  任务详情页     │────────▶│  标注页面         │           │
│  └────────────────┘         └──────────────────┘           │
│         │                            │                      │
│         │ "在新窗口中打开"            │ 显示引导界面          │
│         ▼                            ▼                      │
│  ┌──────────────────────────────────────────────┐          │
│  │         window.open()                        │          │
│  │  打开新窗口: /projects/{id}/data             │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP Request
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Label Studio Community Edition                  │
│                                                              │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │  Data Manager  │         │  Annotation UI   │           │
│  │  数据管理器     │────────▶│  标注界面         │           │
│  └────────────────┘         └──────────────────┘           │
│         │                            │                      │
│         │ Session Cookie             │ 保存标注结果          │
│         ▼                            ▼                      │
│  ┌──────────────────────────────────────────────┐          │
│  │         SQLite Database                      │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 组件关系

```
TaskDetail.tsx
├── handleOpenInNewWindow()
│   ├── 检查 label_studio_project_id
│   ├── 如果不存在 → navigate('/tasks/{id}/annotate')
│   └── 如果存在 → window.open('/projects/{id}/data')
│
TaskAnnotate.tsx
├── fetchData()
│   ├── 获取项目信息
│   ├── 如果项目不存在 → 自动创建
│   └── 导入任务数据
├── 显示引导界面 (Result 组件)
│   ├── 说明文字
│   ├── "在新窗口中打开 Label Studio" 按钮
│   └── "返回任务详情" 按钮
│
LabelStudioEmbed.tsx (保留但不使用)
└── iframe 集成代码（未来可能用于 Enterprise Edition）
```

## 2. URL 设计

### 2.1 Label Studio URL 端点

| 端点 | 用途 | 显示内容 | 是否使用 |
|------|------|----------|----------|
| `/projects/{id}` | 项目仪表盘 | 项目概览、统计信息 | ❌ 错误 |
| `/projects/{id}/data` | 数据管理器 | 任务列表、批量标注 | ✅ 正确 |
| `/projects/{id}/data?task={taskId}` | 特定任务 | 预选特定任务 | ✅ 可选 |

### 2.2 URL 构建逻辑

```typescript
// TaskDetail.tsx - handleOpenInNewWindow()
const handleOpenInNewWindow = () => {
  const projectId = task.label_studio_project_id;
  
  if (!projectId) {
    // 项目不存在，跳转到标注页面创建
    message.info('项目尚未创建，正在跳转到标注页面...');
    navigate(`/tasks/${id}/annotate`);
    return;
  }
  
  // 构建 Label Studio URL
  const labelStudioUrl = import.meta.env.VITE_LABEL_STUDIO_URL || 'http://localhost:8080';
  const projectUrl = `${labelStudioUrl}/projects/${projectId}/data`;
  
  // 在新窗口中打开
  window.open(projectUrl, '_blank', 'noopener,noreferrer');
  message.success('已在新窗口中打开 Label Studio 数据管理器');
};
```

```typescript
// TaskAnnotate.tsx - 引导界面按钮
<Button
  type="primary"
  size="large"
  onClick={() => {
    const labelStudioUrl = 'http://localhost:8080';
    const projectUrl = `${labelStudioUrl}/projects/${project.id}/data`;
    window.open(projectUrl, '_blank', 'noopener,noreferrer');
    message.success('已在新窗口中打开 Label Studio');
  }}
>
  在新窗口中打开 Label Studio
</Button>
```

## 3. 认证设计

### 3.1 认证流程

```
┌─────────────────────────────────────────────────────────────┐
│                    用户认证流程                              │
└─────────────────────────────────────────────────────────────┘

1. 用户登录 SuperInsight
   ├── JWT Token 存储在 localStorage
   └── 用于 SuperInsight API 调用

2. 用户首次访问 Label Studio
   ├── 浏览器打开 Label Studio 登录页面
   ├── 用户输入 Label Studio 凭据
   │   ├── 用户名: admin@example.com
   │   └── 密码: admin
   └── Label Studio 创建 session cookie

3. 后续访问 Label Studio
   ├── 浏览器自动发送 session cookie
   ├── Label Studio 验证 session
   └── 直接显示数据管理器

4. SuperInsight 后端 API 调用
   ├── 使用 Personal Access Token
   ├── Header: Authorization: Bearer {token}
   └── Token: fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8
```

### 3.2 认证配置

```env
# .env
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8
```

```yaml
# docker-compose.yml
label-studio:
  environment:
    - LABEL_STUDIO_SSO_ENABLED=false  # 禁用 SSO，启用 legacy token
    - LABEL_STUDIO_USERNAME=admin@example.com
    - LABEL_STUDIO_PASSWORD=admin
```

## 4. 界面设计

### 4.1 引导界面 (TaskAnnotate.tsx)

```typescript
<Result
  icon={<InfoCircleOutlined style={{ color: '#1890ff' }} />}
  title="请在新窗口中进行标注"
  subTitle={
    <div style={{ maxWidth: 600 }}>
      <p>Label Studio Community Edition 需要在独立窗口中使用以获得最佳体验。</p>
      <p style={{ marginTop: 16, fontSize: 14, color: '#666' }}>
        点击下方按钮将在新窗口中打开 Label Studio 数据管理器，您可以在那里：
      </p>
      <ul style={{ textAlign: 'left', display: 'inline-block', marginTop: 8 }}>
        <li>查看所有待标注任务</li>
        <li>点击 "Label All Tasks" 开始批量标注</li>
        <li>或点击单个任务进行标注</li>
        <li>使用完整的键盘快捷键和功能</li>
      </ul>
      <p style={{ marginTop: 16, fontSize: 12, color: '#999' }}>
        当前项目 ID: {project.id} | 当前任务: {currentTaskIndex + 1} / {tasks.length}
      </p>
    </div>
  }
  extra={[
    <Button
      key="open"
      type="primary"
      size="large"
      onClick={() => {
        const labelStudioUrl = 'http://localhost:8080';
        const projectUrl = `${labelStudioUrl}/projects/${project.id}/data`;
        window.open(projectUrl, '_blank', 'noopener,noreferrer');
        message.success('已在新窗口中打开 Label Studio');
      }}
    >
      在新窗口中打开 Label Studio
    </Button>,
    <Button
      key="back"
      onClick={handleBackToTask}
    >
      返回任务详情
    </Button>,
  ]}
/>
```

### 4.2 任务详情页按钮 (TaskDetail.tsx)

```typescript
<Space style={{ marginTop: 12 }}>
  {annotationPerms.canView ? (
    <Button 
      type="primary" 
      size="large"
      icon={<PlayCircleOutlined />}
      onClick={handleStartAnnotation}
    >
      {t('startAnnotation')}
    </Button>
  ) : (
    <Tooltip title={t('noAnnotationPermission')}>
      <Button 
        type="primary" 
        size="large"
        icon={<PlayCircleOutlined />}
        disabled
      >
        {t('startAnnotation')}
      </Button>
    </Tooltip>
  )}
  <Button 
    size="large"
    icon={<ExportOutlined />}
    onClick={handleOpenInNewWindow}
  >
    {t('openInNewWindow')}
  </Button>
</Space>
```

## 5. 错误处理设计

### 5.1 错误类型

| 错误类型 | 触发条件 | 处理方式 |
|---------|---------|---------|
| 项目不存在 | `label_studio_project_id` 为空 | 跳转到标注页面自动创建 |
| Label Studio 服务不可用 | 网络错误或服务停止 | 显示错误提示，提供重试按钮 |
| 认证失败 | Session 过期或未登录 | 提示用户登录 Label Studio |
| 任务导入失败 | API 调用失败 | 显示错误信息，提供重试选项 |

### 5.2 错误处理流程

```typescript
// TaskDetail.tsx
const handleOpenInNewWindow = () => {
  if (!id || !task) {
    message.error('任务数据加载失败，请刷新页面重试');
    return;
  }
  
  const projectId = task.label_studio_project_id;
  
  if (!projectId) {
    // 项目不存在
    message.info('项目尚未创建，正在跳转到标注页面...');
    navigate(`/tasks/${id}/annotate`);
    return;
  }
  
  // 打开新窗口
  const labelStudioUrl = import.meta.env.VITE_LABEL_STUDIO_URL || 'http://localhost:8080';
  const projectUrl = `${labelStudioUrl}/projects/${projectId}/data`;
  window.open(projectUrl, '_blank', 'noopener,noreferrer');
  message.success('已在新窗口中打开 Label Studio 数据管理器');
};
```

```typescript
// TaskAnnotate.tsx
const fetchData = useCallback(async () => {
  try {
    setLoading(true);
    setError(null);
    
    // 获取项目信息
    let projectId = taskDetail?.label_studio_project_id;
    
    // 如果项目不存在，自动创建
    if (!projectId) {
      const ensureResult = await labelStudioService.ensureProject({
        task_id: id,
        task_name: taskDetail?.name || 'Annotation Project',
        annotation_type: taskDetail?.annotation_type || 'text_classification',
      });
      projectId = ensureResult.project_id;
      message.success('项目创建成功');
    }
    
    // 获取任务列表
    const tasksResponse = await apiClient.get(`/api/label-studio/projects/${projectId}/tasks`);
    setTasks(tasksResponse.data.tasks || []);
    
  } catch (err) {
    console.error('Failed to fetch data:', err);
    
    // 根据错误类型显示不同的错误信息
    const axiosError = err as AxiosError;
    const status = axiosError.response?.status;
    
    if (status === 404) {
      setError({
        type: 'not_found',
        message: '项目不存在',
        details: '请点击下方按钮创建项目',
      });
    } else if (status === 401 || status === 403) {
      setError({
        type: 'auth',
        message: '认证失败',
        details: '请先登录 Label Studio',
      });
    } else {
      setError({
        type: 'unknown',
        message: '加载失败',
        details: err instanceof Error ? err.message : undefined,
      });
    }
  } finally {
    setLoading(false);
  }
}, [id, taskDetail]);
```

## 6. 数据流设计

### 6.1 项目创建流程

```
用户点击"开始标注"
    │
    ▼
检查 label_studio_project_id
    │
    ├─ 存在 ──▶ 显示引导界面
    │
    └─ 不存在
        │
        ▼
    调用 labelStudioService.ensureProject()
        │
        ├─ 创建 Label Studio 项目
        ├─ 导入任务数据
        └─ 更新任务的 label_studio_project_id
        │
        ▼
    显示引导界面
```

### 6.2 标注数据同步

```
用户在 Label Studio 中标注
    │
    ▼
Label Studio 保存标注到 SQLite
    │
    ▼
SuperInsight 后端定期同步
    │
    ├─ 调用 Label Studio API
    ├─ 获取标注结果
    └─ 保存到 PostgreSQL
    │
    ▼
更新任务进度和统计信息
```

## 7. 性能优化

### 7.1 缓存策略
- 项目信息缓存 5 分钟
- 任务列表缓存 1 分钟
- 使用 React Query 自动管理缓存

### 7.2 懒加载
- 任务列表分页加载
- 标注结果按需获取
- 图片和文件延迟加载

### 7.3 并发控制
- 限制同时打开的 Label Studio 窗口数量
- 防止重复创建项目
- 使用防抖处理按钮点击

## 8. 安全设计

### 8.1 认证安全
- Personal Access Token 存储在环境变量中
- 不在前端代码中硬编码 token
- Session cookie 使用 HttpOnly 和 Secure 标志

### 8.2 数据安全
- 标注数据加密传输 (HTTPS)
- 敏感信息脱敏处理
- 访问权限控制

### 8.3 XSS 防护
- 使用 `noopener,noreferrer` 打开新窗口
- 验证 URL 参数
- 转义用户输入

## 9. 监控和日志

### 9.1 关键指标
- Label Studio 窗口打开成功率
- 项目创建成功率
- 标注完成率
- 平均标注时间

### 9.2 日志记录
```typescript
console.log('[handleOpenInNewWindow] ========== START ==========');
console.log('[handleOpenInNewWindow] id:', id);
console.log('[handleOpenInNewWindow] task:', task);
console.log('[handleOpenInNewWindow] Opening Label Studio URL:', projectUrl);
console.log('[handleOpenInNewWindow] ========== END ==========');
```

### 9.3 错误追踪
- 捕获所有异常并记录
- 上报到错误监控系统
- 提供详细的错误上下文

## 10. 测试策略

### 10.1 单元测试
- URL 构建逻辑测试
- 错误处理测试
- 权限检查测试

### 10.2 集成测试
- Label Studio API 调用测试
- 项目创建流程测试
- 数据同步测试

### 10.3 E2E 测试
- 完整标注流程测试
- 多窗口场景测试
- 错误恢复测试

## 11. 部署配置

### 11.1 环境变量

```env
# 前端
VITE_LABEL_STUDIO_URL=http://localhost:8080

# 后端
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8
```

### 11.2 Docker 配置

```yaml
label-studio:
  image: heartexlabs/label-studio:latest
  ports:
    - "8080:8080"
  environment:
    - LABEL_STUDIO_HOST=http://localhost:8080
    - LABEL_STUDIO_USERNAME=admin@example.com
    - LABEL_STUDIO_PASSWORD=admin
    - LABEL_STUDIO_SSO_ENABLED=false
  volumes:
    - label_studio_data:/label-studio/data
```

### 11.3 Nginx 反向代理

```nginx
location /label-studio/ {
    proxy_pass http://label-studio:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 12. 任务列表页面设计

### 12.1 刷新功能设计

#### 12.1.1 刷新流程

```
用户点击"刷新"按钮
    │
    ▼
显示刷新选项菜单
    ├─ 刷新任务列表
    └─ 同步所有任务
        │
        ▼
    执行同步流程
        │
        ├─ 1. 获取 Label Studio 项目列表
        │   └─ GET /api/label-studio/projects
        │
        ├─ 2. 对比本地任务
        │   ├─ 找出未同步的项目
        │   └─ 找出需要更新的任务
        │
        ├─ 3. 同步项目信息
        │   ├─ 更新项目名称
        │   ├─ 更新任务数量
        │   └─ 更新标注进度
        │
        ├─ 4. 同步标注结果
        │   ├─ 获取标注数据
        │   ├─ 更新完成数量
        │   └─ 计算进度百分比
        │
        └─ 5. 更新本地数据
            ├─ 更新任务状态
            ├─ 更新同步时间
            └─ 刷新列表显示
```

#### 12.1.2 同步逻辑实现

```typescript
// frontend/src/pages/Tasks/index.tsx

const handleSyncAllTasks = async () => {
  const hide = message.loading('正在同步任务...', 0);
  
  try {
    // 1. 获取 Label Studio 项目列表
    const projectsResponse = await api.get('/api/label-studio/projects');
    const lsProjects = projectsResponse.data.results || [];
    
    // 2. 获取本地任务列表
    const localTasks = data?.items || [];
    
    // 3. 创建项目 ID 映射
    const projectMap = new Map(
      lsProjects.map(p => [p.id, p])
    );
    
    // 4. 同步每个任务
    let successCount = 0;
    let failCount = 0;
    
    for (const task of localTasks) {
      try {
        const projectId = task.label_studio_project_id;
        
        if (!projectId) {
          // 任务没有关联项目，跳过
          continue;
        }
        
        const lsProject = projectMap.get(projectId);
        
        if (!lsProject) {
          // Label Studio 中找不到项目
          console.warn(`Project ${projectId} not found in Label Studio`);
          continue;
        }
        
        // 5. 获取项目的任务列表
        const tasksResponse = await api.get(
          `/api/label-studio/projects/${projectId}/tasks`
        );
        const lsTasks = tasksResponse.data.tasks || [];
        
        // 6. 计算标注进度
        const totalTasks = lsTasks.length;
        const completedTasks = lsTasks.filter(t => t.is_labeled).length;
        const progress = totalTasks > 0 
          ? Math.round((completedTasks / totalTasks) * 100) 
          : 0;
        
        // 7. 更新本地任务
        await api.patch(`/api/tasks/${task.id}`, {
          total_items: totalTasks,
          completed_items: completedTasks,
          progress: progress,
          label_studio_sync_status: 'synced',
          label_studio_last_sync: new Date().toISOString(),
        });
        
        successCount++;
      } catch (error) {
        console.error(`Failed to sync task ${task.id}:`, error);
        failCount++;
      }
    }
    
    hide();
    
    // 8. 显示同步结果
    if (failCount === 0) {
      message.success(`成功同步 ${successCount} 个任务`);
    } else {
      message.warning(
        `同步完成：成功 ${successCount} 个，失败 ${failCount} 个`
      );
    }
    
    // 9. 刷新列表
    refetch();
    
  } catch (error) {
    hide();
    console.error('Sync failed:', error);
    message.error('同步失败，请重试');
  }
};
```

### 12.2 导出功能设计

#### 12.2.1 导出格式支持

| 格式 | 用途 | 包含内容 |
|------|------|----------|
| CSV | 简单数据导出 | 任务基本信息、进度 |
| JSON | 完整数据导出 | 任务信息、标注结果、配置 |
| Excel | 报表导出 | 多 sheet、图表、统计 |

#### 12.2.2 导出实现

```typescript
// CSV 导出
const exportToCSV = (tasks: Task[]) => {
  const headers = [
    'ID', '名称', '状态', '优先级', '标注类型',
    '进度', '完成数', '总数', '分配人', '创建时间', '截止日期'
  ];
  
  const rows = tasks.map(task => [
    task.id,
    task.name,
    task.status,
    task.priority,
    task.annotation_type,
    `${task.progress}%`,
    task.completed_items,
    task.total_items,
    task.assignee_name || '',
    new Date(task.created_at).toLocaleDateString(),
    task.due_date ? new Date(task.due_date).toLocaleDateString() : ''
  ]);
  
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');
  
  downloadFile(csvContent, 'tasks.csv', 'text/csv');
};

// JSON 导出
const exportToJSON = async (tasks: Task[]) => {
  const exportData = await Promise.all(
    tasks.map(async task => {
      // 获取标注结果
      let annotations = [];
      if (task.label_studio_project_id) {
        try {
          const response = await api.get(
            `/api/label-studio/projects/${task.label_studio_project_id}/export`
          );
          annotations = response.data;
        } catch (error) {
          console.error(`Failed to export annotations for task ${task.id}`);
        }
      }
      
      return {
        ...task,
        annotations
      };
    })
  );
  
  const jsonContent = JSON.stringify(exportData, null, 2);
  downloadFile(jsonContent, 'tasks.json', 'application/json');
};

// Excel 导出
const exportToExcel = async (tasks: Task[]) => {
  const XLSX = await import('xlsx');
  
  // Sheet 1: 任务列表
  const taskSheet = XLSX.utils.json_to_sheet(
    tasks.map(task => ({
      'ID': task.id,
      '名称': task.name,
      '状态': task.status,
      '优先级': task.priority,
      '标注类型': task.annotation_type,
      '进度': `${task.progress}%`,
      '完成数': task.completed_items,
      '总数': task.total_items,
      '分配人': task.assignee_name || '',
      '创建时间': new Date(task.created_at).toLocaleDateString(),
      '截止日期': task.due_date ? new Date(task.due_date).toLocaleDateString() : ''
    }))
  );
  
  // Sheet 2: 统计信息
  const statsSheet = XLSX.utils.json_to_sheet([
    { '指标': '总任务数', '数值': tasks.length },
    { '指标': '进行中', '数值': tasks.filter(t => t.status === 'in_progress').length },
    { '指标': '已完成', '数值': tasks.filter(t => t.status === 'completed').length },
    { '指标': '平均进度', '数值': `${Math.round(tasks.reduce((sum, t) => sum + t.progress, 0) / tasks.length)}%` }
  ]);
  
  // 创建工作簿
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, taskSheet, '任务列表');
  XLSX.utils.book_append_sheet(workbook, statsSheet, '统计信息');
  
  // 导出文件
  XLSX.writeFile(workbook, `tasks_${new Date().toISOString().split('T')[0]}.xlsx`);
};
```

### 12.3 创建任务功能设计

#### 12.3.1 创建流程

```
用户点击"创建任务"
    │
    ▼
打开创建对话框
    │
    ├─ 填写任务基本信息
    │   ├─ 任务名称
    │   ├─ 任务描述
    │   ├─ 标注类型
    │   ├─ 优先级
    │   └─ 截止日期
    │
    ├─ 配置标注设置
    │   ├─ 标注模板
    │   ├─ 标签配置
    │   └─ 质量要求
    │
    └─ 导入数据
        ├─ 上传文件
        ├─ 粘贴文本
        └─ 连接数据源
    │
    ▼
提交创建请求
    │
    ├─ 1. 创建本地任务
    │   └─ POST /api/tasks
    │
    ├─ 2. 创建 Label Studio 项目
    │   └─ POST /api/label-studio/projects
    │
    ├─ 3. 导入标注数据
    │   └─ POST /api/label-studio/projects/{id}/import
    │
    └─ 4. 更新任务关联
        └─ PATCH /api/tasks/{id}
    │
    ▼
显示创建成功
刷新任务列表
```

### 12.4 编辑功能设计

#### 12.4.1 编辑界面

```typescript
// 编辑对话框
<Modal
  title="编辑任务"
  open={editModalOpen}
  onOk={handleEditSubmit}
  onCancel={() => setEditModalOpen(false)}
>
  <Form form={editForm} layout="vertical">
    <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    
    <Form.Item name="description" label="任务描述">
      <Input.TextArea rows={4} />
    </Form.Item>
    
    <Form.Item name="status" label="状态">
      <Select>
        <Select.Option value="pending">待处理</Select.Option>
        <Select.Option value="in_progress">进行中</Select.Option>
        <Select.Option value="completed">已完成</Select.Option>
        <Select.Option value="cancelled">已取消</Select.Option>
      </Select>
    </Form.Item>
    
    <Form.Item name="priority" label="优先级">
      <Select>
        <Select.Option value="low">低</Select.Option>
        <Select.Option value="medium">中</Select.Option>
        <Select.Option value="high">高</Select.Option>
        <Select.Option value="urgent">紧急</Select.Option>
      </Select>
    </Form.Item>
    
    <Form.Item name="assignee_id" label="分配给">
      <Select>
        {users.map(user => (
          <Select.Option key={user.id} value={user.id}>
            {user.name}
          </Select.Option>
        ))}
      </Select>
    </Form.Item>
    
    <Form.Item name="due_date" label="截止日期">
      <DatePicker style={{ width: '100%' }} />
    </Form.Item>
  </Form>
</Modal>
```

### 12.5 删除功能设计

#### 12.5.1 删除确认

```typescript
const handleDelete = (task: Task) => {
  modal.confirm({
    title: '确认删除',
    icon: <ExclamationCircleOutlined />,
    content: (
      <div>
        <p>确定要删除任务 <strong>{task.name}</strong> 吗？</p>
        <Alert
          type="warning"
          message="删除后将无法恢复"
          description={
            <div>
              <p>此操作将：</p>
              <ul>
                <li>删除任务记录</li>
                <li>删除关联的标注数据</li>
                {task.label_studio_project_id && (
                  <li>可选：删除 Label Studio 项目</li>
                )}
              </ul>
            </div>
          }
          showIcon
        />
        {task.label_studio_project_id && (
          <Checkbox
            checked={deleteProjectToo}
            onChange={e => setDeleteProjectToo(e.target.checked)}
            style={{ marginTop: 16 }}
          >
            同时删除 Label Studio 项目
          </Checkbox>
        )}
      </div>
    ),
    okText: '确认删除',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      try {
        // 1. 删除本地任务
        await api.delete(`/api/tasks/${task.id}`);
        
        // 2. 可选：删除 Label Studio 项目
        if (deleteProjectToo && task.label_studio_project_id) {
          await api.delete(
            `/api/label-studio/projects/${task.label_studio_project_id}`
          );
        }
        
        message.success('删除成功');
        refetch();
      } catch (error) {
        message.error('删除失败');
      }
    }
  });
};
```

### 12.6 同步状态显示

#### 12.6.1 同步状态图标

```typescript
// 在任务列表中显示同步状态
const SyncStatusBadge: React.FC<{ task: Task }> = ({ task }) => {
  const getStatusConfig = () => {
    switch (task.label_studio_sync_status) {
      case 'synced':
        return {
          status: 'success',
          text: '已同步',
          icon: <CheckCircleOutlined />,
          color: '#52c41a'
        };
      case 'pending':
        return {
          status: 'processing',
          text: '待同步',
          icon: <SyncOutlined />,
          color: '#1890ff'
        };
      case 'failed':
        return {
          status: 'error',
          text: '同步失败',
          icon: <ExclamationCircleOutlined />,
          color: '#ff4d4f'
        };
      default:
        return {
          status: 'default',
          text: '未同步',
          icon: <ClockCircleOutlined />,
          color: '#d9d9d9'
        };
    }
  };
  
  const config = getStatusConfig();
  
  return (
    <Tooltip
      title={
        <div>
          <div>状态: {config.text}</div>
          {task.label_studio_last_sync && (
            <div>
              最后同步: {new Date(task.label_studio_last_sync).toLocaleString()}
            </div>
          )}
        </div>
      }
    >
      <Badge
        status={config.status as any}
        text={config.text}
        style={{ color: config.color }}
      />
    </Tooltip>
  );
};
```

## 13. 未来改进

### 13.1 短期改进 (1-3 个月)
- 添加标注进度实时同步
- 优化错误提示信息
- 增加快捷键支持

### 13.2 中期改进 (3-6 个月)
- 升级到 Label Studio Enterprise Edition
- 实现 iframe 集成
- 添加标注质量监控

### 13.3 长期改进 (6-12 个月)
- 开发自定义标注界面
- 集成更多 AI 辅助功能
- 支持移动端标注


## 13. 国际化（i18n）设计

### 13.1 i18n 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 i18n 架构                            │
│                                                              │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │  i18n Config   │────────▶│  Language Store  │           │
│  │  配置管理       │         │  语言状态管理     │           │
│  └────────────────┘         └──────────────────┘           │
│         │                            │                      │
│         │                            ▼                      │
│         │                   ┌──────────────────┐           │
│         │                   │  Translation     │           │
│         └──────────────────▶│  Files           │           │
│                             │  翻译文件         │           │
│                             └──────────────────┘           │
│                                      │                      │
│                                      ▼                      │
│  ┌──────────────────────────────────────────────┐          │
│  │         React Components                     │          │
│  │  使用 useTranslation() hook                  │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ 语言参数传递
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Label Studio                                    │
│                                                              │
│  URL: /projects/{id}/data?lang={language}                   │
│                                                              │
│  Django i18n 机制自动切换界面语言                            │
└─────────────────────────────────────────────────────────────┘
```

### 13.2 翻译文件结构

#### 13.2.1 文件组织

```
frontend/src/locales/
├── zh/
│   ├── common.json          # 通用翻译
│   ├── tasks.json           # 任务相关翻译 ⭐ 新增
│   ├── admin.json           # 管理后台翻译
│   └── errors.json          # 错误消息翻译
└── en/
    ├── common.json
    ├── tasks.json           # 任务相关翻译 ⭐ 新增
    ├── admin.json
    └── errors.json
```

#### 13.2.2 tasks.json 翻译键设计

**中文翻译文件** (`frontend/src/locales/zh/tasks.json`):

```json
{
  "tasks": {
    "title": "标注任务",
    "list": {
      "title": "任务列表",
      "refresh": "刷新",
      "refreshList": "刷新列表",
      "syncAllTasks": "同步所有任务",
      "export": "导出数据",
      "create": "创建任务",
      "edit": "编辑",
      "delete": "删除",
      "batchDelete": "批量删除",
      "selectAll": "全选",
      "deselectAll": "取消全选"
    },
    "status": {
      "pending": "待处理",
      "inProgress": "进行中",
      "completed": "已完成",
      "cancelled": "已取消"
    },
    "priority": {
      "low": "低",
      "medium": "中",
      "high": "高",
      "urgent": "紧急"
    },
    "columns": {
      "id": "ID",
      "name": "任务名称",
      "status": "状态",
      "priority": "优先级",
      "annotationType": "标注类型",
      "progress": "进度",
      "completedItems": "完成数",
      "totalItems": "总数",
      "assignee": "分配人",
      "createdAt": "创建时间",
      "dueDate": "截止日期",
      "actions": "操作"
    },
    "actions": {
      "view": "查看",
      "edit": "编辑",
      "delete": "删除",
      "startAnnotation": "开始标注",
      "openInNewWindow": "在新窗口中打开"
    },
    "messages": {
      "syncSuccess": "成功同步 {count} 个任务",
      "syncFailed": "同步失败，请重试",
      "syncPartial": "同步完成：成功 {success} 个，失败 {failed} 个",
      "exportSuccess": "导出成功",
      "exportFailed": "导出失败",
      "deleteConfirm": "确定要删除任务 {name} 吗？",
      "deleteSuccess": "删除成功",
      "deleteFailed": "删除失败",
      "noTasksToSync": "没有需要同步的任务",
      "noTasksToExport": "没有可导出的任务"
    },
    "export": {
      "title": "导出任务",
      "selectFormat": "选择导出格式:",
      "csv": "CSV (简单数据)",
      "json": "JSON (完整数据)",
      "excel": "Excel (报表)",
      "includeAnnotations": "包含标注结果",
      "exporting": "正在导出..."
    },
    "sync": {
      "title": "同步进度",
      "syncing": "正在同步任务 {current} / {total}",
      "completed": "同步完成",
      "success": "成功",
      "failed": "失败",
      "failedTasks": "失败的任务:"
    },
    "annotate": {
      "title": "请在新窗口中进行标注",
      "description": "Label Studio Community Edition 需要在独立窗口中使用以获得最佳体验。",
      "instructions": "点击下方按钮将在新窗口中打开 Label Studio 数据管理器，您可以在那里：",
      "features": {
        "viewTasks": "查看所有待标注任务",
        "labelAll": "点击 \"Label All Tasks\" 开始批量标注",
        "labelSingle": "或点击单个任务进行标注",
        "shortcuts": "使用完整的键盘快捷键和功能"
      },
      "projectInfo": "当前项目 ID: {projectId} | 当前任务: {current} / {total}",
      "openLabelStudio": "在新窗口中打开 Label Studio",
      "backToTask": "返回任务详情",
      "openSuccess": "已在新窗口中打开 Label Studio"
    }
  }
}
```

**英文翻译文件** (`frontend/src/locales/en/tasks.json`):

```json
{
  "tasks": {
    "title": "Annotation Tasks",
    "list": {
      "title": "Task List",
      "refresh": "Refresh",
      "refreshList": "Refresh List",
      "syncAllTasks": "Sync All Tasks",
      "export": "Export Data",
      "create": "Create Task",
      "edit": "Edit",
      "delete": "Delete",
      "batchDelete": "Batch Delete",
      "selectAll": "Select All",
      "deselectAll": "Deselect All"
    },
    "status": {
      "pending": "Pending",
      "inProgress": "In Progress",
      "completed": "Completed",
      "cancelled": "Cancelled"
    },
    "priority": {
      "low": "Low",
      "medium": "Medium",
      "high": "High",
      "urgent": "Urgent"
    },
    "columns": {
      "id": "ID",
      "name": "Task Name",
      "status": "Status",
      "priority": "Priority",
      "annotationType": "Annotation Type",
      "progress": "Progress",
      "completedItems": "Completed",
      "totalItems": "Total",
      "assignee": "Assignee",
      "createdAt": "Created At",
      "dueDate": "Due Date",
      "actions": "Actions"
    },
    "actions": {
      "view": "View",
      "edit": "Edit",
      "delete": "Delete",
      "startAnnotation": "Start Annotation",
      "openInNewWindow": "Open in New Window"
    },
    "messages": {
      "syncSuccess": "Successfully synced {count} tasks",
      "syncFailed": "Sync failed, please try again",
      "syncPartial": "Sync completed: {success} succeeded, {failed} failed",
      "exportSuccess": "Export successful",
      "exportFailed": "Export failed",
      "deleteConfirm": "Are you sure you want to delete task {name}?",
      "deleteSuccess": "Delete successful",
      "deleteFailed": "Delete failed",
      "noTasksToSync": "No tasks to sync",
      "noTasksToExport": "No tasks to export"
    },
    "export": {
      "title": "Export Tasks",
      "selectFormat": "Select export format:",
      "csv": "CSV (Simple Data)",
      "json": "JSON (Complete Data)",
      "excel": "Excel (Report)",
      "includeAnnotations": "Include Annotations",
      "exporting": "Exporting..."
    },
    "sync": {
      "title": "Sync Progress",
      "syncing": "Syncing task {current} / {total}",
      "completed": "Sync Completed",
      "success": "Success",
      "failed": "Failed",
      "failedTasks": "Failed tasks:"
    },
    "annotate": {
      "title": "Please Annotate in New Window",
      "description": "Label Studio Community Edition requires a separate window for the best experience.",
      "instructions": "Click the button below to open Label Studio Data Manager in a new window, where you can:",
      "features": {
        "viewTasks": "View all pending annotation tasks",
        "labelAll": "Click \"Label All Tasks\" to start batch annotation",
        "labelSingle": "Or click individual tasks to annotate",
        "shortcuts": "Use full keyboard shortcuts and features"
      },
      "projectInfo": "Current Project ID: {projectId} | Current Task: {current} / {total}",
      "openLabelStudio": "Open Label Studio in New Window",
      "backToTask": "Back to Task Details",
      "openSuccess": "Label Studio opened in new window"
    }
  }
}
```

### 13.3 i18n 配置

#### 13.3.1 默认语言设置

```typescript
// frontend/src/i18n/config.ts

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// 导入翻译文件
import zhCommon from '@/locales/zh/common.json';
import zhTasks from '@/locales/zh/tasks.json';
import zhAdmin from '@/locales/zh/admin.json';
import zhErrors from '@/locales/zh/errors.json';

import enCommon from '@/locales/en/common.json';
import enTasks from '@/locales/en/tasks.json';
import enAdmin from '@/locales/en/admin.json';
import enErrors from '@/locales/en/errors.json';

const resources = {
  zh: {
    common: zhCommon,
    tasks: zhTasks,
    admin: zhAdmin,
    errors: zhErrors,
  },
  en: {
    common: enCommon,
    tasks: enTasks,
    admin: enAdmin,
    errors: enErrors,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    lng: 'zh', // ⭐ 默认中文
    fallbackLng: 'zh', // ⭐ 回退到中文
    defaultNS: 'common',
    ns: ['common', 'tasks', 'admin', 'errors'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
  });

export default i18n;
```

#### 13.3.2 Label Studio 语言同步

```typescript
// frontend/src/utils/labelStudioUrl.ts

import { useTranslation } from 'react-i18next';

export const useLabelStudioUrl = () => {
  const { i18n } = useTranslation();
  
  const buildLabelStudioUrl = (projectId: number, taskId?: number) => {
    const baseUrl = import.meta.env.VITE_LABEL_STUDIO_URL || 'http://localhost:8080';
    
    // 映射前端语言到 Label Studio 语言代码
    const languageMap: Record<string, string> = {
      'zh': 'zh-cn',  // 中文简体
      'en': 'en',     // 英文
    };
    
    const language = languageMap[i18n.language] || 'zh-cn';
    
    // 构建 URL
    let url = `${baseUrl}/projects/${projectId}/data`;
    
    // 添加语言参数
    url += `?lang=${language}`;
    
    // 可选：添加任务 ID
    if (taskId) {
      url += `&task=${taskId}`;
    }
    
    return url;
  };
  
  return { buildLabelStudioUrl };
};
```

### 13.4 组件国际化示例

#### 13.4.1 任务列表页面

```typescript
// frontend/src/pages/Tasks/index.tsx

import { useTranslation } from 'react-i18next';

const TaskList: React.FC = () => {
  const { t } = useTranslation('tasks');
  
  // 使用翻译键
  const columns: ProColumns<Task>[] = [
    {
      title: t('columns.name'),
      dataIndex: 'name',
    },
    {
      title: t('columns.status'),
      dataIndex: 'status',
      render: (status: string) => t(`status.${status}`),
    },
    // ...
  ];
  
  return (
    <ProTable
      headerTitle={t('list.title')}
      columns={columns}
      // ...
    />
  );
};
```

#### 13.4.2 标注页面

```typescript
// frontend/src/pages/Tasks/TaskAnnotate.tsx

import { useTranslation } from 'react-i18next';
import { useLabelStudioUrl } from '@/utils/labelStudioUrl';

const TaskAnnotate: React.FC = () => {
  const { t } = useTranslation('tasks');
  const { buildLabelStudioUrl } = useLabelStudioUrl();
  
  return (
    <Result
      title={t('annotate.title')}
      subTitle={t('annotate.description')}
      extra={[
        <Button
          key="open"
          type="primary"
          onClick={() => {
            const url = buildLabelStudioUrl(project.id);
            window.open(url, '_blank', 'noopener,noreferrer');
            message.success(t('annotate.openSuccess'));
          }}
        >
          {t('annotate.openLabelStudio')}
        </Button>,
      ]}
    />
  );
};
```

### 13.5 测试策略

#### 13.5.1 翻译键一致性测试

```typescript
// frontend/src/__tests__/i18n.test.ts

import zhTasks from '@/locales/zh/tasks.json';
import enTasks from '@/locales/en/tasks.json';

describe('i18n Translation Keys', () => {
  it('should have matching keys in zh and en', () => {
    const zhKeys = JSON.stringify(Object.keys(zhTasks.tasks).sort());
    const enKeys = JSON.stringify(Object.keys(enTasks.tasks).sort());
    
    expect(zhKeys).toEqual(enKeys);
  });
});
```

#### 13.5.2 Label Studio URL 测试

```typescript
// frontend/src/__tests__/labelStudioUrl.test.ts

import { renderHook } from '@testing-library/react';
import { useLabelStudioUrl } from '@/utils/labelStudioUrl';
import i18n from '@/i18n/config';

describe('Label Studio URL Builder', () => {
  it('should include language parameter', () => {
    i18n.changeLanguage('zh');
    
    const { result } = renderHook(() => useLabelStudioUrl());
    const url = result.current.buildLabelStudioUrl(123);
    
    expect(url).toContain('lang=zh-cn');
  });
});
```
