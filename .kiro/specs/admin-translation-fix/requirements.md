# Admin Console Translation Fix - Requirements

## 1. Problem Statement

The admin console pages are displaying raw translation keys (e.g., `billingManagement.summary.monthlyRevenue`) instead of translated text. This affects multiple pages including:
- Overview/Console page (概览)
- Billing Management page
- Permission Config page
- Other admin subpages

## 2. Root Cause Analysis

### 2.1 Duplicate Translation Keys
**Issue**: The `frontend/src/locales/zh/admin.json` file contains duplicate keys:
- `permissionConfig` appears twice (around lines 1150 and 1250)
- `billingManagement` may have duplicate or incomplete definitions
- `console` section may have duplicates

**Impact**: When translation keys are duplicated, the i18n system becomes confused about which definition to use, causing it to fall back to displaying the raw key path.

### 2.2 Incomplete Translation Sections
**Issue**: Some translation sections may be incomplete or truncated
- The file is 1817 lines long
- Some sections may not have all required keys

## 3. User Stories

### 3.1 As an administrator
**I want** to see properly translated text in all admin console pages  
**So that** I can understand and use the admin interface effectively

**Acceptance Criteria**:
- WHEN I navigate to the admin console overview page, THEN all text should be in Chinese (or English based on language setting)
- WHEN I view the billing management page, THEN all labels, headers, and content should be translated
- WHEN I access any admin subpage, THEN no raw translation keys should be visible

### 3.2 As a developer
**I want** the translation files to have no duplicate keys  
**So that** the i18n system can reliably resolve translations

**Acceptance Criteria**:
- WHEN I check the admin.json files, THEN there should be no duplicate top-level keys
- WHEN I check the admin.json files, THEN all sections should be complete
- WHEN I run the frontend build, THEN there should be no translation-related warnings

## 4. Technical Requirements

### 4.1 Remove Duplicate Keys
- Remove duplicate `permissionConfig` definitions
- Remove duplicate `console` definitions if any
- Remove duplicate `billingManagement` definitions if any
- Merge any unique content from duplicates into a single definition

### 4.2 Verify Translation Completeness
- Ensure all keys used in components exist in translation files
- Ensure Chinese and English files have matching key structures
- Verify no keys are missing

### 4.3 Validate Translation Files
- Ensure JSON syntax is valid
- Ensure no trailing commas
- Ensure proper nesting structure

## 5. Affected Files

### Translation Files
- `frontend/src/locales/zh/admin.json` (1817 lines)
- `frontend/src/locales/en/admin.json` (1817 lines)

### Component Files (for reference)
- `frontend/src/pages/Admin/Console/index.tsx`
- `frontend/src/pages/Admin/BillingManagement.tsx`
- `frontend/src/pages/Admin/PermissionConfig.tsx`
- `frontend/src/pages/Admin/QuotaManagement.tsx`
- Other admin pages

## 6. Success Criteria

### 6.1 No Duplicate Keys
- Run a script to detect duplicate keys in JSON files
- All duplicates removed
- Files pass JSON validation

### 6.2 All Translations Display Correctly
- Navigate to admin console overview page - all text translated
- Navigate to billing management page - all text translated
- Navigate to permission config page - all text translated
- Navigate to quota management page - all text translated
- No raw translation keys visible anywhere

### 6.3 Browser Console Clean
- No i18n warnings in browser console
- No "missing translation" errors
- No "duplicate key" warnings

## 7. Testing Plan

### 7.1 Automated Testing
- Validate JSON syntax
- Check for duplicate keys
- Verify key structure matches between zh and en files

### 7.2 Manual Testing
- Clear browser cache
- Navigate to each admin page
- Verify all text is translated
- Check both Chinese and English languages

## 8. Priority

**P0 - Critical**: This affects user experience and makes the admin console difficult to use.

## 9. Dependencies

- None - this is a pure translation file fix

## 10. Risks

### 10.1 Data Loss Risk
**Risk**: Accidentally removing unique translation content when merging duplicates  
**Mitigation**: Carefully compare duplicate sections before merging

### 10.2 Breaking Changes Risk
**Risk**: Changing key structure might break components  
**Mitigation**: Only remove duplicates, don't change key paths

## 11. Out of Scope

- Adding new translations
- Refactoring component translation usage
- Changing translation key naming conventions
- Adding translation validation to CI/CD pipeline (future enhancement)
