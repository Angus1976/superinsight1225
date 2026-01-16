# Docker Infrastructure - Design Document

## 1. Architecture Overview

```mermaid
graph TD
    A[Docker Compose] --> B[PostgreSQL]
    A --> C[Redis]
    A --> D[Neo4j]
    A --> E[Label Studio]
    A --> F[SuperInsight API]
    
    B -->|Health Check| E
    B -->|Health Check| F
    C -->|Health Check| F
    D -->|Health Check| F
    E -->|Health Check| F
    
    B -->|Init Script| G[init-db.sql]
    G -->|Creates| H[superinsight role]
    G -->|Enables| I[Extensions]
    G -->|Creates| J[alembic_version]
```

## 2. Component Design

### 2.1 PostgreSQL Initialization Script

**Responsibility**: Initialize PostgreSQL database with required roles, permissions, and extensions on first startup.

**File**: `scripts/init-db.sql`

**Technical Decisions**:
- Use PL/pgSQL DO blocks for conditional role creation
- Use `$$` delimiters for proper SQL syntax (not `$` alone)
- Make script idempotent using IF NOT EXISTS checks
- Enable extensions before creating tables
- Set up default privileges for future objects

**SQL Structure**:
```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create role with proper DO block syntax
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'superinsight') THEN
        CREATE ROLE superinsight WITH LOGIN PASSWORD 'password';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE superinsight TO superinsight;
GRANT ALL ON SCHEMA public TO superinsight;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO superinsight;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO superinsight;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO superinsight;
```

**Error Handling**:
- IF NOT EXISTS prevents duplicate role errors
- Idempotent operations allow safe re-execution
- Proper syntax prevents PostgreSQL parser errors

### 2.2 Docker Compose Configuration

**Responsibility**: Orchestrate multi-container application with proper dependencies and health checks.

**File**: `docker-compose.yml`

**Service Dependency Chain**:
```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant PG as PostgreSQL
    participant RD as Redis
    participant N4J as Neo4j
    participant LS as Label Studio
    participant API as SuperInsight API
    
    DC->>PG: Start PostgreSQL
    DC->>RD: Start Redis
    DC->>N4J: Start Neo4j
    
    PG->>PG: Run init-db.sql
    PG->>PG: Health check (pg_isready)
    
    PG-->>DC: Healthy
    RD-->>DC: Healthy
    N4J-->>DC: Healthy
    
    DC->>LS: Start Label Studio (depends on PG)
    LS->>LS: Health check (/health)
    LS-->>DC: Healthy
    
    DC->>API: Start API (depends on all)
    API->>API: Connect to services
    API-->>DC: Ready
```

**Health Check Configuration**:

| Service | Health Check Command | Interval | Timeout | Retries |
|---------|---------------------|----------|---------|---------|
| PostgreSQL | `pg_isready -U superinsight -d superinsight` | 10s | 5s | 5 |
| Redis | `redis-cli ping` | 10s | 5s | 5 |
| Neo4j | `wget -q --spider http://localhost:7474` | 10s | 5s | 5 |
| Label Studio | `curl -f http://localhost:8080/health` | 30s | 10s | 5 |

**Volume Mapping**:
- `postgres_data:/var/lib/postgresql/data` - Database persistence
- `./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql` - Init script injection
- Named volumes for all services to ensure data persistence

### 2.3 Service Dependencies

**Responsibility**: Ensure services start in correct order with proper health checks.

**Dependency Configuration**:
```yaml
depends_on:
  postgres:
    condition: service_healthy
  redis:
    condition: service_healthy
  neo4j:
    condition: service_healthy
  label-studio:
    condition: service_healthy
```

**Rationale**: Using `condition: service_healthy` ensures dependent services only start after dependencies pass health checks, preventing connection errors during startup.

### 2.4 Environment Variables

**Responsibility**: Configure service connections and authentication.

**Configuration Pattern**:
```yaml
environment:
  DATABASE_URL: postgresql://superinsight:password@postgres:5432/superinsight
  REDIS_URL: redis://redis:6379/0
  NEO4J_URI: bolt://neo4j:7687
  LABEL_STUDIO_URL: http://label-studio:8080
```

**Design Decisions**:
- Use container names as hostnames (Docker DNS resolution)
- Externalize credentials via environment variables
- Use consistent URL format across services
- Support override via .env file

## 3. Technical Decisions

### Decision 1: PL/pgSQL DO Block Syntax

**Problem**: PostgreSQL DO blocks require proper delimiter syntax for anonymous code blocks.

**Decision**: Use `$$` delimiters instead of single `$` for DO blocks.

**Rationale**:
- `$$` is the standard PostgreSQL delimiter for dollar-quoted strings
- Single `$` causes syntax errors in the parser
- `$$` allows proper nesting of quotes within the block
- Consistent with PostgreSQL best practices

**Alternatives Considered**:
- Single quotes: Rejected due to escaping complexity
- No conditional logic: Rejected as it would cause errors on re-initialization

### Decision 2: Health Check Strategy

**Problem**: Services need to wait for dependencies before starting.

**Decision**: Use Docker Compose health checks with `condition: service_healthy`.

**Rationale**:
- Prevents connection errors during startup
- Provides clear service status visibility
- Supports automatic retry logic
- Compatible with Kubernetes readiness probes

**Alternatives Considered**:
- Manual wait scripts: Rejected as less reliable
- No health checks: Rejected due to race conditions

### Decision 3: Init Script Location

**Problem**: PostgreSQL needs initialization on first startup.

**Decision**: Mount init script to `/docker-entrypoint-initdb.d/`.

**Rationale**:
- Standard PostgreSQL Docker image convention
- Automatic execution on first startup only
- No manual intervention required
- Supports multiple init scripts if needed

**Alternatives Considered**:
- Manual SQL execution: Rejected as not automated
- Alembic migrations only: Rejected as permissions needed before migrations

## 4. Sequence Diagrams

### Container Startup Sequence

```mermaid
sequenceDiagram
    participant User
    participant Docker
    participant PG as PostgreSQL
    participant Init as init-db.sql
    participant API as SuperInsight API
    
    User->>Docker: docker-compose up
    Docker->>PG: Start container
    
    PG->>Init: Execute /docker-entrypoint-initdb.d/init-db.sql
    Init->>Init: CREATE EXTENSION uuid-ossp
    Init->>Init: CREATE EXTENSION btree_gin
    Init->>Init: DO $$ ... END $$ (Create role)
    Init->>Init: GRANT permissions
    Init->>Init: ALTER DEFAULT PRIVILEGES
    Init-->>PG: Initialization complete
    
    PG->>PG: pg_isready check
    PG-->>Docker: Health check passed
    
    Docker->>API: Start container (dependencies met)
    API->>PG: Connect to database
    PG-->>API: Connection successful
    API-->>User: System ready
```

### Error Recovery Sequence

```mermaid
sequenceDiagram
    participant Docker
    participant PG as PostgreSQL
    participant Init as init-db.sql
    
    Docker->>PG: Start container
    PG->>Init: Execute init script
    
    alt Syntax Error (single $)
        Init-->>PG: ERROR: syntax error at or near "$"
        PG-->>Docker: Container failed
        Docker-->>Docker: Retry (up to 5 times)
        Note over Docker: Container never becomes healthy
    else Correct Syntax ($$)
        Init->>Init: Successfully execute DO block
        Init-->>PG: Initialization complete
        PG-->>Docker: Health check passed
        Note over Docker: Container healthy
    end
```

## 5. Data Models

### PostgreSQL Role Configuration

```sql
-- Role attributes
rolname: 'superinsight'
rolsuper: false
rolinherit: true
rolcreaterole: false
rolcreatedb: false
rolcanlogin: true
rolreplication: false
rolconnlimit: -1
rolpassword: 'SCRAM-SHA-256$...' (hashed)

-- Privileges
database: ALL PRIVILEGES on 'superinsight'
schema: ALL on 'public'
tables: ALL (via DEFAULT PRIVILEGES)
sequences: ALL (via DEFAULT PRIVILEGES)
functions: ALL (via DEFAULT PRIVILEGES)
```

### Docker Volume Structure

```
postgres_data/
├── base/           # Database files
├── global/         # Cluster-wide tables
├── pg_wal/         # Write-ahead logs
└── pg_stat/        # Statistics

redis_data/
└── dump.rdb        # Redis persistence file

neo4j_data/
├── databases/      # Graph databases
└── transactions/   # Transaction logs

label_studio_data/
├── media/          # Uploaded files
└── export/         # Export files
```

## 6. Correctness Properties

### Property 1: Init Script Idempotency
**Specification**: Running init-db.sql multiple times SHALL produce the same result as running it once.

**Validation**: 
- IF role exists, THEN skip creation
- IF extension exists, THEN skip creation
- Permissions can be granted multiple times safely

### Property 2: Service Startup Order
**Specification**: Dependent services SHALL NOT start before their dependencies are healthy.

**Validation**:
- PostgreSQL health check MUST pass before Label Studio starts
- All service health checks MUST pass before API starts
- Failed health checks MUST prevent dependent service startup

### Property 3: Database Connectivity
**Specification**: After initialization, the superinsight role SHALL be able to connect and perform all operations.

**Validation**:
- Connection with superinsight credentials MUST succeed
- CREATE TABLE operations MUST succeed
- INSERT/UPDATE/DELETE operations MUST succeed
- SELECT operations MUST succeed

### Property 4: Volume Persistence
**Specification**: Data SHALL persist across container restarts.

**Validation**:
- Stop and remove containers
- Restart containers
- Data MUST still be present
- No data loss MUST occur

## 7. Performance Considerations

### Startup Time Optimization
- Use Alpine-based images for smaller size
- Parallel service startup where possible
- Efficient health check intervals
- Minimal init script operations

### Resource Allocation
- PostgreSQL: 512MB-1GB RAM
- Redis: 256MB RAM
- Neo4j: 1GB RAM (configurable)
- Label Studio: 512MB RAM
- API: 512MB RAM

### Network Performance
- Use bridge network for inter-container communication
- Avoid unnecessary port exposure
- Use container names for DNS resolution

## 8. Security Considerations

### Credential Management
- Use environment variables for passwords
- Support .env file for local development
- Use secrets management in production
- Rotate credentials regularly

### Network Isolation
- Use dedicated Docker network
- Expose only necessary ports
- Use internal communication where possible
- Implement firewall rules in production

### Volume Security
- Set appropriate file permissions
- Use encrypted volumes in production
- Regular backup of persistent data
- Implement access controls

## References

- [PostgreSQL Docker Documentation](https://hub.docker.com/_/postgres)
- [Docker Compose Health Checks](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [PostgreSQL PL/pgSQL Documentation](https://www.postgresql.org/docs/current/plpgsql.html)
- [Docker Networking](https://docs.docker.com/network/)
