---
inclusion: manual
---

# TypeScript 导出规范

**Version**: 2.0  
**Status**: ✅ Active  
**Last Updated**: 2026-02-04  
**Priority**: HIGH  
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则（必读）

**导出前验证 > 避免冲突 > 明确类型**

防止重复导出、导出不存在的成员、类型不匹配。

---

## 🎯 5 条核心规则（日常使用）

1. **验证成员存在** - 导出前检查源文件
2. **重命名避免冲突** - 不用通配符导出
3. **API 调用加泛型** - `api.get<Type>()`
4. **检查重复导出** - 用工具检测
5. **严格模式检查** - `npx tsc --noEmit`

---

## ⚡ 快速参考（80% 场景够用）

### 常见错误模式

| 错误 | 原因 | 修复 |
|------|------|------|
| TS2308 重复导出 | 多个文件导出同名 | 重命名或删除重复 |
| 导出不存在 | index.ts 导出源文件没有的成员 | 检查源文件实际导出 |
| 类型不匹配 | API 调用缺少泛型 | 添加 `<ResponseType>` |

### 快速检查命令

```bash
# 检查文件实际导出
grep -E "^export" ./useTask.ts

# 检查重复导出
grep -E "^export" ./index.ts | sort | uniq -d

# TypeScript 类型检查
npx tsc --noEmit
```

### Hook 命名规范

| 错误名称 | 正确名称 |
|---------|---------|
| `useTaskList` | `useTasks` |
| `useHover` | `useHoverState` |
| `useFocus` | `useFocusState` |

---

## 📚 详细规则（按需查阅）

<details>
<summary><b>规则 1: 导出前验证成员存在性</b>（点击展开）</summary>

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

</details>

<details>
<summary><b>规则 2: 处理命名冲突时使用重命名</b>（点击展开）</summary>

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

</details>

<details>
<summary><b>规则 3: API 调用必须指定泛型类型</b>（点击展开）</summary>

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

</details>

<details>
<summary><b>规则 4: 索引文件导出检查清单</b>（点击展开）</summary>

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

</details>

<details>
<summary><b>规则 5: 使用 TypeScript 严格模式检查</b>（点击展开）</summary>

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

</details>

<details>
<summary><b>常见错误模式详解</b>（点击展开）</summary>

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

</details>

---

## 🔗 相关资源

- **代码质量标准**：`.kiro/steering/coding-quality-standards.md`
- **前端项目结构**：`.kiro/steering/structure.md`

---

**此规范为强制性规范，所有前端代码必须遵守。**
