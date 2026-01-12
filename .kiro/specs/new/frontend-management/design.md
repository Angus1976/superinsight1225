# Design Document

## Overview

独立前端管理后台为SuperInsight 2.3提供现代化的React 18 + Ant Design Pro管理界面。系统基于现有前端架构扩展，提供租户/工作空间管理、综合仪表盘、任务管理和Label Studio集成，确保企业级用户体验和功能完整性。

## Architecture Design

### System Architecture

```
Frontend Management System
├── Authentication & Authorization
│   ├── Multi-Tenant Login
│   ├── Workspace Switcher
│   └── Permission Guard
├── Dashboard & Analytics
│   ├── Overview Dashboard
│   ├── Quality Reports
│   └── Progress Monitoring
├── Task Management
│   ├── Task Creator
│   ├── Assignment System
│   └── Review Workflow
├── Label Studio Integration
│   ├── Iframe Embedding
│   ├── Project Sync
│   └── User Management
└── System Administration
    ├── User Management
    ├── Tenant Configuration
    └── System Settings
```

### Component Architecture

```typescript
interface FrontendManagementSystem {
  authModule: AuthenticationModule;
  dashboardModule: DashboardModule;
  taskModule: TaskManagementModule;
  labelStudioModule: LabelStudioModule;
  adminModule: AdministrationModule;
}

interface AuthenticationModule {
  login(credentials: LoginCredentials): Promise<AuthResult>;
  switchTenant(tenantId: string): Promise<void>;
  switchWorkspace(workspaceId: string): Promise<void>;
  checkPermission(resource: string, action: string): Promise<boolean>;
}
```
## Data Models

### Frontend State Models

```typescript
interface AppState {
  auth: AuthState;
  tenant: TenantState;
  workspace: WorkspaceState;
  dashboard: DashboardState;
  tasks: TaskState;
  labelStudio: LabelStudioState;
}

interface AuthState {
  user: User | null;
  token: string | null;
  permissions: Permission[];
  isAuthenticated: boolean;
  currentTenant: Tenant | null;
  currentWorkspace: Workspace | null;
}

interface DashboardState {
  overview: OverviewData;
  qualityMetrics: QualityMetrics;
  progressData: ProgressData;
  alerts: Alert[];
  isLoading: boolean;
}

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  filters: TaskFilters;
  pagination: PaginationState;
  isLoading: boolean;
}
```

### UI Component Models

```typescript
interface DashboardCard {
  id: string;
  title: string;
  value: number | string;
  trend: TrendData;
  icon: string;
  color: string;
  action?: CardAction;
}

interface TaskListItem {
  id: string;
  name: string;
  status: TaskStatus;
  assignee: User;
  progress: number;
  dueDate: Date;
  priority: Priority;
  tags: string[];
}

interface LabelStudioConfig {
  projectId: string;
  embedUrl: string;
  authToken: string;
  permissions: LabelStudioPermission[];
}
```

## Implementation Strategy

### Phase 1: 基于现有前端架构扩展

#### 扩展现有React 18架构
```typescript
// 基于现有 frontend/src/ 架构
// 扩展现有组件和页面结构

// frontend/src/pages/Dashboard/
// 基于现有Dashboard组件扩展
import { DashboardPage } from '@/pages/Dashboard';

const EnhancedDashboard: React.FC = () => {
  // 保持现有Dashboard逻辑
  // 添加多租户和工作空间支持
  const { currentTenant, currentWorkspace } = useAuth();
  const dashboardData = useDashboardData(currentTenant?.id, currentWorkspace?.id);
  
  return (
    <DashboardPage
      data={dashboardData}
      tenant={currentTenant}
      workspace={currentWorkspace}
    />
  );
};
```

#### 扩展现有状态管理
```typescript
// 扩展现有状态管理 (基于现有store架构)
// frontend/src/stores/authStore.ts
import { create } from 'zustand';

interface AuthStore extends BaseAuthStore {
  // 保持现有认证状态
  currentTenant: Tenant | null;
  currentWorkspace: Workspace | null;
  
  // 扩展租户和工作空间管理
  switchTenant: (tenantId: string) => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  getUserPermissions: () => Permission[];
}

const useAuthStore = create<AuthStore>((set, get) => ({
  // 保持现有状态逻辑
  ...baseAuthStore,
  
  // 新增租户切换功能
  switchTenant: async (tenantId: string) => {
    const response = await api.post('/auth/switch-tenant', { tenantId });
    set({ 
      currentTenant: response.data.tenant,
      currentWorkspace: response.data.defaultWorkspace 
    });
  },
  
  switchWorkspace: async (workspaceId: string) => {
    const response = await api.post('/auth/switch-workspace', { workspaceId });
    set({ currentWorkspace: response.data.workspace });
  }
}));
```

### Phase 2: 组件库扩展

#### 扩展现有Ant Design Pro组件
```typescript
// 基于现有组件库扩展
// frontend/src/components/TenantSwitcher/
import { Select } from 'antd';
import { useAuthStore } from '@/stores/authStore';

const TenantSwitcher: React.FC = () => {
  const { currentTenant, availableTenants, switchTenant } = useAuthStore();
  
  return (
    <Select
      value={currentTenant?.id}
      onChange={switchTenant}
      placeholder="选择租户"
    >
      {availableTenants.map(tenant => (
        <Select.Option key={tenant.id} value={tenant.id}>
          {tenant.name}
        </Select.Option>
      ))}
    </Select>
  );
};

// frontend/src/components/WorkspaceSwitcher/
const WorkspaceSwitcher: React.FC = () => {
  const { currentWorkspace, availableWorkspaces, switchWorkspace } = useAuthStore();
  
  return (
    <Select
      value={currentWorkspace?.id}
      onChange={switchWorkspace}
      placeholder="选择工作空间"
    >
      {availableWorkspaces.map(workspace => (
        <Select.Option key={workspace.id} value={workspace.id}>
          {workspace.name}
        </Select.Option>
      ))}
    </Select>
  );
};
```

#### 扩展现有仪表盘组件
```typescript
// 扩展现有仪表盘组件
// frontend/src/components/Dashboard/
import { Card, Row, Col, Statistic } from 'antd';
import { useQuery } from '@tanstack/react-query';

const OverviewCards: React.FC = () => {
  const { currentTenant, currentWorkspace } = useAuthStore();
  
  const { data: overview } = useQuery({
    queryKey: ['dashboard-overview', currentTenant?.id, currentWorkspace?.id],
    queryFn: () => api.get('/dashboard/overview'),
    enabled: !!currentTenant && !!currentWorkspace
  });
  
  return (
    <Row gutter={[16, 16]}>
      <Col span={6}>
        <Card>
          <Statistic
            title="总任务数"
            value={overview?.totalTasks || 0}
            prefix={<TaskIcon />}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="完成率"
            value={overview?.completionRate || 0}
            suffix="%"
            prefix={<ProgressIcon />}
          />
        </Card>
      </Col>
      {/* 更多统计卡片 */}
    </Row>
  );
};
```

### Phase 3: Label Studio集成

#### 基于现有iframe实现扩展
```typescript
// 扩展现有Label Studio集成
// frontend/src/components/LabelStudio/
import { useEffect, useRef } from 'react';

const LabelStudioEmbed: React.FC<LabelStudioEmbedProps> = ({
  projectId,
  taskId,
  onComplete,
  onSkip
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const { currentWorkspace } = useAuthStore();
  
  // 基于现有iframe集成逻辑
  const embedUrl = useMemo(() => {
    return `${LABEL_STUDIO_URL}/projects/${projectId}/data/${taskId}?token=${authToken}`;
  }, [projectId, taskId]);
  
  useEffect(() => {
    // 基于现有消息监听逻辑
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== LABEL_STUDIO_URL) return;
      
      switch (event.data.type) {
        case 'annotation_completed':
          onComplete?.(event.data.annotation);
          break;
        case 'task_skipped':
          onSkip?.(event.data.taskId);
          break;
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onComplete, onSkip]);
  
  return (
    <iframe
      ref={iframeRef}
      src={embedUrl}
      width="100%"
      height="600px"
      frameBorder="0"
      sandbox="allow-scripts allow-same-origin allow-forms"
    />
  );
};
```

#### 任务管理集成
```typescript
// frontend/src/pages/Tasks/TaskDetail.tsx
const TaskDetail: React.FC = () => {
  const { taskId } = useParams();
  const { data: task } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => api.get(`/tasks/${taskId}`)
  });
  
  const handleAnnotationComplete = async (annotation: Annotation) => {
    // 更新任务状态
    await api.post(`/tasks/${taskId}/annotations`, annotation);
    
    // 刷新任务数据
    queryClient.invalidateQueries(['task', taskId]);
    
    // 显示成功消息
    message.success('标注已保存');
  };
  
  return (
    <div className="task-detail">
      <Card title={task?.name} extra={<TaskActions task={task} />}>
        <LabelStudioEmbed
          projectId={task?.labelStudioProjectId}
          taskId={taskId}
          onComplete={handleAnnotationComplete}
        />
      </Card>
    </div>
  );
};
```

## Performance Optimization

### Code Splitting and Lazy Loading
```typescript
// 基于现有代码分割策略
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';

// 懒加载页面组件
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const TaskManagement = lazy(() => import('@/pages/Tasks'));
const LabelStudio = lazy(() => import('@/pages/LabelStudio'));

const AppRouter: React.FC = () => {
  return (
    <Suspense fallback={<Spin size="large" />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tasks" element={<TaskManagement />} />
        <Route path="/label-studio" element={<LabelStudio />} />
      </Routes>
    </Suspense>
  );
};
```

### State Management Optimization
```typescript
// 优化状态管理性能
import { useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';

const TaskList: React.FC = () => {
  // 使用shallow比较避免不必要的重渲染
  const { tasks, filters, isLoading } = useTaskStore(
    useShallow(state => ({
      tasks: state.tasks,
      filters: state.filters,
      isLoading: state.isLoading
    }))
  );
  
  // 使用useMemo优化过滤逻辑
  const filteredTasks = useMemo(() => {
    return tasks.filter(task => {
      if (filters.status && task.status !== filters.status) return false;
      if (filters.assignee && task.assignee.id !== filters.assignee) return false;
      return true;
    });
  }, [tasks, filters]);
  
  return (
    <List
      loading={isLoading}
      dataSource={filteredTasks}
      renderItem={task => <TaskListItem task={task} />}
    />
  );
};
```

This comprehensive design provides a modern, scalable frontend management system for SuperInsight 2.3, building upon the existing React 18 + Ant Design Pro architecture while adding enterprise-level features and Label Studio integration.