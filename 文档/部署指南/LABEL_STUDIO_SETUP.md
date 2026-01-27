# Label Studio 认证配置指南

## 认证方法概述

SuperInsight 支持两种 Label Studio 认证方法：

### 1. JWT 认证（推荐 - Label Studio 1.22.0+）🔐
- ✅ 自动令牌管理（刷新、过期处理）
- ✅ 更安全的令牌轮换
- ✅ 支持用户名/密码认证
- ✅ 无需手动管理令牌

### 2. API Token 认证（传统方式）🔑
- ✅ 兼容 Label Studio < 1.22.0
- ✅ 静态令牌，不会过期
- ⚠️ 需要手动管理和轮换

**优先级**: 如果同时配置了 JWT 凭据和 API Token，系统将优先使用 JWT 认证。

---

## 快速开始

### 方法 1: JWT 认证配置（推荐）⚡

#### 步骤 1: 配置环境变量

编辑 `.env` 文件：

```bash
nano .env
```

添加或修改以下配置：

```bash
# Label Studio URL
LABEL_STUDIO_URL=http://localhost:8080

# JWT 认证（Label Studio 1.22.0+）
LABEL_STUDIO_USERNAME=admin
LABEL_STUDIO_PASSWORD=your-secure-password
```

#### 步骤 2: 重启后端容器

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

#### 步骤 3: 验证配置

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    print(f'Authentication method: {ls.auth_method}')
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"
```

预期输出：
```
Authentication method: jwt
Connection test: SUCCESS
```

---

### 方法 2: 自动化配置脚本（API Token）📝

运行配置向导脚本：

```bash
./setup-label-studio-token.sh
```

脚本会自动完成所有配置步骤。

### 方法 3: 手动配置（API Token）📝

1. **访问 Label Studio**
   ```
   http://localhost:8080
   ```
   登录凭据: `admin@example.com` / `admin`

2. **获取 API Token**
   - 点击右上角头像
   - 进入 "Account & Settings"
   - 复制 "Access Token"

3. **编辑 .env 文件**
   ```bash
   nano .env
   ```
   
   找到并修改：
   ```bash
   LABEL_STUDIO_API_TOKEN=your_token_here
   ```

4. **重启后端容器**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart app
   ```

5. **验证配置**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO
   ```

## 文件说明

### `.env` 文件
- ✅ 本地配置文件
- ✅ 不会被上传到 Git
- ✅ 存储敏感信息（API tokens, secrets）
- ✅ 被 `docker-compose.yml` 自动读取

### `setup-label-studio-token.sh` 脚本
- 🚀 自动化配置向导
- 🔍 检查容器状态
- 📝 更新 .env 文件
- ✅ 验证配置

### `.env.example` 文件
- 📋 配置模板
- 📚 文档参考
- ⚠️ 不包含实际的敏感信息

## 安全提示 🔒

1. **永远不要提交 .env 文件到 Git**
   - ✅ 已在 `.gitignore` 中配置
   - ✅ 包含敏感信息

2. **定期轮换 API Token**
   - 建议每 3-6 个月更换一次
   - 使用不同的 token 用于开发和生产环境

3. **限制 Token 权限**
   - 如果 Label Studio 支持，使用最小权限原则

## 向后兼容性

### 从 API Token 迁移到 JWT

如果您当前使用 API Token 认证，可以无缝迁移到 JWT：

1. **保留现有配置**（可选）
   ```bash
   # 保留 API Token 作为备份
   LABEL_STUDIO_API_TOKEN=your_existing_token
   ```

2. **添加 JWT 凭据**
   ```bash
   # 添加 JWT 认证
   LABEL_STUDIO_USERNAME=admin
   LABEL_STUDIO_PASSWORD=your-password
   ```

3. **重启服务**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart app
   ```

系统将自动切换到 JWT 认证，API Token 将作为备份保留。

### 回滚到 API Token

如果需要回滚到 API Token 认证：

1. **移除 JWT 凭据**
   ```bash
   # 注释或删除 JWT 配置
   # LABEL_STUDIO_USERNAME=admin
   # LABEL_STUDIO_PASSWORD=your-password
   ```

2. **确保 API Token 存在**
   ```bash
   LABEL_STUDIO_API_TOKEN=your_token_here
   ```

3. **重启服务**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart app
   ```

---

## 故障排查

### JWT 认证问题

#### 问题: "Authentication failed" 错误

**可能原因**:
- 用户名或密码不正确
- Label Studio 版本 < 1.22.0（不支持 JWT）
- Label Studio 服务未运行

**解决方案**:
1. 验证用户名和密码
   ```bash
   # 在 Label Studio 中登录测试
   curl -X POST http://localhost:8080/api/sessions/ \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"your-password"}'
   ```

2. 检查 Label Studio 版本
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec label-studio \
     label-studio --version
   ```
   
   如果版本 < 1.22.0，请使用 API Token 认证。

3. 检查 Label Studio 服务状态
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio
   ```

#### 问题: "Token expired" 错误

**说明**: 这是正常行为，系统会自动刷新令牌。

**如果持续出现**:
1. 检查系统日志
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose logs app --tail=100 | grep "JWT"
   ```

2. 验证刷新令牌功能
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
   from src.label_studio.auth import JWTAuthManager
   import asyncio
   
   async def test():
       auth = JWTAuthManager(
           base_url='http://label-studio:8080',
           username='admin',
           password='your-password'
       )
       await auth.login()
       print(f'Authenticated: {auth.is_authenticated}')
       await auth.refresh_token()
       print('Token refresh successful')
   
   asyncio.run(test())
   "
   ```

#### 问题: 认证方法未切换到 JWT

**解决方案**:
1. 验证环境变量已设置
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO
   ```
   
   应该看到：
   ```
   LABEL_STUDIO_USERNAME=admin
   LABEL_STUDIO_PASSWORD=***
   ```

2. 确认容器已重启
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart app
   ```

3. 检查认证方法
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
   from src.label_studio.config import LabelStudioConfig
   config = LabelStudioConfig()
   print(f'Auth method: {config.get_auth_method()}')
   "
   ```

### API Token 认证问题

### 问题: Token 不工作（401 错误）

**解决方案**:
1. 检查 token 是否正确复制（无多余空格）
2. 在 Label Studio 中重新生成 token
3. 确认容器已重启并读取了新的环境变量

### 问题: 容器中看不到环境变量

**解决方案**:
```bash
# 重新构建容器
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d --build app

# 检查环境变量
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app env | grep LABEL_STUDIO
```

### 问题: Label Studio 无法访问

**解决方案**:
```bash
# 检查容器状态
/Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio

# 查看日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs label-studio --tail=50

# 重启容器
/Applications/Docker.app/Contents/Resources/bin/docker compose restart label-studio
```

## 测试连接

### JWT 认证测试

配置完成后，测试 JWT 认证：

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    print(f'Authentication method: {ls.auth_method}')
    
    if ls.auth_method == 'jwt':
        print('Testing JWT authentication...')
        await ls.jwt_auth.login()
        print(f'Authenticated: {ls.jwt_auth.is_authenticated}')
        print(f'Access token: {\"Present\" if ls.jwt_auth._access_token else \"Missing\"}')
        print(f'Refresh token: {\"Present\" if ls.jwt_auth._refresh_token else \"Missing\"}')
    
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"
```

### API Token 认证测试

配置完成后，测试 API Token 连接：

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    print(f'Authentication method: {ls.auth_method}')
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"
```

## 性能和安全最佳实践

### JWT 认证

**优势**:
- ✅ 自动令牌刷新（无需手动干预）
- ✅ 令牌过期时自动重新认证
- ✅ 并发请求安全（使用 asyncio.Lock）
- ✅ 令牌仅存储在内存中（不持久化）
- ✅ 日志中不包含敏感信息

**性能特性**:
- 认证延迟: < 5 秒
- 令牌刷新延迟: < 2 秒
- 令牌有效期: 1 小时（自动刷新）
- 刷新令牌有效期: 7 天

**安全建议**:
1. 使用强密码（至少 12 个字符）
2. 定期更换密码（每 3-6 个月）
3. 在生产环境中使用 HTTPS
4. 不要在日志或代码中硬编码凭据

### API Token 认证

**优势**:
- ✅ 简单配置
- ✅ 兼容旧版本 Label Studio
- ✅ 无需密码管理

**安全建议**:
1. 定期轮换 API Token（每 3-6 个月）
2. 使用不同的 token 用于开发和生产环境
3. 限制 Token 权限（如果 Label Studio 支持）
4. 不要在公共仓库中提交 .env 文件

## 相关文档

- 详细设置指南: `.kiro/LABEL_STUDIO_TOKEN_SETUP_GUIDE.md`
- 配置模板: `.env.example`
- Docker 配置: `docker-compose.yml`

## 支持

如有问题，请查看：
1. `.kiro/LABEL_STUDIO_TOKEN_SETUP_GUIDE.md` - 详细故障排查指南
2. Label Studio 官方文档: https://labelstud.io/guide/
3. Label Studio API 文档: https://labelstud.io/api

---

**配置完成后，您就可以使用以下功能：**
- ✅ "开始标注" 按钮
- ✅ "在新窗口中打开" 按钮
- ✅ 自动项目创建
- ✅ 任务同步
- ✅ 多语言支持（中文/英文）
