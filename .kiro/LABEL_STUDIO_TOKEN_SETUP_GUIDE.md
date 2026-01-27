# Label Studio API Token Setup Guide

**Date**: 2026-01-27  
**Status**: 🔧 Action Required  
**Priority**: HIGH

## Problem Summary

The "开始标注" (Start Annotation) and "在新窗口中打开" (Open in New Window) buttons are not working because:

1. **Missing API Token**: The `LABEL_STUDIO_API_TOKEN` environment variable is not set
2. **Authentication Required**: Label Studio requires an API token for all API calls
3. **Integration Failure**: Without the token, all Label Studio API calls return 401 Unauthorized

## Current Configuration Status

### Environment Variables (from docker-compose.yml)
```yaml
label-studio:
  environment:
    - LABEL_STUDIO_HOST=http://localhost:8080
    - LABEL_STUDIO_USERNAME=admin@example.com
    - LABEL_STUDIO_PASSWORD=admin
    - LANGUAGE_CODE=zh-hans
```

### Missing Configuration
- ❌ `LABEL_STUDIO_API_TOKEN` - **NOT SET**

## Solution Steps

### 🚀 快速配置方法 (推荐)

我们已经为您创建了自动化配置脚本和本地配置文件：

**方法 1: 使用自动化脚本（最简单）**

```bash
# 运行配置向导
./setup-label-studio-token.sh
```

这个脚本会：
1. ✅ 检查 Label Studio 是否运行
2. ✅ 引导您获取 API Token
3. ✅ 自动更新 `.env` 文件
4. ✅ 重启后端容器
5. ✅ 验证配置是否成功

**方法 2: 手动配置 .env 文件**

如果您更喜欢手动配置，请按照以下步骤操作：

### Step 1: Access Label Studio Web Interface

1. Open browser and navigate to: http://localhost:8080
2. You should see the Label Studio login page

### Step 2: Create Admin Account (First Time Only)

If this is the first time accessing Label Studio:

1. Click "Sign Up" or use the configured credentials:
   - Email: `admin@example.com`
   - Password: `admin`

2. Complete the registration process

### Step 3: Generate API Token

#### Method 1: Via Web Interface (Recommended)

1. Log in to Label Studio at http://localhost:8080
2. Click on your profile icon (top right corner)
3. Select "Account & Settings"
4. Navigate to "Access Token" section
5. Click "Create New Token" or copy existing token
6. **Save the token** - it looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`

#### Method 2: Via API (Alternative)

```bash
# Get token via API (if you have username/password)
curl -X POST http://localhost:8080/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"admin"}'
```

### Step 4: Update Configuration File

**重要**: 我们已经为您创建了本地配置文件 `.env`，该文件不会被上传到 Git。

编辑 `.env` 文件并添加您的 API token：

```bash
# 使用您喜欢的编辑器打开 .env 文件
nano .env
# 或
vim .env
# 或
code .env
```

找到这一行：
```bash
LABEL_STUDIO_API_TOKEN=
```

将其修改为：
```bash
LABEL_STUDIO_API_TOKEN=your_actual_token_here
```

**替换 `your_actual_token_here` 为您在 Step 3 中获取的实际 token**

保存文件后，`.env` 文件会被 `docker-compose.yml` 自动读取。

### Step 5: Restart Backend Container

```bash
# Restart only the backend container to pick up new environment variable
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app

# Or rebuild if needed
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d --build app
```

### Step 6: Verify Configuration

```bash
# Check if the token is set
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO

# Expected output:
# LABEL_STUDIO_URL=http://label-studio:8080
# LABEL_STUDIO_API_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

### Step 7: Test the Integration

```bash
# Test Label Studio connection from backend
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"
```

## Alternative: Use .env File (Already Done!)

✅ **好消息**: 我们已经为您创建了 `.env` 文件！

`.env` 文件的优势：
- ✅ 不会被上传到 Git（已在 `.gitignore` 中配置）
- ✅ 本地开发环境专用
- ✅ 可以安全地存储敏感信息
- ✅ `docker-compose.yml` 会自动读取

您只需要：
1. 编辑 `.env` 文件
2. 添加您的 `LABEL_STUDIO_API_TOKEN`
3. 重启容器

或者直接运行自动化脚本：
```bash
./setup-label-studio-token.sh
```

## Verification Checklist

After completing the setup:

- [ ] Label Studio web interface accessible at http://localhost:8080
- [ ] Admin account created and can log in
- [ ] API token generated and copied
- [ ] `LABEL_STUDIO_API_TOKEN` environment variable set in docker-compose.yml or .env
- [ ] Backend container restarted
- [ ] Environment variable visible in container (`docker compose exec app printenv`)
- [ ] Connection test passes
- [ ] "开始标注" button works in frontend
- [ ] "在新窗口中打开" button works in frontend

## Troubleshooting

### Issue: Cannot access Label Studio at http://localhost:8080

**Solution**:
```bash
# Check if Label Studio container is running
/Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio

# Check Label Studio logs
/Applications/Docker.app/Contents/Resources/bin/docker compose logs label-studio --tail=50

# Restart Label Studio
/Applications/Docker.app/Contents/Resources/bin/docker compose restart label-studio
```

### Issue: Token not working (401 Unauthorized)

**Possible causes**:
1. Token copied incorrectly (extra spaces, line breaks)
2. Token expired or revoked
3. Wrong token format

**Solution**:
1. Generate a new token from Label Studio web interface
2. Ensure no extra spaces when copying
3. Update environment variable and restart container

### Issue: Backend still can't connect after setting token

**Solution**:
```bash
# Verify token is actually set in container
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app env | grep LABEL_STUDIO_API_TOKEN

# If not set, rebuild container
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d --build app

# Check backend logs for errors
/Applications/Docker.app/Contents/Resources/bin/docker compose logs app --tail=100 | grep -i "label"
```

## Next Steps

Once the API token is configured:

1. The backend will be able to communicate with Label Studio
2. The "开始标注" button will:
   - Validate the project exists
   - Create project if needed
   - Import tasks to Label Studio
   - Enable annotation workflow

3. The "在新窗口中打开" button will:
   - Generate authenticated URL with temporary JWT token
   - Include language preference (zh/en)
   - Open Label Studio in new window with auto-login

## Security Notes

- **Never commit API tokens to git** - use `.env` file and add to `.gitignore`
- **Rotate tokens periodically** for security
- **Use different tokens** for development and production environments
- **Limit token permissions** if Label Studio supports role-based tokens

## Related Files

- `docker-compose.yml` - Container configuration
- `src/label_studio/integration.py` - Integration implementation
- `src/label_studio/config.py` - Configuration management
- `src/api/label_studio_api.py` - API endpoints
- `.env.example` - Environment variable template

## References

- [Label Studio Documentation](https://labelstud.io/guide/)
- [Label Studio API Authentication](https://labelstud.io/api#section/Authentication)
- [Label Studio Docker Setup](https://labelstud.io/guide/install.html#Docker)

---

**Status**: Waiting for user to generate and configure API token  
**Estimated Time**: 5-10 minutes  
**Difficulty**: Easy
