# 快速修复指南

**问题**: http://localhost:3000 打开时无任何内容显示  
**解决方案**: 需要先登录

---

## 🚀 3 步快速修复

### 步骤 1️⃣: 打开登录页面
```
http://localhost:3000/login
```

### 步骤 2️⃣: 输入测试账号
```
用户名: admin_test
密码: admin123
```

### 步骤 3️⃣: 点击登录
等待页面加载，应该看到仪表板

---

## ✅ 验证成功

登录后应该看到:
- ✅ 顶部导航栏
- ✅ 左侧菜单
- ✅ 主要内容区域
- ✅ 各个功能模块

---

## 👤 所有测试账号

| 账号 | 用户名 | 密码 | 角色 |
|------|--------|------|------|
| 1 | admin_test | admin123 | 管理员 |
| 2 | expert_test | expert123 | 业务专家 |
| 3 | annotator_test | annotator123 | 标注员 |
| 4 | viewer_test | viewer123 | 查看者 |

---

## 🔗 直接链接

### 登录页面
```
http://localhost:3000/login
```

### 后端 API
```
http://localhost:8000
```

### 健康检查
```
http://localhost:8000/health
```

---

## 🆘 如果仍然无法显示

### 方案 A: 清除缓存
1. 打开浏览器开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"
4. 重新访问 http://localhost:3000/login

### 方案 B: 检查浏览器控制台
1. 打开浏览器开发者工具 (F12)
2. 点击 Console 标签
3. 查看是否有红色错误信息
4. 截图错误信息

### 方案 C: 重启前端
```bash
# 停止前端
pkill -f "npm run dev"

# 重启前端
cd frontend && npm run dev
```

### 方案 D: 检查后端
```bash
# 测试后端是否运行
curl http://localhost:8000/health

# 测试登录 API
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}'
```

---

## 📝 常见问题

### Q: 为什么打开 http://localhost:3000 时是空白?
**A**: 因为应用需要用户登录。请访问 http://localhost:3000/login 进行登录。

### Q: 登录页面也是空白?
**A**: 可能是 JavaScript 加载失败。请:
1. 清除浏览器缓存
2. 检查浏览器控制台是否有错误
3. 重启前端服务

### Q: 登录后仍然是空白?
**A**: 可能是应用加载失败。请:
1. 打开浏览器开发者工具
2. 查看 Console 标签中的错误
3. 查看 Network 标签中的资源加载情况

### Q: 忘记了测试账号?
**A**: 使用以下账号:
- 用户名: admin_test
- 密码: admin123

---

## ✨ 预期结果

### 登录前
- 访问 http://localhost:3000 → 重定向到登录页面
- 访问 http://localhost:3000/login → 显示登录表单

### 登录后
- 访问 http://localhost:3000 → 显示仪表板
- 可以访问所有功能模块:
  - 仪表板
  - 任务管理
  - 数据提取
  - 质量管理
  - AI 标注
  - 计费管理
  - 安全设置
  - 管理面板
  - 设置

---

## 🎯 下一步

1. ✅ 打开 http://localhost:3000/login
2. ✅ 使用 admin_test / admin123 登录
3. ✅ 验证应用正常显示
4. ✅ 测试各个功能模块
5. ✅ 测试语言切换 (中文/英文)

---

**问题已诊断**: ✅  
**解决方案**: 访问登录页面并使用测试账号登录  
**预期结果**: 应用应该正常显示
