# Annotation Workflow Fix - Requirements

## 1. User Stories

### 1.1 Start Annotation from Task Detail
**As a** data annotator  
**I want** to click "开始标注" button and immediately start annotating tasks  
**So that** I can efficiently complete my annotation work without errors

**Priority**: P0 (Critical)  
**Acceptance Criteria** (EARS):
- WHEN user clicks "开始标注" button on task detail page, THEN system navigates to annotation page without errors
- WHEN annotation page loads, THEN Label Studio project and tasks are successfully fetched
- WHEN Label Studio project exists, THEN user sees the annotation interface with the first unannotated task
- IF Label Studio project does not exist, THEN system creates project automatically and imports tasks
- WHERE user has annotation permissions, THEN annotation interface is fully functional

### 1.2 Open Annotation in New Window
**As a** data annotator  
**I want** to click "在新窗口打开" button and open Label Studio in a new window  
**So that** I can use Label Studio's native interface for annotation

**Priority**: P0 (Critical)  
**Acceptance Criteria** (EARS):
- WHEN user clicks "在新窗口打开" button, THEN system opens Label Studio project in new browser tab
- WHEN new window opens, THEN Label Studio project page loads successfully (no 404 error)
- WHEN Label Studio loads, THEN user is automatically authenticated
- WHERE Label Studio project does not exist, THEN system creates it before opening window
- IF authentication fails, THEN system shows clear error message with retry option
- WHEN Label Studio opens, THEN interface language matches user's current language preference
- WHERE user has selected Chinese in SuperInsight, THEN Label Studio displays in Chinese
- WHERE user has selected English in SuperInsight, THEN Label Studio displays in English

### 1.3 Automatic Project Creation
**As a** system administrator  
**I want** the system to automatically create Label Studio projects when needed  
**So that** users don't encounter "project not found" errors

**Priority**: P0 (Critical)  
**Acceptance Criteria** (EARS):
- WHEN task is created with annotation requirement, THEN system creates corresponding Label Studio project
- WHEN user attempts to annotate task without project, THEN system creates project automatically
- WHEN project is created, THEN system imports all task data into Label Studio
- IF project creation fails, THEN system shows clear error message and logs failure
- WHERE project already exists, THEN system reuses existing project

### 1.4 Task Data Synchronization
**As a** data annotator  
**I want** task data to be automatically synchronized between SuperInsight and Label Studio  
**So that** I always see the latest annotation progress

**Priority**: P1 (High)  
**Acceptance Criteria** (EARS):
- WHEN annotation is created in Label Studio, THEN system syncs it back to SuperInsight database
- WHEN annotation is updated, THEN system updates SuperInsight task progress
- WHEN all tasks are completed, THEN system updates task status to "completed"
- IF sync fails, THEN system retries with exponential backoff
- WHERE sync is in progress, THEN user sees loading indicator

### 1.5 Seamless Language Synchronization
**As a** data annotator  
**I want** Label Studio to display in my preferred language automatically  
**So that** I have a consistent experience across the platform

**Priority**: P0 (Critical)  
**Acceptance Criteria** (EARS):
- WHEN user's language preference is Chinese, THEN Label Studio displays in Chinese by default
- WHEN user's language preference is English, THEN Label Studio displays in English
- WHEN user switches language in SuperInsight, THEN Label Studio language updates automatically on next access
- WHERE Label Studio is embedded in iframe, THEN language preference is passed via URL parameter
- WHERE Label Studio opens in new window, THEN language preference is included in authenticated URL
- IF Label Studio language pack is missing, THEN system falls back to English with warning log

### 1.6 Smooth Navigation Experience
**As a** data annotator  
**I want** instant and smooth transitions when starting annotation  
**So that** I can work efficiently without delays

**Priority**: P0 (Critical)  
**Acceptance Criteria** (EARS):
- WHEN user clicks "开始标注", THEN page transition completes within 2 seconds
- WHEN annotation page loads, THEN loading indicator shows progress
- WHEN project is being created, THEN user sees clear status message
- WHERE network is slow, THEN system shows estimated time remaining
- IF operation takes > 5 seconds, THEN system shows detailed progress steps

### 1.7 Error Handling and Recovery
**As a** data annotator  
**I want** clear error messages when annotation fails  
**So that** I know what went wrong and how to fix it

**Priority**: P1 (High)  
**Acceptance Criteria** (EARS):
- WHEN Label Studio is unavailable, THEN system shows "服务暂时不可用" message
- WHEN project not found, THEN system attempts to create project automatically
- WHEN authentication fails, THEN system shows login prompt
- IF network error occurs, THEN system shows retry button
- WHERE error is recoverable, THEN system provides clear recovery steps

## 2. Non-Functional Requirements

### 2.1 Performance
- Label Studio project creation: < 3 seconds
- Task import (100 tasks): < 5 seconds
- Annotation page load: < 2 seconds
- Annotation sync: < 1 second
- Page transition (开始标注): < 2 seconds
- Language switching: < 500ms

### 2.2 Reliability
- Project creation success rate: > 99%
- Task import success rate: > 99.5%
- Annotation sync success rate: > 99.9%
- System uptime: > 99.5%
- Language synchronization accuracy: 100%

### 2.3 Usability
- Error messages in user's language (Chinese/English)
- Clear loading indicators during async operations
- Automatic retry for transient failures
- Graceful degradation when Label Studio unavailable
- Smooth page transitions with progress feedback
- Consistent language across SuperInsight and Label Studio

### 2.4 Internationalization
- Support Chinese (Simplified) and English
- Default language: Chinese
- Language preference persisted in user profile
- Label Studio language synchronized with user preference
- All UI text properly translated
- Date/time formats localized

### 2.5 Integration Constraints
- No modifications to Label Studio source code
- Use Label Studio's official API and configuration
- Compatible with Label Studio v1.7+ and future versions
- Language configuration via Label Studio's native i18n system
- Authentication via Label Studio's token mechanism

### 2.6 Security
- Authentication token validation before Label Studio access
- Permission checks for annotation operations
- Audit logging for all annotation activities
- Secure token transmission to Label Studio

## 3. Dependencies

### 3.1 Backend Dependencies
- Label Studio service must be running and accessible
- PostgreSQL database for task storage
- Redis for caching and session management
- FastAPI for API endpoints

### 3.2 Frontend Dependencies
- React Router for navigation
- Ant Design for UI components
- TanStack Query for data fetching
- i18n for translations

### 3.3 External Services
- Label Studio API (v1.7+)
- Label Studio authentication service
- Label Studio webhook service

## 4. Current Issues Analysis

### 4.1 Issue 1: "开始标注" Button Error
**Symptom**: Clicking "开始标注" shows error message  
**Root Cause**: 
- Label Studio project not created when task is created
- API endpoint `/api/label-studio/projects/{id}` returns 404
- Frontend assumes project exists without validation

**Impact**: Users cannot start annotation workflow

### 4.2 Issue 2: "在新窗口打开" 404 Error
**Symptom**: New window shows 404 error  
**Root Cause**:
- URL `/label-studio/projects/{id}` not properly proxied
- Label Studio project ID mismatch
- Authentication token not passed to new window

**Impact**: Users cannot use Label Studio native interface

### 4.3 Issue 3: Missing Project Auto-Creation
**Symptom**: Projects not created automatically  
**Root Cause**:
- No automatic project creation in task creation workflow
- No fallback project creation when annotation starts
- No validation of project existence before navigation

**Impact**: Broken annotation workflow, poor user experience

## 5. Success Metrics

### 5.1 User Experience Metrics
- Annotation workflow completion rate: > 95%
- Average time to start annotation: < 5 seconds
- User error rate: < 1%
- User satisfaction score: > 4.5/5

### 5.2 Technical Metrics
- API response time (p95): < 500ms
- Project creation success rate: > 99%
- Task sync success rate: > 99.9%
- Error recovery rate: > 95%

### 5.3 Business Metrics
- Annotation throughput increase: > 30%
- Support ticket reduction: > 50%
- User onboarding time reduction: > 40%

## 6. Out of Scope

The following are explicitly out of scope for this fix:
- Label Studio UI customization
- Advanced annotation features (e.g., multi-label, NER)
- Annotation quality assessment
- Collaborative annotation features
- Annotation export formats beyond JSON
- Label Studio version upgrade
- Custom annotation templates

## 7. Assumptions

- Label Studio service is deployed and accessible
- Label Studio API token is configured correctly
- PostgreSQL database is available
- Users have appropriate permissions
- Network connectivity is stable
- Browser supports modern JavaScript features

## 8. Constraints

### 8.1 Technical Constraints
- Must maintain backward compatibility with existing tasks
- Must not break existing annotation data
- Must work with Label Studio v1.7+
- Must work in Chrome, Firefox, Safari, Edge
- Must handle concurrent users (up to 100)

### 8.2 Integration Constraints
- **MUST NOT modify Label Studio source code** - Use only official APIs and configuration
- **MUST use Label Studio's native i18n system** - No custom language injection
- **MUST be compatible with future Label Studio upgrades** - Avoid version-specific hacks
- **MUST use Label Studio's official authentication** - No custom auth mechanisms
- **MUST respect Label Studio's API rate limits** - Implement proper throttling

### 8.3 Language Constraints
- Must support Chinese (Simplified) and English
- Default language must be Chinese
- Language switching must be instant (< 500ms)
- Label Studio language must sync with SuperInsight language
- All error messages must be localized

## 9. Risks and Mitigations

### 9.1 Risk: Label Studio Service Unavailable
**Probability**: Medium  
**Impact**: High  
**Mitigation**: 
- Implement health check before operations
- Show clear error message to users
- Provide fallback to manual project creation
- Monitor Label Studio service health

### 9.2 Risk: Project Creation Failure
**Probability**: Low  
**Impact**: High  
**Mitigation**:
- Implement retry logic with exponential backoff
- Log all failures for debugging
- Provide manual project creation option
- Alert administrators on repeated failures

### 9.3 Risk: Data Sync Failure
**Probability**: Medium  
**Impact**: Medium  
**Mitigation**:
- Implement idempotent sync operations
- Use transaction for database updates
- Implement sync retry queue
- Provide manual sync trigger

### 9.4 Risk: Authentication Issues
**Probability**: Low  
**Impact**: High  
**Mitigation**:
- Validate token before operations
- Implement token refresh mechanism
- Show clear authentication error messages
- Provide re-login option

## 10. Glossary

- **Label Studio**: Open-source data labeling tool
- **Annotation**: The process of adding labels/tags to data
- **Task**: A unit of work to be annotated
- **Project**: A collection of tasks in Label Studio
- **Sync**: Synchronization of data between systems
- **Pre-annotation**: AI-generated initial annotations
