# 修复标注按钮问题 - 操作指南

**问题**: "开始标注" 和 "在新窗口打开" 按钮无响应  
**原因**: Label Studio Community Edition 不支持 `/api/sessions/` JWT 认证端点  
**解决方案**: 使用 API Token 认证（Legacy Token）

---

## 快速修复步骤

### 步骤 1: 生成 Label Studio API Token

1. **打开 Label Studio 界面**:
   ```
   http://localhost:8080
   ```

2. **登录**:
   - 用户名: `admin@example.com`
   - 密码: `admin`

3. **进入账户设置**:
   - 点击右上角的用户图标
   - 选择 "Account & Settings"

4. **生成 Token**:
   - 查找 "Legacy Tokens" 或 "Access Tokens" 页面
   - 点击 "Generate Token" 或 "Create Token"
   - **复制生成的 Token**（类似: `f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17`）
   - ⚠️ **重要**: 保存这个 Token，它只显示一次！

### 步骤 2: 更新 `.env` 文件

1. **打开项目根目录的 `.env` 文件**

2. **注释掉 JWT 认证配置**:
   ```bash
   # JWT 认证（不支持）/ JWT Authentication (not supported in Community Edition):
   # LABEL_STUDIO_USERNAME=admin@example.com
   # LABEL_STUDIO_PASSWORD=admin
   ```

3. **启用 API Token 认证**:
   ```bash
   # API Token 认证（推荐）/ API Token Authentication (recommended):
   LABEL_STUDIO_API_TOKEN=<粘贴你刚才复制的 Token>
   ```

4. **保存文件**

### 步骤 3: 重启后端容器

```bash
# 方法 1: 重启单个容器
docker-compose restart app

# 方法 2: 重启所有容器（如果需要）
docker-compose restart

# 方法 3: 完全重建（如果上面的方法不行）
docker-compose down
docker-compose up -d
```

### 步骤 4: 验证修复

1. **检查后端日志**:
   ```bash
   docker-compose logs -f app
   ```
   
   应该看到类似的日志:
   ```
   [INFO] Using api_token authentication for Label Studio
   [INFO] Label Studio integration initialized with API token authentication
   ```

2. **测试标注按钮**:
   - 打开浏览器: http://localhost:5173
   - 进入任务详情页面
   - 点击 "开始标注" 按钮 → 应该跳转到标注页面
   - 点击 "在新窗口打开" 按钮 → 应该在新窗口打开 Label Studio

3. **验证语言设置**:
   - 切换 SuperInsight 界面语言（中文 ↔ 英文）
   - 点击 "在新窗口打开"
   - Label Studio 应该以选择的语言打开

---

## 常见问题

### Q1: 找不到 "Legacy Tokens" 页面？

**A**: 可能需要在组织级别启用:
1. 以管理员身份登录 Label Studio
2. 进入 Organization → Settings → Access Token Settings
3. 启用 "Legacy Tokens" 或 "Personal Access Tokens"

### Q2: Token 生成后忘记复制了？

**A**: 重新生成一个新的 Token:
1. 回到 Account & Settings → Legacy Tokens
2. 撤销旧的 Token（如果显示）
3. 生成新的 Token
4. 这次记得复制！

### Q3: 重启后端后仍然不工作？

**A**: 检查以下几点:
1. **确认 `.env` 文件已保存**
2. **确认 Token 正确粘贴**（没有多余空格）
3. **检查后端日志**:
   ```bash
   docker-compose logs app | grep -i "label studio"
   ```
4. **测试 Token 是否有效**:
   ```bash
   export LS_TOKEN="your-token-here"
   curl -H "Authorization: Token $LS_TOKEN" \
        http://localhost:8080/api/projects/
   ```
   应该返回 JSON 数组，不是 401 错误

### Q4: 按钮点击后显示 "Authentication failed"？

**A**: Token 可能无效或已过期:
1. 在 Label Studio UI 中检查 Token 状态
2. 如果 Token 被撤销，生成新的 Token
3. 更新 `.env` 文件
4. 重启后端容器

### Q5: 新窗口打开后要求登录？

**A**: 这是正常的，因为:
1. API Token 用于后端 API 调用
2. 浏览器访问 Label Studio UI 需要单独登录
3. 使用相同的凭据登录即可:
   - 用户名: `admin@example.com`
   - 密码: `admin`

---

## 技术说明

### 为什么 JWT 认证不工作？

Label Studio Community Edition 1.22.0 **不支持** `/api/sessions/` 端点:
- 这个端点可能是 Enterprise 版本的功能
- 或者是更新版本才有的功能
- Community Edition 使用 API Token 认证

### API Token vs JWT 的区别

| 特性 | API Token (Legacy) | JWT (Personal Access Token) |
|------|-------------------|----------------------------|
| 过期时间 | 永不过期 | ~5 分钟（需要刷新） |
| 生成方式 | UI 手动生成 | UI 手动生成 |
| 使用方式 | `Authorization: Token <token>` | `Authorization: Bearer <token>` |
| 刷新端点 | 不需要 | `/api/token/refresh` |
| 支持版本 | Community Edition ✅ | 需要组织级别启用 |

### 代码如何处理认证？

现有代码已经支持 API Token 作为后备方案:

```python
# src/label_studio/config.py
def get_auth_method(self) -> str:
    if self.username and self.password:
        return 'jwt'  # 尝试 JWT（不可用）
    elif self.api_token:
        return 'api_token'  # 后备到 API Token ✅
    else:
        raise LabelStudioConfigError(...)
```

当 JWT 凭据未配置时，代码自动使用 API Token。

---

## 安全建议

### 1. 保护 Token

- ✅ `.env` 文件已在 `.gitignore` 中
- ✅ 不要将 Token 提交到 Git
- ✅ 不要在日志中打印 Token
- ✅ 不要在公共场所分享 Token

### 2. 定期轮换 Token

建议每 90 天轮换一次:
1. 生成新的 Token
2. 更新 `.env` 文件
3. 重启后端
4. 撤销旧的 Token

### 3. 生产环境使用 HTTPS

当前设置使用 HTTP（仅限 localhost）:
- 开发环境: HTTP 可以接受
- 生产环境: **必须使用 HTTPS** 传输 Token

### 4. 最小权限原则

- 如果可能，使用项目级别的 Token
- 避免使用管理员 Token 进行 API 访问
- 定期审查 Token 权限

---

## 验证清单

完成修复后，确认以下所有项目:

- [ ] Label Studio API Token 已生成
- [ ] `.env` 文件已更新（JWT 注释，Token 启用）
- [ ] 后端容器已重启
- [ ] 后端日志显示 "api_token authentication"
- [ ] "开始标注" 按钮可以点击并跳转
- [ ] "在新窗口打开" 按钮可以打开 Label Studio
- [ ] 语言切换功能正常工作
- [ ] 没有 401 或 404 错误

---

## 需要帮助？

如果按照上述步骤操作后仍然有问题:

1. **检查日志**:
   ```bash
   # 后端日志
   docker-compose logs app | tail -100
   
   # Label Studio 日志
   docker-compose logs label-studio | tail -100
   ```

2. **检查服务状态**:
   ```bash
   docker-compose ps
   ```
   
   所有服务应该是 "Up" 状态

3. **测试 API 连接**:
   ```bash
   # 测试后端健康检查
   curl http://localhost:8000/health
   
   # 测试 Label Studio 连接
   curl http://localhost:8080/health
   ```

4. **提供以下信息**:
   - 错误消息（从浏览器控制台和后端日志）
   - 操作步骤
   - 环境信息（Docker 版本，操作系统等）

---

**预期结果**: 完成上述步骤后，标注按钮应该可以正常工作！
