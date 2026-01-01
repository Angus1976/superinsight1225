# SuperInsight Frontend - 开发者指南

## 1. 项目概述

SuperInsight 企业级管理前端是一个基于 React 18 + TypeScript + Vite 构建的现代化 Web 应用，用于管理数据标注任务、账单结算、质量监控等企业级功能。

### 1.1 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.x | UI 框架 |
| TypeScript | 5.x | 类型系统 |
| Vite | 7.x | 构建工具 |
| Ant Design | 5.x | UI 组件库 |
| Zustand | 5.x | 状态管理 |
| TanStack Query | 5.x | 数据获取 |
| React Router | 7.x | 路由管理 |
| i18next | 25.x | 国际化 |
| Vitest | 1.x | 单元测试 |
| Playwright | 1.x | E2E 测试 |

## 2. 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── components/         # 通用组件
│   │   ├── Auth/          # 认证相关组件
│   │   ├── Billing/       # 账单管理组件
│   │   ├── Common/        # 通用组件
│   │   ├── Dashboard/     # 仪表盘组件
│   │   ├── LabelStudio/   # Label Studio 集成
│   │   └── Layout/        # 布局组件
│   ├── pages/             # 页面组件
│   │   ├── Admin/         # 管理员页面
│   │   ├── Augmentation/  # 数据增强页面
│   │   ├── Billing/       # 账单页面
│   │   ├── Dashboard/     # 仪表盘页面
│   │   ├── Error/         # 错误页面
│   │   ├── Login/         # 登录页面
│   │   ├── Quality/       # 质量管理页面
│   │   ├── Register/      # 注册页面
│   │   ├── Security/      # 安全审计页面
│   │   ├── Settings/      # 设置页面
│   │   └── Tasks/         # 任务管理页面
│   ├── hooks/             # 自定义 Hooks
│   ├── stores/            # Zustand 状态管理
│   ├── services/          # API 服务
│   ├── types/             # TypeScript 类型定义
│   ├── constants/         # 常量定义
│   ├── utils/             # 工具函数
│   ├── locales/           # 国际化文件
│   ├── styles/            # 样式文件
│   ├── router/            # 路由配置
│   ├── test/              # 测试工具
│   ├── App.tsx            # 应用入口
│   └── main.tsx           # 主入口
├── e2e/                   # E2E 测试
├── vitest.config.ts       # Vitest 配置
├── playwright.config.ts   # Playwright 配置
├── vite.config.ts         # Vite 配置
├── tsconfig.json          # TypeScript 配置
└── package.json           # 项目配置
```

## 3. 快速开始

### 3.1 环境要求

- Node.js 18+
- npm 或 yarn
- 现代浏览器（Chrome 90+, Firefox 88+, Safari 14+）

### 3.2 安装依赖

```bash
cd frontend
npm install
```

### 3.3 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 3.4 构建生产版本

```bash
npm run build
```

### 3.5 运行测试

```bash
# 单元测试
npm run test

# 单元测试（带 UI）
npm run test:ui

# 单元测试覆盖率
npm run test:coverage

# E2E 测试
npm run test:e2e

# E2E 测试（带 UI）
npm run test:e2e:ui
```

## 4. 开发规范

### 4.1 代码风格

- 使用 TypeScript 进行类型检查
- 遵循 ESLint 规则
- 使用函数式组件和 Hooks
- 组件文件使用 PascalCase 命名

### 4.2 组件开发

```tsx
// 组件示例
import { FC, useState } from 'react';
import { Button } from 'antd';

interface MyComponentProps {
  title: string;
  onAction?: () => void;
}

export const MyComponent: FC<MyComponentProps> = ({ title, onAction }) => {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await onAction?.();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>{title}</h1>
      <Button loading={loading} onClick={handleClick}>
        执行
      </Button>
    </div>
  );
};
```

### 4.3 状态管理

使用 Zustand 进行状态管理：

```typescript
// stores/myStore.ts
import { create } from 'zustand';

interface MyState {
  count: number;
  increment: () => void;
  reset: () => void;
}

export const useMyStore = create<MyState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  reset: () => set({ count: 0 }),
}));
```

### 4.4 数据获取

使用 TanStack Query 进行数据获取：

```typescript
// hooks/useMyData.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { myService } from '@/services/myService';

export const useMyData = (id: string) => {
  return useQuery({
    queryKey: ['myData', id],
    queryFn: () => myService.getData(id),
  });
};

export const useUpdateMyData = () => {
  return useMutation({
    mutationFn: myService.updateData,
    onSuccess: () => {
      // 刷新相关查询
    },
  });
};
```

### 4.5 路由配置

```tsx
// router/routes.tsx
import { lazy } from 'react';

const MyPage = lazy(() => import('@/pages/MyPage'));

export const routes = [
  {
    path: '/my-page',
    element: <MyPage />,
    meta: {
      title: '我的页面',
      requiresAuth: true,
    },
  },
];
```

## 5. 测试指南

### 5.1 单元测试

使用 Vitest + React Testing Library：

```tsx
// components/MyComponent/__tests__/MyComponent.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import { MyComponent } from '../MyComponent';

describe('MyComponent', () => {
  it('renders title correctly', () => {
    render(<MyComponent title="测试标题" />);
    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });

  it('calls onAction when button is clicked', async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();

    render(<MyComponent title="测试" onAction={onAction} />);

    await user.click(screen.getByRole('button', { name: '执行' }));

    expect(onAction).toHaveBeenCalled();
  });
});
```

### 5.2 E2E 测试

使用 Playwright：

```typescript
// e2e/my-feature.spec.ts
import { test, expect } from '@playwright/test';

test.describe('My Feature', () => {
  test('should display correctly', async ({ page }) => {
    await page.goto('/my-page');
    await expect(page.getByRole('heading')).toBeVisible();
  });

  test('should handle user interaction', async ({ page }) => {
    await page.goto('/my-page');
    await page.getByRole('button', { name: '执行' }).click();
    await expect(page.getByText('成功')).toBeVisible();
  });
});
```

## 6. API 集成

### 6.1 API 服务

```typescript
// services/api.ts
import axios from 'axios';
import { getToken } from '@/utils/token';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 处理未授权
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 6.2 服务模块

```typescript
// services/taskService.ts
import api from './api';
import type { Task, CreateTaskDto } from '@/types';

export const taskService = {
  getTasks: async (): Promise<Task[]> => {
    const { data } = await api.get('/tasks');
    return data;
  },

  createTask: async (dto: CreateTaskDto): Promise<Task> => {
    const { data } = await api.post('/tasks', dto);
    return data;
  },
};
```

## 7. 国际化

### 7.1 添加翻译

```json
// locales/zh-CN/common.json
{
  "welcome": "欢迎",
  "logout": "退出登录",
  "save": "保存",
  "cancel": "取消"
}
```

### 7.2 使用翻译

```tsx
import { useTranslation } from 'react-i18next';

export const MyComponent = () => {
  const { t } = useTranslation('common');

  return (
    <div>
      <h1>{t('welcome')}</h1>
      <Button>{t('save')}</Button>
    </div>
  );
};
```

## 8. 主题定制

### 8.1 Ant Design 主题

```typescript
// styles/theme.ts
export const lightTheme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

export const darkTheme = {
  token: {
    colorPrimary: '#177ddc',
    colorBgContainer: '#141414',
  },
  algorithm: theme.darkAlgorithm,
};
```

### 8.2 使用主题

```tsx
import { ConfigProvider, theme } from 'antd';
import { lightTheme, darkTheme } from '@/styles/theme';

export const App = () => {
  const [isDark, setIsDark] = useState(false);

  return (
    <ConfigProvider theme={isDark ? darkTheme : lightTheme}>
      {/* 应用内容 */}
    </ConfigProvider>
  );
};
```

## 9. 性能优化

### 9.1 代码分割

路由级别的代码分割已自动配置：

```tsx
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Tasks = lazy(() => import('@/pages/Tasks'));
```

### 9.2 性能监控

```typescript
// 使用 Web Vitals
import { onCLS, onFID, onLCP } from 'web-vitals';

onCLS(console.log);
onFID(console.log);
onLCP(console.log);
```

## 10. 部署

### 10.1 构建

```bash
npm run build
```

生成的文件在 `dist/` 目录。

### 10.2 Nginx 配置

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/frontend/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
    }
}
```

### 10.3 Docker 部署

```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## 11. 常见问题

### Q1: 如何添加新页面？

1. 在 `src/pages/` 创建页面组件
2. 在 `src/router/routes.tsx` 添加路由配置
3. 在 `src/locales/` 添加翻译

### Q2: 如何处理 API 错误？

使用 TanStack Query 的 `onError` 回调：

```typescript
const { mutate } = useMutation({
  mutationFn: myService.update,
  onError: (error) => {
    message.error(error.message);
  },
});
```

### Q3: 如何添加权限控制？

使用 `PermissionGuard` 组件：

```tsx
<PermissionGuard permission="admin:read">
  <AdminPanel />
</PermissionGuard>
```

---

*本文档最后更新: 2025-01-01*
