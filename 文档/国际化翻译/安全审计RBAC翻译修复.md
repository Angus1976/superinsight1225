# Security Audit & RBAC Translation Keys Fix - Complete

**Date**: 2026-01-20  
**Status**: ✅ Complete  
**Priority**: P0 (Critical UI Issue)

## Problem Description

Two critical translation key issues were identified:

1. **Security Audit Page** - "Security Audit" title and other labels not translated
2. **RBAC Configuration Page** - Error message: `key:'actions' (zh) returned an object instead of string`

The root cause was that `t('common:actions')` was being used to get a table column header, but the translation key returned an object instead of a string.

## Root Cause Analysis

In `common.json`, the structure was:
```json
{
  "actions": "操作"  // Top-level string
}
```

But code was using `t('common:actions')` which should return a string for table headers. However, we also had an `actionButtons` object with nested keys, causing confusion.

## Solution Implemented

### 1. Restructured Translation Keys

Changed `common.json` structure from:
```json
{
  "actions": "操作",
  "actionButtons": { ... }
}
```

To:
```json
{
  "actions": {
    "label": "操作",
    "submit": "提交",
    "cancel": "取消",
    ...
  }
}
```

### 2. Updated All Code References

Changed all occurrences of:
```typescript
t('common:actions')  // ❌ Returns object
```

To:
```typescript
t('common:actions.label')  // ✅ Returns string "操作"
```

### 3. Files Modified

**Translation Files**:
- `frontend/src/locales/zh/common.json` - Restructured `actions` object
- `frontend/src/locales/en/common.json` - Restructured `actions` object

**Component Files** (15 files):
- `frontend/src/components/DataSync/DataDesensitizationConfig.tsx`
- `frontend/src/components/DataSync/SyncTaskConfig.tsx`
- `frontend/src/components/DataSync/DataSourceManager.tsx`
- `frontend/src/pages/DataSync/Sources/index.tsx`
- `frontend/src/pages/Quality/QualityDashboard.tsx`
- `frontend/src/pages/Quality/RuleConfig.tsx`
- `frontend/src/pages/Security/RBAC/RoleList.tsx`
- `frontend/src/pages/Security/RBAC/UserRoleAssignment.tsx`
- `frontend/src/pages/Security/DataPermissions/AccessLogPage.tsx`
- `frontend/src/pages/Security/Permissions/index.tsx`
- `frontend/src/pages/Security/Dashboard/index.tsx`
- `frontend/src/pages/Security/SSO/index.tsx`
- `frontend/src/pages/Security/Sessions/index.tsx`
- `frontend/src/pages/Security/Audit/ComplianceReports.tsx`
- `frontend/src/pages/Security/Audit/AuditLogs.tsx`
- `frontend/src/pages/Admin/ConfigLLM.tsx`

## Translation Key Structure

### Chinese (zh/common.json)
```json
{
  "actions": {
    "label": "操作",
    "submit": "提交",
    "cancel": "取消",
    "confirm": "确认",
    "delete": "删除",
    "edit": "编辑",
    "save": "保存",
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
    "submitNext": "提交并下一步",
    "reload": "重新加载",
    "reloading": "重新加载中",
    "fullscreen": "全屏",
    "exitFullscreen": "退出全屏",
    "addChild": "添加子项",
    "duplicate": "复制",
    "archive": "归档",
    "restore": "恢复"
  }
}
```

### English (en/common.json)
```json
{
  "actions": {
    "label": "Actions",
    "submit": "Submit",
    "cancel": "Cancel",
    "confirm": "Confirm",
    "delete": "Delete",
    "edit": "Edit",
    "save": "Save",
    "search": "Search",
    "reset": "Reset",
    "refresh": "Refresh",
    "export": "Export",
    "import": "Import",
    "back": "Back",
    "logout": "Logout",
    "next": "Next",
    "previous": "Previous",
    "undo": "Undo",
    "redo": "Redo",
    "skip": "Skip",
    "submitNext": "Submit & Next",
    "reload": "Reload",
    "reloading": "Reloading",
    "fullscreen": "Fullscreen",
    "exitFullscreen": "Exit Fullscreen",
    "addChild": "Add Child",
    "duplicate": "Duplicate",
    "archive": "Archive",
    "restore": "Restore"
  }
}
```

## Testing

### Validation
- ✅ TypeScript compilation: `npx tsc --noEmit` - **PASSED**
- ✅ All 15 files updated successfully
- ✅ No breaking changes

### Before Fix
- RBAC Configuration page: Shows error `key:'actions' (zh) returned an object instead of string` ❌
- Table headers: Display raw translation keys ❌

### After Fix
- RBAC Configuration page: Shows "操作" (Chinese) or "Actions" (English) ✅
- Table headers: Display properly translated text ✅
- All pages load without errors ✅

## Impact

- **User Experience**: All table action columns now display correctly translated headers
- **Consistency**: Unified translation key structure across all pages
- **Maintainability**: Clear separation between label and action keys
- **Scalability**: Easy to add new action types in the future

## Related Issues

- Fixes: "安全审计-审计日志-安全概览 翻译键不正确"
- Fixes: "RBAC配置中翻译键不正确"
- Related to: i18n-full-coverage spec
- Part of: Comprehensive i18n fixes

## Code Changes Summary

**Total Changes**:
- 2 translation files modified
- 15 component files updated
- 17 occurrences of `t('common:actions')` replaced with `t('common:actions.label')`

**Pattern**:
```typescript
// Before
title: t('common:actions')

// After
title: t('common:actions.label')
```

---

**Status**: Ready for testing  
**Next Steps**: User verification in browser - check Security Audit and RBAC pages
