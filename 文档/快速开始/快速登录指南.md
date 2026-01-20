# SuperInsight 快速登录指南

## 系统状态
✅ 所有服务正常运行  
✅ 登录系统完全可用  
✅ 所有测试账户已创建  

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端应用 | http://localhost:5173 | 主应用界面 |
| 登录页面 | http://localhost:5173/login | 登录入口 |
| 后端API | http://localhost:8000 | API服务器 |
| Label Studio | http://localhost:8080 | 标注工具 |

## 测试账户

### 管理员账户
- **用户名**: admin_user
- **密码**: Admin@123456
- **角色**: 管理员
- **权限**: 完全访问

### 业务专家账户
- **用户名**: business_expert
- **密码**: Business@123456
- **角色**: 业务专家
- **权限**: 业务相关功能

### 技术专家账户
- **用户名**: technical_expert
- **密码**: Technical@123456
- **角色**: 技术专家
- **权限**: 技术相关功能

### 承包商账户
- **用户名**: contractor
- **密码**: Contractor@123456
- **角色**: 承包商
- **权限**: 有限访问

### 查看者账户
- **用户名**: viewer
- **密码**: Viewer@123456
- **角色**: 查看者
- **权限**: 只读访问

## 登录步骤

### 方法1: 网页登录
1. 打开浏览器，访问 http://localhost:5173/login
2. 输入用户名（例如：admin_user）
3. 输入密码（例如：Admin@123456）
4. 选择租户：Default Tenant
5. 点击"登录"按钮
6. 系统将自动跳转到仪表板

### 方法2: API登录（使用curl）
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin_user",
    "password": "Admin@123456"
  }'
```

响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "7b6a3c79-74d0-44d7-a243-1d449e21a955",
    "username": "admin_user",
    "email": "admin@superinsight.local",
    "full_name": "Admin User",
    "role": "admin",
    "tenant_id": "default_tenant",
    "is_active": true
  }
}
```

## 常见问题

### Q: 登录后无法访问仪表板？
**A**: 
1. 检查浏览器控制台是否有错误
2. 确保后端API正在运行：`docker ps`
3. 清除浏览器缓存并重新登录

### Q: 忘记密码怎么办？
**A**: 
1. 点击登录页面的"忘记密码？"链接
2. 输入注册邮箱
3. 按照邮件中的链接重置密码

### Q: 如何切换租户？
**A**:
1. 登录后，在用户菜单中选择"切换租户"
2. 选择要切换的租户
3. 系统将重新加载新租户的数据

### Q: 如何退出登录？
**A**:
1. 点击右上角用户菜单
2. 选择"退出登录"
3. 系统将清除认证信息并返回登录页面

## 技术信息

### 认证方式
- JWT (JSON Web Token)
- 令牌有效期：24小时
- 支持令牌刷新

### 安全特性
- 密码使用bcrypt加密
- HTTPS支持（生产环境）
- CORS配置
- 审计日志记录

### 支持的语言
- 中文 (简体)
- English

## 故障排查

### 检查服务状态
```bash
docker ps
```

应该看到以下容器运行中：
- superinsight-frontend
- superinsight-api
- superinsight-postgres
- superinsight-redis
- superinsight-neo4j
- superinsight-label-studio

### 查看日志
```bash
# 后端日志
docker logs superinsight-api

# 前端日志
docker logs superinsight-frontend
```

### 测试API连接
```bash
curl http://localhost:8000/health
```

应该返回：
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

## 获取帮助

如需帮助，请：
1. 查看系统日志
2. 检查网络连接
3. 确保所有服务都在运行
4. 尝试清除浏览器缓存

---

**最后更新**: 2026-01-09  
**系统版本**: 1.0.0  
**状态**: ✅ 正常运行
