# Docker Infrastructure - Tasks

## Task Breakdown

### Phase 1: Fix PostgreSQL Initialization (Critical)

- [ ] 1. Fix PostgreSQL Init Script SQL Syntax (Est: 0.5h)
  - [ ] 1.1 Update DO block to use $$ delimiters instead of $ (Est: 0.1h)
    - **File**: `scripts/init-db.sql`
    - **Change**: Replace `DO $` with `DO $$` and `END $;` with `END $$;`
    - **Validates**: Requirements 1.1, 1.7
  - [ ] 1.2 Verify script syntax with PostgreSQL parser (Est: 0.1h)
    - **Command**: `psql -f scripts/init-db.sql --dry-run` (if available)
    - **Validates**: Requirements 1.1
  - [ ] 1.3 Test script idempotency (Est: 0.2h)
    - **Action**: Run script twice, verify no errors
    - **Validates**: Property 1 (Idempotency)
  - [ ] 1.4 Document the fix in CHANGELOG.md (Est: 0.1h)
    - **Section**: [Unreleased] > Fixed
    - **Validates**: Documentation-first workflow

### Phase 2: Container Cleanup and Rebuild (Critical)

- [ ] 2. Clean Old Docker Resources (Est: 0.5h)
  - [ ] 2.1 Stop all running containers (Est: 0.1h)
    - **Command**: `docker-compose down`
    - **Validates**: Requirements 2.1
  - [ ] 2.2 Remove old containers (Est: 0.1h)
    - **Command**: `docker container prune -f`
    - **Validates**: Clean state
  - [ ] 2.3 Remove old images (Est: 0.2h)
    - **Command**: `docker image prune -a -f`
    - **Validates**: No cached problematic images
  - [ ] 2.4 Verify volumes are preserved (Est: 0.1h)
    - **Command**: `docker volume ls`
    - **Validates**: Requirements 4.1-4.4

- [ ] 3. Rebuild and Start Containers (Est: 1h)
  - [ ] 3.1 Rebuild API container (Est: 0.3h)
    - **Command**: `docker-compose build --no-cache superinsight-api`
    - **Validates**: Fresh build
  - [ ] 3.2 Start all services (Est: 0.3h)
    - **Command**: `docker-compose up -d`
    - **Validates**: Requirements 2.1-2.5
  - [ ] 3.3 Monitor container startup logs (Est: 0.2h)
    - **Command**: `docker-compose logs -f`
    - **Validates**: No startup errors
  - [ ] 3.4 Wait for all health checks to pass (Est: 0.2h)
    - **Command**: `docker-compose ps`
    - **Validates**: Requirements 5.1-5.5

### Phase 3: Verification and Testing (High Priority)

- [ ] 4. Verify PostgreSQL Initialization (Est: 0.5h)
  - [ ] 4.1 Check PostgreSQL container logs (Est: 0.1h)
    - **Command**: `docker-compose logs postgres`
    - **Validates**: No SQL syntax errors
  - [ ] 4.2 Verify superinsight role exists (Est: 0.1h)
    - **Command**: `docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\du"`
    - **Validates**: Requirements 1.2
  - [ ] 4.3 Verify extensions are enabled (Est: 0.1h)
    - **Command**: `docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\dx"`
    - **Validates**: Requirements 1.4
  - [ ] 4.4 Verify permissions are granted (Est: 0.1h)
    - **Command**: Test CREATE TABLE operation
    - **Validates**: Requirements 3.1-3.5
  - [ ] 4.5 Verify alembic_version table exists (Est: 0.1h)
    - **Command**: `docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\dt alembic_version"`
    - **Validates**: Requirements 1.5

- [ ] 5. Verify Service Health Checks (Est: 0.5h)
  - [ ] 5.1 Check PostgreSQL health (Est: 0.1h)
    - **Command**: `docker exec superinsight-postgres pg_isready -U superinsight -d superinsight`
    - **Validates**: Requirements 5.1
  - [ ] 5.2 Check Redis health (Est: 0.1h)
    - **Command**: `docker exec superinsight-redis redis-cli ping`
    - **Validates**: Requirements 5.2
  - [ ] 5.3 Check Neo4j health (Est: 0.1h)
    - **Command**: `curl http://localhost:7474`
    - **Validates**: Requirements 5.3
  - [ ] 5.4 Check Label Studio health (Est: 0.1h)
    - **Command**: `curl http://localhost:8080/health`
    - **Validates**: Requirements 5.4
  - [ ] 5.5 Check API health (Est: 0.1h)
    - **Command**: `curl http://localhost:8000/health`
    - **Validates**: Overall system health

- [ ] 6. Verify Service Connectivity (Est: 0.5h)
  - [ ] 6.1 Test API to PostgreSQL connection (Est: 0.1h)
    - **Command**: `curl http://localhost:8000/system/status`
    - **Validates**: Requirements 6.1
  - [ ] 6.2 Test API to Redis connection (Est: 0.1h)
    - **Validates**: Cache operations work
  - [ ] 6.3 Test API to Neo4j connection (Est: 0.1h)
    - **Validates**: Graph database operations work
  - [ ] 6.4 Test API to Label Studio connection (Est: 0.1h)
    - **Validates**: Annotation service integration works
  - [ ] 6.5 Generate comprehensive connectivity report (Est: 0.1h)
    - **Output**: Connection status for all services
    - **Validates**: Property 3 (Database Connectivity)

### Phase 4: Documentation and Logging (Medium Priority)

- [ ] 7. Generate Test Logs (Est: 0.5h)
  - [ ] 7.1 Collect all container logs (Est: 0.2h)
    - **Command**: `docker-compose logs > docker-startup-test.log`
    - **Validates**: Troubleshooting capability
  - [ ] 7.2 Generate health check report (Est: 0.1h)
    - **Format**: JSON with all service statuses
    - **Validates**: Monitoring capability
  - [ ] 7.3 Document startup time metrics (Est: 0.1h)
    - **Metrics**: Time to healthy for each service
    - **Validates**: Performance requirements
  - [ ] 7.4 Create troubleshooting guide (Est: 0.1h)
    - **Content**: Common issues and solutions
    - **Validates**: Maintainability

- [ ] 8. Update Documentation (Est: 0.5h)
  - [ ] 8.1 Update CHANGELOG.md (Est: 0.1h)
    - **Section**: [Unreleased] > Fixed
    - **Entry**: "Fixed PostgreSQL init script SQL syntax error"
  - [ ] 8.2 Update README.md if needed (Est: 0.1h)
    - **Section**: Docker setup instructions
  - [ ] 8.3 Update deployment documentation (Est: 0.2h)
    - **File**: `docs/deployment/docker-setup.md`
  - [ ] 8.4 Commit all documentation changes (Est: 0.1h)
    - **Validates**: Documentation-first workflow compliance

## Progress Tracking

- **Total Tasks**: 8 main tasks, 32 subtasks
- **Completed**: 0
- **In Progress**: 0
- **Blocked**: 0
- **Estimated Total Time**: 4.5 hours

## Dependencies

- Task 2 depends on Task 1 (fix must be applied before rebuild)
- Task 3 depends on Task 2 (cleanup before rebuild)
- Task 4 depends on Task 3 (services must be running)
- Task 5 depends on Task 3 (services must be running)
- Task 6 depends on Tasks 4 and 5 (health checks must pass)
- Task 7 can run in parallel with Task 6
- Task 8 depends on all previous tasks (documentation after verification)

## Critical Path

1. Fix SQL syntax (Task 1.1) - **BLOCKING**
2. Clean Docker resources (Task 2) - **BLOCKING**
3. Rebuild containers (Task 3) - **BLOCKING**
4. Verify initialization (Task 4) - **CRITICAL**
5. Verify health checks (Task 5) - **CRITICAL**
6. Verify connectivity (Task 6) - **CRITICAL**

## Success Criteria

- [ ] PostgreSQL container starts without errors
- [ ] All containers pass health checks
- [ ] API can connect to all services
- [ ] No SQL syntax errors in logs
- [ ] All services respond to health check endpoints
- [ ] Comprehensive test logs generated
- [ ] Documentation updated and committed
