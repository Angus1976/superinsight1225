---
inclusion: manual
---

# 技术栈与构建系统

**类型**: 项目信息  
**优先级**: MEDIUM  
**加载方式**: 手动加载（按需引用）

---

## 核心技术栈

### 后端
- FastAPI (Python 3.11+)
- PostgreSQL 15+ (JSONB)
- Redis 7+
- Neo4j 5+ (知识图谱)
- SQLAlchemy 2.0+ + Alembic
- Celery + Redis

### 前端
- React 19 + TypeScript
- Vite 7+
- Ant Design 5+ Pro
- Zustand (状态管理)
- TanStack Query (数据获取)
- React Router DOM 7+
- Vitest + Playwright (测试)

### 核心集成
- Label Studio (标注引擎)
- Transformers, PyTorch, Ollama (AI/ML)
- Presidio (数据隐私)
- Ragas (质量评估)
- Prometheus + Grafana (监控)
- JWT, bcrypt (安全)

---

## 常用命令

### 开发环境

```bash
# 后端
pip install -r requirements.txt
python main.py  # 初始化系统
uvicorn src.app:app --reload

# 前端
cd frontend
npm install
npm run dev

# 数据库
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Docker 操作

```bash
# 启动完整栈
docker-compose up -d

# 健康检查
curl http://localhost:8000/health
```

### 测试

```bash
# 后端
pytest tests/ -v --cov=src

# 前端
cd frontend
npm run test
npm run test:e2e
```

### 代码质量

```bash
# Python
black src/ tests/
isort src/ tests/
mypy src/

# TypeScript
cd frontend
npm run lint
npm run typecheck
```

---

## 环境配置

关键环境变量在 `.env` 中定义（从 `.env.example` 复制）：
- 数据库连接（PostgreSQL, Redis, Neo4j）
- Label Studio 集成设置
- AI 服务 API 密钥
- 安全和加密密钥
- 部署特定设置

---

## 部署模式

1. **本地开发**: 直接 Python + Node.js 执行
2. **Docker Compose**: 完整容器化栈
3. **腾讯云 TCB**: 云原生部署 `tcb framework deploy`