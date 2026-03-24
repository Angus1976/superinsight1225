---
inclusion: manual
---

# 安全审查清单 (Security Review Checklist)

**Version**: 1.0
**Status**: ✅ Active
**Last Updated**: 2026-03-16
**Priority**: CRITICAL
**来源**: 参考 everything-claude-code 安全审查模式，适配本项目
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则

**安全是不可妥协的底线，尤其是处理企业敏感数据的标注平台。**

---

## 🔴 OWASP Top 10 检查（每次 PR 必查）

### 1. 注入攻击防护
- [ ] SQL 查询使用参数化（SQLAlchemy ORM / `text()` + bindparams）
- [ ] 禁止字符串拼接 SQL
- [ ] Neo4j Cypher 查询使用参数化
- [ ] 用户输入经过 Pydantic schema 验证

### 2. 认证与会话管理
- [ ] JWT token 有合理过期时间
- [ ] 密码使用 bcrypt 哈希（不用 MD5/SHA1）
- [ ] 敏感操作需要重新认证
- [ ] Token 刷新机制安全

### 3. 敏感数据保护
- [ ] API 响应不泄露内部错误详情
- [ ] 日志不记录密码、token、API key
- [ ] 数据脱敏中间件正常工作（Presidio）
- [ ] `.env` 文件不提交到 git

### 4. 访问控制 (RBAC)
- [ ] 每个 API 端点有权限检查
- [ ] 多租户数据隔离（tenant_id 过滤）
- [ ] 文件上传限制类型和大小
- [ ] 管理员操作有审计日志

### 5. 安全配置
- [ ] CORS 配置限制允许的域名
- [ ] 生产环境关闭 debug 模式
- [ ] HTTP 安全头设置（CSP, X-Frame-Options 等）
- [ ] Rate limiting 已启用

---

## 🟡 代码级安全检查

### Python/FastAPI
```python
# ❌ 危险：字符串拼接 SQL
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全：参数化查询
query = select(User).where(User.id == user_id)

# ❌ 危险：不验证文件类型
@app.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()

# ✅ 安全：验证文件类型和大小
ALLOWED_TYPES = {"text/csv", "application/json", "application/pdf"}
MAX_SIZE = 50 * 1024 * 1024  # 50MB

@app.post("/upload")
async def upload(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Unsupported file type")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large")
```

### TypeScript/React
```typescript
// ❌ 危险：直接渲染 HTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ✅ 安全：使用文本渲染或 DOMPurify
<div>{userInput}</div>

// ❌ 危险：在 URL 中拼接用户输入
window.location.href = `/page?redirect=${userInput}`

// ✅ 安全：验证和编码
const safeUrl = new URL(userInput, window.location.origin)
if (safeUrl.origin === window.location.origin) {
  window.location.href = safeUrl.toString()
}
```

---

## 🟢 密钥和凭证检查

### 禁止出现在代码中的模式
- `sk-` (API keys)
- `ghp_` (GitHub tokens)
- `AKIA` (AWS access keys)
- `password = "..."` (硬编码密码)
- `secret = "..."` (硬编码密钥)
- Base64 编码的凭证

### 正确做法
- 所有密钥通过 `.env` 文件或环境变量注入
- 使用 `src/config/` 中的配置管理模块读取
- CI/CD 中使用 secrets 管理

---

## 📋 PR 安全审查流程

1. **自动检查**：确认无硬编码密钥
2. **输入验证**：所有外部输入经过 Pydantic 验证
3. **权限检查**：新 API 端点有 RBAC 装饰器
4. **数据隔离**：查询包含 tenant_id 过滤
5. **错误处理**：异常不泄露内部信息
6. **日志安全**：敏感字段已脱敏

---

## ⚠️ 项目特有陷阱

### 双路由 JWT 密钥一致性
- `auth_simple.py` 和 `auth.py` 都注册在 `/api/auth` 前缀，路由加载顺序决定哪个处理 `/api/auth/login`
- 两个模块的 `SECRET_KEY` / `ALGORITHM` / token payload 结构必须一致，否则一个签发的 token 另一个验证必失败
- 症状：登录成功但页面一闪跳回仪表盘（401 → refresh 失败 → 重定向 login → 已登录 → 重定向 dashboard）

### `HTTPBearer(auto_error=False)` 静默降级
- `business_metrics.py` 等使用 `HTTPBearer(auto_error=False)` + `Optional[UserModel]`，token 无效时 user=None 而非 401
- 这会掩盖认证配置错误，dashboard 正常但其他页面全部跳转，误导排查方向
- 审查时确认：使用 `auto_error=False` 的端点是否真的允许匿名访问

### LS SSO token 必须由 LS 自身签发
- 给 Label Studio 的 SSO token 必须调用 LS 的 `/api/sso/token` 端点获取，不能用 SuperInsight 的 `jwt_secret_key` 签发
- LS 的 `JWTAutoLoginMiddleware` 只认 LS 自己的 `SECRET_KEY`，跨系统 JWT 信任边界不可混用

---

## 🔗 相关资源

- **异步安全**: `.kiro/rules/async-sync-safety-quick-reference.md`
- **代码质量**: `.kiro/rules/coding-quality-standards.md`
- **项目安全架构**: `src/security/` 目录
