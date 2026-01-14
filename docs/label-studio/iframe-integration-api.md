# Label Studio iframe Integration API Documentation

## Overview

The Label Studio iframe Integration module provides seamless embedding of Label Studio annotation interface within the SuperInsight platform. This documentation covers the API reference, configuration options, and usage patterns.

## Core Components

### IframeManager

Manages iframe lifecycle, creation, destruction, and state management.

```typescript
import { IframeManager } from '@/services/iframe/IframeManager';

const iframeManager = new IframeManager();
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `create(config, container)` | `IframeConfig, HTMLElement` | `Promise<HTMLIFrameElement>` | Creates and initializes an iframe |
| `destroy()` | - | `Promise<void>` | Destroys the current iframe |
| `reload()` | - | `Promise<void>` | Reloads the iframe content |
| `getIframe()` | - | `HTMLIFrameElement \| null` | Returns the current iframe element |
| `getState()` | - | `IframeState` | Returns current iframe state |

#### IframeConfig

```typescript
interface IframeConfig {
  url: string;              // Label Studio URL
  projectId: string;        // Project identifier
  taskId?: string;          // Optional task identifier
  userId: string;           // User identifier
  token: string;            // Authentication token
  permissions: Permission[]; // User permissions
  theme?: 'light' | 'dark'; // UI theme
  fullscreen?: boolean;     // Start in fullscreen mode
  timeout?: number;         // Load timeout in ms (default: 30000)
  retryAttempts?: number;   // Retry attempts on failure (default: 3)
}
```

### PostMessageBridge

Handles secure bidirectional communication between main window and iframe.

```typescript
import { PostMessageBridge } from '@/services/iframe/PostMessageBridge';

const bridge = new PostMessageBridge({
  targetOrigin: 'https://labelstudio.example.com',
  timeout: 5000,
  maxRetries: 3,
});
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `initialize(targetWindow)` | `Window` | `Promise<void>` | Initializes the bridge |
| `send(message)` | `Message` | `Promise<Response>` | Sends a message and waits for response |
| `on(event, handler)` | `string, Function` | `void` | Registers an event handler |
| `off(event, handler)` | `string, Function` | `void` | Removes an event handler |
| `cleanup()` | - | `void` | Cleans up resources |

#### Message Types

```typescript
interface Message {
  id: string;
  type: string;
  payload: unknown;
  timestamp: number;
  signature?: string;
  source?: 'main' | 'iframe';
}
```

### ContextManager

Manages annotation context and user session data.

```typescript
import { ContextManager } from '@/services/iframe/ContextManager';

const contextManager = new ContextManager();
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `setContext(context)` | `AnnotationContext` | `void` | Sets the current context |
| `getContext()` | - | `AnnotationContext \| null` | Gets the current context |
| `updateContext(updates)` | `Partial<AnnotationContext>` | `void` | Updates context fields |
| `clearContext()` | - | `void` | Clears the current context |

### PermissionController

Handles permission checking and access control.

```typescript
import { PermissionController } from '@/services/iframe/PermissionController';

const permissionController = new PermissionController();
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `checkPermission(context, action, resource)` | `AnnotationContext, string, string` | `boolean` | Checks if action is allowed |
| `updateUserPermissions(context, permissions)` | `AnnotationContext, Permission[]` | `AnnotationContext` | Updates user permissions |
| `getEffectivePermissions(context)` | `AnnotationContext` | `Permission[]` | Gets all effective permissions |

### SyncManager

Manages data synchronization between frontend and backend.

```typescript
import { SyncManager } from '@/services/iframe/SyncManager';

const syncManager = new SyncManager({
  enableIncrementalSync: true,
  syncInterval: 5000,
  maxRetries: 3,
});
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `addOperation(type, data)` | `string, AnnotationData` | `Promise<void>` | Adds a sync operation |
| `forceSync()` | - | `Promise<void>` | Forces immediate synchronization |
| `getStats()` | - | `SyncStats` | Gets synchronization statistics |
| `getConflicts()` | - | `Conflict[]` | Gets unresolved conflicts |
| `resolveConflictManually(id, resolution)` | `string, string` | `Promise<void>` | Resolves a conflict |
| `destroy()` | - | `void` | Stops sync and cleans up |

### UICoordinator

Coordinates UI state between main window and iframe.

```typescript
import { UICoordinator } from '@/services/iframe/UICoordinator';

const uiCoordinator = new UICoordinator({
  enableFullscreen: true,
  enableKeyboardShortcuts: true,
});
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `initialize(iframe, container)` | `HTMLIFrameElement, HTMLElement` | `void` | Initializes the coordinator |
| `setFullscreen(enabled)` | `boolean` | `void` | Sets fullscreen mode |
| `toggleFullscreen()` | - | `void` | Toggles fullscreen mode |
| `resize(width, height)` | `number, number` | `void` | Resizes the iframe |
| `getUIState()` | - | `UIState` | Gets current UI state |
| `cleanup()` | - | `void` | Cleans up resources |

## Events

### IframeManager Events

| Event | Payload | Description |
|-------|---------|-------------|
| `iframe:created` | `{ iframe: HTMLIFrameElement }` | Iframe created |
| `iframe:loaded` | `{ iframe: HTMLIFrameElement }` | Iframe content loaded |
| `iframe:error` | `{ error: Error }` | Iframe error occurred |
| `iframe:destroyed` | `{}` | Iframe destroyed |

### PostMessageBridge Events

| Event | Payload | Description |
|-------|---------|-------------|
| `message:received` | `{ message: Message }` | Message received |
| `message:sent` | `{ message: Message }` | Message sent |
| `security:violation` | `{ origin: string }` | Security violation detected |

### SyncManager Events

| Event | Payload | Description |
|-------|---------|-------------|
| `sync:started` | `{}` | Sync started |
| `sync:completed` | `{ stats: SyncStats }` | Sync completed |
| `sync:error` | `{ error: Error }` | Sync error |
| `conflict:detected` | `{ conflict: Conflict }` | Conflict detected |

## Security

### Origin Validation

All messages are validated against the configured `targetOrigin`. Messages from untrusted origins are rejected.

### Message Signing

Optional message signing using HMAC-SHA256 for additional security:

```typescript
const bridge = new PostMessageBridge({
  targetOrigin: 'https://labelstudio.example.com',
  enableSigning: true,
  signingKey: 'your-secret-key',
});
```

### Content Security Policy

Recommended CSP headers for iframe integration:

```
Content-Security-Policy: frame-src 'self' https://labelstudio.example.com;
```

## Error Handling

### Error Types

| Error Code | Description | Recovery |
|------------|-------------|----------|
| `IFRAME_LOAD_ERROR` | Failed to load iframe | Retry with exponential backoff |
| `MESSAGE_TIMEOUT` | Message response timeout | Retry or notify user |
| `PERMISSION_DENIED` | Permission check failed | Show error message |
| `SYNC_CONFLICT` | Data conflict detected | Manual resolution required |
| `SECURITY_VIOLATION` | Security check failed | Log and reject |

### Error Recovery

```typescript
import { ErrorHandler } from '@/services/iframe/ErrorHandler';

const errorHandler = new ErrorHandler({
  maxRetries: 3,
  retryDelay: 1000,
  onError: (error) => console.error(error),
});
```

## Performance

### Lazy Loading

```typescript
import { LazyLoader } from '@/services/iframe/LazyLoader';

const lazyLoader = new LazyLoader({
  preloadDelay: 1000,
  cacheSize: 5,
});
```

### Performance Monitoring

```typescript
import { PerformanceMonitor } from '@/services/iframe/PerformanceMonitor';

const monitor = new PerformanceMonitor();
const metrics = monitor.getMetrics();
```

## Version

- API Version: 1.0.0
- Last Updated: January 2026
