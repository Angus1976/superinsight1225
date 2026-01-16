# SuperInsight 国际化 (i18n) 开发指南

## 概述

SuperInsight 平台使用 [react-i18next](https://react.i18next.com/) 实现国际化支持，目前支持中文（zh）和英文（en）两种语言。本文档提供了国际化开发的完整指南，确保所有新增或修改的页面都能正确支持多语言切换。

## 技术栈

- **核心库**: react-i18next
- **语言检测**: i18next-browser-languagedetector
- **状态管理**: Zustand (languageStore)
- **默认语言**: 中文 (zh)
- **支持语言**: 中文 (zh), 英文 (en)

## 目录结构

```
frontend/src/locales/
├── config.ts              # i18n 配置文件
├── zh/                    # 中文翻译文件
│   ├── common.json        # 通用翻译
│   ├── auth.json          # 认证相关
│   ├── tasks.json         # 任务管理
│   ├── billing.json       # 账单管理
│   ├── quality.json       # 质量管理
│   ├── security.json      # 安全管理
│   ├── admin.json         # 管理控制台
│   ├── workspace.json     # 工作空间
│   ├── dashboard.json     # 仪表盘
│   ├── dataSync.json      # 数据同步
│   ├── license.json       # 许可证管理
│   ├── settings.json      # 系统设置
│   ├── collaboration.json # 协作功能
│   ├── crowdsource.json   # 众包管理
│   ├── augmentation.json  # 数据增强
│   ├── versioning.json    # 版本管理
│   ├── lineage.json       # 数据血缘
│   ├── impact.json        # 影响分析
│   ├── snapshot.json      # 快照管理
│   ├── system.json        # 系统配置
│   ├── businessLogic.json # 业务逻辑
│   └── annotation.json    # 标注相关
└── en/                    # 英文翻译文件
    └── (与 zh/ 目录结构相同)
```

## 命名空间说明

| 命名空间 | 用途 | 示例键 |
|---------|------|--------|
| `common` | 通用文本、菜单、操作按钮 | `actions.submit`, `status.loading` |
| `auth` | 登录、注册、密码重置 | `login.appName`, `register.title` |
| `tasks` | 任务管理、标注、审核 | `statusPending`, `ai.preAnnotationResults` |
| `billing` | 账单、工时、计费规则 | `workHours.report.title`, `ruleConfig.modes.perItem` |
| `quality` | 质量管理、改进任务、报告 | `improvementTask.status.pending`, `reports.types.daily` |
| `security` | 权限、角色、审计、会话 | `permissions.columns.name`, `audit.actions.login` |
| `admin` | 管理控制台、系统配置 | `console.title`, `llm.providers.qwen` |
| `workspace` | 工作空间管理 | `createSuccess`, `fields.name` |
| `dashboard` | 仪表盘统计 | `stats.totalTasks`, `charts.taskTrend` |
| `dataSync` | 数据同步、导出、调度 | `export.title`, `scheduler.frequency.daily` |
| `license` | 许可证管理 | `activation.title`, `usage.current` |
| `settings` | 系统设置 | `profile.title`, `notifications.email` |
| `collaboration` | 协作功能 | `status.pending`, `review.approved` |
| `crowdsource` | 众包管理 | `annotatorStatus.active`, `platform.title` |
| `augmentation` | 数据增强 | `strategy.backTranslation`, `status.running` |
| `versioning` | 版本管理 | `timeline.title`, `diff.added` |
| `lineage` | 数据血缘 | `graph.title`, `node.source` |
| `impact` | 影响分析 | `analysis.title`, `scope.downstream` |
| `snapshot` | 快照管理 | `create.title`, `restore.confirm` |
| `system` | 系统配置 | `health.status`, `config.database` |
| `businessLogic` | 业务逻辑规则 | `ruleType.sentiment`, `validation.required` |
| `annotation` | 标注相关 | `label.add`, `entity.type` |

## 基本用法

### 1. 导入 useTranslation Hook

```typescript
import { useTranslation } from 'react-i18next';
```

### 2. 使用单个命名空间

```typescript
const MyComponent: React.FC = () => {
  const { t } = useTranslation('tasks');
  
  return (
    <div>
      <h1>{t('title')}</h1>
      <p>{t('description')}</p>
    </div>
  );
};
```

### 3. 使用多个命名空间

当组件需要使用多个命名空间的翻译时，推荐使用数组形式：

```typescript
const MyComponent: React.FC = () => {
  // 第一个命名空间为默认命名空间
  const { t } = useTranslation(['tasks', 'common']);
  
  return (
    <div>
      {/* 使用默认命名空间 (tasks) */}
      <h1>{t('title')}</h1>
      
      {/* 使用其他命名空间需要加前缀 */}
      <Button>{t('common:actions.submit')}</Button>
      <Button>{t('common:actions.cancel')}</Button>
    </div>
  );
};
```

### 4. 带参数的翻译

```typescript
// 翻译文件
{
  "confirmDeleteTasks": "确定要删除 {{count}} 个任务吗？",
  "totalRecords": "共 {{total}} 条记录"
}

// 组件中使用
t('confirmDeleteTasks', { count: 5 })  // "确定要删除 5 个任务吗？"
t('totalRecords', { total: 100 })      // "共 100 条记录"
```

### 5. 嵌套键访问

```typescript
// 翻译文件
{
  "workHours": {
    "report": {
      "columns": {
        "rank": "排名",
        "user": "用户"
      }
    }
  }
}

// 组件中使用
t('workHours.report.columns.rank')  // "排名"
t('workHours.report.columns.user')  // "用户"
```

## 翻译键命名规范

### 命名格式

```
{module}.{submodule}.{key}
```

### 规范要求

1. **使用 camelCase**: 所有键名使用驼峰命名法
   - ✅ `statusPending`, `createSuccess`
   - ❌ `status_pending`, `create-success`

2. **使用点号分隔层级**: 嵌套结构使用点号
   - ✅ `workHours.report.columns.rank`
   - ❌ `workHours_report_columns_rank`

3. **按功能模块分组**: 相关翻译放在同一对象下
   ```json
   {
     "workHours": {
       "report": { ... },
       "stats": { ... }
     }
   }
   ```

4. **描述性命名**: 键名应自解释
   - ✅ `confirmDeleteTask`, `exportSuccess`
   - ❌ `msg1`, `btn2`

5. **避免缩写**: 除非是通用缩写
   - ✅ `configuration`, `application`
   - ❌ `cfg`, `app` (除非是通用缩写如 `API`, `URL`)

## 动态键的最佳实践

### ⚠️ 重要：使用映射对象，避免字符串操作

**错误示例** - 字符串操作容易产生 bug：

```typescript
// ❌ 错误：字符串操作可能产生错误的键名
const statusKey = `status${status.charAt(0).toUpperCase() + status.slice(1)}`;
t(statusKey);

// 对于 'in_progress': 
// 'I' + 'n_progress' = 'In_progress' (错误!)
// 期望: 'statusInProgress'
```

**正确示例** - 使用映射对象：

```typescript
// ✅ 正确：使用显式映射对象
const statusKeyMap: Record<TaskStatus, string> = {
  pending: 'statusPending',
  in_progress: 'statusInProgress',
  completed: 'statusCompleted',
  cancelled: 'statusCancelled',
};

// 使用映射获取翻译键
t(statusKeyMap[record.status]);
```

### 完整示例

```typescript
import { useTranslation } from 'react-i18next';
import type { TaskStatus, TaskPriority } from '@/types';

const TaskStatusTag: React.FC<{ status: TaskStatus }> = ({ status }) => {
  const { t } = useTranslation('tasks');
  
  // 状态键映射
  const statusKeyMap: Record<TaskStatus, string> = {
    pending: 'statusPending',
    in_progress: 'statusInProgress',
    completed: 'statusCompleted',
    cancelled: 'statusCancelled',
  };
  
  // 状态颜色映射
  const statusColorMap: Record<TaskStatus, string> = {
    pending: 'default',
    in_progress: 'processing',
    completed: 'success',
    cancelled: 'error',
  };
  
  return (
    <Tag color={statusColorMap[status]}>
      {t(statusKeyMap[status])}
    </Tag>
  );
};
```

### 使用 TypeScript 确保映射完整性

```typescript
// 使用 Record 类型确保所有枚举值都有对应的映射
type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';

// TypeScript 会在缺少任何状态时报错
const statusKeyMap: Record<TaskStatus, string> = {
  pending: 'statusPending',
  in_progress: 'statusInProgress',
  completed: 'statusCompleted',
  cancelled: 'statusCancelled',
};
```

## 添加新翻译的步骤

### 1. 确定命名空间

根据功能模块选择合适的命名空间，或创建新的命名空间。

### 2. 同时更新中英文翻译文件

**必须同时更新两个语言的翻译文件**，确保翻译完整性。

```json
// zh/tasks.json
{
  "newFeature": {
    "title": "新功能",
    "description": "这是新功能的描述"
  }
}

// en/tasks.json
{
  "newFeature": {
    "title": "New Feature",
    "description": "This is the description of the new feature"
  }
}
```

### 3. 如果创建新命名空间

1. 创建翻译文件：
   ```
   frontend/src/locales/zh/newNamespace.json
   frontend/src/locales/en/newNamespace.json
   ```

2. 更新 `config.ts`：
   ```typescript
   // 导入新的翻译文件
   import zhNewNamespace from './zh/newNamespace.json';
   import enNewNamespace from './en/newNamespace.json';
   
   const resources = {
     zh: {
       // ... 现有命名空间
       newNamespace: zhNewNamespace,
     },
     en: {
       // ... 现有命名空间
       newNamespace: enNewNamespace,
     },
   };
   
   // 更新 ns 数组
   i18n.init({
     // ...
     ns: ['common', /* ... */, 'newNamespace'],
   });
   ```

### 4. 在组件中使用

```typescript
const { t } = useTranslation('newNamespace');
// 或
const { t } = useTranslation(['newNamespace', 'common']);
```

## UI 布局适配

### 文本长度差异

中英文翻译长度差异显著，需要特别处理：

| 中文 | 英文 | 长度比 |
|------|------|--------|
| 刷新 | Refresh | 1:3.5 |
| 导出 Excel | Export Excel | 1:2 |
| 工时统计明细 | Work Hours Statistics Details | 1:4 |

### 布局适配策略

#### 1. 按钮组件

```typescript
// 使用 minWidth 确保按钮最小宽度
<Button style={{ minWidth: 80 }}>
  {t('actions.refresh')}
</Button>

// 使用 Space 组件自动处理间距
<Space>
  <Button>{t('actions.refresh')}</Button>
  <Button>{t('actions.export')}</Button>
</Space>
```

#### 2. 表格列宽

```typescript
const columns: ColumnsType = [
  {
    title: t('columns.user'),
    key: 'user',
    width: 150,  // 固定宽度适应较长的英文
  },
  {
    title: t('columns.efficiencyScore'),
    key: 'efficiency',
    width: 120,
  },
];
```

#### 3. 长文本处理

```typescript
// 使用 Tooltip 显示完整文本
<Tooltip title={t('longText')}>
  <Text ellipsis style={{ maxWidth: 100 }}>
    {t('longText')}
  </Text>
</Tooltip>
```

#### 4. 翻译文本长度控制

在翻译文件中，应尽量保持翻译简洁：

```json
// ✅ 好的翻译 - 简洁
{
  "efficiencyScore": "Efficiency",
  "totalAnnotations": "Annotations"
}

// ❌ 避免 - 过长
{
  "efficiencyScore": "Efficiency Score Rating",
  "totalAnnotations": "Total Number of Annotations"
}
```

## 语言切换

### 使用 languageStore

```typescript
import { useLanguageStore } from '@/stores/languageStore';

const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage } = useLanguageStore();
  
  return (
    <Select
      value={language}
      onChange={setLanguage}
      options={[
        { value: 'zh', label: '中文' },
        { value: 'en', label: 'English' },
      ]}
    />
  );
};
```

### 语言持久化

语言偏好自动保存到 localStorage，页面刷新后会恢复之前选择的语言。

## 测试指南

### 单元测试

```typescript
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/locales/config';

describe('MyComponent', () => {
  it('should display translated text', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <MyComponent />
      </I18nextProvider>
    );
    
    // 验证翻译文本显示
    expect(screen.getByText('任务列表')).toBeInTheDocument();
  });
});
```

### 语言切换测试

```typescript
import { act } from '@testing-library/react';
import i18n from '@/locales/config';

describe('Language switching', () => {
  it('should switch language correctly', async () => {
    // 切换到英文
    await act(async () => {
      await i18n.changeLanguage('en');
    });
    
    expect(i18n.language).toBe('en');
    
    // 切换回中文
    await act(async () => {
      await i18n.changeLanguage('zh');
    });
    
    expect(i18n.language).toBe('zh');
  });
});
```

## 常见问题

### Q: 翻译键不存在时会显示什么？

A: 会显示翻译键本身作为 fallback，同时在开发模式下会在控制台输出警告。

### Q: 如何处理复数形式？

A: 使用 i18next 的复数功能：

```json
{
  "item": "{{count}} 个项目",
  "item_plural": "{{count}} 个项目"
}
```

```typescript
t('item', { count: 1 })  // "1 个项目"
t('item', { count: 5 })  // "5 个项目"
```

### Q: 如何在非 React 组件中使用翻译？

A: 直接导入 i18n 实例：

```typescript
import i18n from '@/locales/config';

const message = i18n.t('common:status.success');
```

### Q: 如何处理 HTML 内容？

A: 使用 Trans 组件：

```typescript
import { Trans } from 'react-i18next';

<Trans i18nKey="richText">
  这是 <strong>加粗</strong> 文本
</Trans>
```

## 检查清单

在提交代码前，请确保：

- [ ] 所有用户可见文本都使用了 `t()` 函数
- [ ] 中英文翻译文件都已更新
- [ ] 翻译键遵循命名规范
- [ ] 动态键使用映射对象而非字符串操作
- [ ] UI 布局在两种语言下都正常显示
- [ ] 语言切换后所有文本都能正确更新

## 相关资源

- [react-i18next 官方文档](https://react.i18next.com/)
- [i18next 官方文档](https://www.i18next.com/)
- [Ant Design 国际化](https://ant.design/docs/react/i18n-cn)
