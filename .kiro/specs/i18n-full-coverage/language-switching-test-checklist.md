# Language Switching Test Checklist

## Overview

This document provides a comprehensive checklist for QA to manually verify that language switching works correctly across all pages in the SuperInsight platform.

**Test Date:** _______________  
**Tester:** _______________  
**Build Version:** _______________

## Prerequisites

1. Access to the SuperInsight frontend application
2. User account with appropriate permissions to access all modules
3. Both Chinese (zh) and English (en) languages should be available

## Test Environment Setup

1. Clear browser localStorage before testing
2. Start with default language (Chinese)
3. Use the LanguageSwitcher component in the header to switch languages

---

## Test Procedure

For each page/component listed below:
1. Navigate to the page
2. Verify all text is displayed in the current language (Chinese by default)
3. Switch language using the LanguageSwitcher
4. Verify all text updates immediately without page reload
5. Check for any hardcoded text that doesn't change
6. Note any layout issues caused by text length differences

---

## 1. Authentication Pages

### 1.1 Login Page (`/login`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| App name (问视间/SuperInsight) | ☐ | ☐ | | |
| Logo alt text | ☐ | ☐ | | |
| Subtitle | ☐ | ☐ | | |
| Form labels (Username, Password) | ☐ | ☐ | | |
| Login button | ☐ | ☐ | | |
| Register link | ☐ | ☐ | | |
| Error messages | ☐ | ☐ | | |

### 1.2 Register Page (`/register`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Validation messages | ☐ | ☐ | | |
| Submit button | ☐ | ☐ | | |
| Login link | ☐ | ☐ | | |

### 1.3 Forgot Password Page (`/forgot-password`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Instructions | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Submit button | ☐ | ☐ | | |

### 1.4 Reset Password Page (`/reset-password`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Validation messages | ☐ | ☐ | | |
| Submit button | ☐ | ☐ | | |

---

## 2. Error Pages

### 2.1 404 Not Found Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Error title (404) | ☐ | ☐ | | |
| Error message | ☐ | ☐ | | |
| Back to home button | ☐ | ☐ | | |

### 2.2 403 Forbidden Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Error title (403) | ☐ | ☐ | | |
| Error message | ☐ | ☐ | | |
| Back to home button | ☐ | ☐ | | |

### 2.3 500 Server Error Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Error title (500) | ☐ | ☐ | | |
| Error message | ☐ | ☐ | | |
| Back to home button | ☐ | ☐ | | |
| Refresh button | ☐ | ☐ | | |

---

## 3. Dashboard (`/dashboard`)

| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Welcome message | ☐ | ☐ | | |
| Tab labels (Overview, Quality Reports, Knowledge Graph) | ☐ | ☐ | | |
| Chart titles | ☐ | ☐ | | |
| Statistic card titles | ☐ | ☐ | | |
| Quick action buttons | ☐ | ☐ | | |
| Error messages | ☐ | ☐ | | |

---

## 4. Tasks Module (`/tasks`)

### 4.1 Task List Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Table column headers | ☐ | ☐ | | |
| Status tags (Pending, In Progress, Completed, Cancelled) | ☐ | ☐ | | |
| Priority tags (Low, Medium, High, Urgent) | ☐ | ☐ | | |
| Annotation type tags | ☐ | ☐ | | |
| Action buttons (View, Annotate, Edit, Delete) | ☐ | ☐ | | |
| Batch action buttons | ☐ | ☐ | | |
| Search/Filter labels | ☐ | ☐ | | |
| Pagination text | ☐ | ☐ | | |
| Statistics cards | ☐ | ☐ | | |

### 4.2 Task Detail Page (`/tasks/:id`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Field labels | ☐ | ☐ | | |
| Status/Priority indicators | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |

### 4.3 Task Annotate Page (`/tasks/:id/annotate`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Loading message | ☐ | ☐ | | |
| No tasks message | ☐ | ☐ | | |
| Permission error messages | ☐ | ☐ | | |
| Navigation buttons | ☐ | ☐ | | |
| Progress indicators | ☐ | ☐ | | |
| Sync status | ☐ | ☐ | | |

### 4.4 Task Review Page (`/tasks/:id/review`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Statistics (Total, Pending, Approved, Rejected) | ☐ | ☐ | | |
| Action buttons (Approve, Reject, Request Revision) | ☐ | ☐ | | |
| Batch action buttons | ☐ | ☐ | | |
| Comment placeholder | ☐ | ☐ | | |

### 4.5 AI Annotation Panel
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Panel title | ☐ | ☐ | | |
| Statistics labels | ☐ | ☐ | | |
| Confidence distribution labels | ☐ | ☐ | | |
| Action buttons (Accept, Reject) | ☐ | ☐ | | |
| No results message | ☐ | ☐ | | |

---

## 5. Admin Module (`/admin`)

### 5.1 Admin Console
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| System status labels | ☐ | ☐ | | |
| Health indicators (Healthy/Unhealthy, Normal/Abnormal) | ☐ | ☐ | | |
| Statistics section titles | ☐ | ☐ | | |
| Service status table headers | ☐ | ☐ | | |
| Status values (Running, Degraded, Stopped) | ☐ | ☐ | | |
| Refresh button | ☐ | ☐ | | |

### 5.2 LLM Config Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Provider names | ☐ | ☐ | | |
| Status indicators | ☐ | ☐ | | |
| Configuration labels | ☐ | ☐ | | |

---

## 6. Quality Module (`/quality`)

### 6.1 Improvement Task List
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Statistics cards | ☐ | ☐ | | |
| Table column headers | ☐ | ☐ | | |
| Status values | ☐ | ☐ | | |
| Priority labels | ☐ | ☐ | | |
| Filter labels | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |

### 6.2 Quality Reports
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Report type labels | ☐ | ☐ | | |
| Table headers | ☐ | ☐ | | |
| Statistics labels | ☐ | ☐ | | |

---

## 7. Security Module (`/security`)

### 7.1 Permissions Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Tab labels | ☐ | ☐ | | |
| Table column headers | ☐ | ☐ | | |
| Status values (Enabled/Disabled) | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |
| Modal titles | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Success/Error messages | ☐ | ☐ | | |

### 7.2 Roles Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Table column headers | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |
| Modal content | ☐ | ☐ | | |

### 7.3 User Permissions Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Table column headers | ☐ | ☐ | | |
| "Never logged in" text | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |

---

## 8. Workspace Module (`/workspace`)

### 8.1 Workspace Management
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Tree view labels | ☐ | ☐ | | |
| Context menu items | ☐ | ☐ | | |
| Detail panel labels | ☐ | ☐ | | |
| Status tags | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |
| Confirmation dialogs | ☐ | ☐ | | |
| Empty state messages | ☐ | ☐ | | |
| Drag hint text | ☐ | ☐ | | |

---

## 9. Billing Module (`/billing`)

### 9.1 Billing Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Statistics cards | ☐ | ☐ | | |
| Table column headers | ☐ | ☐ | | |
| Status tags | ☐ | ☐ | | |
| Tab labels | ☐ | ☐ | | |
| Filter labels | ☐ | ☐ | | |
| Export button | ☐ | ☐ | | |

### 9.2 Work Hours Report
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Report title | ☐ | ☐ | | |
| Table column headers | ☐ | ☐ | | |
| Statistics labels | ☐ | ☐ | | |
| Date presets | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |
| Modal content | ☐ | ☐ | | |
| Messages | ☐ | ☐ | | |

---

## 10. Settings Page (`/settings`)

| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Tab labels (Profile, Security, Notifications, Appearance) | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Validation messages | ☐ | ☐ | | |
| Button text | ☐ | ☐ | | |
| Language selector options | ☐ | ☐ | | |
| Theme toggle labels | ☐ | ☐ | | |
| Success/Error messages | ☐ | ☐ | | |

---

## 11. DataSync Module (`/datasync`)

### 11.1 Export Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Form labels | ☐ | ☐ | | |
| Button text | ☐ | ☐ | | |

### 11.2 History Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Table headers | ☐ | ☐ | | |
| Status labels | ☐ | ☐ | | |

### 11.3 Scheduler Page
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page title | ☐ | ☐ | | |
| Schedule labels | ☐ | ☐ | | |
| Action buttons | ☐ | ☐ | | |

---

## 12. License Module (`/license`)

| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Dashboard labels | ☐ | ☐ | | |
| Activation wizard steps | ☐ | ☐ | | |
| Usage monitor labels | ☐ | ☐ | | |
| Alert configuration | ☐ | ☐ | | |

---

## 13. Other Modules

### 13.1 Collaboration (`/collaboration`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page content | ☐ | ☐ | | |

### 13.2 Crowdsource (`/crowdsource`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page content | ☐ | ☐ | | |

### 13.3 Augmentation (`/augmentation`)
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Page content | ☐ | ☐ | | |

---

## 14. Label Studio Integration

| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Language indicator visible | ☐ | ☐ | | |
| Language syncs when switched | ☐ | ☐ | | |
| Loading indicator during sync | ☐ | ☐ | | |

---

## 15. Global Components

### 15.1 Header/Navigation
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Menu items | ☐ | ☐ | | |
| User dropdown | ☐ | ☐ | | |
| Language switcher | ☐ | ☐ | | |

### 15.2 Sidebar
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Menu labels | ☐ | ☐ | | |
| Submenu labels | ☐ | ☐ | | |

### 15.3 Common Components
| Test Item | Chinese | English | Pass/Fail | Notes |
|-----------|---------|---------|-----------|-------|
| Loading spinners | ☐ | ☐ | | |
| Empty states | ☐ | ☐ | | |
| Confirmation dialogs | ☐ | ☐ | | |
| Toast messages | ☐ | ☐ | | |

---

## 16. Language Persistence Tests

| Test Item | Pass/Fail | Notes |
|-----------|-----------|-------|
| Language preference saved to localStorage | | |
| Language restored after page refresh | | |
| Language restored after browser restart | | |
| Language synced across multiple tabs | | |

---

## 17. UI Layout Tests

For each page, verify that the UI layout remains visually consistent when switching between languages:

| Test Item | Pass/Fail | Notes |
|-----------|-----------|-------|
| Buttons maintain proper sizing | | |
| Table columns don't overflow | | |
| Text doesn't get truncated unexpectedly | | |
| Modal dialogs display correctly | | |
| Form layouts remain aligned | | |
| Navigation menus display correctly | | |

---

## Summary

| Category | Total Tests | Passed | Failed | Notes |
|----------|-------------|--------|--------|-------|
| Authentication Pages | | | | |
| Error Pages | | | | |
| Dashboard | | | | |
| Tasks Module | | | | |
| Admin Module | | | | |
| Quality Module | | | | |
| Security Module | | | | |
| Workspace Module | | | | |
| Billing Module | | | | |
| Settings Page | | | | |
| DataSync Module | | | | |
| License Module | | | | |
| Other Modules | | | | |
| Label Studio | | | | |
| Global Components | | | | |
| Persistence Tests | | | | |
| UI Layout Tests | | | | |
| **TOTAL** | | | | |

---

## Issues Found

| Issue # | Page/Component | Description | Severity | Status |
|---------|----------------|-------------|----------|--------|
| | | | | |
| | | | | |
| | | | | |

---

## Sign-off

**Tester Signature:** _______________  
**Date:** _______________

**Reviewer Signature:** _______________  
**Date:** _______________
