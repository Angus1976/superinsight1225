# Task 48.1: Components Directory Hardcoded Chinese Text Audit

## Summary

**Total files with hardcoded Chinese text:** 39 component files + 7 test files = 46 files
**Total instances of hardcoded Chinese text:** 517+ occurrences

## Task 48.2 Progress

### Completed Updates

The following components have been internationalized:

| File | Status | Notes |
|------|--------|-------|
| `BusinessLogic/BusinessRuleManager.tsx` | ✅ Complete | Added useTranslation, created businessLogic.json |
| `Annotation/AnnotationInterface.tsx` | ✅ Complete | Added useTranslation, created annotation.json |
| `Auth/PermissionGuard.tsx` | ✅ Complete | Added useTranslation, updated auth.json |
| `Auth/TenantIsolationGuard.tsx` | ✅ Complete | Added useTranslation, updated auth.json |
| `Common/DesignSystem/EmptyState.tsx` | ✅ Complete | Added useTranslation, updated common.json |
| `Common/DesignSystem/ConfirmModal.tsx` | ✅ Complete | Added useTranslation, updated common.json |

### New Translation Files Created

- `frontend/src/locales/zh/businessLogic.json` - BusinessLogic component translations
- `frontend/src/locales/en/businessLogic.json` - BusinessLogic component translations (English)
- `frontend/src/locales/zh/annotation.json` - Annotation component translations
- `frontend/src/locales/en/annotation.json` - Annotation component translations (English)

### Updated Translation Files

- `frontend/src/locales/zh/auth.json` - Added permission.* namespace
- `frontend/src/locales/en/auth.json` - Added permission.* namespace
- `frontend/src/locales/zh/common.json` - Added emptyState.*, confirmModal.* namespaces
- `frontend/src/locales/en/common.json` - Added emptyState.*, confirmModal.* namespaces
- `frontend/src/locales/config.ts` - Added businessLogic and annotation namespaces

## Files Requiring Internationalization Updates (Remaining)

### High Priority (>20 instances) - Remaining

| File | Count | Category | Status |
|------|-------|----------|--------|
| `BusinessLogic/BusinessRuleManager.tsx` | 74 | BusinessLogic | ✅ Complete |
| `BusinessLogic/BusinessLogicDashboard.tsx` | 59 | BusinessLogic | ⏳ Pending |
| `BusinessLogic/PatternAnalysis.tsx` | 51 | BusinessLogic | ⏳ Pending |
| `Annotation/AnnotationInterface.tsx` | 47 | Annotation | ✅ Complete |
| `Auth/PermissionGuard.tsx` | 36 | Auth | ✅ Complete |
| `BusinessLogic/InsightNotification.tsx` | 34 | BusinessLogic | ⏳ Pending |
| `Auth/TenantIsolationGuard.tsx` | 27 | Auth | ✅ Complete |
| `BusinessLogic/RuleVisualization.tsx` | 26 | BusinessLogic | ⏳ Pending |
| `BusinessLogic/InsightCards.tsx` | 24 | BusinessLogic | ⏳ Pending |
| `Auth/WorkspaceSwitcher.tsx` | 20 | Auth | ⏳ Pending |

### Medium Priority (10-19 instances)

| File | Count | Category |
|------|-------|----------|
| `LabelStudio/LabelStudioEmbed.tsx` | 17 | LabelStudio |
| `Common/ErrorHandling/ErrorBoundary.tsx` | 13 | Common |
| `LabelStudio/PermissionMapper.tsx` | 10 | LabelStudio |
| `Dashboard/KnowledgeGraph.tsx` | 10 | Dashboard |

### Low Priority (<10 instances) - Remaining

| File | Count | Category | Status |
|------|-------|----------|--------|
| `LabelStudio/ProjectSync.tsx` | 8 | LabelStudio | ⏳ Pending |
| `Common/DesignSystem/EmptyState.tsx` | 8 | Common | ✅ Complete |
| `Common/DesignSystem/StatusBadge.tsx` | 6 | Common | ⏳ Pending |
| `Common/DesignSystem/ConfirmModal.tsx` | 6 | Common | ✅ Complete |
| `Common/Composable/StatusIndicator.tsx` | 5 | Common | ⏳ Pending |
| `Common/Composable/InfiniteScroll.tsx` | 4 | Common | ⏳ Pending |
| `Common/Composable/DataTable.tsx` | 4 | Common | ⏳ Pending |
| `Common/Composable/FilterGroup.tsx` | 3 | Common | ⏳ Pending |
| `Layout/ResponsiveLayout.tsx` | 2 | Layout | ⏳ Pending |
| `Layout/HeaderContent.tsx` | 2 | Layout | ⏳ Pending |
| `Dashboard/QualityReports.tsx` | 2 | Dashboard | ⏳ Pending |
| `Dashboard/ProgressOverview.tsx` | 2 | Dashboard | ⏳ Pending |
| `Common/ErrorBoundary.tsx` | 2 | Common | ⏳ Pending |
| `Common/Composable/ConditionalRender.tsx` | 2 | Common | ⏳ Pending |
| `Common/Composable/AsyncContent.tsx` | 2 | Common | ⏳ Pending |
| `Auth/TenantSelector.tsx` | 2 | Auth | ⏳ Pending |
| `System/TenantManager.tsx` | 1 | System | ⏳ Pending |
| `LanguageSwitcher/index.tsx` | 1 | LanguageSwitcher | ⏳ Pending |
| `Common/ResponsiveTable.tsx` | 1 | Common | ⏳ Pending |
| `Common/DesignSystem/LoadingOverlay.tsx` | 1 | Common | ⏳ Pending |
| `Common/DesignSystem/ContentCard.tsx` | 1 | Common | ⏳ Pending |
| `Common/Composable/SearchInput.tsx` | 1 | Common | ⏳ Pending |
| `Common/Composable/NotificationBanner.tsx` | 1 | Common | ⏳ Pending |
| `Common/Composable/FormField.tsx` | 1 | Common | ⏳ Pending |
| `Common/Composable/DataList.tsx` | 1 | Common | ⏳ Pending |

## Test Files with Hardcoded Chinese Text

| File | Count |
|------|-------|
| `Auth/__tests__/LoginForm.test.tsx` | 33 |
| `Billing/__tests__/BillingReports.test.tsx` | 11 |
| `Dashboard/__tests__/MetricCard.test.tsx` | 7 |
| `Auth/__tests__/WorkspaceSwitcher.test.tsx` | 6 |
| `Auth/__tests__/PermissionGuard.test.tsx` | 5 |
| `Auth/__tests__/TenantIsolationGuard.test.tsx` | 2 |
| `Common/__tests__/Loading.test.tsx` | 1 |

## Files Already Using i18n (Good Examples)

The following files already properly use `useTranslation` hook:
- `Tasks/ProgressTracker.tsx` - Uses `useTranslation(['tasks', 'common'])`
- `Tasks/TaskStats.tsx` - Uses translation functions
- `Dashboard/QuickActions.tsx` - Uses `useTranslation('dashboard')`
- `Common/Loading.tsx` - Uses `useTranslation('common')`
- `DataSync/DataDesensitizationConfig.tsx` - Uses `useTranslation(['dataSync', 'security', 'common'])`

## Categories Summary

| Category | Files | Total Instances |
|----------|-------|-----------------|
| BusinessLogic | 6 | 268 |
| Auth | 4 | 85 |
| Common | 15 | 53 |
| LabelStudio | 3 | 35 |
| Annotation | 1 | 47 |
| Dashboard | 2 | 12 |
| Layout | 2 | 4 |
| System | 1 | 1 |
| LanguageSwitcher | 1 | 1 |

## Common Patterns Found

### 1. Default Parameter Values
```typescript
// Found in ConfirmModal.tsx
confirmText = '确认',
cancelText = '取消',
```

### 2. Fallback Text in t() Function
```typescript
// Found in WorkspaceSwitcher.tsx
t('workspace.loading', '加载工作空间...')
t('workspace.createFailed', '创建工作空间失败')
```

### 3. Direct String Literals
```typescript
// Found in AnnotationInterface.tsx
message.error('您没有创建标注的权限');
message.success('标注已保存');
```

### 4. Status/Label Mappings
```typescript
// Found in StatusBadge.tsx
defaultLabel: '成功',
defaultLabel: '失败',
defaultLabel: '待处理',
```

### 5. Comments in Chinese (Lower Priority)
```typescript
// Found in PermissionGuard.tsx
showLoading?: boolean; // 是否显示加载状态
```

## Recommendations

1. **Create new translation namespaces:**
   - `businessLogic.json` - For BusinessLogic components
   - `annotation.json` - For Annotation components
   - Update existing `common.json` for shared components

2. **Priority Order for Updates:**
   1. BusinessLogic components (highest count)
   2. Auth components (user-facing)
   3. Annotation components (core functionality)
   4. Common/DesignSystem components (reusable)
   5. LabelStudio components
   6. Test files (use English or mock translations)

3. **Pattern to Follow:**
   - Use `useTranslation` hook with appropriate namespaces
   - Replace default parameter values with `t()` calls
   - Remove Chinese fallback text from `t()` calls after adding keys
   - Use mapping objects for status/type translations

## Next Steps

Task 48.2 should implement the internationalization updates for these components, starting with the highest priority files.
