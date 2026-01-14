# Label Studio iframe Integration Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common issues with the Label Studio iframe integration.

## Diagnostic Tools

### Browser Console

Open browser developer tools (F12) and check the Console tab for errors:

```javascript
// Enable verbose logging
localStorage.setItem('IFRAME_DEBUG', 'true');
```

### Network Tab

Check the Network tab for:
- Failed requests (red entries)
- CORS errors
- Blocked resources

### Performance Monitor

```typescript
import { PerformanceMonitor } from '@/services/iframe';

const monitor = new PerformanceMonitor();
const metrics = monitor.getMetrics();
console.log('Performance metrics:', metrics);
```

## Common Issues

### 1. Iframe Not Loading

**Symptoms:**
- Blank iframe
- Loading spinner never disappears
- Console shows "Refused to display in a frame"

**Causes:**
- X-Frame-Options header blocking embedding
- CSP frame-src directive missing
- Invalid URL

**Solutions:**

1. Check Label Studio server configuration:
```nginx
# nginx.conf
add_header X-Frame-Options "ALLOW-FROM https://superinsight.example.com";
```

2. Update CSP headers:
```
Content-Security-Policy: frame-ancestors 'self' https://superinsight.example.com;
```

3. Verify URL is correct:
```typescript
console.log('Iframe URL:', config.url);
// Should be: https://labelstudio.example.com/projects/1/data
```

### 2. Communication Failures

**Symptoms:**
- Messages not received
- Timeout errors
- "Message from untrusted origin" warnings

**Causes:**
- Origin mismatch
- Iframe not fully loaded
- Message format incorrect

**Solutions:**

1. Verify origin configuration:
```typescript
const bridge = new PostMessageBridge({
  targetOrigin: 'https://labelstudio.example.com', // Must match exactly
});
```

2. Wait for iframe load:
```typescript
iframe.addEventListener('load', async () => {
  await bridge.initialize(iframe.contentWindow);
});
```

3. Check message format:
```typescript
// Correct format
const message = {
  id: 'unique-id',
  type: 'annotation:update',
  payload: { ... },
  timestamp: Date.now(),
};
```

### 3. Permission Denied Errors

**Symptoms:**
- "Permission denied" messages
- Actions blocked
- UI elements disabled

**Causes:**
- Missing permissions in context
- Role not authorized
- Permission cache stale

**Solutions:**

1. Check user permissions:
```typescript
const context = contextManager.getContext();
console.log('User permissions:', context.permissions);
```

2. Clear permission cache:
```typescript
permissionController.clearCache();
```

3. Verify role hierarchy:
```typescript
const effectivePermissions = permissionController.getEffectivePermissions(context);
console.log('Effective permissions:', effectivePermissions);
```

### 4. Synchronization Issues

**Symptoms:**
- Data not saving
- Conflicts appearing
- Sync status stuck

**Causes:**
- Network connectivity issues
- Backend API errors
- Concurrent edits

**Solutions:**

1. Check sync status:
```typescript
const stats = syncManager.getStats();
console.log('Sync stats:', stats);
// { totalOperations: 10, completedOperations: 8, failedOperations: 2, pendingOperations: 0 }
```

2. Force sync:
```typescript
try {
  await syncManager.forceSync();
} catch (error) {
  console.error('Sync failed:', error);
}
```

3. Resolve conflicts:
```typescript
const conflicts = syncManager.getConflicts();
for (const conflict of conflicts) {
  console.log('Conflict:', conflict);
  await syncManager.resolveConflictManually(conflict.id, 'remote');
}
```

### 5. UI Coordination Problems

**Symptoms:**
- Fullscreen not working
- Keyboard shortcuts not responding
- Focus issues

**Causes:**
- Focus trap not configured
- Keyboard events not propagating
- Container element issues

**Solutions:**

1. Check UI state:
```typescript
const state = uiCoordinator.getUIState();
console.log('UI state:', state);
```

2. Verify container:
```typescript
const container = document.getElementById('iframe-container');
console.log('Container:', container);
console.log('Container dimensions:', container.getBoundingClientRect());
```

3. Reset UI state:
```typescript
uiCoordinator.cleanup();
uiCoordinator.initialize(iframe, container);
```

### 6. Performance Issues

**Symptoms:**
- Slow loading
- Laggy interactions
- High memory usage

**Causes:**
- Large data sets
- Memory leaks
- Too many event listeners

**Solutions:**

1. Monitor performance:
```typescript
const monitor = new PerformanceMonitor();
setInterval(() => {
  const metrics = monitor.getMetrics();
  console.log('Memory:', metrics.memoryUsage);
  console.log('CPU:', metrics.cpuUsage);
}, 5000);
```

2. Clear caches:
```typescript
resourceCache.clear();
syncManager.clearCache();
```

3. Reduce sync frequency:
```typescript
const syncManager = new SyncManager({
  syncInterval: 30000, // Increase from 5000 to 30000
});
```

## Error Codes Reference

| Code | Description | Solution |
|------|-------------|----------|
| `E001` | Iframe load timeout | Increase timeout, check network |
| `E002` | Message timeout | Retry, check iframe state |
| `E003` | Permission denied | Check user permissions |
| `E004` | Sync conflict | Resolve manually |
| `E005` | Security violation | Check origin configuration |
| `E006` | Invalid configuration | Verify config parameters |
| `E007` | Network error | Check connectivity |
| `E008` | Authentication failed | Refresh token |

## Logging

### Enable Debug Logging

```typescript
// In development
if (process.env.NODE_ENV === 'development') {
  window.IFRAME_DEBUG = true;
}
```

### Log Levels

```typescript
import { Logger } from '@/services/iframe';

Logger.setLevel('debug'); // 'error' | 'warn' | 'info' | 'debug'
```

### Export Logs

```typescript
const logs = Logger.export();
console.log(JSON.stringify(logs, null, 2));
```

## Health Checks

### System Health

```typescript
const healthCheck = async () => {
  const results = {
    iframe: iframeManager.getState().status === 'loaded',
    bridge: bridge.isConnected(),
    sync: syncManager.getStats().failedOperations === 0,
  };
  
  console.log('Health check:', results);
  return Object.values(results).every(v => v);
};
```

### Automated Recovery

```typescript
const recoveryManager = new AutoRecoveryManager({
  enableAutoRecovery: true,
  healthCheckInterval: 30000,
  maxRecoveryAttempts: 3,
});

recoveryManager.on('recovery:failed', () => {
  showErrorMessage('Unable to recover. Please refresh the page.');
});
```

## Support

If issues persist after following this guide:

1. Collect diagnostic information:
   - Browser console logs
   - Network requests
   - Performance metrics
   - Error codes

2. Contact support with:
   - Issue description
   - Steps to reproduce
   - Diagnostic information
   - Environment details (browser, OS)

## Version Compatibility

| SuperInsight | Label Studio | Status |
|--------------|--------------|--------|
| 2.3.x | 1.8.x+ | Supported |
| 2.2.x | 1.7.x+ | Supported |
| 2.1.x | 1.6.x+ | Limited |
