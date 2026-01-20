# SuperInsight AI 数据治理与标注平台

SuperInsight 是一款专为 AI 时代设计的企业级语料治理与智能标注平台，深度借鉴龙石数据成熟的"理采存管用"方法论，同时针对大模型（LLM）和生成式 AI（GenAI）应用场景进行全面升级。

## 🚨 Documentation-First Development (文档优先开发)

**本项目强制执行严格的文档优先开发工作流。**

在修改任何代码之前，您必须：
1. ✅ 更新文档 (requirements, design, tasks, CHANGELOG)
2. ✅ 运行验证脚本
3. ✅ 获得批准

**快速开始**: 查看 [文档优先快速参考](.kiro/specs/DOC_FIRST_QUICK_REFERENCE.md)  
**完整指南**: 查看 [文档优先工作流](.kiro/steering/doc-first-workflow.md)  
**实例演示**: 查看 [实时演示](.kiro/specs/DOC_FIRST_DEMO.md)

---

## 特性

- 🔒 **安全数据提取**: 只读权限提取各种数据源
- 🤖 **AI 预标注**: 集成多种 LLM 模型进行智能预标注
- 👥 **人机协同**: 支持业务专家、技术专家协作标注
- 📊 **质量管理**: 基于 Ragas 的语义质量评估
- 💰 **计费结算**: 精确的工时和条数统计
- 🛡️ **企业级安全**: 完整的审计、权限控制、数据脱敏系统
- 🔍 **实时监控**: 安全事件监控、威胁检测、合规报告
- 🎯 **自动脱敏**: 基于 Presidio 的智能数据脱敏和隐私保护
- 📋 **合规管理**: GDPR、SOX、ISO 27001 等标准合规报告
- ☁️ **多部署**: 支持云托管、私有化、混合云部署

## 技术架构

- **核心引擎**: Label Studio
- **数据存储**: PostgreSQL + JSONB
- **缓存**: Redis
- **Web 框架**: FastAPI
- **AI 集成**: Ollama, HuggingFace, 国产 LLM APIs
- **安全审计**: 企业级审计日志系统，支持防篡改和完整性验证
- **权限控制**: 基于 RBAC 的细粒度权限管理，支持多租户隔离
- **数据脱敏**: Microsoft Presidio 集成，自动 PII 检测和脱敏
- **安全监控**: 实时威胁检测、安全事件监控、自动告警
- **合规报告**: 自动化合规报告生成，支持多种国际标准
- **部署**: Docker Compose, 腾讯云 TCB

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (可选)
- Microsoft Presidio (可选，用于数据脱敏)

### 本地开发环境

1. **克隆项目**
```bash
git clone https://github.com/Angus1976/superinsight1225.git
cd superinsight1225
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

4. **启动数据库服务**
```bash
# 使用 Docker Compose 启动所有服务
docker-compose up -d postgres redis label-studio

# 或者手动启动 PostgreSQL 和 Redis
```

5. **初始化数据库**
```bash
# 数据库会通过 init-db.sql 自动初始化
# 或者手动运行初始化脚本
psql -h localhost -U superinsight -d superinsight -f scripts/init-db.sql
```

6. **启动应用**
```bash
python main.py
```

### Docker 部署

使用 Docker Compose 一键启动完整环境：

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f superinsight-api
```

服务访问地址：
- SuperInsight API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 安全仪表盘: http://localhost:8000/security/dashboard
- 审计日志: http://localhost:8000/audit/events
- Label Studio: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 腾讯云 TCB 部署

1. **安装 TCB CLI**
```bash
npm install -g @cloudbase/cli
```

2. **配置 TCB 环境**
```bash
# 登录腾讯云
tcb login

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 TCB 相关信息
```

3. **部署到 TCB**
```bash
# 部署云托管服务
tcb framework deploy
```

## 项目结构

```
superinsight-platform/
├── src/                          # 源代码目录
│   ├── models/                   # 数据模型
│   ├── config/                   # 配置管理
│   ├── database/                 # 数据库连接
│   ├── extractors/               # 数据提取器
│   ├── label_studio/             # Label Studio 集成
│   ├── ai/                       # AI 预标注服务
│   ├── quality/                  # 质量管理
│   ├── billing/                  # 计费系统
│   ├── security/                 # 安全控制与审计系统
│   │   ├── audit_service.py      # 企业级审计服务
│   │   ├── rbac_controller.py    # RBAC 权限控制
│   │   ├── auto_desensitization_service.py  # 自动脱敏服务
│   │   ├── security_event_monitor.py        # 安全事件监控
│   │   └── threat_detector.py    # 威胁检测引擎
│   ├── compliance/               # 合规管理
│   │   ├── report_generator.py   # 合规报告生成
│   │   └── performance_optimizer.py  # 性能优化
│   ├── desensitization/          # 数据脱敏
│   │   └── validator.py          # 脱敏效果验证
│   ├── sync/desensitization/     # 同步脱敏系统
│   │   ├── presidio_engine.py    # Presidio 引擎集成
│   │   ├── rule_manager.py       # 脱敏规则管理
│   │   └── data_classifier.py    # 数据分类器
│   ├── api/                      # API 接口
│   └── utils/                    # 工具函数
├── tests/                        # 测试代码
├── scripts/                      # 脚本文件
├── .kiro/specs/                  # 项目规范文档
├── alembic/                      # 数据库迁移
├── docker-compose.yml            # Docker 编排文件
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
└── main.py                       # 应用入口
```

## 配置说明

### 数据库配置

```bash
# PostgreSQL 配置
DATABASE_URL=postgresql://username:password@localhost:5432/superinsight
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=superinsight
DATABASE_USER=username
DATABASE_PASSWORD=password
```

### Label Studio 配置

```bash
# Label Studio 配置
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_API_TOKEN=your_api_token_here
LABEL_STUDIO_PROJECT_ID=1
```

### AI 服务配置

```bash
# Ollama 本地模型
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# HuggingFace 模型
HUGGINGFACE_API_TOKEN=your_token_here
HUGGINGFACE_MODEL=bert-base-chinese

# 国产 LLM APIs
ZHIPU_API_KEY=your_zhipu_key_here
BAIDU_API_KEY=your_baidu_key_here
ALIBABA_API_KEY=your_alibaba_key_here
TENCENT_API_KEY=your_tencent_key_here
```

### 安全与审计配置

```bash
# 审计日志配置
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=2555  # 7年保留期
AUDIT_BATCH_SIZE=1000
AUDIT_COMPRESSION_ENABLED=true

# 数据脱敏配置
PRESIDIO_ENABLED=true
PRESIDIO_ANALYZER_ENABLED=true
PRESIDIO_ANONYMIZER_ENABLED=true
DESENSITIZATION_DEFAULT_LANGUAGE=zh
DESENSITIZATION_CONFIDENCE_THRESHOLD=0.8

# RBAC 权限配置
RBAC_CACHE_ENABLED=true
RBAC_CACHE_TTL=300
PERMISSION_CHECK_TIMEOUT=10  # 10ms 权限检查超时

# 安全监控配置
SECURITY_MONITORING_ENABLED=true
THREAT_DETECTION_ENABLED=true
SECURITY_ALERT_ENABLED=true
SECURITY_SCAN_INTERVAL=30  # 30秒扫描间隔

# 合规报告配置
COMPLIANCE_REPORTS_ENABLED=true
COMPLIANCE_STANDARDS=GDPR,SOX,ISO27001,HIPAA,CCPA
COMPLIANCE_AUTO_GENERATION=true
```

## 企业级安全特性

SuperInsight 提供完整的企业级安全和合规解决方案：

### 🔍 审计日志系统

- **完整审计**: 记录所有用户操作和系统事件
- **防篡改保护**: 数字签名确保审计日志完整性
- **高性能存储**: 批量存储，压缩优化，分区管理
- **长期保留**: 支持 7 年数据保留，自动归档
- **查询导出**: 多条件查询，支持 Excel/CSV/JSON 导出

### 🛡️ 数据脱敏系统

- **智能检测**: 基于 Microsoft Presidio 的 PII 自动检测
- **多语言支持**: 支持中英文敏感数据识别
- **策略管理**: 租户级别脱敏策略配置
- **效果验证**: 脱敏完整性和准确性自动验证
- **实时监控**: 脱敏质量实时监控和告警

### 🔐 RBAC 权限控制

- **细粒度权限**: 基于角色的访问控制，支持资源级权限
- **多租户隔离**: 完整的租户级别权限隔离
- **高性能缓存**: <10ms 权限检查，>90% 缓存命中率
- **动态管理**: 运行时角色和权限动态配置
- **权限审计**: 所有权限操作完整审计记录

### 🚨 安全监控系统

- **实时监控**: 30秒间隔安全事件扫描
- **威胁检测**: 多方法威胁检测（规则、统计、行为、ML）
- **自动响应**: IP 封禁、用户暂停、管理员通知
- **安全仪表盘**: 实时安全状态可视化
- **告警系统**: 多级别安全告警和紧急通知

### 📋 合规报告系统

- **多标准支持**: GDPR、SOX、ISO 27001、HIPAA、CCPA
- **自动生成**: 支持日、周、月、季度自动报告
- **多格式导出**: JSON、PDF、Excel、HTML、CSV
- **违规检测**: 自动检测合规违规和修复建议
- **执行摘要**: 专业的管理层报告和关键发现

### 性能指标

- **审计性能**: <50ms 审计日志写入，1000条/批次存储
- **权限性能**: <10ms 权限检查，>95% 缓存命中率
- **脱敏性能**: >95% 准确率，零数据泄露
- **监控性能**: <5秒安全事件响应，实时威胁检测
- **合规性能**: <30秒报告生成，自动化流程

## 开发指南

### 代码规范

项目使用以下工具确保代码质量：

```bash
# 代码格式化
black src/ tests/

# 导入排序
isort src/ tests/

# 类型检查
mypy src/

# 安全测试
pytest tests/security/ -v
pytest tests/test_*security*.py -v
pytest tests/test_*audit*.py -v
pytest tests/test_*rbac*.py -v

# 运行测试
pytest tests/ -v --cov=src
```

### 数据库迁移

使用 Alembic 管理数据库迁移：

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 测试

项目包含单元测试、集成测试和安全测试：

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_models.py

# 运行安全测试套件
pytest tests/security/ -v

# 运行审计系统测试
pytest tests/test_*audit*.py -v

# 运行权限系统测试
pytest tests/test_*rbac*.py -v

# 运行脱敏系统测试
pytest tests/test_*desensitization*.py -v

# 运行属性测试
pytest tests/ -k "property"

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 性能测试
pytest tests/benchmarks/ -v
```

### 安全验证

系统提供多层安全验证：

```bash
# 权限绕过防护测试
python validate_fine_grained_permission_control.py

# 审计完整性验证
python test_audit_integrity_implementation.py

# 数据泄露防护测试
python complete_zero_leakage_implementation.py

# 性能安全测试
python validate_10ms_performance.py
python validate_compliance_performance_30s.py
python validate_real_time_security_performance.py

# 脱敏效果验证
python test_final_desensitization_performance.py
```

## API 文档

启动应用后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 核心 API 端点

#### 审计系统 API
```bash
# 查询审计事件
POST /api/audit/events/query

# 导出审计日志
POST /api/audit/export/excel
POST /api/audit/export/csv
POST /api/audit/export/json

# 审计统计
GET /api/audit/statistics

# 审计健康检查
GET /api/audit/health
```

#### 数据脱敏 API
```bash
# PII 检测
POST /api/desensitization/detect

# 数据匿名化
POST /api/desensitization/anonymize

# 脱敏规则管理
GET /api/desensitization/rules
POST /api/desensitization/rules
PUT /api/desensitization/rules/{rule_id}

# 脱敏策略管理
GET /api/desensitization/policies
POST /api/desensitization/policies
PUT /api/desensitization/policies/{policy_id}
```

#### RBAC 权限 API
```bash
# 权限检查
POST /api/rbac/check-permission

# 角色管理
GET /api/rbac/roles
POST /api/rbac/roles
PUT /api/rbac/roles/{role_id}

# 用户角色分配
POST /api/rbac/users/{user_id}/roles
DELETE /api/rbac/users/{user_id}/roles/{role_id}

# 权限缓存管理
GET /api/rbac/cache/stats
POST /api/rbac/cache/invalidate
```

#### 安全监控 API
```bash
# 安全事件查询
GET /api/security/events

# 威胁检测状态
GET /api/security/threats

# 安全仪表盘数据
GET /api/security/dashboard

# 安全告警
GET /api/security/alerts
POST /api/security/alerts/acknowledge
```

#### 合规报告 API
```bash
# 生成合规报告
POST /api/compliance/reports/generate

# 获取合规报告
GET /api/compliance/reports/{report_id}

# 导出合规报告
GET /api/compliance/reports/{report_id}/export

# 合规统计
GET /api/compliance/statistics
```

### WebSocket 端点

```bash
# 实时安全监控
ws://localhost:8000/ws/security/dashboard

# 实时审计事件
ws://localhost:8000/ws/audit/events

# 实时告警通知
ws://localhost:8000/ws/alerts
```

## 监控与运维

### 健康检查

```bash
# 系统健康检查
curl http://localhost:8000/health

# 详细系统状态
curl http://localhost:8000/system/status

# 安全系统健康检查
curl http://localhost:8000/security/health

# 审计系统健康检查
curl http://localhost:8000/audit/health

# 数据库连接检查
curl http://localhost:8000/health/database

# Redis 连接检查
curl http://localhost:8000/health/redis
```

### 性能监控

```bash
# Prometheus 指标
curl http://localhost:8000/metrics

# 安全指标
curl http://localhost:8000/security/metrics

# 审计性能指标
curl http://localhost:8000/audit/performance

# 权限缓存统计
curl http://localhost:8000/rbac/cache/stats
```

### 故障排查

常见问题和解决方案：

1. **权限检查超时**
   ```bash
   # 检查权限缓存状态
   curl http://localhost:8000/rbac/cache/stats
   
   # 清理权限缓存
   curl -X POST http://localhost:8000/rbac/cache/invalidate
   ```

2. **审计日志写入失败**
   ```bash
   # 检查审计系统状态
   curl http://localhost:8000/audit/health
   
   # 查看审计性能指标
   curl http://localhost:8000/audit/performance
   ```

3. **脱敏服务异常**
   ```bash
   # 检查 Presidio 服务状态
   curl http://localhost:8000/desensitization/health
   
   # 验证脱敏配置
   curl http://localhost:8000/desensitization/config
   ```

4. **安全告警过多**
   ```bash
   # 查看安全事件统计
   curl http://localhost:8000/security/statistics
   
   # 调整威胁检测阈值
   curl -X POST http://localhost:8000/security/config \
     -H "Content-Type: application/json" \
     -d '{"threat_threshold": 0.8}'
   ```

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 支持

如有问题，请联系：
- 邮箱: support@superinsight.ai
- 安全问题: security@superinsight.ai
- 文档: https://docs.superinsight.ai
- 安全文档: https://docs.superinsight.ai/security

### 安全报告

如发现安全漏洞，请通过以下方式报告：
- 安全邮箱: security@superinsight.ai
- 加密通信: 使用我们的 PGP 公钥
- 响应时间: 24小时内确认，72小时内初步响应

### 企业支持

企业客户可获得：
- 7x24 技术支持
- 专属安全顾问
- 定制化合规方案
- 现场部署支持
- 安全培训服务
