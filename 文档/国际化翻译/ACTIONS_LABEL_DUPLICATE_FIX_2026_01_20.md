# Actions.label 重复定义修复 - 2026-01-20

**Date**: 2026-01-20  
**Status**: ✅ Complete  
**Priority**: P0 (Critical Translation Issue)

## 问题描述

翻译文件中 `actions` 对象被定义了两次：
1. 第一个定义只有 `label: "操作"`
2. 第二个定义有完整的操作按钮翻译但没有 `label`

由于 JSON 中后面的定义会覆盖前面的定义，导致 `actions.label` 被覆盖掉，表格的"操作"列标题无法正确翻译。

## 根本原因

**中文翻译文件** (`frontend/src/locales/zh/common.json`):
```json
// 第一个定义 (第 25-28 行)
"actions": {
  "label": "操作"
}

// 第二个定义 (第 132-163 行) - 覆盖了第一个
"actions": {
  "submit": "提交",
  "cancel": "取消",
  // ... 没有 label
}
```

**英文翻译文件** (`frontend/src/locales/en/common.json`):
同样的问题。

## 解决方案

### 1. 合并两个 `actions` 定义

将 `label` 添加到第二个 `actions` 定义中，并删除第一个重复的定义。

**修复后的结构**:
```json
"actions": {
  "label": "操作",  // 添加 label
  "submit": "提交",
  "cancel": "取消",
  "create": "创建",
  "confirm": "确认",
  "delete": "删除",
  "edit": "编辑",
  "save": "保存",
  "saved": "已保存",
  "search": "搜索",
  "reset": "重置",
  "refresh": "刷新",
  "export": "导出",
  "import": "导入",
  "back": "返回",
  "logout": "退出登录",
  "next": "下一步",
  "previous": "上一步",
  "undo": "撤销",
  "redo": "重做",
  "skip": "跳过",
  "submitNext": "提交并下一个",
  "reload": "重新加载",
  "reloading": "重新加载中...",
  "fullscreen": "全屏",
  "exitFullscreen": "退出全屏",
  "addChild": "添加子工作空间",
  "duplicate": "复制",
  "archive": "归档",
  "restore": "恢复"
}
```

## 修改的文件

### 1. frontend/src/locales/zh/common.json
- 删除第一个重复的 `actions` 定义
- 在第二个 `actions` 定义中添加 `"label": "操作"`

### 2. frontend/src/locales/en/common.json
- 删除第一个重复的 `actions` 定义
- 在第二个 `actions` 定义中添加 `"label": "Actions"`

## 验证结果

### ✅ JSON 验证
```
zh/common.json is valid JSON
en/common.json is valid JSON
```

### ✅ actions.label 验证
```
中文: actions.label = "操作"
英文: actions.label = "Actions"
```

### ✅ TypeScript 编译
```
npm run typecheck - PASSED
```

## 影响的组件

以下组件使用 `t('common:actions.label')` 作为表格"操作"列标题：

1. `frontend/src/pages/Admin/ConfigLLM.tsx`
2. `frontend/src/components/DataSync/DataSourceManager.tsx`
3. `frontend/src/pages/Quality/RuleConfig.tsx`
4. `frontend/src/pages/Security/Sessions/index.tsx`
5. `frontend/src/pages/Security/Dashboard/index.tsx`
6. `frontend/src/pages/Security/SSO/index.tsx`
7. `frontend/src/pages/Security/Audit/ComplianceReports.tsx`
8. `frontend/src/pages/Security/index.tsx`
9. `frontend/src/pages/Security/Permissions/index.tsx`
10. `frontend/src/pages/Quality/QualityDashboard.tsx`
11. `frontend/src/pages/Security/DataPermissions/AccessLogPage.tsx`
12. `frontend/src/pages/Security/Audit/AuditLogs.tsx`
13. `frontend/src/pages/Security/RBAC/UserRoleAssignment.tsx`
14. `frontend/src/components/DataSync/SyncTaskConfig.tsx`
15. `frontend/src/components/DataSync/DataDesensitizationConfig.tsx`
16. `frontend/src/pages/DataSync/Sources/index.tsx`
17. `frontend/src/pages/Security/RBAC/RoleList.tsx`

**总计**: 17+ 个组件

## 国际化功能

### ✅ 语言切换
- 表格"操作"列标题现在正确跟随国际化语言选择
- 中文: "操作"
- 英文: "Actions"
- 切换语言时，所有表格的"操作"列标题自动更新

## 最佳实践

### ✅ 避免重复定义
- JSON 文件中每个键只应定义一次
- 后面的定义会覆盖前面的定义
- 使用 JSON 验证工具检查重复键

### ✅ 翻译文件结构
- 保持翻译文件结构清晰
- 相关的翻译键放在同一个对象中
- 避免分散定义同一个对象

## 测试步骤

### 1. 清除浏览器缓存
```
Chrome/Firefox: Ctrl+Shift+Delete
Mac: Cmd+Shift+Delete
```

### 2. 访问页面
```
http://localhost:5174/security
```

### 3. 验证表格"操作"列
- 检查所有表格的"操作"列标题
- 中文模式: 应显示 "操作"
- 英文模式: 应显示 "Actions"

### 4. 验证语言切换
- 在中英文之间切换
- 确认所有表格的"操作"列标题实时更新

## 预期结果

✅ 所有表格的"操作"列标题正确翻译  
✅ 中英文切换实时更新  
✅ 无硬编码的英文文本  
✅ 无翻译键显示 (如 "actions.label")  
✅ 无控制台错误  

---

**Status**: ✅ 修复完成，已验证  
**Ready for**: 用户测试和验证  
**Root Cause**: JSON 文件中 `actions` 对象重复定义，后面的定义覆盖了前面的 `label` 键

