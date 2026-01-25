# Manual Raw Translation Key Verification

## Purpose
Verify that no raw translation keys (like "billingManagement.summary.monthlyRevenue") are visible in the UI.

## What to Look For

Raw translation keys typically have these characteristics:
1. **Dot notation**: Contains multiple dots (e.g., `admin.console.title`)
2. **camelCase**: Mixed case words (e.g., `billingManagement`, `quotaManagement`)
3. **Common prefixes**: Starts with module names like:
   - `billingManagement.`
   - `permissionConfig.`
   - `quotaManagement.`
   - `console.`
   - `admin.`
   - `common.`

## Pages to Check

### 1. Admin Console - Overview
**URL**: http://localhost:5173/admin/console

**Check in Chinese (zh)**:
- [ ] Page title
- [ ] Navigation menu items
- [ ] All card titles
- [ ] All labels and text
- [ ] Button text
- [ ] Tooltips (hover over elements)
- [ ] Placeholder text in inputs

**Check in English (en)**:
- [ ] Page title
- [ ] Navigation menu items
- [ ] All card titles
- [ ] All labels and text
- [ ] Button text
- [ ] Tooltips (hover over elements)
- [ ] Placeholder text in inputs

### 2. Admin Console - Billing Management
**URL**: http://localhost:5173/admin/billing

**Check in Chinese (zh)**:
- [ ] Page title
- [ ] Tab labels
- [ ] Table headers
- [ ] Table content
- [ ] Summary cards
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

**Check in English (en)**:
- [ ] Page title
- [ ] Tab labels
- [ ] Table headers
- [ ] Table content
- [ ] Summary cards
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

### 3. Admin Console - Permission Config
**URL**: http://localhost:5173/admin/permissions

**Check in Chinese (zh)**:
- [ ] Page title
- [ ] Section headers
- [ ] Permission names
- [ ] Permission descriptions
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

**Check in English (en)**:
- [ ] Page title
- [ ] Section headers
- [ ] Permission names
- [ ] Permission descriptions
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

### 4. Admin Console - Quota Management
**URL**: http://localhost:5173/admin/quota

**Check in Chinese (zh)**:
- [ ] Page title
- [ ] Tab labels
- [ ] Table headers
- [ ] Quota type names
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

**Check in English (en)**:
- [ ] Page title
- [ ] Tab labels
- [ ] Table headers
- [ ] Quota type names
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

### 5. Admin Console - Tenant Management
**URL**: http://localhost:5173/admin/tenants

**Check in Chinese (zh)**:
- [ ] Page title
- [ ] Table headers
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

**Check in English (en)**:
- [ ] Page title
- [ ] Table headers
- [ ] All labels and text
- [ ] Button text
- [ ] Form labels
- [ ] Tooltips

## How to Perform the Check

### Step 1: Open Browser DevTools
1. Open Chrome/Firefox
2. Press F12 to open DevTools
3. Go to Console tab

### Step 2: Navigate to Each Page
1. Visit each URL listed above
2. Switch between Chinese and English using the language selector
3. Carefully scan all visible text

### Step 3: Look for Suspicious Text
Look for text that:
- Contains dots (e.g., `admin.console.title`)
- Has camelCase (e.g., `billingManagement`)
- Looks like a code identifier rather than human-readable text

### Step 4: Document Findings
For each raw key found, note:
- Page URL
- Language (zh/en)
- Exact text displayed
- Location on page (e.g., "in page title", "in table header")

## Common False Positives (NOT translation keys)

These are valid text that might look like keys but are not:
- URLs: `localhost:5173`, `http://`, `www.`
- File extensions: `.json`, `.ts`, `.tsx`
- Version numbers: `v1.0`, `v2.0`
- Abbreviations: `API`, `ID`, `URL`
- Email addresses: `user@example.com`

## Expected Result

✅ **PASS**: All text is properly translated, no raw translation keys visible
❌ **FAIL**: One or more raw translation keys are visible in the UI

## Quick Visual Check Script

You can also use this browser console script to help identify potential issues:

```javascript
// Run this in browser console on each page
const allText = Array.from(document.querySelectorAll('body *'))
  .map(el => el.textContent.trim())
  .filter(text => text && text.length > 0)
  .filter(text => /\w+\.\w+\.\w+/.test(text) || /^[a-z]+[A-Z]/.test(text));

console.log('Suspicious texts found:', allText.length);
allText.forEach((text, idx) => {
  console.log(`${idx + 1}. "${text}"`);
});
```

## Automated Check (if puppeteer is available)

If puppeteer is installed in the frontend directory:
```bash
cd frontend
npm install puppeteer
node ../scripts/check_raw_translation_keys.js
```
