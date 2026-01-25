# Hardcoded English Text Fix - Additional Issues

## Problem Identified

After fixing the duplicate translation keys, there are still English texts displaying in the admin console because **many components have hardcoded English text** instead of using the translation system.

## Affected Files

### 1. `frontend/src/pages/System/index.tsx`
**Hardcoded texts**:
- "System Management" (page title)
- "Tenant Management" (tab label)
- "System Monitoring" (tab label)
- "Security & Audit" (tab label)

**Should use**:
- `t('admin:systemManagement')`
- `t('admin:tenantManagement')`
- `t('admin:systemMonitoring')`
- `t('admin:securityAudit')`

### 2. `frontend/src/components/System/TenantManager.tsx`
**Hardcoded texts in table columns**:
- "Tenant Name"
- "Status"
- "Plan"
- "Users"
- "Storage Used"
- "Resources"
- "Created"
- "Actions"

**Should use**:
- `t('admin:tenants.columns.tenantInfo')` or similar
- Need to check what other hardcoded texts exist in this component

### 3. Possibly other System components
- `frontend/src/components/System/SystemMonitoring.tsx`
- `frontend/src/components/System/SecurityAudit.tsx`

## Solution

1. Import `useTranslation` hook in each component
2. Replace all hardcoded English strings with `t('key')` calls
3. Ensure translation keys exist in `admin.json` files
4. Test all pages to verify translations work

## Translation Keys Needed

Check if these keys exist in `admin.json`:
- `systemManagement`
- `tenantManagement`
- `systemMonitoring`
- `securityAudit`
- Table column keys for tenant manager

## Next Steps

1. Read complete TenantManager component to find all hardcoded texts
2. Read SystemMonitoring and SecurityAudit components
3. Create a comprehensive list of all hardcoded texts
4. Add missing translation keys if needed
5. Replace hardcoded texts with translation calls
6. Rebuild and test
