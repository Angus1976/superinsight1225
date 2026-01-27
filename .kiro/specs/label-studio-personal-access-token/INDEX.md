# Label Studio Personal Access Token Authentication - Spec Index

**Feature**: Label Studio Personal Access Token (PAT) Authentication  
**Status**: ✅ Complete and Production Ready  
**Version**: 1.0  
**Last Updated**: 2026-01-27

## Quick Navigation

| Document | Purpose | Key Content |
|----------|---------|-------------|
| [requirements.md](./requirements.md) | Feature requirements | User stories, acceptance criteria, constraints |
| [design.md](./design.md) | Technical design | Architecture, flow diagrams, component design |
| [tasks.md](./tasks.md) | Implementation tasks | Task breakdown, test results, deployment checklist |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | Executive summary | What was built, test results, deployment guide |

## Feature Overview

### What is Personal Access Token (PAT) Authentication?

Personal Access Token is Label Studio's primary authentication method for API access. Unlike username/password login:
- Token is generated in Label Studio's UI (Account & Settings → Personal Access Token)
- Token is a JWT refresh token that must be exchanged for access tokens
- Access tokens expire after ~5 minutes and are automatically refreshed
- Provides simpler, more secure API authentication

### Key Capabilities

✅ **Automatic Token Detection** - Detects JWT format and switches authentication method  
✅ **Token Refresh** - Exchanges refresh token for access tokens automatically  
✅ **Auto-Renewal** - Refreshes tokens 30 seconds before expiration  
✅ **Concurrent Safety** - Thread-safe token management with asyncio.Lock()  
✅ **Project Title Handling** - Automatically truncates titles to 50-character limit  
✅ **Error Handling** - Clear error messages and recovery strategies  
✅ **Backward Compatibility** - Legacy API tokens still work  

## Document Relationships

```
requirements.md (WHAT)
    ↓
    Defines 12 requirements covering:
    - Token detection
    - Token refresh
    - Auto-renewal
    - Bearer authentication
    - Concurrent safety
    - Title handling
    - Error handling
    - Backward compatibility
    - Configuration
    - Security
    - Integration
    - Logging

design.md (HOW)
    ↓
    Implements requirements through:
    - Architecture overview
    - Authentication flow diagrams
    - Component design
    - Data models
    - Error handling strategy
    - Concurrency model
    - Integration points
    - Security considerations
    - Performance characteristics
    - Correctness properties

tasks.md (EXECUTION)
    ↓
    Breaks down into 12 tasks:
    - Phase 1: Core Implementation (4 tasks)
    - Phase 2: Project Title Handling (3 tasks)
    - Phase 3: Configuration & Error Handling (2 tasks)
    - Phase 4: Testing & Validation (4 tasks)
    - Phase 5: Documentation & Deployment (2 tasks)
    
    Results:
    - 51/51 unit + integration tests passing
    - 600 property-based test iterations passing
    - 86% code coverage
    - 8/9 Docker integration tests passing

IMPLEMENTATION_SUMMARY.md (RESULTS)
    ↓
    Summarizes:
    - What was implemented
    - Test results
    - Code coverage
    - Files modified
    - Performance metrics
    - Security considerations
    - Deployment instructions
    - Troubleshooting guide
```

## Reading Guide

### For Project Managers
1. Start with [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Executive summary
2. Check "Success Metrics" section for test results
3. Review "Deployment Instructions" for go-live plan

### For Developers
1. Read [requirements.md](./requirements.md) - Understand what needs to be built
2. Study [design.md](./design.md) - Learn the architecture and design decisions
3. Review [tasks.md](./tasks.md) - See implementation breakdown and test results
4. Reference [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Deployment and troubleshooting

### For QA/Testers
1. Review [requirements.md](./requirements.md) - Acceptance criteria
2. Check [tasks.md](./tasks.md) - Test results and coverage
3. Reference [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Troubleshooting guide

### For DevOps/Operations
1. Read [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Deployment instructions
2. Review "Troubleshooting" section
3. Check "Performance Metrics" for monitoring

## Key Sections by Topic

### Authentication Flow
- [design.md - Authentication Flow Diagram](./design.md#authentication-flow-diagram)
- [IMPLEMENTATION_SUMMARY.md - Authentication Flow](./IMPLEMENTATION_SUMMARY.md#authentication-flow)

### Implementation Details
- [design.md - Component Design](./design.md#component-design)
- [tasks.md - Task Breakdown](./tasks.md#task-breakdown)

### Testing
- [tasks.md - Test Results](./tasks.md#test-results)
- [IMPLEMENTATION_SUMMARY.md - Test Results](./IMPLEMENTATION_SUMMARY.md#test-results)

### Deployment
- [IMPLEMENTATION_SUMMARY.md - Deployment Instructions](./IMPLEMENTATION_SUMMARY.md#deployment-instructions)
- [IMPLEMENTATION_SUMMARY.md - Troubleshooting](./IMPLEMENTATION_SUMMARY.md#troubleshooting)

### Security
- [design.md - Security Considerations](./design.md#security-considerations)
- [IMPLEMENTATION_SUMMARY.md - Security Considerations](./IMPLEMENTATION_SUMMARY.md#security-considerations)

## Requirements Traceability

### Requirement 1: Personal Access Token Detection
- **Design**: [design.md - Component Design](./design.md#1-labelstudiointegration-class)
- **Tasks**: [tasks.md - Task 1](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Unit Tests 8.1](./tasks.md#phase-4-testing-and-validation)

### Requirement 2: Token Refresh Mechanism
- **Design**: [design.md - Token Refresh Logic](./design.md#2-token-refresh-logic)
- **Tasks**: [tasks.md - Task 2](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Unit Tests 8.2](./tasks.md#phase-4-testing-and-validation)

### Requirement 3: Automatic Token Renewal
- **Design**: [design.md - Sequence Diagram: Token Refresh](./design.md#sequence-diagram-token-refresh)
- **Tasks**: [tasks.md - Task 3](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Unit Tests 8.3](./tasks.md#phase-4-testing-and-validation)

### Requirement 4: Bearer Token Authentication
- **Design**: [design.md - Component Design](./design.md#1-labelstudiointegration-class)
- **Tasks**: [tasks.md - Task 4](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Unit Tests 8.4](./tasks.md#phase-4-testing-and-validation)

### Requirement 5: Concurrent Request Handling
- **Design**: [design.md - Concurrency Model](./design.md#concurrency-model)
- **Tasks**: [tasks.md - Task 3.2](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Integration Tests 9.2](./tasks.md#phase-4-testing-and-validation)

### Requirement 6: Project Title Length Handling
- **Design**: [design.md - Project Title Truncation](./design.md#3-project-title-truncation)
- **Tasks**: [tasks.md - Task 5](./tasks.md#phase-2-project-title-handling)
- **Tests**: [tasks.md - Unit Tests 8.5](./tasks.md#phase-4-testing-and-validation)

### Requirement 7: Error Handling
- **Design**: [design.md - Error Handling](./design.md#error-handling)
- **Tasks**: [tasks.md - Task 7](./tasks.md#phase-3-configuration-and-error-handling)
- **Tests**: [tasks.md - Integration Tests 9.4](./tasks.md#phase-4-testing-and-validation)

### Requirement 8: Backward Compatibility
- **Design**: [design.md - Backward Compatibility](./design.md#backward-compatibility)
- **Tasks**: [tasks.md - Task 4.2](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Integration Tests 9.3](./tasks.md#phase-4-testing-and-validation)

### Requirement 9: Configuration Management
- **Design**: [design.md - Configuration](./design.md#configuration)
- **Tasks**: [tasks.md - Task 6](./tasks.md#phase-3-configuration-and-error-handling)
- **Tests**: [tasks.md - Unit Tests](./tasks.md#phase-4-testing-and-validation)

### Requirement 10: Security Best Practices
- **Design**: [design.md - Security Considerations](./design.md#security-considerations)
- **Tasks**: [tasks.md - Task 7.3](./tasks.md#phase-3-configuration-and-error-handling)
- **Tests**: [tasks.md - Property-Based Tests](./tasks.md#phase-4-testing-and-validation)

### Requirement 11: Integration with Existing Features
- **Design**: [design.md - Integration Points](./design.md#integration-points)
- **Tasks**: [tasks.md - Task 4.2](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Integration Tests 9.1](./tasks.md#phase-4-testing-and-validation)

### Requirement 12: Logging and Monitoring
- **Design**: [design.md - Component Design](./design.md#1-labelstudiointegration-class)
- **Tasks**: [tasks.md - Task 1.3, 3.3, 6.3, 7.3](./tasks.md#phase-1-core-implementation)
- **Tests**: [tasks.md - Unit Tests](./tasks.md#phase-4-testing-and-validation)

## Test Coverage Summary

| Category | Count | Status |
|----------|-------|--------|
| Unit Tests | 27 | ✅ 100% passing |
| Integration Tests | 12 | ✅ 100% passing |
| Property-Based Tests | 600 | ✅ 100% passing |
| Docker Integration Tests | 9 | ✅ 89% passing (8/9) |
| **Total** | **648** | **✅ 99.8% passing** |

## Code Files

### Core Implementation
- `src/label_studio/integration.py` - PAT detection, token refresh, Bearer auth
- `src/label_studio/config.py` - Configuration management
- `src/api/label_studio_sync.py` - Project title truncation
- `src/api/label_studio_api.py` - Project title truncation

### Configuration
- `.env` - Personal Access Token configuration
- `.env.example` - Example configuration

### Documentation
- `README.md` - Comprehensive authentication guide
- `LABEL_STUDIO_INTEGRATION_SUCCESS.md` - Success report

### Testing
- `tests/integration/test_label_studio_*.py` - Integration tests
- `docker-compose-integration-test.py` - End-to-end tests

## Related Specs

### Related Features
- [label-studio-jwt-authentication](../label-studio-jwt-authentication/) - JWT username/password authentication
- [label-studio-iframe-integration](../label-studio-iframe-integration/) - Iframe integration
- [label-studio-enterprise-workspace](../label-studio-enterprise-workspace/) - Enterprise features

### Related Steering Files
- [async-sync-safety.md](../../steering/async-sync-safety.md) - Async/sync safety rules
- [doc-first-workflow.md](../../steering/doc-first-workflow.md) - Documentation-first workflow
- [tech.md](../../steering/tech.md) - Technology stack

## Glossary

| Term | Definition |
|------|-----------|
| **PAT** | Personal Access Token - JWT refresh token from Label Studio UI |
| **JWT** | JSON Web Token - Token format with 3 parts separated by dots |
| **Refresh Token** | Long-lived token used to obtain access tokens |
| **Access Token** | Short-lived token (valid ~5 minutes) used for API authentication |
| **Bearer Token** | Authentication method using `Authorization: Bearer <token>` header |
| **Token Refresh** | Process of exchanging refresh token for new access token |
| **Auto-refresh** | Automatic token refresh before expiration |

## Quick Reference

### Token Detection
```python
def _is_jwt_token(token: str) -> bool:
    return len(token.split('.')) == 3
```

### Token Refresh
```python
POST /api/token/refresh
Body: {"refresh": "<personal-access-token>"}
Response: {"access": "<access-token>"}
```

### Bearer Authentication
```
Authorization: Bearer <access-token>
```

### Project Title Truncation
```
Format: {task_name[:N]}... ({task_id[:8]})
Max Length: 50 characters
Example: Integration Test Task (6b5805c9)
```

## Support and Maintenance

### For Issues
1. Check [IMPLEMENTATION_SUMMARY.md - Troubleshooting](./IMPLEMENTATION_SUMMARY.md#troubleshooting)
2. Review [design.md - Error Handling](./design.md#error-handling)
3. Check logs for authentication errors

### For Updates
1. Update requirements.md if requirements change
2. Update design.md if architecture changes
3. Update tasks.md with new tasks
4. Update IMPLEMENTATION_SUMMARY.md with results

### For Questions
- Refer to [requirements.md](./requirements.md) for "what"
- Refer to [design.md](./design.md) for "how"
- Refer to [tasks.md](./tasks.md) for "implementation"
- Refer to [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for "results"

---

**Last Updated**: 2026-01-27  
**Status**: ✅ Complete  
**Version**: 1.0  
**Maintainer**: SuperInsight Development Team

</content>
