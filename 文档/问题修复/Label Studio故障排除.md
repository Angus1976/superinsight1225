# Label Studio iframe 集成故障排查指南

## 概述

本指南提供了 Label Studio iframe 集成过程中常见问题的诊断方法和解决方案。

## 常见问题分类

### 1. iframe 加载问题

#### 问题：iframe 无法加载或显示空白页面

**症状**:
- iframe 容器显示空白
- 控制台显示加载错误
- 长时间显示加载状态

**可能原因**:
1. Label Studio 服务未启动
2. URL 配置错误
3. 网络连接问题
4. CORS 配置问题

**诊断步骤**:

```typescript
// 1. 检查 Label Studio 服务状态
const checkLabelStudioStatus = async () => {
  try {
    const response = await fetch(`${LABEL_STUDIO_URL}/api/health`);
    console.log('Label Studio status:', response.status);
    return response.ok;
  } catch (error) {
    console.error('Label Studio connection failed:', error);
    return false;
  }
};

// 2. 检查 iframe 配置
const validateIframeConfig = (config: IframeConfig) => {
  const errors: string[] = [];
  
  if (!config.url) errors.push('URL is required');
  if (!config.projectId) errors.push('Project ID is required');
  if (!config.taskId) errors.push('Task ID is required');
  if (!config.token) errors.push('Token is required');
  
  return errors;
};

// 3. 检查网络连接
const checkNetworkConnectivity = async () => {
  try {
    const response = await fetch(LABEL_STUDIO_URL, { method: 'HEAD' });
    return response.ok;
  } catch (error) {
    console.error('Network connectivity check failed:', error);
    return false;
  }
};
```

**解决方案**:

1. **检查服务状态**:
   ```bash
   # 检查 Label Studio 服务
   curl http://localhost:8080/api/health
   
   # 重启 Label Studio 服务
   docker-compose restart label-studio
   ```

2. **修复 CORS 配置**:
   ```python
   # Label Studio 设置
   CORS_ALLOW_ALL_ORIGINS = False
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
       "https://your-domain.com"
   ]
   ```

3. **验证 URL 配置**:
   ```typescript
   // 确保 URL 格式正确
   const config = {
     url: 'http://localhost:8080/projects/1/data/1',
     // 其他配置...
   };
   ```

#### 问题：iframe 加载超时

**症状**:
- iframe 长时间处于加载状态
- 控制台显示超时错误

**解决方案**:

```typescript
// 增加超时时间
const config = {
  timeout: 60000, // 60秒
  retryAttempts: 5,
  // 其他配置...
};

// 实现重试机制
const createIframeWithRetry = async (config: IframeConfig, attempts = 3) => {
  for (let i = 0; i < attempts; i++) {
    try {
      return await iframeManager.create(config);
    } catch (error) {
      if (i === attempts - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 2000 * (i + 1)));
    }
  }
};
```

### 2. 通信问题

#### 问题：PostMessage 通信失败

**症状**:
- 消息发送后无响应
- 控制台显示通信错误
- 数据同步失败

**诊断步骤**:

```typescript
// 1. 检查消息格式
const validateMessage = (message: Message) => {
  const required = ['id', 'type', 'payload', 'timestamp'];
  const missing = required.filter(field => !message[field]);
  
  if (missing.length > 0) {
    console.error('Missing required fields:', missing);
    return false;
  }
  
  return true;
};

// 2. 检查通信状态
const checkBridgeStatus = (bridge: PostMessageBridge) => {
  const status = bridge.getStatus();
  console.log('Bridge status:', status);
  
  if (status !== 'connected') {
    console.error('Bridge not connected');
    return false;
  }
  
  return true;
};

// 3. 测试消息发送
const testMessageSending = async (bridge: PostMessageBridge) => {
  try {
    const response = await bridge.send({
      id: 'test-message',
      type: 'PING',
      payload: { test: true },
      timestamp: Date.now()
    });
    
    console.log('Test message response:', response);
    return response.success;
  } catch (error) {
    console.error('Test message failed:', error);
    return false;
  }
};
```

**解决方案**:

1. **检查消息签名**:
   ```typescript
   // 启用消息签名验证
   const bridge = new PostMessageBridge(iframe, {
     requireSignature: true,
     secretKey: 'your-secret-key'
   });
   ```

2. **增加重试机制**:
   ```typescript
   const sendWithRetry = async (message: Message, maxRetries = 3) => {
     for (let i = 0; i < maxRetries; i++) {
       try {
         return await bridge.send(message);
       } catch (error) {
         if (i === maxRetries - 1) throw error;
         await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
       }
     }
   };
   ```

3. **调试消息流**:
   ```typescript
   // 启用详细日志
   bridge.on('messageSent', (message) => {
     console.log('Message sent:', message);
   });
   
   bridge.on('messageReceived', (message) => {
     console.log('Message received:', message);
   });
   
   bridge.on('messageError', (error) => {
     console.error('Message error:', error);
   });
   ```

### 3. 权限问题

#### 问题：权限验证失败

**症状**:
- 用户无法执行标注操作
- 控制台显示权限错误
- 功能按钮被禁用

**诊断步骤**:

```typescript
// 1. 检查权限配置
const validatePermissions = (permissions: Permission[]) => {
  const requiredActions = ['annotate', 'view', 'save'];
  const hasRequired = requiredActions.every(action => 
    permissions.some(p => p.action === action && p.allowed)
  );
  
  if (!hasRequired) {
    console.error('Missing required permissions');
    return false;
  }
  
  return true;
};

// 2. 检查权限上下文
const validateContext = (context: AnnotationContext) => {
  if (!context.user || !context.project || !context.task) {
    console.error('Incomplete context');
    return false;
  }
  
  if (Date.now() - context.timestamp > 3600000) { // 1小时
    console.error('Context expired');
    return false;
  }
  
  return true;
};

// 3. 测试权限检查
const testPermissionCheck = (contextManager: ContextManager) => {
  const actions = ['annotate', 'view', 'save', 'delete'];
  
  actions.forEach(action => {
    const allowed = contextManager.checkPermission(action);
    console.log(`Permission ${action}:`, allowed);
  });
};
```

**解决方案**:

1. **更新权限配置**:
   ```typescript
   const permissions: Permission[] = [
     { action: 'annotate', resource: 'task', allowed: true },
     { action: 'view', resource: 'task', allowed: true },
     { action: 'save', resource: 'annotation', allowed: true },
     { action: 'delete', resource: 'annotation', allowed: false }
   ];
   ```

2. **刷新权限**:
   ```typescript
   // 定期刷新权限
   const refreshPermissions = async () => {
     try {
       const newPermissions = await fetchUserPermissions(userId);
       contextManager.updatePermissions(newPermissions);
     } catch (error) {
       console.error('Failed to refresh permissions:', error);
     }
   };
   
   // 每30分钟刷新一次
   setInterval(refreshPermissions, 30 * 60 * 1000);
   ```

### 4. 数据同步问题

#### 问题：标注数据同步失败

**症状**:
- 标注数据未保存到后端
- 同步状态显示错误
- 数据丢失或不一致

**诊断步骤**:

```typescript
// 1. 检查同步状态
const checkSyncStatus = (syncManager: SyncManager) => {
  const status = syncManager.getStatus();
  console.log('Sync status:', status);
  
  if (status === 'error') {
    console.error('Sync is in error state');
    return false;
  }
  
  return true;
};

// 2. 测试手动同步
const testManualSync = async (syncManager: SyncManager) => {
  try {
    const result = await syncManager.sync();
    console.log('Manual sync result:', result);
    return result.success;
  } catch (error) {
    console.error('Manual sync failed:', error);
    return false;
  }
};

// 3. 检查网络连接
const checkApiConnectivity = async () => {
  try {
    const response = await fetch('/api/health');
    return response.ok;
  } catch (error) {
    console.error('API connectivity check failed:', error);
    return false;
  }
};
```

**解决方案**:

1. **启用离线缓存**:
   ```typescript
   const syncManager = new SyncManager({
     enableOfflineCache: true,
     cacheSize: 1000,
     syncInterval: 30000 // 30秒
   });
   ```

2. **实现冲突解决**:
   ```typescript
   syncManager.on('syncConflict', (conflict) => {
     // 自动解决冲突或提示用户
     const resolution = resolveConflict(conflict);
     syncManager.resolveConflict(conflict.id, resolution);
   });
   ```

3. **增加错误恢复**:
   ```typescript
   syncManager.on('syncError', async (error) => {
     console.error('Sync error:', error);
     
     // 等待网络恢复后重试
     await waitForNetworkRecovery();
     await syncManager.sync();
   });
   ```

### 5. 性能问题

#### 问题：iframe 加载缓慢或卡顿

**症状**:
- iframe 加载时间过长
- 操作响应缓慢
- 内存占用过高

**诊断步骤**:

```typescript
// 1. 监控性能指标
const monitorPerformance = (monitor: PerformanceMonitor) => {
  monitor.on('metricsUpdated', (metrics) => {
    console.log('Performance metrics:', metrics);
    
    if (metrics.loadTime > 5000) {
      console.warn('Load time too high:', metrics.loadTime);
    }
    
    if (metrics.memoryUsage > 100 * 1024 * 1024) { // 100MB
      console.warn('Memory usage too high:', metrics.memoryUsage);
    }
  });
};

// 2. 检查资源缓存
const checkResourceCache = (cache: ResourceCache) => {
  const stats = cache.getStats();
  console.log('Cache stats:', stats);
  
  if (stats.hitRate < 0.8) {
    console.warn('Low cache hit rate:', stats.hitRate);
  }
};

// 3. 分析加载时间
const analyzeLoadTime = () => {
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  const loadTime = navigation.loadEventEnd - navigation.fetchStart;
  
  console.log('Page load time:', loadTime);
  
  if (loadTime > 3000) {
    console.warn('Page load time too high');
  }
};
```

**解决方案**:

1. **启用懒加载**:
   ```typescript
   const lazyLoader = new LazyLoader({
     threshold: 0.1,
     rootMargin: '50px'
   });
   
   lazyLoader.observe(iframeContainer);
   ```

2. **优化资源缓存**:
   ```typescript
   const cache = new ResourceCache({
     maxSize: 50 * 1024 * 1024, // 50MB
     ttl: 3600000 // 1小时
   });
   ```

3. **实现预加载**:
   ```typescript
   // 预加载下一个任务
   const preloadNextTask = async (nextTaskId: string) => {
     try {
       await cache.preload(`/api/tasks/${nextTaskId}`);
     } catch (error) {
       console.error('Preload failed:', error);
     }
   };
   ```

### 6. 安全问题

#### 问题：安全策略违规

**症状**:
- CSP 违规警告
- 跨域请求被阻止
- 消息验证失败

**诊断步骤**:

```typescript
// 1. 检查 CSP 策略
const checkCSPViolations = () => {
  document.addEventListener('securitypolicyviolation', (event) => {
    console.error('CSP violation:', {
      violatedDirective: event.violatedDirective,
      blockedURI: event.blockedURI,
      originalPolicy: event.originalPolicy
    });
  });
};

// 2. 验证消息来源
const validateMessageOrigin = (event: MessageEvent) => {
  const allowedOrigins = ['http://localhost:8080', 'https://label-studio.com'];
  
  if (!allowedOrigins.includes(event.origin)) {
    console.error('Invalid message origin:', event.origin);
    return false;
  }
  
  return true;
};

// 3. 检查加密状态
const checkEncryptionStatus = (encryption: DataEncryption) => {
  const status = encryption.getStatus();
  console.log('Encryption status:', status);
  
  if (!status.enabled) {
    console.warn('Encryption is disabled');
  }
};
```

**解决方案**:

1. **更新 CSP 策略**:
   ```html
   <meta http-equiv="Content-Security-Policy" 
         content="frame-src 'self' http://localhost:8080 https://label-studio.com; 
                  script-src 'self' 'unsafe-inline'; 
                  style-src 'self' 'unsafe-inline';">
   ```

2. **配置消息验证**:
   ```typescript
   const security = new MessageSecurity({
     allowedOrigins: ['http://localhost:8080'],
     requireSignature: true,
     encryptionKey: 'your-encryption-key'
   });
   ```

3. **启用审计日志**:
   ```typescript
   const auditLogger = new SecurityAuditLogger({
     logLevel: 'info',
     logToConsole: true,
     logToServer: true
   });
   ```

## 调试工具

### 1. 开发者工具扩展

```typescript
// 创建调试面板
const createDebugPanel = () => {
  const panel = document.createElement('div');
  panel.id = 'label-studio-debug-panel';
  panel.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    width: 300px;
    background: white;
    border: 1px solid #ccc;
    padding: 10px;
    z-index: 9999;
  `;
  
  document.body.appendChild(panel);
  return panel;
};

// 显示实时状态
const updateDebugInfo = (panel: HTMLElement, info: any) => {
  panel.innerHTML = `
    <h3>Label Studio Debug Info</h3>
    <p>Status: ${info.status}</p>
    <p>Load Time: ${info.loadTime}ms</p>
    <p>Memory Usage: ${(info.memoryUsage / 1024 / 1024).toFixed(2)}MB</p>
    <p>Messages Sent: ${info.messagesSent}</p>
    <p>Messages Received: ${info.messagesReceived}</p>
  `;
};
```

### 2. 日志收集器

```typescript
// 统一日志收集
class LogCollector {
  private logs: LogEntry[] = [];
  
  collect(level: 'info' | 'warn' | 'error', message: string, data?: any) {
    const entry: LogEntry = {
      timestamp: Date.now(),
      level,
      message,
      data,
      source: 'label-studio-iframe'
    };
    
    this.logs.push(entry);
    
    // 发送到服务器
    if (level === 'error') {
      this.sendToServer(entry);
    }
  }
  
  private async sendToServer(entry: LogEntry) {
    try {
      await fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry)
      });
    } catch (error) {
      console.error('Failed to send log to server:', error);
    }
  }
  
  export() {
    return JSON.stringify(this.logs, null, 2);
  }
}
```

### 3. 健康检查工具

```typescript
// 系统健康检查
const performHealthCheck = async () => {
  const results = {
    labelStudioService: false,
    apiConnectivity: false,
    iframeStatus: false,
    communicationStatus: false,
    syncStatus: false
  };
  
  try {
    // 检查 Label Studio 服务
    const lsResponse = await fetch(`${LABEL_STUDIO_URL}/api/health`);
    results.labelStudioService = lsResponse.ok;
    
    // 检查 API 连接
    const apiResponse = await fetch('/api/health');
    results.apiConnectivity = apiResponse.ok;
    
    // 检查 iframe 状态
    results.iframeStatus = iframeManager.getStatus() === 'ready';
    
    // 检查通信状态
    results.communicationStatus = bridge.getStatus() === 'connected';
    
    // 检查同步状态
    results.syncStatus = syncManager.getStatus() !== 'error';
    
  } catch (error) {
    console.error('Health check failed:', error);
  }
  
  return results;
};
```

## 联系支持

如果以上解决方案无法解决您的问题，请联系技术支持：

- **邮箱**: support@superinsight.com
- **文档**: [在线文档](https://docs.superinsight.com)
- **GitHub**: [问题反馈](https://github.com/superinsight/issues)

提交问题时，请包含：
1. 详细的错误描述
2. 浏览器控制台日志
3. 系统环境信息
4. 重现步骤

---

**版本**: v1.0  
**更新日期**: 2026年1月5日