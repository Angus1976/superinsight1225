# 标注按钮修复 - 快速参考卡

## 🚨 问题
"开始标注" 和 "在新窗口打开" 按钮无响应

## 🔍 原因
Label Studio Community Edition 不支持 JWT 认证（`/api/sessions/` 端点不存在）

## ✅ 解决方案
使用 API Token 认证（3 步修复）

---

## 📋 修复步骤

### 1️⃣ 生成 Token
```
1. 打开: http://localhost:8080
2. 登录: admin@example.com / admin
3. 点击: 用户图标 → Account & Settings
4. 进入: Legacy Tokens 或 Access Tokens
5. 点击: Generate Token
6. 复制: Token (类似 f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17)
```

### 2️⃣ 更新配置
编辑 `.env` 文件:
```bash
# 注释掉 JWT 配置
# LABEL_STUDIO_USERNAME=admin@example.com
# LABEL_STUDIO_PASSWORD=admin

# 启用 API Token
LABEL_STUDIO_API_TOKEN=<粘贴你的Token>
```

### 3️⃣ 重启后端
```bash
docker-compose restart app
```

---

## ✔️ 验证

### 检查日志
```bash
docker-compose logs app | grep -i "label studio"
```
应该看到: `Using api_token authentication for Label Studio`

### 测试按钮
1. 打开: http://localhost:5173
2. 进入任务详情页面
3. 点击 "开始标注" → 应该跳转
4. 点击 "在新窗口打开" → 应该打开新窗口

### 测试 API
```bash
export TOKEN="your-token-here"
curl -H "Authorization: Token $TOKEN" http://localhost:8080/api/projects/
```
应该返回 JSON 数组（不是 401 错误）

---

## 🔧 故障排查

### 问题: 找不到 Legacy Tokens 页面
**解决**: 在 Organization → Settings → Access Token Settings 中启用

### 问题: Token 无效（401 错误）
**解决**: 
1. 检查 Token 是否正确复制（无多余空格）
2. 在 Label Studio UI 中验证 Token 状态
3. 如果被撤销，生成新 Token

### 问题: 重启后仍不工作
**解决**:
1. 确认 `.env` 文件已保存
2. 检查后端日志: `docker-compose logs app`
3. 验证所有容器运行: `docker-compose ps`

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| `ANNOTATION_BUTTONS_FIX_SUMMARY.md` | 问题总结和解决方案概述 |
| `FIX_ANNOTATION_BUTTONS_GUIDE.md` | 详细操作指南（中文） |
| `LABEL_STUDIO_AUTH_SOLUTION.md` | 技术分析和认证方法详解 |
| `LABEL_STUDIO_AUTH_FLOW.md` | 认证流程图和对比 |
| `test-annotation-buttons.md` | 测试指南 |

---

## 🎯 预期结果

✅ "开始标注" 按钮可以点击并跳转  
✅ "在新窗口打开" 按钮可以打开 Label Studio  
✅ 语言切换功能正常工作  
✅ 没有 401 或 404 认证错误  

---

## ⏱️ 预计时间
**5-10 分钟**

## 🛡️ 风险等级
**低** - 只需配置更改，无代码修改

---

## 💡 关键要点

### 为什么 JWT 不工作？
- `/api/sessions/` 端点在 Community Edition 中不存在
- 返回 404 错误
- 可能是 Enterprise 版本或更新版本的功能

### 为什么 API Token 可以工作？
- 这是 Community Edition 的标准认证方式
- 代码已经支持 API Token 作为后备方案
- 只需配置即可启用

### 需要修改代码吗？
- **不需要！** 代码已经支持 API Token
- 只需更新 `.env` 配置文件
- 重启后端容器即可

---

## 🔐 安全提示

- ✅ `.env` 文件已在 `.gitignore` 中
- ✅ 不要将 Token 提交到 Git
- ✅ 定期轮换 Token（建议每 90 天）
- ✅ 生产环境使用 HTTPS

---

## 📞 需要帮助？

如果遇到问题:
1. 查看详细文档（上面列出的文档）
2. 检查日志和服务状态
3. 测试 API 连接
4. 提供错误信息和操作步骤

---

**准备好了吗？** 按照上面的 3 个步骤操作，5 分钟内修复问题！

**文档位置**: 
- 快速参考: `QUICK_FIX_REFERENCE.md` (本文件)
- 详细指南: `FIX_ANNOTATION_BUTTONS_GUIDE.md`
- 技术分析: `LABEL_STUDIO_AUTH_SOLUTION.md`
