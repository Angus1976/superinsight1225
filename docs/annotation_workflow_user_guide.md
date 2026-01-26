# Annotation Workflow User Guide

## Overview

This guide explains how to use the annotation workflow in SuperInsight to annotate data using Label Studio.

## Getting Started

### Prerequisites

- You must be logged in to SuperInsight
- You must have annotation permissions for the task
- Label Studio service must be running

### Accessing Annotation

1. Navigate to **Tasks** in the main menu
2. Click on a task to view its details
3. Click **开始标注** (Start Annotation) to begin annotating

## Annotation Methods

### Method 1: Embedded Annotation (Recommended)

The embedded annotation view displays Label Studio directly within SuperInsight.

**Steps:**
1. From the task detail page, click **开始标注**
2. The annotation interface will load in the same page
3. Complete your annotations
4. Progress is automatically saved

**Benefits:**
- Seamless integration with SuperInsight
- Automatic language synchronization
- Progress tracking visible in SuperInsight

### Method 2: New Window

Open Label Studio in a separate browser window for a larger workspace.

**Steps:**
1. From the task detail page, click **在新窗口打开** (Open in New Window)
2. Label Studio opens in a new browser tab
3. Complete your annotations
4. Close the tab when finished

**Benefits:**
- Larger workspace
- Can work on multiple tasks simultaneously
- Full Label Studio interface

## Language Settings

### Automatic Language Synchronization

SuperInsight automatically synchronizes your language preference with Label Studio:

- If you're using SuperInsight in Chinese, Label Studio will display in Chinese
- If you're using SuperInsight in English, Label Studio will display in English

### Changing Language

1. Click the language switcher in the top navigation bar
2. Select your preferred language (中文 or English)
3. The Label Studio interface will automatically update

**Note:** When changing language, the Label Studio iframe will reload to apply the new language setting.

## Troubleshooting

### "Project not found" Error

**Cause:** The Label Studio project for this task doesn't exist yet.

**Solution:** 
- Click **开始标注** again - the system will automatically create the project
- Wait for the project creation to complete (usually 2-3 seconds)

### "Authentication failed" Error

**Cause:** Your session may have expired or Label Studio authentication failed.

**Solution:**
1. Refresh the page
2. If the error persists, log out and log back in
3. Contact your administrator if the issue continues

### "Service unavailable" Error

**Cause:** Label Studio service is not running or unreachable.

**Solution:**
1. Wait a few moments and try again
2. Check if Label Studio is running (contact your administrator)
3. Try the **在新窗口打开** option as an alternative

### Label Studio Not Loading

**Cause:** Network issues or browser compatibility problems.

**Solution:**
1. Check your internet connection
2. Try refreshing the page
3. Clear your browser cache
4. Try a different browser (Chrome or Firefox recommended)

### Language Not Changing

**Cause:** The iframe may not have reloaded properly.

**Solution:**
1. Click the **重新加载** (Reload) button in the annotation interface
2. If that doesn't work, navigate away and return to the annotation page

## Best Practices

### For Efficient Annotation

1. **Use keyboard shortcuts** - Label Studio supports hotkeys for faster annotation
2. **Save frequently** - Although auto-save is enabled, manually save important work
3. **Take breaks** - Annotation quality decreases with fatigue

### For Quality Annotations

1. **Read the instructions** - Each task may have specific annotation guidelines
2. **Be consistent** - Apply the same criteria throughout the task
3. **Ask questions** - If unsure, consult with your team lead

### For Team Collaboration

1. **Check progress** - Monitor the task progress in the task detail page
2. **Communicate** - Use the collaboration features to discuss difficult cases
3. **Review** - Participate in quality review when assigned

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Submit annotation |
| `Ctrl + S` | Save current work |
| `Esc` | Cancel current selection |
| `←` / `→` | Navigate between tasks |

## FAQ

### Q: Can I annotate offline?

A: No, annotation requires an active connection to the SuperInsight and Label Studio servers.

### Q: How do I know my progress?

A: The task detail page shows your progress percentage and the number of completed items.

### Q: Can I undo an annotation?

A: Yes, you can modify or delete annotations before submitting. After submission, contact your administrator for changes.

### Q: What happens if I close the browser accidentally?

A: Your work is automatically saved. When you return, you can continue from where you left off.

### Q: Can I work on multiple tasks at once?

A: Yes, you can open multiple tasks in different browser tabs using the **在新窗口打开** option.

## Support

If you encounter issues not covered in this guide:

1. Check the [API Documentation](./label_studio_annotation_workflow_api.md)
2. Contact your system administrator
3. Submit a support ticket through the help desk

---

**Last Updated:** 2026-01-26  
**Version:** 1.0
