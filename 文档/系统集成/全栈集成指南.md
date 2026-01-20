# SuperInsight 全栈集成完整指南

## 项目概述

SuperInsight 是一个企业级 AI 数据治理与标注平台，采用现代全栈架构：

- **前端**: React 18 + TypeScript + Ant Design Pro + Vite
- **后端**: FastAPI + Python 3.9+ + PostgreSQL
- **数据库**: PostgreSQL 12+
- **缓存**: Redis (可选)
- **消息队列**: RabbitMQ (可选)
- **国际化**: 中文 + 英文支持

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端应用 (React)                         │
│  - 登录/注册                                                 │
│  - 仪表板                                                    │
│  - 任务管理                                                  │
│  - 计费管理                                                  │
│  - 质量管理                                                  │
│  - 安全设置                                                  │
│  - 数据增强                                                  │
│  - 管理员面板                                                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI 后端服务                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API 路由层                                           │  │
│  │ - /api/security (认证、用户管理)                     │  │
│  │ - /api/billing (计费系统)                            │  │
│  │ - /api/quality (质量管理)                            │  │
│  │ - /api/export (数据导出)                             │  │
│  │ - /api/ai_annotation (AI 标注)                       │  │
│  │ - /api/i18n (国际化)                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 业务逻辑层                                           │  │
│  │ - 用户认证与授权                                     │  │
│  │ - 计费统计与报表                                     │  │
│  │ - 质量评估与工单                                     │  │
│  │ - 数据导出与转换                                     │  │
│  │ - AI 模型集成                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 中间件层                                             │  │
│  │ - CORS 跨域处理                                      │  │
│  │ - 请求监控与追踪                                     │  │
│  │ - 错误处理                                           │  │
│  │ - 国际化处理                                         │  │
│  │ - 安全审计                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL/ORM
┌────────────────────────▼────────────────────────────────────┐
│                   PostgreSQL 数据库                          │
│  - 用户表 (users)                                            │
│  - 租户表 (tenants)                                          │
│  - 任务表 (tasks)                                            │
│  - 计费表 (billing_records)                                  │
│  - 质量表 (quality_issues)                                   │
│  - 审计日志表 (audit_logs)                                   │
│  - 其他业务表                                                │
└─────────────────────────────────────────────────────────────┘
```

## 第一部分: 环境准备

### 1.1 系统要求

**最低配置:**
- CPU: 2 核
- 内存: 4GB
- 磁盘: 20GB
- 操作系统: macOS 10.15+, Ubuntu 18.04+, Windows 10 WSL2

**推荐配置:**
- CPU: 4 核
- 内存: 8GB
- 磁盘: 50GB

### 1.2 安装依赖

#### 后端依赖

```bash
# 检查 Python 版本
python --version  # 需要 3.9+

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装 Python 依赖
pip install -r requirements.txt
```

#### 前端依赖

```bash
# 检查 Node.js 版本
node --version  # 需要 16+
npm --version   # 需要 8+

# 进入前端目录
cd frontend

# 安装依赖
npm install
```

#### 数据库依赖

```bash
# macOS (使用 Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# 验证 PostgreSQL
psql --version
```

### 1.3 环境配置

#### 后端环境变量 (.env)

```bash
# 数据库配置
DATABASE_URL=postgresql://superinsight:password@localhost:5432/superinsight_db
SQLALCHEMY_DATABASE_URL=postgresql://superinsight:password@localhost:5432/superinsight_db

# JWT 配置
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=True
ENVIRONMENT=development

# CORS 配置
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/0

# AI 模型配置
OPENAI_API_KEY=your-key
ALIBABA_API_KEY=your-key
CHATGLM_API_KEY=your-key

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

#### 前端环境变量 (frontend/.env.development)

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_ENABLE_MOCK=false
VITE_LOG_LEVEL=debug
```

## 第二部分: 数据库初始化

### 2.1 创建数据库和用户

```bash
# 连接到 PostgreSQL
psql -U postgres

# 创建数据库用户
CREATE USER superinsight WITH PASSWORD 'password';

# 创建数据库
CREATE DATABASE superinsight_db OWNER superinsight;

# 授予权限
GRANT ALL PRIVILEGES ON DATABASE superinsight_db TO superinsight;

# 退出
\q
```

### 2.2 运行数据库迁移

```bash
# 进入项目根目录
cd superinsight

# 运行 Alembic 迁移
alembic upgrade head

# 验证迁移
psql -U superinsight -d superinsight_db -c "\dt"
```

### 2.3 初始化测试数据

```bash
# 运行初始化脚本
python init_test_accounts.py

# 预期输出:
# ✅ 创建租户: SuperInsight
# ✅ 创建用户: admin@superinsight.com
# ✅ 创建用户: analyst@superinsight.com
# ✅ 创建用户: editor@superinsight.com
# ✅ 创建用户: user@superinsight.com
# ✅ 创建用户: guest@superinsight.com
```

## 第三部分: 启动服务

### 3.1 启动后端服务

```bash
# 方式 1: 使用 Uvicorn (开发模式)
python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# 方式 2: 使用启动脚本
python start_api_server.py

# 预期输出:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### 3.2 启动前端应用

在新的终端窗口中：

```bash
# 进入前端目录
cd frontend

# 启动开发服务器
npm run dev

# 预期输出:
#   VITE v4.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5173/
```

### 3.3 验证服务状态

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查 i18n 服务
curl http://localhost:8000/health/i18n

# 查看 API 文档
# 浏览器访问: http://localhost:8000/docs
```

## 第四部分: 前端登录与功能测试

### 4.1 访问应用

打开浏览器访问: **http://localhost:5173**

### 4.2 测试账户

| 账户 | 用户名 | 密码 | 角色 | 语言 |
|------|--------|------|------|------|
| 管理员 | admin@superinsight.com | Admin@123456 | Administrator | 中文 |
| 分析师 | analyst@superinsight.com | Analyst@123456 | Data Analyst | 英文 |
| 编辑 | editor@superinsight.com | Editor@123456 | Content Editor | 中文 |
| 用户 | user@superinsight.com | User@123456 | Regular User | 英文 |
| 访客 | guest@superinsight.com | Guest@123456 | Guest | 中文 |

### 4.3 登录流程测试

#### 步骤 1: 访问登录页面
- URL: http://localhost:5173/login
- 预期: 显示登录表单，包含用户名、密码字段

#### 步骤 2: 输入凭证
- 使用管理员账户: admin@superinsight.com / Admin@123456
- 点击"登录"按钮

#### 步骤 3: 验证登录成功
- 预期: 重定向到仪表板 (http://localhost:5173/dashboard)
- 显示用户信息和欢迎消息
- 左侧菜单显示可访问的功能

### 4.4 功能测试清单

#### 4.4.1 仪表板 (Dashboard)
```
测试项目:
□ 显示系统概览统计
□ 显示最近任务列表
□ 显示计费信息
□ 显示质量指标
□ 图表正确加载
□ 数据实时更新

预期结果:
- 所有统计数据正确显示
- 图表清晰可读
- 响应时间 < 2 秒
```

#### 4.4.2 任务管理 (Tasks)
```
测试项目:
□ 显示任务列表
□ 创建新任务
□ 编辑任务
□ 删除任务
□ 任务搜索和过滤
□ 任务状态更新

预期结果:
- 任务列表正确加载
- CRUD 操作成功
- 搜索功能有效
- 状态变更实时反映
```

#### 4.4.3 计费管理 (Billing)
```
测试项目:
□ 显示计费规则
□ 显示账单历史
□ 显示成本分摊
□ 显示工时统计
□ 导出报表
□ 查看成本趋势

预期结果:
- 计费数据准确
- 报表可导出
- 图表显示正确
- 数据一致性验证
```

#### 4.4.4 质量管理 (Quality)
```
测试项目:
□ 显示质量评估
□ 创建质量工单
□ 查看工单列表
□ 更新工单状态
□ 查看质量报表
□ 质量趋势分析

预期结果:
- 质量数据准确
- 工单流程正常
- 报表生成成功
- 趋势分析有效
```

#### 4.4.5 安全设置 (Security)
```
测试项目:
□ 显示用户权限
□ 显示审计日志
□ 配置 IP 白名单
□ 配置数据脱敏
□ 查看登录历史
□ 修改密码

预期结果:
- 权限配置正确
- 审计日志完整
- 安全设置生效
- 日志记录准确
```

#### 4.4.6 数据增强 (Augmentation)
```
测试项目:
□ 显示增强规则
□ 创建增强任务
□ 查看增强结果
□ 下载增强数据
□ 增强历史记录
□ 性能统计

预期结果:
- 增强功能正常
- 数据质量提升
- 下载成功
- 历史记录完整
```

#### 4.4.7 管理员面板 (Admin)
```
测试项目:
□ 显示系统监控
□ 用户管理
□ 租户管理
□ 系统配置
□ 日志查看
□ 性能监控

预期结果:
- 管理功能完整
- 数据准确
- 操作成功
- 权限控制正确
```

#### 4.4.8 设置 (Settings)
```
测试项目:
□ 修改个人信息
□ 修改密码
□ 语言切换
□ 主题切换
□ 通知设置
□ 隐私设置

预期结果:
- 设置保存成功
- 语言切换生效
- 主题切换生效
- 通知正常工作
```

### 4.5 国际化测试

#### 中文界面测试
```bash
# 使用中文账户登录
用户名: admin@superinsight.com
密码: Admin@123456

验证项目:
□ 所有菜单项显示中文
□ 所有按钮标签显示中文
□ 所有错误消息显示中文
□ 所有提示信息显示中文
□ 日期格式为中文格式
□ 数字格式为中文格式
```

#### 英文界面测试
```bash
# 使用英文账户登录
用户名: analyst@superinsight.com
密码: Analyst@123456

验证项目:
□ 所有菜单项显示英文
□ 所有按钮标签显示英文
□ 所有错误消息显示英文
□ 所有提示信息显示英文
□ 日期格式为英文格式
□ 数字格式为英文格式
```

#### 语言切换测试
```bash
# 在设置页面切换语言
1. 点击"设置" (Settings)
2. 找到"语言" (Language) 选项
3. 从中文切换到英文
4. 验证整个界面切换为英文
5. 从英文切换回中文
6. 验证整个界面切换为中文

预期结果:
- 语言切换立即生效
- 所有文本正确翻译
- 布局不变
- 功能不受影响
```

## 第五部分: API 集成测试

### 5.1 认证 API

```bash
# 登录
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@superinsight.com",
    "password": "Admin@123456"
  }'

# 预期响应:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "admin@superinsight.com",
  "role": "admin",
  "tenant_id": "uuid"
}
```

### 5.2 用户 API

```bash
# 获取当前用户信息
curl -X GET http://localhost:8000/api/security/users/me \
  -H "Authorization: Bearer {access_token}"

# 获取用户列表
curl -X GET http://localhost:8000/api/security/users \
  -H "Authorization: Bearer {access_token}"
```

### 5.3 计费 API

```bash
# 获取月度账单
curl -X GET http://localhost:8000/api/billing/enhanced-report \
  -H "Authorization: Bearer {access_token}"

# 获取工时统计
curl -X GET http://localhost:8000/api/billing/work-hours/{tenant_id} \
  -H "Authorization: Bearer {access_token}"
```

### 5.4 质量 API

```bash
# 创建质量工单
curl -X POST http://localhost:8000/api/quality/issues \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quality Issue",
    "description": "Description",
    "severity": "high"
  }'

# 获取质量报表
curl -X GET http://localhost:8000/api/quality/report \
  -H "Authorization: Bearer {access_token}"
```

## 第六部分: 性能测试

### 6.1 负载测试

```bash
# 运行性能测试
python performance_load_test.py

# 预期结果:
# - 平均响应时间 < 500ms
# - P95 响应时间 < 1000ms
# - 错误率 < 1%
# - 吞吐量 > 100 req/s
```

### 6.2 并发测试

```bash
# 使用 Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8000/health
```

## 第七部分: 故障排查

### 7.1 常见问题

#### 问题 1: 数据库连接失败
```
错误信息: psycopg2.OperationalError: could not connect to server

解决方案:
1. 检查 PostgreSQL 是否运行: pg_isready
2. 检查数据库 URL 是否正确
3. 检查用户名和密码
4. 检查防火墙设置
```

#### 问题 2: 前端无法连接后端
```
错误信息: CORS error / Network error

解决方案:
1. 检查后端是否运行: curl http://localhost:8000/health
2. 检查 CORS 配置
3. 检查防火墙和代理设置
4. 检查前端 API 地址配置
```

#### 问题 3: 登录失败
```
错误信息: Invalid username or password

解决方案:
1. 检查用户是否存在: python init_test_accounts.py
2. 检查密码是否正确
3. 检查用户是否被禁用
4. 查看后端日志
```

#### 问题 4: 页面加载缓慢
```
解决方案:
1. 检查网络连接
2. 检查后端性能: curl http://localhost:8000/health
3. 检查数据库查询性能
4. 检查浏览器开发者工具中的网络标签
```

### 7.2 日志查看

```bash
# 查看后端日志
tail -f logs/app.log

# 查看前端控制台
# 打开浏览器开发者工具 (F12) -> Console 标签

# 查看数据库日志
tail -f /var/log/postgresql/postgresql.log
```

### 7.3 调试模式

```bash
# 启用后端调试模式
DEBUG=True python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# 启用前端调试模式
VITE_LOG_LEVEL=debug npm run dev
```

## 第八部分: 部署检查清单

在部署到生产环境前，请完成以下检查:

```
□ 数据库备份已配置
□ 环境变量已设置
□ SSL/TLS 证书已配置
□ 日志系统已配置
□ 监控系统已配置
□ 备份和恢复流程已测试
□ 性能基准已建立
□ 安全审计已完成
□ 用户文档已准备
□ 支持流程已建立
```

## 第九部分: 快速参考

### 常用命令

```bash
# 启动所有服务
./quick_start.sh

# 停止所有服务
pkill -f uvicorn
pkill -f "npm run dev"

# 重置数据库
alembic downgrade base
alembic upgrade head
python init_test_accounts.py

# 查看日志
tail -f logs/app.log

# 运行测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 有用的 URL

| 功能 | URL |
|------|-----|
| 前端应用 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 数据库 | localhost:5432 |
| 健康检查 | http://localhost:8000/health |
| i18n 健康检查 | http://localhost:8000/health/i18n |

## 支持和反馈

如有问题或建议，请:

1. 查看 [故障排查指南](./docs/troubleshooting.md)
2. 查看 [API 文档](./docs/api/README.md)
3. 提交 Issue 到 GitHub
4. 联系技术支持团队

---

**最后更新**: 2024年1月
**版本**: 1.0
