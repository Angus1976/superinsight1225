# Label Studio iframe Integration Guide

## Introduction

This guide explains how to integrate Label Studio annotation interface into the SuperInsight platform using the iframe integration module. The integration provides seamless embedding with full permission control, data synchronization, and UI coordination.

## Prerequisites

- SuperInsight platform running (frontend + backend)
- Label Studio instance accessible via HTTPS
- Valid authentication tokens for both systems

## Quick Start

### 1. Basic Integration

```typescript
import { 
  IframeManager, 
  PostMessageBridge, 
  ContextManager,
  SyncManager 
} from '@/services/iframe';

// Initialize components
const iframeManager = new IframeManager();
const bridge = new PostMessageBridge({
  targetOrigin: 'https://labelstudio.example.com',
  timeout: 5000,
});
const contextManager = new ContextManager();
const syncManager = new SyncManager({
  enableIncrementalSync: true,
  syncInterval: 5000,
});

// Create iframe
const container = document.getElementById('annotation-container');
const iframe = await iframeManager.create({
  url: 'https://labelstudio.example.com/projects/1/data',
  projectId: 'project-1',
  userId: 'user-123',
  token: 'auth-token',
  permissions: [
    { action: 'read', resource: 'annotations', allowed: true },
    { action: 'write', resource: 'annotations', allowed: true },
  ],
}, container);

// Initialize communication
await bridge.initialize(iframe.contentWindow);

// Set context
contextManager.setContext({
  user: { id: 'user-123', name: 'John Doe', role: 'annotator' },
  project: { id: 'project-1', name: 'My Project' },
  task: { id: 'task-1', name: 'Annotation Task' },
  permissions: [...],
});
```

### 2. React Component Integration

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { 
  IframeManager, 
  PostMessageBridge,
  UICoordinator 
} from '@/services/iframe';

const LabelStudioEmbed: React.FC<{ projectId: string }> = ({ projectId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const iframeManager = new IframeManager();
    const bridge = new PostMessageBridge({
      targetOrigin: process.env.LABEL_STUDIO_URL,
    });
    const uiCoordinator = new UICoordinator();

    const init = async () => {
      try {
        const iframe = await iframeManager.create({
          url: `${process.env.LABEL_STUDIO_URL}/projects/${projectId}`,
          projectId,
          userId: getCurrentUserId(),
          token: getAuthToken(),
          permissions: getUserPermissions(),
        }, containerRef.current!);

        await bridge.initialize(iframe.contentWindow);
        uiCoordinator.initialize(iframe, containerRef.current!);
        
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    init();

    return () => {
      iframeManager.destroy();
      bridge.cleanup();
      uiCoordinator.cleanup();
    };
  }, [projectId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return <div ref={containerRef} className="label-studio-container" />;
};
```

## Configuration

### Environment Variables

```env
# .env.development
VITE_LABEL_STUDIO_URL=https://labelstudio.example.com
VITE_LABEL_STUDIO_API_KEY=your-api-key
```

### Security Configuration

```typescript
// Configure CSP in your server
const cspConfig = {
  'frame-src': ["'self'", 'https://labelstudio.example.com'],
  'connect-src': ["'self'", 'https://labelstudio.example.com'],
};
```

## Permission Management

### Permission Types

| Action | Resource | Description |
|--------|----------|-------------|
| `read` | `annotations` | View annotations |
| `write` | `annotations` | Create/edit annotations |
| `delete` | `annotations` | Delete annotations |
| `admin` | `projects` | Manage project settings |

### Role-Based Permissions

```typescript
const rolePermissions = {
  viewer: [
    { action: 'read', resource: 'annotations', allowed: true },
  ],
  annotator: [
    { action: 'read', resource: 'annotations', allowed: true },
    { action: 'write', resource: 'annotations', allowed: true },
  ],
  reviewer: [
    { action: 'read', resource: 'annotations', allowed: true },
    { action: 'write', resource: 'annotations', allowed: true },
    { action: 'delete', resource: 'annotations', allowed: true },
  ],
  admin: [
    { action: '*', resource: '*', allowed: true },
  ],
};
```

## Data Synchronization

### Automatic Sync

```typescript
const syncManager = new SyncManager({
  enableIncrementalSync: true,
  syncInterval: 5000, // Sync every 5 seconds
  maxRetries: 3,
  conflictResolution: 'manual', // or 'local' or 'remote'
});

// Listen for sync events
syncManager.addEventListener((event) => {
  switch (event.type) {
    case 'sync_completed':
      console.log('Sync completed:', event.data);
      break;
    case 'conflict_detected':
      handleConflict(event.data);
      break;
  }
});
```

### Manual Sync

```typescript
// Force immediate sync
await syncManager.forceSync();

// Get sync status
const stats = syncManager.getStats();
console.log(`Pending: ${stats.pendingOperations}, Completed: ${stats.completedOperations}`);
```

### Conflict Resolution

```typescript
// Get conflicts
const conflicts = syncManager.getConflicts();

// Resolve conflict
await syncManager.resolveConflictManually(conflicts[0].id, 'remote');
// Options: 'local', 'remote', 'merge'
```

## UI Coordination

### Fullscreen Mode

```typescript
const uiCoordinator = new UICoordinator({
  enableFullscreen: true,
  focusTrapOnFullscreen: true,
});

// Toggle fullscreen
uiCoordinator.toggleFullscreen();

// Check state
const state = uiCoordinator.getUIState();
console.log('Is fullscreen:', state.isFullscreen);
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F11` | Toggle fullscreen |
| `Escape` | Exit fullscreen |
| `Ctrl+Shift+F` | Toggle fullscreen |
| `Ctrl+H` | Toggle navigation |

### Custom Shortcuts

```typescript
const uiCoordinator = new UICoordinator({
  shortcuts: {
    'Ctrl+S': 'save_annotation',
    'Ctrl+N': 'next_task',
    'Ctrl+P': 'previous_task',
  },
});

uiCoordinator.on('shortcut:triggered', (event) => {
  switch (event.action) {
    case 'save_annotation':
      saveCurrentAnnotation();
      break;
  }
});
```

## Error Handling

### Error Recovery

```typescript
import { ErrorHandler, AutoRecoveryManager } from '@/services/iframe';

const errorHandler = new ErrorHandler({
  maxRetries: 3,
  retryDelay: 1000,
});

const recoveryManager = new AutoRecoveryManager({
  enableAutoRecovery: true,
  recoveryStrategies: ['reload', 'reconnect', 'fallback'],
});

// Handle errors
errorHandler.on('error', (error) => {
  if (error.recoverable) {
    recoveryManager.attemptRecovery(error);
  } else {
    showErrorMessage(error.message);
  }
});
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `IFRAME_LOAD_TIMEOUT` | Network issues | Check connectivity, increase timeout |
| `PERMISSION_DENIED` | Missing permissions | Verify user permissions |
| `SYNC_CONFLICT` | Concurrent edits | Resolve conflict manually |
| `SECURITY_VIOLATION` | Invalid origin | Check CORS configuration |

## Performance Optimization

### Lazy Loading

```typescript
import { LazyLoader } from '@/services/iframe';

const lazyLoader = new LazyLoader({
  preloadDelay: 1000,
  cacheSize: 5,
});

// Preload next task
lazyLoader.preload(`/projects/${projectId}/tasks/${nextTaskId}`);
```

### Resource Caching

```typescript
import { ResourceCache } from '@/services/iframe';

const cache = new ResourceCache({
  maxSize: 100,
  ttl: 3600000, // 1 hour
});

// Cache annotation data
cache.set(`annotation:${id}`, annotationData);
```

## Testing

### Unit Testing

```typescript
import { describe, it, expect, vi } from 'vitest';
import { IframeManager } from '@/services/iframe';

describe('IframeManager', () => {
  it('should create iframe', async () => {
    const manager = new IframeManager();
    const container = document.createElement('div');
    
    const iframe = await manager.create({
      url: 'https://labelstudio.example.com',
      projectId: 'test',
      userId: 'user',
      token: 'token',
      permissions: [],
    }, container);
    
    expect(iframe).toBeDefined();
    expect(container.contains(iframe)).toBe(true);
  });
});
```

### Integration Testing

```typescript
import { test, expect } from '@playwright/test';

test('annotation workflow', async ({ page }) => {
  await page.goto('/projects/1/annotate');
  
  // Wait for iframe to load
  const iframe = page.frameLocator('#label-studio-iframe');
  await iframe.locator('.annotation-panel').waitFor();
  
  // Perform annotation
  await iframe.locator('.annotation-tool').click();
  
  // Verify sync
  await expect(page.locator('.sync-status')).toHaveText('Synced');
});
```

## Troubleshooting

### Common Issues

1. **Iframe not loading**
   - Check CORS configuration
   - Verify Label Studio URL is accessible
   - Check browser console for errors

2. **Messages not received**
   - Verify targetOrigin matches Label Studio domain
   - Check if iframe is fully loaded before sending messages

3. **Sync failures**
   - Check network connectivity
   - Verify authentication token is valid
   - Check backend API status

### Debug Mode

```typescript
// Enable debug logging
const bridge = new PostMessageBridge({
  targetOrigin: 'https://labelstudio.example.com',
  debug: true, // Logs all messages
});
```

## Support

For issues and feature requests, please contact the SuperInsight development team or create an issue in the project repository.
