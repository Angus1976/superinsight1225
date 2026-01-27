# Label Studio API Token 问题修复

**日期**: 2026-01-27  
**状态**: ⚠️ Token 类型错误  
**优先级**: HIGH

## 问题诊断

### 当前状态

✅ `.env` 文件已创建并配置  
✅ `LABEL_STUDIO_API_TOKEN` 已设置  
✅ 环境变量已正确传递到容器  
✅ Label Studio 容器正在运行  
❌ **API 认证失败 - 401 Invalid token**

### 问题原因

您当前使用的 token 是一个 **JWT Refresh Token**，而不是 Label Studio 的 **API Access Token**。

**当前 token** (错误类型):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA3NjY3NzU2NSwiaWF0IjoxNzY5NDc3NTY1LCJqdGkiOiJhMDFlZjlmZGQ5Mzk0YzhmYmVkOTYzMDVkOWZhZjgwYSIsInVzZXJfaWQiOiIyIn0.8XjIlEaCVnlfC-jLTeVDk2tyxKbo00wd6A_0WVZvtpk
```

解码后显示: `"token_type":"refresh"` - 这是刷新 token，不是 API token。

### 测试结果

```bash
$ curl http://localhost:8080/api/projects/ -H "Authorization: Token <your_token>"
{"status_code":401,"detail":"Invalid token."}
```

## 解决方案

### 方法 1: 通过 Label Studio Web 界面获取正确的 API Token（推荐）

#### 步骤 1: 访问 Label Studio

在浏览器中打开:
```
http://localhost:8080
```

#### 步骤 2: 登录

使用以下凭据登录:
- **Email**: `admin@example.com`
- **Password**: `admin`

#### 步骤 3: 进入 Account Settings

1. 点击右上角的**用户头像**或**用户名**
2. 从下拉菜单中选择 **"Account & Settings"** 或 **"账户设置"**

#### 步骤 4: 找到 Access Token 部分

在 Account Settings 页面中:
1. 查找 **"Access Token"** 或 **"访问令牌"** 部分
2. 这通常在侧边栏或主要设置区域

#### 步骤 5: 获取或创建 Token

**如果已有 token**:
- 直接复制显示的 token
- Token 通常是一个 40 字符的十六进制字符串
- 格式类似: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`

**如果没有 token**:
1. 点击 **"Create Token"** 或 **"创建令牌"** 按钮
2. 复制新生成的 token
3. **重要**: 立即保存这个 token，因为它可能只显示一次

#### 步骤 6: 更新 .env 文件

编辑 `.env` 文件:
```bash
nano .env
```

找到这一行:
```bash
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

替换为新的 token:
```bash
LABEL_STUDIO_API_TOKEN=your_new_40_character_token_here
```

**正确的 token 格式**:
- ✅ 40 个字符的十六进制字符串
- ✅ 只包含字母和数字
- ✅ 没有 JWT 的三段式结构（没有两个点 `.`）

**错误的 token 格式**:
- ❌ JWT token (包含两个点 `.` 分隔三段)
- ❌ 包含 `eyJ` 开头的 Base64 编码字符串

#### 步骤 7: 重启容器

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

#### 步骤 8: 验证配置

```bash
# 检查环境变量
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO_API_TOKEN

# 测试连接
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio
asyncio.run(LabelStudioIntegration().test_connection())
"
```

**期望输出**: `Connection test: SUCCESS`

### 方法 2: 通过 Label Studio API 获取 Token（备选）

如果 Web 界面无法访问，可以尝试通过 API 获取:

```bash
# 尝试获取 token
curl -X POST http://localhost:8080/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}' \
  | python3 -m json.tool
```

或者:

```bash
# 尝试另一个端点
curl -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}' \
  | python3 -m json.tool
```

### 方法 3: 检查 Label Studio 数据库（高级）

如果以上方法都不行，可以直接从 Label Studio 的数据库中查询 token:

```bash
# 进入 Label Studio 容器
/Applications/Docker.app/Contents/Resources/bin/docker compose exec label-studio sh

# 在容器内执行
python manage.py shell

# 在 Python shell 中
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

user = User.objects.get(email='admin@example.com')
token, created = Token.objects.get_or_create(user=user)
print(f"API Token: {token.key}")
exit()
```

## Token 类型对比

### JWT Refresh Token (❌ 错误类型)

**特征**:
- 三段式结构: `header.payload.signature`
- 以 `eyJ` 开头
- 包含两个点 `.`
- Base64 编码
- 解码后包含 `"token_type":"refresh"`

**示例**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA3NjY3NzU2NSwiaWF0IjoxNzY5NDc3NTY1LCJqdGkiOiJhMDFlZjlmZGQ5Mzk0YzhmYmVkOTYzMDVkOWZhZjgwYSIsInVzZXJfaWQiOiIyIn0.8XjIlEaCVnlfC-jLTeVDk2tyxKbo00wd6A_0WVZvtpk
```

**用途**: 用于刷新访问令牌，不能直接用于 API 调用

### Label Studio API Token (✅ 正确类型)

**特征**:
- 40 个字符的十六进制字符串
- 只包含 `0-9` 和 `a-f`
- 没有点 `.` 或其他特殊字符
- 不是 Base64 编码

**示例**:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

**用途**: 用于 Label Studio API 认证

## 验证 Token 是否正确

### 快速测试

```bash
# 使用您的 token 测试
TOKEN="your_token_here"

curl -s http://localhost:8080/api/projects/ \
  -H "Authorization: Token $TOKEN" \
  | python3 -m json.tool
```

**成功响应** (200 OK):
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

**失败响应** (401 Unauthorized):
```json
{
  "status_code": 401,
  "detail": "Invalid token."
}
```

## 常见问题

### Q1: 我在 Label Studio 界面找不到 "Access Token" 选项

**A**: 不同版本的 Label Studio 界面可能略有不同。尝试以下位置:
1. 右上角头像 → Account Settings → Access Token
2. 右上角头像 → User Settings → API Token
3. Settings → Account → Access Token
4. Profile → API Access

### Q2: 我创建了 token 但还是 401 错误

**A**: 检查以下几点:
1. Token 是否完整复制（没有多余空格或换行）
2. Token 是否是 40 字符的十六进制字符串
3. 容器是否已重启并读取了新的环境变量
4. Label Studio 容器是否正常运行

### Q3: Label Studio 界面无法访问

**A**: 
```bash
# 检查容器状态
/Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio

# 查看日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs label-studio --tail=50

# 重启容器
/Applications/Docker.app/Contents/Resources/bin/docker compose restart label-studio
```

### Q4: 我忘记了 admin 密码

**A**: 重置密码:
```bash
# 进入 Label Studio 容器
/Applications/Docker.app/Contents/Resources/bin/docker compose exec label-studio sh

# 重置密码
python manage.py changepassword admin@example.com
```

## 下一步

完成 token 更新后:

1. ✅ 重启后端容器
2. ✅ 验证环境变量
3. ✅ 测试 Label Studio 连接
4. ✅ 测试 "开始标注" 按钮
5. ✅ 测试 "在新窗口中打开" 按钮

## 相关文档

- Label Studio API 文档: https://labelstud.io/api
- Label Studio 认证指南: https://labelstud.io/guide/auth.html
- 配置指南: `LABEL_STUDIO_SETUP.md`
- 详细设置: `.kiro/LABEL_STUDIO_TOKEN_SETUP_GUIDE.md`

---

**状态**: 等待用户获取正确的 API Token  
**预计时间**: 5 分钟  
**难度**: 简单
