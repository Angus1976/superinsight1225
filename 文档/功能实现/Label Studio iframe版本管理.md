# Label Studio 版本管理指南

## 概述

SuperInsight 支持 Label Studio 容器版本的快速切换，确保在开源版本更新时能够平滑升级。本指南介绍版本管理功能和最佳实践。

官方 Docker 镜像: `heartexlabs/label-studio`  
官方文档: https://labelstud.io/guide/install

## 支持的版本

### 推荐版本

| 版本 | 状态 | 发布日期 | 特性 |
|------|------|----------|------|
| 1.18.0 | ✅ 推荐 | 2025-12 | LLM 评估模板增强、性能优化 |
| 1.12.0 | LTS | 2024-12 | 长期支持版本 |

### 所有可用版本

| 版本 | Docker 镜像 | LTS | 说明 |
|------|-------------|-----|------|
| latest | heartexlabs/label-studio:latest | ❌ | 滚动更新 |
| 1.18.0 | heartexlabs/label-studio:1.18.0 | ✅ | 推荐生产使用 |
| 1.17.0 | heartexlabs/label-studio:1.17.0 | ❌ | RLHF 支持改进 |
| 1.16.0 | heartexlabs/label-studio:1.16.0 | ❌ | 多页文档标注 |
| 1.15.0 | heartexlabs/label-studio:1.15.0 | ❌ | 时间序列改进 |
| 1.14.0 | heartexlabs/label-studio:1.14.0 | ❌ | 视频时间线分割 |
| 1.13.0 | heartexlabs/label-studio:1.13.0 | ❌ | LLM 微调模板 |
| 1.12.0 | heartexlabs/label-studio:1.12.0 | ✅ | LTS 版本 |

## 使用方法

### 版本管理器

```typescript
import { VersionManager } from '@/services/iframe';

const versionManager = new VersionManager({
  currentVersion: '1.16.0',
});

// 获取当前版本
const current = versionManager.getCurrentVersion();

// 获取推荐版本
const recommended = versionManager.getRecommendedVersion();

// 获取所有版本
const allVersions = versionManager.getAllVersions();

// 获取 LTS 版本
const ltsVersions = versionManager.getLTSVersions();
```

### 检查更新

```typescript
const updateInfo = await versionManager.checkForUpdates();

if (updateInfo.updateAvailable) {
  console.log(`新版本可用: ${updateInfo.latestVersion}`);
}
```

### 版本兼容性检查

```typescript
const compatibility = versionManager.checkCompatibility('1.16.0', '1.18.0');

if (!compatibility.compatible) {
  console.log('警告:', compatibility.warnings);
}
```

### 切换版本

```typescript
const result = await versionManager.switchVersion('1.18.0');

console.log('Docker 命令:', result.dockerCommand);
console.log('警告:', result.warnings);
```

## 版本切换流程

### 1. 准备工作

```bash
# 备份数据库
docker exec label-studio-postgres pg_dump -U labelstudio labelstudio > backup.sql

# 导出项目配置
curl -X GET "http://localhost:8080/api/projects" -H "Authorization: Token YOUR_TOKEN" > projects.json
```

### 2. 停止当前容器

```bash
docker-compose stop label-studio
```

### 3. 拉取新版本

```bash
docker pull heartexlabs/label-studio:1.18.0
```

### 4. 更新配置

修改 `docker-compose.yml`:

```yaml
services:
  label-studio:
    image: heartexlabs/label-studio:1.18.0
    # ... 其他配置
```

### 5. 启动新版本

```bash
docker-compose up -d label-studio
```

### 6. 验证升级

```bash
# 检查版本
docker exec label-studio label-studio --version

# 检查健康状态
curl http://localhost:8080/health
```

## 生成 Docker Compose 配置

```typescript
const config = versionManager.generateDockerComposeConfig('1.18.0');
console.log(config);
```

输出示例:

```yaml
version: '3.8'

services:
  label-studio:
    image: heartexlabs/label-studio:1.18.0
    container_name: label-studio
    ports:
      - "8080:8080"
    volumes:
      - label-studio-data:/label-studio/data
    environment:
      - LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
      - DJANGO_DB=default
      - POSTGRE_NAME=${POSTGRES_DB:-labelstudio}
      - POSTGRE_USER=${POSTGRES_USER:-labelstudio}
      - POSTGRE_PASSWORD=${POSTGRES_PASSWORD:-labelstudio}
      - POSTGRE_HOST=${POSTGRES_HOST:-postgres}
      - POSTGRE_PORT=${POSTGRES_PORT:-5432}
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: label-studio-postgres
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-labelstudio}
      - POSTGRES_USER=${POSTGRES_USER:-labelstudio}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-labelstudio}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  label-studio-data:
  postgres-data:
```

## 迁移指南

### 获取迁移指南

```typescript
const guide = versionManager.getMigrationGuide('1.16.0', '1.18.0');
console.log(guide);
```

### 版本比较

```typescript
const comparison = versionManager.compareVersions('1.16.0', '1.18.0');

console.log('较新版本:', comparison.newer);
console.log('新增功能:', comparison.featureDiff);
```

## 回滚流程

如果升级后出现问题:

```bash
# 1. 停止当前容器
docker-compose stop label-studio

# 2. 恢复旧版本镜像
docker pull heartexlabs/label-studio:1.16.0

# 3. 更新 docker-compose.yml 为旧版本

# 4. 如需要，恢复数据库备份
docker exec -i label-studio-postgres psql -U labelstudio labelstudio < backup.sql

# 5. 启动旧版本
docker-compose up -d label-studio
```

## 版本变更监听

```typescript
const unsubscribe = versionManager.onVersionChange((newVersion) => {
  console.log(`版本已切换到: ${newVersion}`);
  // 执行必要的重新初始化
});

// 取消监听
unsubscribe();
```

## 最佳实践

### 1. 版本选择

- **生产环境**: 使用推荐版本或 LTS 版本
- **测试环境**: 可使用 `latest` 进行新功能测试
- **开发环境**: 与生产环境保持一致

### 2. 升级策略

- 先在测试环境验证新版本
- 准备完整的回滚方案
- 选择低峰期进行升级
- 保留至少两个版本的备份

### 3. 兼容性检查

- 升级前检查 API 兼容性
- 验证自定义模板在新版本中的表现
- 测试与后端集成的功能

### 4. 监控与告警

- 升级后监控系统性能
- 设置异常告警
- 记录升级日志

## 常见问题

### Q: 如何确定当前运行的版本?

```bash
docker exec label-studio label-studio --version
```

### Q: 升级后数据会丢失吗?

不会，数据存储在 PostgreSQL 数据库和挂载的卷中，与容器版本无关。但建议升级前备份。

### Q: 可以跨多个版本升级吗?

可以，但建议查看每个版本的变更日志，确保没有破坏性变更。

### Q: 如何处理自定义插件?

自定义插件可能需要针对新版本进行适配，建议在测试环境先验证。

## 参考资源

- [Label Studio 发布说明](https://github.com/HumanSignal/label-studio/releases)
- [Label Studio Docker Hub](https://hub.docker.com/r/heartexlabs/label-studio)
- [Label Studio 安装指南](https://labelstud.io/guide/install)

## 版本信息

- 版本管理器版本: 1.0.0
- 更新日期: 2026年1月
