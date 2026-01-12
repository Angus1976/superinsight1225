# Technology Stack & Build System

## Core Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with JSONB support
- **Cache**: Redis 7+
- **Graph Database**: Neo4j 5+ (for knowledge graphs)
- **ORM**: SQLAlchemy 2.0+ with Alembic migrations
- **Task Queue**: Celery with Redis broker

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite 7+
- **UI Library**: Ant Design 5+ with Pro Components
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router DOM 7+
- **Testing**: Vitest + Playwright for E2E

### Core Integrations
- **Annotation Engine**: Label Studio (containerized)
- **AI/ML**: Transformers, PyTorch, Ollama, multiple LLM APIs
- **Data Privacy**: Presidio (analyzer + anonymizer)
- **Quality Assessment**: Ragas framework
- **Monitoring**: Prometheus + Grafana
- **Security**: JWT, bcrypt, cryptography

## Common Commands

### Development Setup
```bash
# Backend setup
pip install -r requirements.txt
python main.py  # Initialize system
uvicorn src.app:app --reload  # Start API server

# Frontend setup
cd frontend
npm install
npm run dev  # Development server

# Database operations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Docker Operations
```bash
# Full stack startup
docker-compose up -d
./start-fullstack.sh  # Alternative startup script

# Individual services
docker-compose up -d postgres redis neo4j label-studio
docker-compose logs -f superinsight-api

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/system/status
```

### Testing
```bash
# Backend testing
pytest tests/ -v --cov=src
pytest --cov=src --cov-report=html

# Frontend testing
cd frontend
npm run test  # Unit tests with Vitest
npm run test:e2e  # E2E tests with Playwright
npm run test:coverage  # Coverage report
```

### Code Quality
```bash
# Python formatting and linting
black src/ tests/
isort src/ tests/
mypy src/

# Frontend linting and type checking
cd frontend
npm run lint
npm run typecheck
```

## Environment Configuration

Key environment variables are defined in `.env` (copy from `.env.example`):
- Database connections (PostgreSQL, Redis, Neo4j)
- Label Studio integration settings
- AI service API keys (Ollama, HuggingFace, Chinese LLMs)
- Security and encryption keys
- Deployment-specific settings (TCB, Docker)

## Deployment Modes

1. **Local Development**: Direct Python + Node.js execution
2. **Docker Compose**: Full containerized stack
3. **Tencent Cloud TCB**: Cloud-native deployment with `tcb framework deploy`