# Project Structure & Organization

## Root Directory Layout

```
superinsight-platform/
├── src/                          # Main source code
├── frontend/                     # React frontend application
├── tests/                        # Backend test suites
├── alembic/                      # Database migration scripts
├── scripts/                      # Utility and deployment scripts
├── docs/                         # Documentation
├── .kiro/                        # Kiro IDE configuration and specs
├── data/                         # Persistent data volumes
├── deploy/                       # Deployment configurations
├── config/                       # Configuration templates
└── docker-compose*.yml          # Container orchestration
```

## Backend Source Structure (`src/`)

### Core System Components
- `src/app.py` - Main FastAPI application with middleware and routing
- `src/config/` - Application settings and configuration management
- `src/database/` - Database connections, models, and utilities
- `src/system/` - System integration, monitoring, health checks, logging

### Feature Modules (Domain-Driven Design)
- `src/api/` - FastAPI routers and endpoint definitions
- `src/models/` - SQLAlchemy database models
- `src/schemas/` - Pydantic request/response schemas
- `src/extractors/` - Data extraction from various sources
- `src/label_studio/` - Label Studio integration and management
- `src/ai/` - AI model integration and annotation services
- `src/quality/` - Quality assessment and management
- `src/billing/` - Billing, analytics, and reporting
- `src/security/` - Authentication, authorization, audit, compliance
- `src/i18n/` - Internationalization and localization

### Specialized Services
- `src/knowledge_graph/` - Neo4j integration and graph operations
- `src/sync/` - Data synchronization and real-time updates
- `src/monitoring/` - System monitoring and alerting
- `src/desensitization/` - Data privacy and PII protection
- `src/multi_tenant/` - Multi-tenancy support
- `src/export/` - Data export in various formats

## Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── components/               # Reusable UI components
│   ├── pages/                    # Page-level components
│   ├── hooks/                    # Custom React hooks
│   ├── stores/                   # Zustand state management
│   ├── services/                 # API client functions
│   ├── utils/                    # Utility functions
│   └── types/                    # TypeScript type definitions
├── public/                       # Static assets
├── e2e/                         # Playwright E2E tests
└── package.json                 # Dependencies and scripts
```

## Configuration & Deployment

### Environment Configuration
- `.env.example` - Template for environment variables
- `config/` - YAML configuration templates for various services
- `deploy/` - Deployment-specific configurations (TCB, hybrid, private)

### Database Management
- `alembic/` - Database migration scripts and version control
- `alembic.ini` - Alembic configuration
- Database initialization scripts in `scripts/`

### Container Orchestration
- `docker-compose.yml` - Main development stack
- `docker-compose.fullstack.yml` - Complete production-like setup
- `docker-compose.local.yml` - Local development overrides
- `Dockerfile.backend`, `Dockerfile.dev` - Container definitions

## Key Architectural Patterns

### API Organization
- RESTful endpoints organized by domain (`/api/v1/{domain}`)
- Consistent error handling and response formats
- Automatic API documentation via FastAPI/OpenAPI

### Database Design
- Multi-tenant architecture with tenant isolation
- Audit logging for all critical operations
- JSONB fields for flexible schema evolution
- Graph database (Neo4j) for knowledge relationships

### Security Architecture
- Role-based access control (RBAC) with fine-grained permissions
- Automatic data desensitization middleware
- Comprehensive audit trails with integrity protection
- Real-time security monitoring and alerting

### Quality & Monitoring
- Ragas-based semantic quality assessment
- Prometheus metrics collection
- Health checks at multiple levels (service, database, external APIs)
- Business metrics tracking (annotation efficiency, user activity)

## Development Conventions

### File Naming
- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Test files: `test_*.py` or `*.test.tsx`

### Module Organization
- Each domain module should have: `models.py`, `schemas.py`, `service.py`, `api.py`
- Shared utilities in `src/utils/`
- Database models in `src/models/`
- API schemas in `src/schemas/`

### Import Conventions
- Absolute imports from `src/` root
- Group imports: standard library, third-party, local modules
- Use `from src.module import specific_item` pattern