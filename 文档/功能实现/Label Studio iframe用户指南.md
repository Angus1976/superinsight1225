# Label Studio iframe Integration User Guide

## Introduction

Welcome to the Label Studio integration in SuperInsight! This guide will help you understand how to use the embedded annotation interface effectively.

## Getting Started

### Accessing the Annotation Interface

1. Log in to SuperInsight
2. Navigate to your project
3. Click on "Annotate" or "Start Annotation"
4. The Label Studio interface will load within the page

### Interface Overview

The annotation interface consists of:

- **Annotation Panel**: Main area for viewing and annotating data
- **Toolbar**: Tools for annotation (labels, shapes, etc.)
- **Task Navigation**: Move between tasks
- **Status Bar**: Shows sync status and current task info

## Basic Operations

### Creating Annotations

1. Select the appropriate tool from the toolbar
2. Click or drag on the data to create an annotation
3. Choose a label from the available options
4. Your annotation is automatically saved

### Editing Annotations

1. Click on an existing annotation to select it
2. Modify the annotation as needed
3. Changes are saved automatically

### Deleting Annotations

1. Select the annotation you want to delete
2. Press the Delete key or click the delete button
3. Confirm the deletion if prompted

## Navigation

### Task Navigation

| Action | Shortcut | Description |
|--------|----------|-------------|
| Next Task | `Ctrl+→` | Go to next task |
| Previous Task | `Ctrl+←` | Go to previous task |
| Submit | `Ctrl+Enter` | Submit current annotation |

### View Controls

| Action | Shortcut | Description |
|--------|----------|-------------|
| Fullscreen | `F11` | Toggle fullscreen mode |
| Exit Fullscreen | `Escape` | Exit fullscreen mode |
| Zoom In | `Ctrl++` | Zoom in on content |
| Zoom Out | `Ctrl+-` | Zoom out on content |
| Reset Zoom | `Ctrl+0` | Reset to default zoom |

## Synchronization

### Understanding Sync Status

The sync indicator shows the current synchronization state:

| Icon | Status | Description |
|------|--------|-------------|
| ✓ Green | Synced | All changes saved |
| ↻ Blue | Syncing | Saving changes... |
| ⚠ Yellow | Pending | Changes waiting to sync |
| ✗ Red | Error | Sync failed |

### Manual Sync

If automatic sync fails:

1. Click the sync icon in the status bar
2. Select "Force Sync"
3. Wait for sync to complete

### Offline Mode

When working offline:

1. Continue annotating normally
2. Changes are saved locally
3. When online, changes sync automatically

## Handling Conflicts

### What is a Conflict?

A conflict occurs when:
- Multiple users edit the same annotation
- Your local changes conflict with server changes

### Resolving Conflicts

1. A conflict notification appears
2. Review both versions:
   - **Your Version**: Your local changes
   - **Server Version**: Changes from server
3. Choose an option:
   - **Keep Mine**: Use your changes
   - **Keep Server**: Use server changes
   - **Merge**: Combine both (if available)

## Permissions

### Understanding Your Role

| Role | Can View | Can Edit | Can Delete | Can Manage |
|------|----------|----------|------------|------------|
| Viewer | ✓ | ✗ | ✗ | ✗ |
| Annotator | ✓ | ✓ | ✗ | ✗ |
| Reviewer | ✓ | ✓ | ✓ | ✗ |
| Admin | ✓ | ✓ | ✓ | ✓ |

### Permission Errors

If you see "Permission Denied":
1. Check your assigned role
2. Contact your project administrator
3. Request appropriate permissions

## Best Practices

### Annotation Quality

1. **Be Consistent**: Follow the annotation guidelines
2. **Be Precise**: Make accurate selections
3. **Review Your Work**: Check annotations before submitting
4. **Use Shortcuts**: Learn keyboard shortcuts for efficiency

### Performance Tips

1. **Stable Connection**: Use a reliable internet connection
2. **Regular Saves**: Don't wait too long between saves
3. **Clear Cache**: If experiencing issues, clear browser cache
4. **Close Unused Tabs**: Free up browser resources

## Troubleshooting

### Common Issues

#### Interface Not Loading

1. Refresh the page
2. Clear browser cache
3. Check internet connection
4. Try a different browser

#### Changes Not Saving

1. Check sync status indicator
2. Click "Force Sync"
3. Check internet connection
4. Contact support if issue persists

#### Slow Performance

1. Close other browser tabs
2. Clear browser cache
3. Reduce zoom level
4. Use a faster internet connection

### Getting Help

If you encounter issues:

1. Check this user guide
2. Review the troubleshooting section
3. Contact your project administrator
4. Submit a support ticket

## Keyboard Shortcuts Reference

### General

| Shortcut | Action |
|----------|--------|
| `F11` | Toggle fullscreen |
| `Escape` | Exit fullscreen / Cancel |
| `Ctrl+S` | Save annotation |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

### Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+→` | Next task |
| `Ctrl+←` | Previous task |
| `Ctrl+Enter` | Submit annotation |
| `Tab` | Next field |
| `Shift+Tab` | Previous field |

### Annotation

| Shortcut | Action |
|----------|--------|
| `Delete` | Delete selected |
| `Ctrl+A` | Select all |
| `Ctrl+D` | Duplicate selected |
| `1-9` | Quick label selection |

## FAQ

### Q: Can I work offline?

A: Yes, changes are saved locally and sync when you're back online.

### Q: How do I know if my work is saved?

A: Check the sync status indicator. Green checkmark means saved.

### Q: Can multiple people annotate the same task?

A: This depends on project settings. Contact your administrator.

### Q: How do I report a bug?

A: Use the feedback button or contact support with details.

### Q: Can I customize the interface?

A: Some customization is available in Settings. Contact admin for more options.

## Version Information

- User Guide Version: 1.0
- Last Updated: January 2026
- Compatible with SuperInsight 2.3+
