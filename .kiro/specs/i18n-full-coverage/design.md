# Design Document

## Overview

本设计文档描述 SuperInsight 平台前端国际化全面覆盖的技术实现方案。基于现有的 react-i18next 基础设施，扩展翻译覆盖范围，消除所有硬编码文本，并建立可持续的国际化开发规范。

### 设计目标

1. **消除硬编码文本** - 将所有用户可见文本替换为翻译函数调用
2. **完善翻译文件** - 补充缺失的翻译键，确保中英文翻译完整
3. **实时语言切换** - 确保语言切换后所有内容立即更新
4. **开发规范** - 建立国际化开发指南，确保新增页面遵循规范
5. **类型安全** - 提供 TypeScript 类型定义，防止翻译键拼写错误

### 设计原则

1. **最小改动原则** - 仅修改必要的文件，不改变现有架构
2. **向后兼容** - 保持现有翻译键不变，仅新增缺失的键
3. **一致性** - 遵循现有的翻译键命名规范
4. **可维护性** - 翻译键按功能模块组织，便于查找和维护

## Architecture

### 现有 i18n 架构

```
frontend/
├── src/
│   ├── locales/
│   │   ├── config.ts          # i18n 配置
│   │   ├── zh/                 # 中文翻译
│   │   │   ├── auth.json
│   │   │   ├── billing.json
│   │   │   ├── common.json
│   │   │   └── ...
│   │   └── en/                 # 英文翻译
│   │       ├── auth.json
│   │       ├── billing.json
│   │       ├── common.json
│   │       └── ...
│   ├── stores/
│   │   └── languageStore.ts   # Zustand 语言状态管理
│   └── components/
│       └── LanguageSwitcher/  # 语言切换组件
```

### 扩展架构

```mermaid
graph TB
    subgraph "Translation Files"
        A[zh/common.json] --> |新增 error pages| A1[error.notFound, error.forbidden]
        B[zh/billing.json] --> |新增 workHours| B1[workHours.report.*]
        C[zh/auth.json] --> |新增 login| C1[login.appName, login.logoAlt]
    end
    
    subgraph "Components to Update"
        D[Login/index.tsx] --> |使用 t()| A1
        E[Error/404.tsx] --> |使用 t()| A1
        F[Error/403.tsx] --> |使用 t()| A1
        G[WorkHoursReport.tsx] --> |使用 t()| B1
    end
    
    subgraph "i18n System"
        H[react-i18next] --> I[useTranslation hook]
        I --> D
        I --> E
        I --> F
        I --> G
    end
```

## Components and Interfaces

### 1. 翻译文件扩展

#### common.json 扩展 - 错误页面翻译

```typescript
// 新增翻译键结构
interface CommonTranslations {
  // 现有键...
  error: {
    // 现有错误处理键...
    pages: {
      notFound: {
        title: string;        // "404"
        subtitle: string;     // "抱歉，您访问的页面不存在。"
        backHome: string;     // "返回首页"
      };
      forbidden: {
        title: string;        // "403"
        subtitle: string;     // "抱歉，您没有权限访问此页面。"
        backHome: string;     // "返回首页"
      };
    };
  };
}
```

#### billing.json 扩展 - 工时报表翻译

```typescript
// 新增翻译键结构
interface BillingTranslations {
  // 现有键...
  workHours: {
    // 现有键...
    report: {
      title: string;              // "工时统计明细"
      userDetail: string;         // "工时详情"
      statisticPeriod: string;    // "统计周期"
      
      // 表格列标题
      columns: {
        rank: string;             // "排名"
        user: string;             // "用户"
        totalHours: string;       // "总工时"
        billableHours: string;    // "计费工时"
        annotations: string;      // "标注数"
        rate: string;             // "时效"
        efficiencyScore: string;  // "效率评分"
        cost: string;             // "成本"
        action: string;           // "操作"
      };
      
      // 统计卡片
      stats: {
        totalUsers: string;       // "统计人数"
        totalHours: string;       // "总工时"
        billableHours: string;    // "计费工时"
        totalAnnotations: string; // "总标注数"
        avgEfficiency: string;    // "平均效率"
        totalCost: string;        // "总成本"
      };
      
      // 图表
      charts: {
        hoursRanking: string;     // "工时排名 (Top 10)"
        efficiencyDist: string;   // "效率分布"
        totalHours: string;       // "总工时"
        billableHours: string;    // "计费工时"
      };
      
      // 日期预设
      datePresets: {
        thisWeek: string;         // "本周"
        thisMonth: string;        // "本月"
        lastMonth: string;        // "上月"
        thisQuarter: string;      // "本季度"
      };
      
      // 用户详情模态框
      modal: {
        userId: string;           // "用户ID"
        userName: string;         // "用户名称"
        totalHours: string;       // "总工时"
        billableHours: string;    // "计费工时"
        billableRate: string;     // "计费率"
        efficiencyScore: string;  // "效率评分"
        annotationCount: string;  // "标注数量"
        rate: string;             // "时效"
        totalCost: string;        // "总成本"
        hours: string;            // "小时"
        items: string;            // "条"
        perHour: string;          // "条/小时"
      };
      
      // 按钮和操作
      actions: {
        refresh: string;          // "刷新"
        exportExcel: string;      // "导出 Excel"
        detail: string;           // "详情"
        close: string;            // "关闭"
        retry: string;            // "重试"
      };
      
      // 消息提示
      messages: {
        exportSuccess: string;    // "工时报表导出成功"
        exportFailed: string;     // "导出失败，请重试"
        loadFailed: string;       // "加载工时数据失败"
        noData: string;           // "暂无数据"
        totalRecords: string;     // "共 {{total}} 条记录"
        persons: string;          // "人"
      };
    };
  };
}
```

#### auth.json 扩展 - 登录页面翻译

```typescript
// 新增翻译键结构
interface AuthTranslations {
  // 现有键...
  login: {
    // 现有键...
    appName: string;              // "问视间" / "SuperInsight"
    logoAlt: string;              // "问视间 Logo" / "SuperInsight Logo"
  };
}
```

### 2. 组件更新接口

#### Login 页面更新

```typescript
// frontend/src/pages/Login/index.tsx
import { useTranslation } from 'react-i18next';

const LoginPage: React.FC = () => {
  const { t } = useTranslation('auth');
  
  return (
    <div className={styles.container}>
      <Card className={styles.card}>
        <div className={styles.header}>
          <img src="/logo-wenshijian.svg" alt={t('login.logoAlt')} className={styles.logo} />
          <Title level={2} className={styles.title}>
            {t('login.appName')}
          </Title>
          {/* ... */}
        </div>
      </Card>
    </div>
  );
};
```

#### Error 页面更新

```typescript
// frontend/src/pages/Error/404.tsx
import { useTranslation } from 'react-i18next';

const NotFoundPage: React.FC = () => {
  const { t } = useTranslation('common');
  
  return (
    <Result
      status="404"
      title={t('error.pages.notFound.title')}
      subTitle={t('error.pages.notFound.subtitle')}
      extra={
        <Button type="primary" onClick={() => navigate(ROUTES.HOME)}>
          {t('error.pages.notFound.backHome')}
        </Button>
      }
    />
  );
};
```

#### WorkHoursReport 组件更新

```typescript
// frontend/src/components/Billing/WorkHoursReport.tsx
import { useTranslation } from 'react-i18next';

export function WorkHoursReport({ tenantId, onExport }: WorkHoursReportProps) {
  const { t } = useTranslation('billing');
  
  const columns: ColumnsType<WorkHoursStatistics> = [
    {
      title: t('workHours.report.columns.rank'),
      key: 'rank',
      // ...
    },
    {
      title: t('workHours.report.columns.user'),
      key: 'user',
      // ...
    },
    // ...
  ];
  
  return (
    <Card title={t('workHours.report.title')}>
      {/* ... */}
    </Card>
  );
}
```

### 3. TypeScript 类型定义

```typescript
// frontend/src/types/i18n.d.ts
import 'react-i18next';

declare module 'react-i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof import('../locales/zh/common.json');
      auth: typeof import('../locales/zh/auth.json');
      billing: typeof import('../locales/zh/billing.json');
      // ... 其他命名空间
    };
  }
}
```

## Data Models

### 翻译键命名规范

```
{namespace}.{module}.{submodule}.{key}

示例:
- billing.workHours.report.columns.rank
- common.error.pages.notFound.subtitle
- auth.login.appName
```

### 翻译文件结构规范

```json
{
  "module": {
    "submodule": {
      "key": "翻译文本",
      "keyWithParam": "包含 {{param}} 的文本"
    }
  }
}
```

### 参数化翻译格式

```typescript
// 使用 {{param}} 语法
t('workHours.report.messages.totalRecords', { total: 100 })
// 输出: "共 100 条记录"
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following consolidated properties have been identified for testing:

### Property 1: Component Translation Key Usage

*For any* React component that displays user-visible text, all text content should be retrieved via the `t()` translation function rather than hardcoded strings.

**Validates: Requirements 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

### Property 2: Real-time Language Switching

*For any* rendered component, when the language is switched via the language store, all displayed text should update immediately to the new language without requiring a page reload or user interaction.

**Validates: Requirements 1.4, 2.4, 3.7, 6.1, 6.5, 8.4, 9.5**

### Property 3: Translation File Bidirectional Completeness

*For any* translation key that exists in the Chinese translation file, the same key should exist in the English translation file, and vice versa.

**Validates: Requirements 4.4, 4.5**

### Property 4: Translation Namespace Completeness

*For any* namespace (billing, common, auth), all required translation keys for the associated components should exist in the translation file.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 5: Translation Key Naming Convention

*For any* translation key in the translation files, the key should follow dot notation for nested structures and use camelCase for individual key names.

**Validates: Requirements 5.1, 5.2**

### Property 6: Language Preference Persistence Round-trip

*For any* language selection, saving to localStorage and then restoring on application reload should produce the same language setting.

**Validates: Requirements 6.2, 6.3**

### Property 7: No Hardcoded Text After Language Switch

*For any* page or component, after switching language, no hardcoded Chinese or English text should remain visible in the DOM (excluding technical identifiers and non-translatable content).

**Validates: Requirements 6.4**

### Property 8: Dynamic Content Internationalization

*For any* dynamic content (messages, tooltips, form validation, dates, numbers), the content should be formatted according to the current language locale and update when language changes.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

## Error Handling

### Translation Key Not Found

- **Behavior**: Return the translation key itself as fallback text
- **Logging**: Log a warning in development mode for missing keys
- **User Impact**: User sees the key name instead of translated text (graceful degradation)

### Invalid Language Code

- **Behavior**: Fallback to Chinese (default language)
- **Logging**: Log a warning about invalid language code
- **User Impact**: User sees Chinese interface instead of error

### Translation File Load Failure

- **Behavior**: Use cached translations if available, otherwise show keys
- **Logging**: Log error with file path and reason
- **User Impact**: Partial or no translations, but application remains functional

### localStorage Access Failure

- **Behavior**: Use default language (Chinese)
- **Logging**: Log warning about storage access
- **User Impact**: Language preference not persisted across sessions

## Testing Strategy

### Unit Testing

Unit tests focus on specific examples and edge cases:

- **Login Page**: Verify `t('login.appName')` and `t('login.logoAlt')` are called
- **Error Pages**: Verify 404 and 403 pages use correct translation keys
- **WorkHoursReport**: Verify all column headers, buttons, and messages use translation keys
- **Translation Files**: Verify required keys exist in both languages
- **Language Switching**: Verify localStorage is updated and components re-render

### Property-Based Testing

Property-based tests validate universal properties using Vitest with fast-check:

- **Minimum 100 iterations** per property test
- **Random input generation** for language codes, translation keys
- **Property validation** across all generated inputs

Each property test is tagged with the format: **Feature: i18n-full-coverage, Property {number}: {property_text}**

### Test Configuration

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/**/*.d.ts'],
    },
  },
});
```

### Test Data Management

- **Translation Fixtures**: Predefined translation sets for consistent testing
- **Mock i18n Provider**: Wrapper component for testing with controlled translations
- **Language Code Generators**: Valid and invalid language code generation for property tests

### Integration Testing

- **E2E Language Switching**: Playwright tests for full language switch flow
- **Cross-Component Consistency**: Verify all components update when language changes
- **Persistence Testing**: Verify language preference survives page reload

## UI Layout Adaptation

### 文本长度差异处理

中英文翻译长度差异显著，需要特别处理以保持 UI 美观：

| 中文 | 英文 | 长度比 |
|------|------|--------|
| 刷新 | Refresh | 1:3.5 |
| 导出 Excel | Export Excel | 1:2 |
| 工时统计明细 | Work Hours Statistics Details | 1:4 |
| 返回首页 | Back to Home | 1:2.5 |

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
// 使用 width 或 minWidth 确保列宽足够
const columns: ColumnsType = [
  {
    title: t('workHours.report.columns.user'),
    key: 'user',
    width: 150,  // 固定宽度
  },
  {
    title: t('workHours.report.columns.efficiencyScore'),
    key: 'efficiency',
    width: 120,  // 适应较长的英文标题
  },
];
```

#### 3. 统计卡片

```typescript
// Ant Design Statistic 组件自动处理文本换行
<Statistic
  title={t('workHours.report.stats.totalAnnotations')}
  value={count}
/>

// 如需限制宽度，使用 Col span 控制
<Col span={4}>
  <Card>
    <Statistic title={t('...')} value={...} />
  </Card>
</Col>
```

#### 4. 长文本处理

```typescript
// 使用 Tooltip 显示完整文本
<Tooltip title={t('workHours.report.columns.efficiencyScore')}>
  <Text ellipsis style={{ maxWidth: 100 }}>
    {t('workHours.report.columns.efficiencyScore')}
  </Text>
</Tooltip>
```

### 翻译文本长度控制

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

### CSS 适配

```scss
// 按钮组使用 flex 布局
.button-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;  // 允许换行
}

// 表格标题使用 nowrap 防止换行
.ant-table-thead th {
  white-space: nowrap;
}

// 卡片标题使用 ellipsis
.stat-card-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

## Implementation Notes

### Files to Modify

1. **frontend/src/pages/Login/index.tsx** - Replace hardcoded "问视间" with `t('login.appName')`
2. **frontend/src/pages/Error/404.tsx** - Replace hardcoded text with translation keys
3. **frontend/src/pages/Error/403.tsx** - Replace hardcoded text with translation keys
4. **frontend/src/components/Billing/WorkHoursReport.tsx** - Replace all hardcoded Chinese text

### Files to Update

1. **frontend/src/locales/zh/common.json** - Add error page translations
2. **frontend/src/locales/en/common.json** - Add error page translations
3. **frontend/src/locales/zh/billing.json** - Add WorkHoursReport translations
4. **frontend/src/locales/en/billing.json** - Add WorkHoursReport translations
5. **frontend/src/locales/zh/auth.json** - Add login page translations
6. **frontend/src/locales/en/auth.json** - Add login page translations

### New Files to Create

1. **frontend/src/types/i18n.d.ts** - TypeScript type definitions for translation keys
2. **docs/i18n-guidelines.md** - Development guidelines for internationalization
