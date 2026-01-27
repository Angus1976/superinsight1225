# Label Studio JWT 认证解决方案

**日期**: 2026-01-27  
**状态**: 🔧 正在解决  
**优先级**: CRITICAL

## 问题分析

### 发现的问题

1. **Label Studio 版本**: 1.22.0
2. **认证方式**: 该版本禁用了传统的 Token 认证
3. **错误信息**: "Authentication token no longer valid: legacy token authentication has been disabled for this organization"

### 当前状态

- ✅ 生成了传统 API Token: `f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17`
- ❌ 传统 Token 认证被禁用
- ⚠️ 界面显示的是 JWT Refresh Token，不能直接用于 API 调用

## 解决方案选项

### 选项 1: 降级 Label Studio 到支持传统 Token 的版本（推荐）

使用较早版本的 Label Studio，这些版本支持传统的 Token 认证。

**步骤**:

1. 修改 `docker-compose.yml`，使用特定版本：
   ```yaml
   label-studio:
     image: heartexlabs/label-studio:1.7.3  # 或其他支持 token 的版本
   ```

2. 重启容器并重新生成 token

**优点**:
- ✅ 简单直接
- ✅ 与现有代码兼容
- ✅ 稳定可靠

**缺点**:
- ❌ 使用旧版本，可能缺少新功能
- ❌ 需要重新创建项目和数据

### 选项 2: 修改代码支持 JWT 认证

更新我们的集成代码以支持 JWT 认证流程。

**JWT 认证流程**:
1. 使用用户名/密码登录获取 access token 和 refresh token
2. 使用 access token 进行 API 调用
3. Access token 过期后使用 refresh token 获取新的 access token

**需要修改的代码**:
- `src/label_studio/integration.py` - 添加 JWT 认证逻辑
- `src/label_studio/config.py` - 支持用户名/密码配置
- `.env` - 添加用户名和密码

**优点**:
- ✅ 使用最新版本
- ✅ 符合现代认证标准

**缺点**:
- ❌ 需要大量代码修改
- ❌ 更复杂的认证流程
- ❌ 需要管理 token 刷新

### 选项 3: 使用 Label Studio Enterprise 或配置组织设置

某些 Label Studio 版本允许通过配置启用传统 token 认证。

**步骤**:
1. 检查是否有环境变量可以启用传统认证
2. 或者使用 Label Studio Enterprise 版本

**状态**: 需要进一步研究

## 推荐方案：降级到 Label Studio 1.7.3

这是最简单且最可靠的解决方案。

### 实施步骤

#### 1. 备份当前数据（如果需要）

```bash
# 备份 Label Studio 数据
/Applications/Docker.app/Contents/Resources/bin/docker compose cp label-studio:/label-studio/data ./label-studio-backup
```

#### 2. 修改 docker-compose.yml

```yaml
label-studio:
  image: heartexlabs/label-studio:1.7.3
  # ... 其他配置保持不变
```

#### 3. 停止并删除当前容器

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose stop label-studio
/Applications/Docker.app/Contents/Resources/bin/docker compose rm -f label-studio
```

#### 4. 启动新版本

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d label-studio
```

#### 5. 等待启动完成

```bash
sleep 20
/Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio
```

#### 6. 重新生成 API Token

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec -T label-studio sh -c "cd /label-studio && python label_studio/manage.py shell" << 'EOF'
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
user = User.objects.filter(email='admin@example.com').first()
if not user:
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='admin',
        username='admin'
    )
token, created = Token.objects.get_or_create(user=user)
print(f"\n=== API TOKEN ===")
print(token.key)
print(f"=== END ===\n")
exit()
EOF
```

#### 7. 更新 .env 文件

将生成的 token 更新到 `.env` 文件中。

#### 8. 重启后端容器

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

#### 9. 测试连接

```bash
# 测试 API 连接
curl -s http://localhost:8080/api/projects/ \
  -H "Authorization: Token YOUR_NEW_TOKEN" \
  | python3 -m json.tool

# 测试后端集成
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio
asyncio.run(LabelStudioIntegration().test_connection())
"
```

## 临时解决方案：使用用户名密码认证

如果不想降级，可以修改代码使用用户名/密码进行认证。

### 修改 .env 文件

```bash
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_USERNAME=admin@example.com
LABEL_STUDIO_PASSWORD=admin
# LABEL_STUDIO_API_TOKEN 暂时不使用
```

### 修改集成代码

需要在 `src/label_studio/integration.py` 中添加登录逻辑：

```python
async def _get_access_token(self):
    """Get access token using username/password"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{self.base_url}/api/auth/login/",
            json={
                "email": self.username,
                "password": self.password
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            raise LabelStudioAuthenticationError("Login failed")
```

但这需要大量代码修改，不推荐。

## 决策

**推荐**: 使用选项 1 - 降级到 Label Studio 1.7.3

**原因**:
1. 最简单的解决方案
2. 与现有代码完全兼容
3. 稳定可靠
4. 快速实施

## 下一步

等待用户确认是否同意降级 Label Studio 版本。

如果同意，我将：
1. 修改 `docker-compose.yml` 使用 Label Studio 1.7.3
2. 重启容器
3. 重新生成 API token
4. 测试所有功能

---

**状态**: 等待用户决策  
**预计时间**: 10-15 分钟（如果选择降级）
