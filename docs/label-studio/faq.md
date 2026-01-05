# Label Studio iframe 集成常见问题解答

## 概述

本文档收集了用户在使用 Label Studio iframe 集成过程中最常遇到的问题和解答，帮助用户快速解决问题。

## 安装和配置

### Q1: 如何配置 Label Studio iframe 集成？

**A**: 按照以下步骤配置：

1. **环境变量配置**:
   ```bash
   # .env 文件
   REACT_APP_LABEL_STUDIO_URL=http://localhost:8080
   REACT_APP_LABEL_STUDIO_API_KEY=your-api-key
   REACT_APP_IFRAME_ALLOWED_ORIGINS=http://localhost:3000
   ```

2. **安装依赖**:
   ```bash
   npm install @types/node crypto-js
   ```

3. **初始化配置**:
   ```typescript
   import { LabelStudioConfig } from '@/config/labelStudioConfig';
   
   const config = new LabelStudioConfig({
     baseUrl: process.env.REACT_APP_LABEL_STUDIO_URL,
     apiKey: process.env.REACT_APP_LABEL_STUDIO_API_KEY
   });
   ```

### Q2: 支持哪些浏览器版本？

**A**: 支持的浏览器版本：
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**注意**: 不支持 Internet Explorer。

### Q3: 如何检查配置是否正确？

**A**: 使用健康检查功能：

```typescript
import { HealthChecker } from '@/services/iframe/HealthChecker';

const checker = new HealthChecker();
const result = await checker.performHealthCheck();

console.log('Health check result:', result);
```

## 功能使用

### Q4: 如何创建新的标注项目？

**A**: 创建标注项目的步骤：

1. **登录系统**: 使用管理员账户登录
2. **进入项目管理**: 点击左侧导航栏的"项目管理"
3. **创建新项目**: 点击"新建项目"按钮
4. **配置项目信息**:
   ```json
   {
     "name": "项目名称",
     "description": "项目描述",
     "dataType": "image", // image, text, audio, video
     "annotationType": "detection", // classification, detection, segmentation
     "labels": ["person", "car", "bike"]
   }
   ```
5. **上传数据**: 批量上传标注数据
6. **分配用户**: 添加标注员和审核员

### Q5: 如何批量上传数据？

**A**: 支持多种批量上传方式：

1. **ZIP 压缩包上传**:
   - 将所有文件打包成 ZIP 格式
   - 在项目页面点击"批量上传"
   - 选择 ZIP 文件并上传

2. **拖拽上传**:
   - 直接将文件拖拽到上传区域
   - 支持多文件同时选择

3. **API 上传**:
   ```typescript
   const uploadData = async (files: File[]) => {
     const formData = new FormData();
     files.forEach(file => formData.append('files', file));
     
     const response = await fetch('/api/projects/upload', {
       method: 'POST',
       body: formData
     });
     
     return response.json();
   };
   ```

### Q6: 如何设置标注权限？

**A**: 权限设置步骤：

1. **进入用户管理**: 在项目设置中选择"用户管理"
2. **添加用户**: 输入用户邮箱或用户名
3. **分配角色**:
   ```typescript
   const permissions = [
     { action: 'annotate', resource: 'task', allowed: true },
     { action: 'review', resource: 'annotation', allowed: false },
     { action: 'export', resource: 'data', allowed: false }
   ];
   ```
4. **保存设置**: 点击"保存"按钮

### Q7: 如何导出标注数据？

**A**: 数据导出步骤：

1. **选择导出格式**:
   - JSON: 通用格式
   - COCO: 计算机视觉标准格式
   - YOLO: 目标检测格式
   - CSV: 表格格式

2. **配置导出选项**:
   ```typescript
   const exportConfig = {
     format: 'COCO',
     includeImages: true,
     includeAnnotations: true,
     filterByStatus: 'completed'
   };
   ```

3. **执行导出**:
   ```typescript
   const exportData = async (projectId: string, config: ExportConfig) => {
     const response = await fetch(`/api/projects/${projectId}/export`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(config)
     });
     
     const blob = await response.blob();
     const url = URL.createObjectURL(blob);
     
     // 下载文件
     const a = document.createElement('a');
     a.href = url;
     a.download = `export_${projectId}.zip`;
     a.click();
   };
   ```

## 故障排除

### Q8: iframe 无法加载，显示空白页面怎么办？

**A**: 按照以下步骤排查：

1. **检查 Label Studio 服务状态**:
   ```bash
   curl http://localhost:8080/api/health
   ```

2. **检查网络连接**:
   ```typescript
   const checkConnection = async () => {
     try {
       const response = await fetch(LABEL_STUDIO_URL);
       return response.ok;
     } catch (error) {
       console.error('Connection failed:', error);
       return false;
     }
   };
   ```

3. **检查 CORS 配置**:
   ```python
   # Label Studio 配置
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
       "https://your-domain.com"
   ]
   ```

4. **检查浏览器控制台错误**:
   - 打开开发者工具 (F12)
   - 查看 Console 和 Network 标签页
   - 查找相关错误信息

### Q9: 标注数据保存失败怎么办？

**A**: 数据保存失败的常见原因和解决方案：

1. **网络连接问题**:
   ```typescript
   // 实现重试机制
   const saveWithRetry = async (data: any, maxRetries = 3) => {
     for (let i = 0; i < maxRetries; i++) {
       try {
         return await saveAnnotation(data);
       } catch (error) {
         if (i === maxRetries - 1) throw error;
         await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
       }
     }
   };
   ```

2. **权限不足**:
   - 检查用户是否有保存权限
   - 联系管理员分配相应权限

3. **数据格式错误**:
   ```typescript
   // 验证数据格式
   const validateAnnotation = (annotation: any) => {
     const required = ['id', 'taskId', 'userId', 'data'];
     const missing = required.filter(field => !annotation[field]);
     
     if (missing.length > 0) {
       throw new Error(`Missing required fields: ${missing.join(', ')}`);
     }
   };
   ```

4. **服务器错误**:
   - 检查服务器日志
   - 确认数据库连接正常
   - 检查磁盘空间是否充足

### Q10: 标注界面卡顿或响应缓慢怎么办？

**A**: 性能优化建议：

1. **清理浏览器缓存**:
   - 清除浏览器缓存和 Cookie
   - 重启浏览器

2. **检查系统资源**:
   ```typescript
   // 监控内存使用
   const checkMemoryUsage = () => {
     if ('memory' in performance) {
       const memory = (performance as any).memory;
       console.log('Memory usage:', {
         used: Math.round(memory.usedJSHeapSize / 1024 / 1024) + 'MB',
         total: Math.round(memory.totalJSHeapSize / 1024 / 1024) + 'MB',
         limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024) + 'MB'
       });
     }
   };
   ```

3. **优化数据加载**:
   ```typescript
   // 启用懒加载
   const lazyLoader = new LazyLoader({
     threshold: 0.1,
     rootMargin: '50px'
   });
   ```

4. **减少并发操作**:
   - 避免同时打开多个标注任务
   - 关闭不必要的浏览器标签页

### Q11: 权限验证失败怎么办？

**A**: 权限问题解决步骤：

1. **检查用户权限**:
   ```typescript
   const checkUserPermissions = async (userId: string) => {
     const response = await fetch(`/api/users/${userId}/permissions`);
     const permissions = await response.json();
     console.log('User permissions:', permissions);
   };
   ```

2. **刷新权限缓存**:
   ```typescript
   const refreshPermissions = async () => {
     await fetch('/api/auth/refresh-permissions', {
       method: 'POST',
       headers: { 'Authorization': `Bearer ${token}` }
     });
   };
   ```

3. **重新登录**:
   - 退出当前账户
   - 重新登录系统
   - 确认权限是否恢复

4. **联系管理员**:
   - 如果问题持续存在，联系系统管理员
   - 提供用户ID和错误信息

## 性能相关

### Q12: 如何提高标注效率？

**A**: 提高标注效率的方法：

1. **使用快捷键**:
   ```markdown
   - 数字键 1-9: 快速选择标签
   - Ctrl+Z: 撤销操作
   - Ctrl+Y: 重做操作
   - Space: 下一个任务
   - Enter: 保存标注
   ```

2. **批量操作**:
   ```typescript
   // 批量应用标签
   const applyBatchLabels = (annotations: any[], label: string) => {
     return annotations.map(annotation => ({
       ...annotation,
       label: label
     }));
   };
   ```

3. **使用模板**:
   ```typescript
   // 创建标注模板
   const createTemplate = (templateData: any) => {
     return {
       id: generateId(),
       name: templateData.name,
       config: templateData.config,
       createdAt: Date.now()
     };
   };
   ```

4. **AI 辅助标注**:
   - 启用预标注功能
   - 使用智能推荐
   - 利用相似数据的标注结果

### Q13: 如何优化大数据集的标注性能？

**A**: 大数据集优化策略：

1. **分批处理**:
   ```typescript
   const processBatch = async (data: any[], batchSize = 100) => {
     const batches = [];
     for (let i = 0; i < data.length; i += batchSize) {
       batches.push(data.slice(i, i + batchSize));
     }
     
     for (const batch of batches) {
       await processBatchData(batch);
       // 添加延迟避免过载
       await new Promise(resolve => setTimeout(resolve, 100));
     }
   };
   ```

2. **启用缓存**:
   ```typescript
   const cache = new Map();
   
   const getCachedData = (key: string) => {
     if (cache.has(key)) {
       return cache.get(key);
     }
     
     const data = fetchData(key);
     cache.set(key, data);
     return data;
   };
   ```

3. **预加载策略**:
   ```typescript
   // 预加载下一批数据
   const preloadNextBatch = async (currentIndex: number) => {
     const nextBatchStart = currentIndex + 10;
     const nextBatch = await fetchDataBatch(nextBatchStart, 10);
     cache.set(`batch_${nextBatchStart}`, nextBatch);
   };
   ```

## 集成相关

### Q14: 如何与现有系统集成？

**A**: 系统集成步骤：

1. **API 集成**:
   ```typescript
   // 创建 API 客户端
   class SuperInsightAPI {
     constructor(private baseUrl: string, private apiKey: string) {}
     
     async createProject(projectData: any) {
       const response = await fetch(`${this.baseUrl}/api/projects`, {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
           'Authorization': `Bearer ${this.apiKey}`
         },
         body: JSON.stringify(projectData)
       });
       
       return response.json();
     }
   }
   ```

2. **数据同步**:
   ```typescript
   // 实现数据同步
   class DataSynchronizer {
     async syncAnnotations(projectId: string) {
       const localData = await this.getLocalAnnotations(projectId);
       const remoteData = await this.getRemoteAnnotations(projectId);
       
       const conflicts = this.detectConflicts(localData, remoteData);
       if (conflicts.length > 0) {
         await this.resolveConflicts(conflicts);
       }
       
       await this.mergeData(localData, remoteData);
     }
   }
   ```

3. **用户认证集成**:
   ```typescript
   // SSO 集成
   class SSOIntegration {
     async authenticateUser(token: string) {
       const response = await fetch('/api/auth/verify', {
         headers: { 'Authorization': `Bearer ${token}` }
       });
       
       if (response.ok) {
         const userData = await response.json();
         return userData;
       }
       
       throw new Error('Authentication failed');
     }
   }
   ```

### Q15: 如何自定义标注界面？

**A**: 界面自定义方法：

1. **主题定制**:
   ```typescript
   const customTheme = {
     colors: {
       primary: '#1890ff',
       secondary: '#52c41a',
       background: '#f0f2f5',
       text: '#262626'
     },
     fonts: {
       primary: 'Arial, sans-serif',
       secondary: 'Helvetica, sans-serif'
     }
   };
   ```

2. **工具栏定制**:
   ```typescript
   const customToolbar = {
     tools: [
       { name: 'rectangle', icon: 'rectangle', shortcut: 'R' },
       { name: 'polygon', icon: 'polygon', shortcut: 'P' },
       { name: 'brush', icon: 'brush', shortcut: 'B' }
     ],
     layout: 'horizontal', // or 'vertical'
     position: 'top' // or 'left', 'right', 'bottom'
   };
   ```

3. **标签配置**:
   ```typescript
   const labelConfig = {
     categories: [
       {
         name: 'Objects',
         labels: ['person', 'car', 'bike'],
         color: '#ff4d4f'
       },
       {
         name: 'Background',
         labels: ['sky', 'road', 'building'],
         color: '#52c41a'
       }
     ]
   };
   ```

## 安全相关

### Q16: 如何确保数据安全？

**A**: 数据安全措施：

1. **数据加密**:
   ```typescript
   import CryptoJS from 'crypto-js';
   
   const encryptData = (data: any, secretKey: string) => {
     const jsonString = JSON.stringify(data);
     return CryptoJS.AES.encrypt(jsonString, secretKey).toString();
   };
   
   const decryptData = (encryptedData: string, secretKey: string) => {
     const bytes = CryptoJS.AES.decrypt(encryptedData, secretKey);
     const decryptedString = bytes.toString(CryptoJS.enc.Utf8);
     return JSON.parse(decryptedString);
   };
   ```

2. **访问控制**:
   ```typescript
   // 实现基于角色的访问控制
   class AccessController {
     checkAccess(userId: string, resource: string, action: string): boolean {
       const userRoles = this.getUserRoles(userId);
       const requiredPermissions = this.getRequiredPermissions(resource, action);
       
       return userRoles.some(role => 
         requiredPermissions.every(permission => 
           role.permissions.includes(permission)
         )
       );
     }
   }
   ```

3. **审计日志**:
   ```typescript
   // 记录用户操作
   class AuditLogger {
     logAction(userId: string, action: string, resource: string, details?: any) {
       const logEntry = {
         userId,
         action,
         resource,
         details,
         timestamp: Date.now(),
         ip: this.getClientIP(),
         userAgent: this.getUserAgent()
       };
       
       this.saveToDatabase(logEntry);
     }
   }
   ```

### Q17: 如何配置 HTTPS？

**A**: HTTPS 配置步骤：

1. **获取 SSL 证书**:
   ```bash
   # 使用 Let's Encrypt
   certbot --nginx -d your-domain.com
   ```

2. **Nginx 配置**:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/private.key;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **强制 HTTPS 重定向**:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

## 其他问题

### Q18: 如何备份和恢复数据？

**A**: 数据备份和恢复方案：

1. **自动备份**:
   ```bash
   #!/bin/bash
   # backup.sh
   
   DATE=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/backup/superinsight_$DATE"
   
   # 备份数据库
   pg_dump superinsight > "$BACKUP_DIR/database.sql"
   
   # 备份文件
   tar -czf "$BACKUP_DIR/files.tar.gz" /path/to/data/files
   
   # 上传到云存储
   aws s3 cp "$BACKUP_DIR" s3://backup-bucket/ --recursive
   ```

2. **数据恢复**:
   ```bash
   #!/bin/bash
   # restore.sh
   
   BACKUP_DATE=$1
   BACKUP_DIR="/backup/superinsight_$BACKUP_DATE"
   
   # 恢复数据库
   psql superinsight < "$BACKUP_DIR/database.sql"
   
   # 恢复文件
   tar -xzf "$BACKUP_DIR/files.tar.gz" -C /path/to/data/
   ```

3. **增量备份**:
   ```typescript
   class IncrementalBackup {
     async createBackup(lastBackupTime: Date) {
       const changedData = await this.getChangedData(lastBackupTime);
       const backupFile = await this.createBackupFile(changedData);
       await this.uploadToStorage(backupFile);
       
       return {
         backupId: generateId(),
         timestamp: Date.now(),
         size: backupFile.size,
         itemCount: changedData.length
       };
     }
   }
   ```

### Q19: 如何监控系统性能？

**A**: 性能监控方案：

1. **前端监控**:
   ```typescript
   // 性能指标收集
   class PerformanceCollector {
     collectMetrics() {
       const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
       
       return {
         loadTime: navigation.loadEventEnd - navigation.fetchStart,
         domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
         firstPaint: this.getFirstPaint(),
         firstContentfulPaint: this.getFirstContentfulPaint()
       };
     }
     
     private getFirstPaint() {
       const paintEntries = performance.getEntriesByType('paint');
       const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
       return firstPaint ? firstPaint.startTime : 0;
     }
   }
   ```

2. **后端监控**:
   ```python
   # 使用 Prometheus 监控
   from prometheus_client import Counter, Histogram, Gauge
   
   REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
   REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
   ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
   
   @REQUEST_DURATION.time()
   def process_request():
       REQUEST_COUNT.labels(method='GET', endpoint='/api/tasks').inc()
       # 处理请求逻辑
   ```

3. **告警配置**:
   ```yaml
   # alertmanager.yml
   groups:
   - name: superinsight
     rules:
     - alert: HighErrorRate
       expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
       for: 5m
       annotations:
         summary: "High error rate detected"
     
     - alert: HighResponseTime
       expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
       for: 5m
       annotations:
         summary: "High response time detected"
   ```

### Q20: 如何获取技术支持？

**A**: 技术支持渠道：

1. **在线文档**:
   - 用户手册: [用户手册](./user-manual.md)
   - API 文档: [API 参考](./api-reference.md)
   - 故障排查: [故障排查指南](./troubleshooting.md)

2. **社区支持**:
   - GitHub Issues: https://github.com/superinsight/issues
   - 技术论坛: https://forum.superinsight.com
   - Stack Overflow: 标签 `superinsight`

3. **商业支持**:
   - 邮箱: support@superinsight.com
   - 电话: +86-400-xxx-xxxx
   - 在线客服: 工作日 9:00-18:00

4. **提交问题时请包含**:
   ```markdown
   - 问题详细描述
   - 重现步骤
   - 错误信息和截图
   - 系统环境信息
   - 浏览器版本
   - 相关日志文件
   ```

---

**版本**: v1.0  
**更新日期**: 2026年1月5日  
**维护团队**: SuperInsight 技术支持团队

如果您的问题未在此 FAQ 中找到答案，请通过上述支持渠道联系我们。我们会持续更新此文档，添加新的常见问题和解答。