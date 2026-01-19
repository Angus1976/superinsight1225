# TypeScript 导出规范

**Version**: 1.0  
**Status**: ✅ Active  
**Last Updated**: 2026-01-19  
**Priority**: HIGH

## 概述

本规范旨在防止 TypeScript 模块导出时出现的常见错误，包括：
- 重复导出（TS2308）
- 导出不存在的成员
- 类型不匹配的导出
- 命名冲突

## 问题背景

2026-01-19 修复了 675 个 TypeScript 错误，主要问题包括：

1. **hooks/index.ts 导出不存在的函数**
   - `useTaskList` 应为 `useTasks`
   - `useTaskDetail` 不存在
   - `useCPUMonitor`、`useNetworkMonitor` 不存在
   - `useHover` 应为 `useHoverState`
   - `useFocus` 应为 `useFocusState`

2. **types/index.ts 重复导出**
   - `ApiError` 在多个文件中定义
   - `PaginationParams`、`AsyncState` 重复导出

3. **API 服务缺少泛型类型**
   - `api.get()` 应为 `api.get<ResponseType>()`

## 强制规则

### 规则 1: 导出前验证成员存在性

**❌ 错误示例**:
```typescript
// index.ts - 导出不存在的成员
export { useTaskList, useTaskDetail } from './useTask';
// 但 useTask.ts 中只有 useTasks 和 useTask
```

**✅ 正确示例**:
```typescript
// 先检查 useTask.ts 的实际导出
// useTask.ts 导出: useTask, useTasks, useTaskStats, useCreateTask...
export { useTask, useTasks, useTaskStats } from './useTask';
```

### 规则 2: 处理命名冲突时使用重命名

**❌ 错误示例**:
```typescript
// 两个文件都导出 ApiError，造成冲突
export * from './api';
export * from './api-enhanced';
```

**✅ 正确示例**:
```typescript
// 使用重命名避免冲突
export * from './api';
export { 
  ApiError as EnhancedApiError,
  // 其他需要重命名的导出
} from './api-enhanced';
```

### 规则 3: API 调用必须指定泛型类型

**❌ 错误示例**:
```typescript
const response = await api.get('/api/users');
const data = await api.post('/api/users', payload);
```

**✅ 正确示例**:
```typescript
const response = await api.get<User[]>('/api/users');
const data = await api.post<User>('/api/users', payload);
```

### 规则 4: 索引文件导出检查清单

创建或修改 `index.ts` 导出文件时，必须：

1. **列出源文件的所有导出**
   ```bash
   # 检查文件实际导出了什么
   grep -E "^export (function|const|class|type|interface)" ./useTask.ts
   ```

2. **检查命名冲突**
   ```bash
   # 检查是否有重复的导出名称
   grep -E "^export" ./index.ts | sort | uniq -d
   ```

3. **验证导出存在性**
   - 每个 `export { name } from './file'` 中的 `name` 必须在 `file` 中存在

### 规则 5: 使用 TypeScript 严格模式检查

在 `tsconfig.json` 中保持以下配置：

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

## 常见错误模式

### 模式 1: Hook 命名不一致

| 错误名称 | 正确名称 | 说明 |
|---------|---------|------|
| `useTaskList` | `useTasks` | 复数形式表示列表 |
| `useHover` | `useHoverState` | 带 State 后缀表示状态 hook |
| `useFocus` | `useFocusState` | 带 State 后缀表示状态 hook |

### 模式 2: 重复类型定义

当多个文件定义相同类型时：
1. 选择一个作为主定义
2. 其他文件使用 `import type` 引入
3. 或使用不同名称区分

### 模式 3: 通配符导出冲突

```typescript
// 危险：可能导致冲突
export * from './moduleA';
export * from './moduleB';

// 安全：明确指定导出
export { specificExport } from './moduleA';
export { anotherExport } from './moduleB';
```

## 开发流程检查点

### 新建模块时

1. 定义清晰的导出接口
2. 在 index.ts 中添加导出前，先验证成员存在
3. 检查是否与现有导出冲突

### 修改现有模块时

1. 如果重命名导出，同步更新所有 index.ts
2. 如果删除导出，检查是否有其他文件依赖
3. 运行 `npx tsc --noEmit` 验证

### 代码审查时

1. 检查新增的 index.ts 导出是否正确
2. 验证 API 调用是否有泛型类型
3. 确认没有重复导出

## 自动化检查

### 提交前检查

```bash
# 在 frontend 目录运行
npx tsc --noEmit

# 如果有错误，必须修复后才能提交
```

### CI/CD 检查

```yaml
# GitHub Actions 示例
- name: TypeScript Check
  run: |
    cd frontend
    npx tsc --noEmit
```

## 参考资料

- [TypeScript Module Resolution](https://www.typescriptlang.org/docs/handbook/module-resolution.html)
- [TypeScript Re-exports](https://www.typescriptlang.org/docs/handbook/modules.html#re-exports)
- [React Query TypeScript](https://tanstack.com/query/latest/docs/react/typescript)

---

**此规范为强制性规范，所有前端代码必须遵守。**
