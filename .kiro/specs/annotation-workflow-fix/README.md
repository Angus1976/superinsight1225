# Annotation Workflow Fix - Specification

## Overview

This specification addresses critical issues in the SuperInsight annotation workflow where users encounter errors when trying to start annotation or open Label Studio in a new window.

## Problem Statement

### Current Issues

1. **"开始标注" Button Error**: Clicking the "Start Annotation" button shows an error message instead of navigating to the annotation page
2. **"在新窗口打开" 404 Error**: Opening Label Studio in a new window results in a 404 error
3. **Missing Project Auto-Creation**: Label Studio projects are not created automatically, causing workflow failures

### Root Causes

- Label Studio projects are not created when tasks are created
- No validation of project existence before navigation
- No automatic project creation fallback
- Authentication issues when opening new windows
- Missing task import to Label Studio

## Solution Overview

### Key Features

1. **Automatic Project Creation**: Projects are created automatically when users start annotation
2. **Project Validation**: System validates project existence before navigation
3. **Authenticated URLs**: Generate secure URLs for opening Label Studio in new windows
4. **Task Import**: Automatically import tasks from SuperInsight to Label Studio
5. **Error Recovery**: Comprehensive error handling with automatic recovery
6. **Language Synchronization**: Seamless Chinese/English language sync between SuperInsight and Label Studio
7. **Smooth Navigation**: Progressive loading with visual feedback for better UX
8. **No Source Code Modification**: Uses Label Studio's official APIs and configuration only

### Architecture

```
Frontend (React)
├── Task Detail Page
│   ├── Project Validation
│   ├── Start Annotation Handler
│   └── Open New Window Handler
└── Annotation Page
    ├── Project Validation
    ├── Auto Project Creation
    └── Task Import

Backend (FastAPI)
├── Project Manager Service
│   ├── ensure_project_exists()
│   ├── import_task_data()
│   └── generate_authenticated_url()
└── API Endpoints
    ├── POST /api/label-studio/projects/ensure
    ├── GET /api/label-studio/projects/{id}/validate
    ├── POST /api/label-studio/projects/{id}/import-tasks
    └── GET /api/label-studio/projects/{id}/auth-url

Label Studio
└── Projects, Tasks, Annotations
```

## Implementation Plan

### Phase 1: Backend Infrastructure (16h)
- Create Project Manager Service
- Enhance API Endpoints
- Update Database Schema
- Implement Error Handling

### Phase 2: Frontend Implementation (12h)
- Enhance Task Detail Page
- Enhance Annotation Page
- Create API Client Functions
- Update Translations

### Phase 3: Testing (10h)
- Backend Unit Tests
- Frontend Unit Tests
- Integration Tests

### Phase 4: Property-Based Testing (6h)
- Project Creation Idempotency
- Annotation Sync Consistency
- Task Progress Accuracy

### Phase 5: Documentation and Deployment (4h)
- Update Documentation
- Deploy Changes
- Verify Production

**Total Estimated Time**: 54 hours (increased from 48h to include language sync and smooth navigation)

## Key Technical Decisions

### 1. Automatic Project Creation
- **Decision**: Create projects automatically when users start annotation
- **Rationale**: Improves UX, prevents errors, reduces support burden
- **Implementation**: Lazy creation on first annotation attempt

### 2. Project Validation
- **Decision**: Validate project existence before navigation
- **Rationale**: Prevents broken pages, enables recovery
- **Implementation**: Frontend validation hook with caching

### 3. Authenticated URLs
- **Decision**: Generate temporary authenticated URLs for new windows
- **Rationale**: Avoids CORS, maintains security, seamless UX
- **Implementation**: Temporary tokens with 1-hour expiration

### 4. Error Handling
- **Decision**: Multi-level error handling with automatic recovery
- **Rationale**: Improves reliability, reduces user frustration
- **Implementation**: Retry logic, fallbacks, clear error messages

### 5. Language Synchronization
- **Decision**: Use Label Studio's native i18n without source code modification
- **Rationale**: Compatible with upgrades, uses official features, instant switching
- **Implementation**: URL parameters (?lang=zh), environment variables, language mapping

### 6. Smooth Navigation
- **Decision**: Progressive loading with visual feedback
- **Rationale**: Improves perceived performance, reduces user anxiety
- **Implementation**: Loading modal with progress steps, clear status messages

## Success Metrics

### Functional
- ✅ "开始标注" button works without errors
- ✅ "在新窗口打开" opens Label Studio successfully
- ✅ Projects created automatically
- ✅ Tasks imported to Label Studio
- ✅ Annotations synced back

### Performance
- Project creation: < 3 seconds
- Task import (100 tasks): < 5 seconds
- Annotation page load: < 2 seconds
- Annotation sync: < 1 second
- Page transition: < 2 seconds
- Language switching: < 500ms

### User Experience
- No "project not found" errors
- No 404 errors
- Clear loading indicators with progress
- Helpful error messages
- Smooth workflow
- Consistent language (Chinese/English)
- Default Chinese for Chinese users
- Instant language switching

## Files Structure

```
.kiro/specs/annotation-workflow-fix/
├── README.md              # This file - overview and summary
├── requirements.md        # Detailed requirements and user stories
├── design.md             # Technical design and architecture
├── tasks.md              # Implementation tasks breakdown
├── ISSUE_ANALYSIS.md     # Issue analysis with Chinese/English
└── LANGUAGE_SYNC.md      # Language synchronization guide (NEW)
```

## Getting Started

### For Developers

1. **Read Requirements**: Start with `requirements.md` to understand user needs
2. **Review Design**: Read `design.md` for technical architecture
3. **Check Tasks**: Review `tasks.md` for implementation plan
4. **Start Implementation**: Begin with Phase 1 backend tasks

### For Project Managers

1. **Review Requirements**: Understand scope and acceptance criteria
2. **Check Timeline**: Review 48-hour estimate in `tasks.md`
3. **Monitor Progress**: Track task completion in `tasks.md`
4. **Verify Success**: Check success metrics after deployment

### For QA Engineers

1. **Review Requirements**: Understand acceptance criteria
2. **Check Test Plan**: Review testing strategy in `tasks.md`
3. **Prepare Test Cases**: Create test cases based on requirements
4. **Execute Tests**: Run unit, integration, and property-based tests

## Dependencies

### Backend
- Label Studio service (v1.7+)
- PostgreSQL database
- Redis for caching
- FastAPI framework

### Frontend
- React 19
- Ant Design 5
- TanStack Query
- React Router DOM 7

### External Services
- Label Studio API
- Label Studio authentication

## Risks and Mitigations

### High Risk
1. **Label Studio Unavailable**
   - Mitigation: Health checks, clear error messages, fallback options

2. **Project Creation Failure**
   - Mitigation: Retry logic, error logging, manual creation option

3. **Data Sync Failure**
   - Mitigation: Idempotent operations, retry queue, manual sync

### Medium Risk
1. **Authentication Issues**
   - Mitigation: Token validation, refresh mechanism, re-login option

2. **Performance Degradation**
   - Mitigation: Caching, lazy loading, batch operations

## Next Steps

1. **Review Specification**: Team reviews requirements and design
2. **Approve Plan**: Stakeholders approve implementation plan
3. **Start Development**: Begin Phase 1 backend implementation
4. **Iterative Testing**: Test each phase before moving to next
5. **Deploy**: Gradual rollout with monitoring

## Questions?

For questions or clarifications:
- Requirements: See `requirements.md` Section 10 (Glossary)
- Design: See `design.md` Section 4 (Technical Decisions)
- Tasks: See `tasks.md` Dependencies and Risk Mitigation sections

## Related Documents

- [Language Synchronization Guide](./LANGUAGE_SYNC.md) - **NEW** - Detailed guide for i18n
- [Issue Analysis](./ISSUE_ANALYSIS.md) - Problem analysis with solutions
- [Label Studio Integration Design](../../../docs/label_studio_enterprise_extension_design.md)
- [Label Studio API Documentation](../../../docs/label_studio_enterprise_extension.md)
- [Task Management API](../../../src/api/tasks.py)
- [Label Studio Integration](../../../src/label_studio/integration.py)
