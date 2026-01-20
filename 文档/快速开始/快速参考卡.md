# SuperInsight 快速参考卡

## 🚀 快速启动 (5 分钟)

### 方式 1: 自动化设置 (推荐)
```bash
chmod +x fullstack_setup.sh
./fullstack_setup.sh
```

### 方式 2: 手动启动

**终端 1 - 后端:**
```bash
source venv/bin/activate
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 前端:**
```bash
cd frontend
npm run dev
```

## 📍 访问地址

| 功能 | URL |
|------|-----|
| 前端应用 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

## 👤 测试账户

```
管理员:
  用户名: admin@superinsight.com
  密码: Admin@123456
  语言: 中文

分析师:
  用户名: analyst@superinsight.com
  密码: Analyst@123456
  语言: 英文

编辑:
  用户名: editor@superinsight.com
  密码: Editor@123456
  语言: 中文

用户:
  用户名: user@superinsight.com
  密码: User@123456
  语言: 英文

访客:
  用户名: guest@superinsight.com
  密码: Guest@123456
  语言: 中文
```

## 🧪 测试

### 运行集成测试
```bash
python fullstack_integration_test.py
```

### 运行单元测试
```bash
pytest tests/ -v
```

### 运行性能测试
```bash
python performance_load_test.py
```

## 📚 主要功能

| 功能 | 路由 | 说明 |
|------|------|------|
| 登录 | /login | 用户认证 |
| 仪表板 | /dashboard | 系统概览 |
| 任务管理 | /tasks | 创建和管理任务 |
| 计费管理 | /billing | 计费规则和账单 |
| 质量管理 | /quality | 质量评估和工单 |
| 安全设置 | /security | 权限和审计 |
| 数据增强 | /augmentation | 数据增强规则 |
| 管理员 | /admin | 系统管理 |
| 设置 | /settings | 个人设置 |

## 🔌 主要 API 端点

### 认证
```
POST /api/security/login
POST /api/security/logout
GET /api/security/users/me
```

### 用户
```
GET /api/security/users
POST /api/security/users
GET /api/security/users/{user_id}
PUT /api/security/users/{user_id}
DELETE /api/security/users/{user_id}
```

### 计费
```
GET /api/billing/enhanced-report
GET /api/billing/work-hours/{tenant_id}
POST /api/billing/rules/versions
GET /api/billing/project-breakdown
```

### 质量
```
GET /api/quality/report
POST /api/quality/issues
GET /api/quality/issues
PUT /api/quality/issues/{issue_id}
```

### i18n
```
GET /api/i18n/translations
GET /api/i18n/languages
POST /api/i18n/set-language
```

## 🛠️ 常用命令

### 数据库
```bash
# 运行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade base

# 初始化测试数据
python init_test_accounts.py

# 备份数据库
pg_dump superinsight_db > backup.sql

# 恢复数据库
psql superinsight_db < backup.sql
```

### 前端
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 运行测试
npm run test

# 代码检查
npm run lint
```

### 后端
```bash
# 启动服务
python -m uvicorn src.app:app --reload

# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 查看日志
tail -f logs/app.log
```

## 🐛 常见问题

### 问题: 无法连接到后端
**解决**: 
1. 检查后端是否运行: `curl http://localhost:8000/health`
2. 检查防火墙设置
3. 检查 CORS 配置

### 问题: 登录失败
**解决**:
1. 检查用户是否存在: `python init_test_accounts.py`
2. 检查密码是否正确
3. 查看后端日志: `tail -f logs/app.log`

### 问题: 数据库连接失败
**解决**:
1. 检查 PostgreSQL 是否运行: `pg_isready`
2. 检查数据库 URL 配置
3. 检查用户名和密码

### 问题: 前端页面加载缓慢
**解决**:
1. 检查网络连接
2. 检查后端性能: `curl http://localhost:8000/health`
3. 打开浏览器开发者工具查看网络标签

## 📖 文档

| 文档 | 说明 |
|------|------|
| FULLSTACK_INTEGRATION_GUIDE.md | 完整集成指南 |
| FRONTEND_TESTING_GUIDE.md | 前端测试指南 |
| FULLSTACK_DEPLOYMENT_REPORT.md | 部署报告 |
| FULLSTACK_INTEGRATION_SUMMARY.md | 项目总结 |
| LOCAL_STARTUP_GUIDE.md | 本地启动指南 |

## 🔐 安全提示

- ✅ 生产环境中更改 SECRET_KEY
- ✅ 启用 HTTPS/TLS
- ✅ 配置 IP 白名单
- ✅ 定期备份数据库
- ✅ 监控审计日志
- ✅ 定期更新依赖包

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 平均响应时间 | 150ms |
| 最大响应时间 | 500ms |
| 吞吐量 | 150 req/s |
| 错误率 | 0.1% |
| 可用性 | 99.9% |

## 🌍 国际化

### 支持的语言
- 中文 (zh)
- 英文 (en)

### 切换语言
1. 点击右上角用户菜单
2. 选择"设置"
3. 选择"语言"
4. 选择目标语言
5. 点击"保存"

## 📞 支持

- **技术支持**: support@superinsight.com
- **问题报告**: issues@superinsight.com
- **文档**: https://docs.superinsight.com
- **GitHub**: https://github.com/superinsight/platform

## ✅ 检查清单

启动前检查:
- [ ] Python 3.9+ 已安装
- [ ] Node.js 16+ 已安装
- [ ] PostgreSQL 已安装并运行
- [ ] 依赖包已安装
- [ ] 环境变量已配置
- [ ] 数据库已初始化

启动后检查:
- [ ] 后端服务运行正常
- [ ] 前端应用可访问
- [ ] 可以成功登录
- [ ] 所有功能正常
- [ ] 集成测试通过

## 🎯 下一步

1. **立即**: 运行自动化设置脚本
2. **今天**: 启动服务并测试功能
3. **本周**: 完成前端功能测试
4. **本月**: 部署到生产环境

---

**最后更新**: 2024年1月  
**版本**: 1.0

💡 **提示**: 保存此文档以便快速参考！
