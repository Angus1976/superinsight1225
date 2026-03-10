# Implementation Plan: Data Lifecycle Management System

## Overview

This implementation plan breaks down the Data Lifecycle Management System into discrete coding tasks. The system provides comprehensive data flow management from MD document parsing through structured conversion, review, sample library management, annotation tasks, enhancement processing, and AI trial calculations. The implementation follows an incremental approach, building core infrastructure first, then adding services layer by layer, and finally integrating frontend components with full internationalization support.

The backend uses Python FastAPI with PostgreSQL, while the frontend uses React + TypeScript with Ant Design components. All user-facing text is internationalized using react-i18next.

## Tasks

- [x] 1. Set up project infrastructure and database models
  - Create database schema with all tables (temp_data, samples, annotation_tasks, enhanced_data, versions, permissions, audit_logs)
  - Define SQLAlchemy models with validation rules
  - Create Alembic migration scripts
  - Set up database indexes on frequently queried fields (state, userId, createdAt)
  - Configure connection pooling
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 23.1, 23.5_

- [x] 2. Implement core state management system
  - [x] 2.1 Create DataState enum and state machine definition
    - Define all 13 states and valid transition rules
    - Implement state validation logic
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Implement State Manager service
    - Write getCurrentState, transitionState, validateTransition, getStateHistory methods
    - Implement state transition atomicity with database transactions
    - Add state change event emission
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 22.5_

  - [x] 2.3 Write property test for state transitions
    - **Property 2: State Transition Validity**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 2.4 Write property test for state history
    - **Property 3: State History Completeness**
    - **Validates: Requirements 2.3**


- [-] 3. Implement permission and access control system
  - [x] 3.1 Create Permission Manager service
    - Implement checkPermission, grantPermission, revokePermission methods
    - Add role-based access control (RBAC) support
    - Implement permission expiration handling
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 3.2 Create permission middleware for FastAPI
    - Implement request permission validation
    - Add 403 Forbidden error responses with required permissions
    - _Requirements: 9.1, 9.3, 24.1_

  - [x] 3.3 Write property test for permission enforcement
    - **Property 20: Permission Enforcement**
    - **Validates: Requirements 9.1, 9.3**

  - [x] 3.4 Write property test for permission expiration
    - **Property 22: Permission Expiration**
    - **Validates: Requirements 9.6**

- [ ] 4. Implement audit logging system
  - [x] 4.1 Create Audit Logger service
    - Implement logOperation, getAuditLog, getDataHistory, getUserActivity, exportAuditLog methods
    - Add CSV export functionality
    - Ensure audit log immutability
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 4.2 Create audit middleware for FastAPI
    - Automatically log all state-changing operations
    - Record timestamp, user, operation details, duration, and result
    - _Requirements: 3.6, 10.1, 10.2_

  - [x] 4.3 Write property test for audit logging completeness
    - **Property 6: Audit Logging Completeness**
    - **Validates: Requirements 3.6, 10.1, 10.2**

  - [x] 4.4 Write property test for audit log immutability
    - **Property 25: Audit Log Immutability**
    - **Validates: Requirements 10.6**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 6. Implement Structure Parser service
  - [x] 6.1 Create MD document parser
    - Implement parseDocument, validateStructure, extractMetadata methods
    - Parse MD format into structured sections
    - Extract metadata (title, author, tags)
    - Handle parsing errors gracefully
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 6.2 Create temporary data storage API endpoints
    - POST /api/documents/upload - Upload and parse MD document
    - GET /api/temp-data - List temporary data with pagination
    - GET /api/temp-data/{id} - Get specific temporary data
    - DELETE /api/temp-data/{id} - Delete temporary data
    - _Requirements: 1.3, 12.1, 12.2_

  - [ ] 6.3 Write property test for document parsing round-trip
    - **Property 1: Document Parsing Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ] 6.4 Write unit tests for parser error handling
    - Test invalid MD format handling
    - Test metadata extraction edge cases
    - _Requirements: 1.4_

- [ ] 7. Implement Review Service
  - [x] 7.1 Create Review Service with workflow methods
    - Implement submitForReview, assignReviewer, approveData, rejectData, getReviewStatus methods
    - Integrate with State Manager for state transitions
    - Integrate with Audit Logger for review action logging
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 7.2 Create review API endpoints
    - POST /api/reviews - Submit data for review
    - PUT /api/reviews/{id}/assign - Assign reviewer
    - POST /api/reviews/{id}/approve - Approve data
    - POST /api/reviews/{id}/reject - Reject data with reason
    - GET /api/reviews/{id} - Get review status
    - _Requirements: 3.1, 3.2, 3.3, 12.3, 12.4, 12.5_

  - [ ] 7.3 Write property test for review workflow integrity
    - **Property 5: Review Workflow Integrity**
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [ ] 7.4 Write property test for rejection reason requirement
    - **Property 27: Rejection Reason Requirement**
    - **Validates: Requirements 12.5**


- [ ] 8. Implement Sample Library Manager
  - [x] 8.1 Create Sample Library Manager service
    - Implement addSample, getSample, searchSamples, updateSample, deleteSample, getSamplesByTag methods
    - Add search and filtering logic with pagination
    - Track usage count and last used timestamp
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 8.2 Create sample library API endpoints
    - POST /api/samples - Add sample to library
    - GET /api/samples - Search samples with filters (tags, category, quality, date range)
    - GET /api/samples/{id} - Get specific sample
    - PUT /api/samples/{id} - Update sample
    - DELETE /api/samples/{id} - Delete sample
    - GET /api/samples/tags/{tag} - Get samples by tag
    - _Requirements: 4.1, 4.2, 4.3, 13.1, 13.2, 13.3_

  - [ ] 8.3 Write property test for sample library search correctness
    - **Property 7: Sample Library Search Correctness**
    - **Validates: Requirements 4.2, 4.3, 23.4**

  - [ ] 8.4 Write property test for sample usage tracking
    - **Property 8: Sample Usage Tracking**
    - **Validates: Requirements 4.4**

- [ ] 9. Implement Version Control Manager
  - [x] 9.1 Create Version Control Manager service
    - Implement createVersion, getVersion, getVersionHistory, compareVersions, rollbackToVersion, tagVersion methods
    - Calculate and store checksums for integrity verification
    - Implement version comparison diff logic
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 9.2 Integrate version control with data modifications
    - Auto-create versions on sample updates
    - Auto-create versions on annotation completion
    - Auto-create versions on enhancement completion
    - _Requirements: 4.6, 6.6, 8.1_

  - [ ] 9.3 Write property test for version creation on modification
    - **Property 9: Version Creation on Modification**
    - **Validates: Requirements 4.6, 6.6, 8.1**

  - [ ] 9.4 Write property test for version monotonicity
    - **Property 10: Version Monotonicity**
    - **Validates: Requirements 8.2, 20.6**

  - [ ] 9.5 Write property test for version checksum integrity
    - **Property 19: Version Checksum Integrity**
    - **Validates: Requirements 8.5**

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 11. Implement Annotation Task Service
  - [x] 11.1 Create Annotation Task Service
    - Implement createTask, assignAnnotator, getTask, submitAnnotation, getTaskProgress, completeTask methods
    - Add task progress tracking logic
    - Validate task completion (all samples annotated)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 11.2 Create annotation task API endpoints
    - POST /api/annotation-tasks - Create annotation task
    - PUT /api/annotation-tasks/{id}/assign - Assign annotator
    - GET /api/annotation-tasks/{id} - Get task details
    - POST /api/annotation-tasks/{id}/annotations - Submit annotation
    - GET /api/annotation-tasks/{id}/progress - Get task progress
    - POST /api/annotation-tasks/{id}/complete - Mark task complete
    - GET /api/annotation-tasks - List tasks with pagination
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 14.1, 14.2_

  - [ ] 11.3 Write property test for task progress consistency
    - **Property 11: Task Progress Consistency**
    - **Validates: Requirements 5.4**

  - [ ] 11.4 Write property test for task completion validation
    - **Property 12: Task Completion Validation**
    - **Validates: Requirements 5.6**

- [x] 12. Implement Enhancement Service
  - [x] 12.1 Create Enhancement Service
    - Implement createEnhancementJob, getJobStatus, applyEnhancement, validateEnhancement, rollbackEnhancement methods
    - Set up Celery for async job processing
    - Implement enhancement algorithms (data augmentation, quality improvement, noise reduction, feature extraction, normalization)
    - Add rollback support
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 12.2 Create enhancement API endpoints
    - POST /api/enhancements - Create enhancement job
    - GET /api/enhancements/{id} - Get job status
    - POST /api/enhancements/{id}/apply - Apply enhancement
    - POST /api/enhancements/{id}/rollback - Rollback enhancement
    - GET /api/enhancements - List enhancement jobs
    - POST /api/enhancements/{id}/cancel - Cancel running job
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 15.1, 15.3_

  - [ ] 12.3 Write property test for enhancement failure safety
    - **Property 13: Enhancement Failure Safety**
    - **Validates: Requirements 6.4**

  - [ ] 12.4 Write property test for enhancement rollback
    - **Property 14: Enhancement Rollback**
    - **Validates: Requirements 6.5**


- [x] 13. Implement AI Trial Service
  - [x] 13.1 Create AI Trial Service
    - Implement createTrial, executeTrial, getTrialResult, compareTrial, cancelTrial methods
    - Provide read-only data access at all lifecycle stages
    - Calculate performance metrics (accuracy, precision, recall, F1 score)
    - Ensure trial operations don't modify production data
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 13.2 Create AI trial API endpoints
    - POST /api/trials - Create trial
    - POST /api/trials/{id}/execute - Execute trial
    - GET /api/trials/{id}/results - Get trial results
    - POST /api/trials/compare - Compare multiple trials
    - POST /api/trials/{id}/cancel - Cancel trial
    - GET /api/trials - List trials
    - _Requirements: 7.2, 7.3, 7.6, 16.1, 16.2, 16.3, 16.4, 16.5_

  - [ ] 13.3 Write property test for AI trial data immutability
    - **Property 15: AI Trial Data Immutability**
    - **Validates: Requirements 7.1, 7.5**

  - [ ] 13.4 Write property test for trial result completeness
    - **Property 16: Trial Result Completeness**
    - **Validates: Requirements 7.6**

- [x] 14. Implement iterative optimization support
  - [x] 14.1 Add enhanced data to sample library functionality
    - Implement logic to add enhanced data back to sample library
    - Link new sample to original data for traceability
    - Preserve version history
    - Track iteration count
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_

  - [x] 14.2 Create API endpoint for iterative enhancement
    - POST /api/enhancements/{id}/add-to-library - Add enhanced data to sample library
    - _Requirements: 21.1_

  - [ ] 14.3 Write property test for iterative enhancement traceability
    - **Property 30: Iterative Enhancement Traceability**
    - **Validates: Requirements 21.2, 21.3, 21.4, 21.6**

- [x] 15. Implement concurrent operation handling
  - [x] 15.1 Add optimistic locking for concurrent modifications
    - Implement version conflict detection
    - Return 409 Conflict errors with conflicting version info
    - Add retry logic for conflict resolution
    - _Requirements: 22.1, 22.2, 22.3, 22.4_

  - [ ] 15.2 Write property test for concurrent modification detection
    - **Property 31: Concurrent Modification Detection**
    - **Validates: Requirements 22.1, 22.2, 22.3**

- [x] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 17. Implement security and data protection
  - [x] 17.1 Add security middleware and validation
    - Implement JWT-based authentication with token expiration
    - Add input validation and sanitization for all user inputs
    - Implement rate limiting on API endpoints
    - Add row-level security for data access control
    - Implement data encryption at rest for sensitive content
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6_

  - [ ] 17.2 Write property test for input sanitization
    - **Property 34: Input Sanitization**
    - **Validates: Requirements 24.3**

  - [ ] 17.3 Write property test for token expiration
    - **Property 36: Token Expiration**
    - **Validates: Requirements 24.5**

- [x] 18. Implement data validation and integrity checks
  - [x] 18.1 Add comprehensive data validation
    - Validate UUID format for all IDs
    - Validate foreign key references
    - Validate quality score ranges (0-1)
    - Validate version number monotonicity
    - Return descriptive error messages for validation failures
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6_

  - [ ] 18.2 Write property test for data validation
    - **Property 29: Data Validation**
    - **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**

- [x] 19. Implement error handling and recovery
  - [x] 19.1 Add comprehensive error handling
    - Return valid transition options for invalid state transitions
    - Return required permissions in permission denial errors
    - Return specific validation errors for data validation failures
    - Provide retry options for failed enhancement jobs
    - Log all errors with sufficient context
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6_

  - [ ] 19.2 Write property test for error message informativeness
    - **Property 37: Error Message Informativeness**
    - **Validates: Requirements 25.2, 25.6**

- [x] 20. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 21. Set up frontend project structure and i18n configuration
  - [x] 21.1 Create data lifecycle components directory structure
    - Create frontend/src/components/DataLifecycle/ directory
    - Create subdirectories: Visualization/, TempData/, Review/, SampleLibrary/, AnnotationTask/, Enhancement/, AITrial/, AuditLog/, StateTransition/
    - Create frontend/src/types/dataLifecycle.ts for TypeScript interfaces
    - Create frontend/src/hooks/useDataLifecycle.ts for custom hooks
    - _Requirements: 11.5, 19.1_

  - [x] 21.2 Configure react-i18next for data lifecycle namespace
    - Create translation namespace 'dataLifecycle' in frontend/src/locales/config.ts
    - Create frontend/src/locales/zh/dataLifecycle.json (Chinese translations)
    - Create frontend/src/locales/en/dataLifecycle.json (English translations)
    - Ensure both files have identical key structures
    - Add all translation keys from design document (visualization, tempData, review, sampleLibrary, tasks, enhancement, aiTrial, audit, stateTransition, states)
    - _Requirements: 19.1, 19.2, 19.3, 19.4_

  - [x] 21.3 Create data lifecycle page structure
    - Create frontend/src/pages/DataLifecycle/ directory
    - Create index page: frontend/src/pages/DataLifecycle/index.tsx (main dashboard)
    - Create sub-pages: TempData.tsx, SampleLibrary.tsx, AnnotationTasks.tsx, Enhancement.tsx, AITrial.tsx, AuditLog.tsx
    - _Requirements: 11.1, 12.1, 13.1, 14.1, 15.1, 16.1, 17.1_

  - [x] 21.4 Add data lifecycle routes to router configuration
    - Add /data-lifecycle route group in frontend/src/router/routes.tsx
    - Add child routes: /data-lifecycle/temp-data, /data-lifecycle/samples, /data-lifecycle/tasks, /data-lifecycle/enhancement, /data-lifecycle/trials, /data-lifecycle/audit
    - Use lazy loading with preload support for all routes
    - Use appropriate skeleton types for each route
    - _Requirements: 11.3_

  - [x] 21.5 Add data lifecycle navigation to sidebar
    - Add new nav group 'dataLifecycle' in frontend/src/config/navGroups.ts
    - Add menu items: Dashboard (overview), Temp Data, Sample Library, Annotation Tasks, Enhancement, AI Trial, Audit Log
    - Use appropriate icons for each menu item
    - Add translation keys to menu.dataLifecycle namespace
    - Position after 'dataManage' group and before 'aiCapability' group
    - _Requirements: 11.1_

  - [ ] 21.6 Write property test for internationalization completeness
    - **Property 26: Internationalization Completeness**
    - **Validates: Requirements 11.5, 19.2, 19.3, 19.4, 19.5, 19.6**

- [ ] 22. Implement API client and state management
  - [x] 22.1 Create TypeScript API client for data lifecycle
    - Create frontend/src/services/dataLifecycleApi.ts
    - Define API methods for all backend endpoints (temp data, samples, tasks, enhancement, trials, audit)
    - Add request/response type definitions matching backend schemas
    - Implement error handling and retry logic
    - Add authentication token management
    - Follow existing API client patterns from frontend/src/services/
    - _Requirements: 11.5_

  - [x] 22.2 Create Zustand store for data lifecycle state
    - Create frontend/src/stores/dataLifecycleStore.ts
    - Define state slices: tempData, samples, annotationTasks, enhancementJobs, trials, auditLogs, currentState
    - Implement actions: fetchTempData, approveTempData, rejectTempData, searchSamples, createTask, createEnhancement, createTrial, fetchAuditLogs
    - Add loading and error state handling
    - Follow existing store patterns from frontend/src/stores/
    - _Requirements: 11.4_

  - [x] 22.3 Create custom hooks for data lifecycle operations
    - Create frontend/src/hooks/useDataLifecycle.ts
    - Implement hooks: useTempData, useSampleLibrary, useAnnotationTasks, useEnhancement, useAITrial, useAuditLog, useStateTransition
    - Add data fetching, caching, and mutation logic
    - Integrate with Zustand store
    - _Requirements: 11.4_

- [ ] 23. Implement Data Lifecycle Dashboard (main overview page)
  - [x] 23.1 Create DataLifecycleDashboard page component
    - Create frontend/src/pages/DataLifecycle/index.tsx
    - Display data flow visualization showing all lifecycle stages
    - Show statistics cards: total data items, items by stage, recent activities
    - Add quick action buttons: Upload Document, View Temp Data, Browse Samples, Create Task
    - Integrate with existing Dashboard layout patterns
    - Use t() for all labels with 'dataLifecycle' namespace
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 11.1, 11.2, 11.5, 19.3_

  - [x] 23.2 Create DataFlowVisualization component
    - Create frontend/src/components/DataLifecycle/Visualization/DataFlowVisualization.tsx
    - Display visual representation of all 13 lifecycle stages using Mermaid or custom SVG
    - Show current data count at each stage (fetch from API)
    - Handle stage click navigation to detailed management pages
    - Add real-time updates using WebSocket or polling
    - Use t() for all stage labels
    - Add translation keys for all stages
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 19.3_

  - [ ] 23.3 Write unit tests for DataFlowVisualization
    - Test stage rendering with different data counts
    - Test click handlers and navigation
    - Test real-time updates
    - _Requirements: 11.4_


- [ ] 24. Implement Temporary Data Management page
  - [x] 24.1 Create TempData page component
    - Create frontend/src/pages/DataLifecycle/TempData.tsx
    - Display page header with title, breadcrumb, and action buttons (Upload Document)
    - Integrate TempDataTable component
    - Integrate ReviewModal component
    - Add filters: state (all, pending, under review, approved, rejected), uploader, date range
    - Use Ant Design PageHeader, Card, and layout components
    - Follow existing page patterns from frontend/src/pages/
    - _Requirements: 12.1, 12.6, 19.3_

  - [x] 24.2 Create TempDataTable component
    - Create frontend/src/components/DataLifecycle/TempData/TempDataTable.tsx
    - Display Ant Design Table with columns: ID, filename, uploader, upload time, state, actions
    - Add action buttons: View, Review, Delete (with permission checks)
    - Implement pagination with configurable page size
    - Add row selection for batch operations
    - Use t() for all column headers and action labels
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 12.1, 12.2, 12.6, 19.3_

  - [x] 24.3 Create ReviewModal component
    - Create frontend/src/components/DataLifecycle/Review/ReviewModal.tsx
    - Display Ant Design Modal with data preview (JSON viewer or structured display)
    - Add approval form with optional comments TextArea
    - Add rejection form with required reason TextArea (validation)
    - Add action buttons: Approve, Reject, Cancel
    - Integrate with StateTransitionVisualizer to show current state and next states
    - Use t() for all labels, placeholders, and button text
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 12.3, 12.4, 12.5, 18.1, 19.3_

  - [x] 24.4 Integrate with existing DataStructuring workflow
    - Add "Transfer to Lifecycle" button in DataStructuring/Results.tsx
    - When user clicks, transfer structured data to temporary table
    - Navigate to /data-lifecycle/temp-data after transfer
    - Show success notification with link to temp data page
    - _Requirements: 1.3, 12.1_

  - [ ] 24.5 Write unit tests for TempDataTable and ReviewModal
    - Test table rendering and pagination
    - Test action button handlers
    - Test modal form validation (rejection reason required)
    - Test approval/rejection flow
    - _Requirements: 12.1, 12.5_

- [ ] 25. Implement Sample Library Management page
  - [x] 25.1 Create SampleLibrary page component
    - Create frontend/src/pages/DataLifecycle/SampleLibrary.tsx
    - Display page header with title, breadcrumb, and action buttons (Create Task from Selected)
    - Integrate SampleLibrary component with search filters
    - Add statistics cards: total samples, samples by category, average quality score
    - Use Ant Design PageHeader, Card, and layout components
    - _Requirements: 13.1, 19.3_

  - [x] 25.2 Create SampleLibrary component
    - Create frontend/src/components/DataLifecycle/SampleLibrary/SampleLibrary.tsx
    - Display Ant Design Table with columns: ID, category, quality score, tags, created date, usage count, actions
    - Add SearchFilters component for tags, category, quality score range, date range
    - Implement multi-select with row selection
    - Add "Create Task" button (enabled when samples selected)
    - Add action buttons per row: View Details, Edit Tags, Delete
    - Implement pagination with configurable page size
    - Use t() for all labels and filter options
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 19.3_

  - [x] 25.3 Create SearchFilters component
    - Create frontend/src/components/DataLifecycle/SampleLibrary/SearchFilters.tsx
    - Add filter inputs: Tags (Select with multiple), Category (Select), Quality Score (Slider range), Date Range (DatePicker.RangePicker)
    - Add Search and Reset buttons
    - Implement filter state management
    - Use t() for all filter labels
    - _Requirements: 13.2_

  - [x] 25.4 Create SampleDetailDrawer component
    - Create frontend/src/components/DataLifecycle/SampleLibrary/SampleDetailDrawer.tsx
    - Display Ant Design Drawer with sample details: content preview, metadata, quality scores, version history, usage history
    - Add tabs: Overview, Content, Versions, Usage
    - Show StateTransitionVisualizer for current state
    - Add action buttons: Edit, Add to Task, Delete
    - Use t() for all labels
    - _Requirements: 4.1, 8.2, 18.1_

  - [ ] 25.5 Write unit tests for SampleLibrary
    - Test search and filtering
    - Test multi-select functionality
    - Test create task action
    - Test pagination
    - _Requirements: 13.2, 13.3_

- [ ] 26. Implement Annotation Task Management page
  - [x] 26.1 Create AnnotationTasks page component
    - Create frontend/src/pages/DataLifecycle/AnnotationTasks.tsx
    - Display page header with title, breadcrumb, and action buttons (Create New Task)
    - Integrate TaskManagement component
    - Add filters: status (all, created, in progress, completed, cancelled), assignee, deadline range
    - Show statistics cards: total tasks, tasks by status, completion rate
    - Use Ant Design PageHeader, Card, and layout components
    - _Requirements: 14.1, 19.3_

  - [x] 26.2 Create TaskManagement component
    - Create frontend/src/components/DataLifecycle/AnnotationTask/TaskManagement.tsx
    - Display Ant Design Table with columns: name, status, progress, assignees, deadline, actions
    - Add Progress component showing completed/total counts with percentage
    - Implement expandable rows showing task details (description, instructions, sample list)
    - Add action buttons per row: View Details, Edit, Assign, Cancel (with permission checks)
    - Use t() for all labels and status values
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 19.3_

  - [x] 26.3 Create CreateTaskModal component
    - Create frontend/src/components/DataLifecycle/AnnotationTask/CreateTaskModal.tsx
    - Display Ant Design Modal with multi-step form (Step 1: Basic Info, Step 2: Select Samples, Step 3: Assign Annotators)
    - Add form fields: name (required), description, annotation type (Select), instructions (TextArea), deadline (DatePicker), assignees (Select multiple)
    - Integrate with SampleLibrary for sample selection (show selected samples from parent)
    - Validate required fields and deadline (must be future date)
    - Use t() for all form labels, placeholders, and validation messages
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 14.2, 19.3_

  - [x] 26.4 Create TaskDetailDrawer component
    - Create frontend/src/components/DataLifecycle/AnnotationTask/TaskDetailDrawer.tsx
    - Display Ant Design Drawer with task details: basic info, progress, sample list, annotation results, assignee list
    - Add tabs: Overview, Samples, Annotations, Activity Log
    - Show progress visualization (pie chart or progress ring)
    - Add action buttons: Edit, Assign More, Complete Task, Cancel Task
    - Use t() for all labels
    - _Requirements: 5.3, 5.4, 14.3_

  - [x] 26.5 Integrate with existing Tasks module
    - Add "View in Lifecycle" link in existing Tasks pages (frontend/src/pages/Tasks/)
    - When user clicks, navigate to /data-lifecycle/tasks with task filter
    - Show notification explaining the relationship between Tasks and Annotation Tasks
    - _Requirements: 5.1, 14.1_

  - [ ] 26.6 Write unit tests for TaskManagement
    - Test task table rendering
    - Test progress calculation and display
    - Test expandable row functionality
    - Test create task flow
    - _Requirements: 14.3, 14.4_


- [ ] 27. Implement Enhancement Management page
  - [x] 27.1 Create Enhancement page component
    - Create frontend/src/pages/DataLifecycle/Enhancement.tsx
    - Display page header with title, breadcrumb, and action buttons (Create Enhancement Job)
    - Integrate EnhancementManagement component
    - Add filters: status (all, queued, running, completed, failed, cancelled), enhancement type, date range
    - Show statistics cards: total jobs, jobs by status, average quality improvement
    - Use Ant Design PageHeader, Card, and layout components
    - _Requirements: 15.1, 19.3_

  - [x] 27.2 Create EnhancementManagement component
    - Create frontend/src/components/DataLifecycle/Enhancement/EnhancementManagement.tsx
    - Display Ant Design Table with columns: ID, type, status, start time, completion time, quality improvement, actions
    - Use color-coded Tag components for job status (queued: blue, running: processing, completed: success, failed: error, cancelled: default)
    - Add action buttons per row: View Results, Cancel (only for running), Retry (only for failed), Delete
    - Add filter by status and type (Select dropdowns)
    - Use t() for all labels, status values, and enhancement types
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 19.3_

  - [x] 27.3 Create CreateEnhancementModal component
    - Create frontend/src/components/DataLifecycle/Enhancement/CreateEnhancementModal.tsx
    - Display Ant Design Modal with form for enhancement configuration
    - Add form fields: data source (Select from annotated data), enhancement type (Select: data augmentation, quality improvement, noise reduction, feature extraction, normalization), parameters (dynamic based on type), target quality score (Slider)
    - Add parameter configuration panels for each enhancement type
    - Validate required fields and parameter ranges
    - Use t() for all form labels and enhancement type options
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 6.1, 15.1, 19.3_

  - [x] 27.4 Create EnhancementResultDrawer component
    - Create frontend/src/components/DataLifecycle/Enhancement/EnhancementResultDrawer.tsx
    - Display Ant Design Drawer with enhancement results: before/after comparison, quality metrics, enhanced data preview
    - Add tabs: Overview, Metrics, Data Comparison, Parameters Used
    - Show quality improvement visualization (bar chart or radar chart)
    - Add action buttons: Add to Sample Library, Rollback, Download Results
    - Use t() for all labels
    - _Requirements: 6.3, 6.5, 21.1_

  - [x] 27.5 Integrate with Augmentation module
    - Add "View in Lifecycle" link in Augmentation pages (frontend/src/pages/Augmentation/)
    - When user clicks, navigate to /data-lifecycle/enhancement
    - Show notification explaining the relationship between Augmentation and Enhancement
    - _Requirements: 6.1, 15.1_

  - [ ] 27.6 Write unit tests for EnhancementManagement
    - Test job table rendering
    - Test status color coding
    - Test cancel action
    - Test filter functionality
    - _Requirements: 15.1, 15.2, 15.3_

- [ ] 28. Implement AI Trial Dashboard page
  - [x] 28.1 Create AITrial page component
    - Create frontend/src/pages/DataLifecycle/AITrial.tsx
    - Display page header with title, breadcrumb, and action buttons (Create New Trial, Compare Selected)
    - Integrate AITrialDashboard component
    - Add filters: status (all, created, running, completed, failed), data stage, AI model, date range
    - Show statistics cards: total trials, trials by status, average accuracy
    - Use Ant Design PageHeader, Card, and layout components
    - _Requirements: 16.1, 19.3_

  - [x] 28.2 Create AITrialDashboard component
    - Create frontend/src/components/DataLifecycle/AITrial/AITrialDashboard.tsx
    - Display Ant Design Table with columns: name, data stage, AI model, status, created date, accuracy, actions
    - Add multi-select with row selection for trial comparison
    - Add "Compare" button (enabled when 2+ trials selected)
    - Add action buttons per row: Execute (only for created), View Results (only for completed), Cancel (only for running), Delete
    - Use t() for all labels and data stage values
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 19.3_

  - [x] 28.3 Create CreateTrialModal component
    - Create frontend/src/components/DataLifecycle/AITrial/CreateTrialModal.tsx
    - Display Ant Design Modal with multi-step form (Step 1: Basic Config, Step 2: Data Source, Step 3: Model & Parameters)
    - Add form fields: name (required), data stage (Select: temp table, sample library, data source, annotated, enhanced), AI model (Select), parameters (JSON editor or dynamic form), sample size (InputNumber)
    - Add data source selector with filters based on selected stage
    - Validate required fields and parameter format
    - Use t() for all form labels and data stage options
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 16.1, 16.2, 19.3_

  - [x] 28.4 Create TrialResultDrawer component
    - Create frontend/src/components/DataLifecycle/AITrial/TrialResultDrawer.tsx
    - Display Ant Design Drawer with trial results: metrics (accuracy, precision, recall, F1 score), predictions preview, execution time, data quality score
    - Add tabs: Overview, Metrics, Predictions, Data Quality
    - Show metrics visualization (radar chart or bar chart)
    - Add action buttons: Download Results, Create New Trial with Same Config, Compare with Others
    - Use t() for all labels
    - _Requirements: 7.6, 16.4, 16.6_

  - [x] 28.5 Create TrialComparisonModal component
    - Create frontend/src/components/DataLifecycle/AITrial/TrialComparisonModal.tsx
    - Display Ant Design Modal with side-by-side comparison of selected trials
    - Show comparison table: trial name, data stage, AI model, accuracy, precision, recall, F1 score, execution time
    - Add metrics comparison chart (line chart or bar chart)
    - Highlight best performing trial for each metric
    - Use t() for all labels
    - _Requirements: 7.4, 16.5_

  - [x] 28.6 Integrate with AI Assistant module
    - Add "Run Trial" action in AI Assistant pages (frontend/src/pages/AIAssistant/)
    - When user clicks, open CreateTrialModal with pre-filled AI model
    - Navigate to /data-lifecycle/trials after trial creation
    - _Requirements: 7.2, 16.1_

  - [ ] 28.7 Write unit tests for AITrialDashboard
    - Test trial table rendering
    - Test multi-select for comparison
    - Test execute and view results actions
    - Test comparison modal
    - _Requirements: 16.3, 16.4, 16.5_

- [ ] 29. Implement Audit Log Viewer page
  - [x] 29.1 Create AuditLog page component
    - Create frontend/src/pages/DataLifecycle/AuditLog.tsx
    - Display page header with title, breadcrumb, and action buttons (Export Logs, Refresh)
    - Integrate AuditLogViewer component
    - Add advanced filters panel (collapsible)
    - Show statistics cards: total operations, operations by type, operations by result
    - Use Ant Design PageHeader, Card, and layout components
    - _Requirements: 17.1, 19.3_

  - [x] 29.2 Create AuditLogViewer component
    - Create frontend/src/components/DataLifecycle/AuditLog/AuditLogViewer.tsx
    - Display Ant Design Table with columns: timestamp, user ID, operation type, resource type, action, result, duration (ms)
    - Add filters: user ID (Input with autocomplete), resource type (Select), operation type (Select), date range (DatePicker.RangePicker), result (Select: success, failure, partial)
    - Implement expandable rows showing detailed operation information (JSON viewer)
    - Add export to CSV button with current filters applied
    - Implement pagination with configurable page size
    - Use t() for all labels and filter options
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 19.3_

  - [x] 29.3 Create AuditLogDetailDrawer component
    - Create frontend/src/components/DataLifecycle/AuditLog/AuditLogDetailDrawer.tsx
    - Display Ant Design Drawer with full audit log details: operation info, user info, resource info, request/response data, error details (if any)
    - Add tabs: Overview, Request Data, Response Data, Error Details
    - Show operation timeline if multiple related operations exist
    - Add action buttons: View Related Logs, Export This Log
    - Use t() for all labels
    - _Requirements: 10.1, 10.2, 17.3_

  - [x] 29.4 Integrate with Security Audit module
    - Add "View in Lifecycle Audit" link in Security/Audit pages (frontend/src/pages/Security/Audit.tsx)
    - When user clicks, navigate to /data-lifecycle/audit with pre-filled filters
    - Show notification explaining the relationship between Security Audit and Lifecycle Audit
    - _Requirements: 10.1, 17.1_

  - [ ] 29.5 Write unit tests for AuditLogViewer
    - Test log table rendering
    - Test filtering functionality
    - Test export action
    - Test expandable row with JSON viewer
    - _Requirements: 17.2, 17.3, 17.4_


- [ ] 30. Implement State Transition Visualizer component
  - [x] 30.1 Create StateTransitionVisualizer component
    - Create frontend/src/components/DataLifecycle/StateTransition/StateTransitionVisualizer.tsx
    - Display current state with visual indicator (Tag with color coding)
    - Show available next states as actionable Button components
    - Display state history as Ant Design Timeline component
    - Disable buttons for invalid transitions (based on state machine rules)
    - Add confirmation modal for critical transitions (e.g., delete, archive)
    - Use t() for all state names and labels
    - Add translation keys to zh/dataLifecycle.json and en/dataLifecycle.json
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 19.3_

  - [x] 30.2 Create StateHistoryTimeline component
    - Create frontend/src/components/DataLifecycle/StateTransition/StateHistoryTimeline.tsx
    - Display Ant Design Timeline with state history entries
    - Show state name, timestamp, user who triggered transition, reason (if any)
    - Add color coding for different state types (pending: blue, approved: green, rejected: red, etc.)
    - Implement collapsible timeline for long histories
    - Use t() for all labels
    - _Requirements: 2.3, 18.4_

  - [x] 30.3 Integrate StateTransitionVisualizer into detail views
    - Add StateTransitionVisualizer to TempDataTable row expansion
    - Add StateTransitionVisualizer to SampleDetailDrawer
    - Add StateTransitionVisualizer to TaskDetailDrawer
    - Add StateTransitionVisualizer to EnhancementResultDrawer
    - Ensure consistent styling and behavior across all integrations
    - _Requirements: 18.1, 18.2_

  - [ ] 30.4 Write property test for state transition button validity
    - **Property 28: State Transition Button Validity**
    - **Validates: Requirements 18.2, 18.6**

  - [ ] 30.5 Write unit tests for StateTransitionVisualizer
    - Test current state display
    - Test button enable/disable logic based on valid transitions
    - Test timeline rendering
    - Test transition confirmation modal
    - _Requirements: 18.1, 18.2, 18.4_

- [ ] 31. Implement routing and navigation
  - [x] 31.1 Set up React Router configuration for data lifecycle
    - Add data lifecycle routes in frontend/src/router/routes.tsx
    - Create route group: /data-lifecycle with child routes (index, temp-data, samples, tasks, enhancement, trials, audit)
    - Use lazy loading with preload support for all routes
    - Use appropriate skeleton types: dashboard (index), table (temp-data, samples, tasks, enhancement, trials, audit)
    - Add route guards for admin-only pages (if any)
    - _Requirements: 11.3, 19.3_

  - [x] 31.2 Add data lifecycle navigation to sidebar
    - Update frontend/src/config/navGroups.ts
    - Add new nav group 'dataLifecycle' with titleKey 'navGroup.dataLifecycle'
    - Add menu items: Dashboard, Temp Data, Sample Library, Annotation Tasks, Enhancement, AI Trial, Audit Log
    - Use appropriate icons: DashboardOutlined (dashboard), InboxOutlined (temp data), DatabaseOutlined (samples), CheckSquareOutlined (tasks), ThunderboltOutlined (enhancement), ExperimentOutlined (trials), AuditOutlined (audit)
    - Position after 'dataManage' group and before 'aiCapability' group
    - Add translation keys to menu.dataLifecycle namespace in zh and en JSON files
    - _Requirements: 11.1, 19.3_

  - [x] 31.3 Add breadcrumb navigation
    - Update breadcrumb configuration in MainLayout
    - Add breadcrumb items for all data lifecycle pages
    - Use t() for all breadcrumb labels
    - Add translation keys to breadcrumb namespace
    - _Requirements: 11.3_

  - [x] 31.4 Add quick navigation shortcuts
    - Add "Go to Data Lifecycle" shortcut in Dashboard page
    - Add "View in Lifecycle" links in related modules (DataStructuring, Tasks, Augmentation, Security/Audit)
    - Add navigation hints in empty states (e.g., "No temp data yet. Upload a document to get started.")
    - Use t() for all navigation labels
    - _Requirements: 11.3_

  - [ ] 31.5 Write integration tests for routing
    - Test navigation between data lifecycle pages
    - Test route guards (if any)
    - Test breadcrumb updates
    - Test lazy loading and preloading
    - _Requirements: 11.3_

- [x] 32. Checkpoint - Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 33. Implement end-to-end integration tests
  - [ ] 33.1 Write integration test for MD upload to sample library workflow
    - Test: Upload MD document → Parse → Store in temp table → Review → Approve → Transfer to sample library
    - Verify state transitions at each step
    - Verify audit logs are created
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3, 3.1, 3.2, 4.1, 10.1_

  - [ ] 33.2 Write integration test for annotation workflow
    - Test: Select samples → Create annotation task → Assign annotator → Submit annotations → Complete task
    - Verify task progress updates
    - Verify version creation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 8.1_

  - [ ] 33.3 Write integration test for enhancement and iteration workflow
    - Test: Annotated data → Create enhancement job → Apply enhancement → Add to sample library → Create new task
    - Verify enhanced data quality improvement
    - Verify iteration count tracking
    - _Requirements: 6.1, 6.2, 6.3, 21.1, 21.2, 21.3, 21.4, 21.6_

  - [ ] 33.4 Write integration test for AI trial workflow
    - Test: Create trial → Select data stage → Execute trial → View results → Compare trials
    - Verify data immutability after trial
    - Verify trial metrics completeness
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ] 33.5 Write integration test for permission enforcement
    - Test: User without permissions attempts operations → Verify 403 errors
    - Test: Grant permissions → Verify operations succeed
    - Test: Permission expiration → Verify expired permissions are not honored
    - _Requirements: 9.1, 9.3, 9.4, 9.5, 9.6_

- [ ] 34. Performance optimization and caching
  - [ ] 34.1 Implement caching layer
    - Add Redis caching for sample library searches
    - Add Redis caching for permission checks
    - Implement cache invalidation on data updates
    - _Requirements: 23.2_

  - [ ] 34.2 Add database query optimization
    - Verify indexes are created on frequently queried fields
    - Optimize complex queries with joins
    - Add query performance logging for slow queries (>2 seconds)
    - _Requirements: 23.1, 23.6_

  - [ ] 34.3 Write performance tests
    - Test sample library search with large datasets
    - Test pagination performance
    - Test concurrent request handling
    - _Requirements: 23.1, 23.4_


- [ ] 35. Create deployment configuration and documentation
  - [x] 35.1 Create database migration scripts
    - Write Alembic migration for initial schema
    - Write migration for indexes
    - Add migration rollback scripts
    - Document migration process
    - _Requirements: 20.1, 23.1_

  - [x] 35.2 Create environment configuration
    - Create .env.example with all required variables
    - Document environment variables (database URL, Redis URL, JWT secret, etc.)
    - Add configuration validation on startup
    - _Requirements: 24.1_

  - [x] 35.3 Create Docker configuration
    - Write Dockerfile for backend service
    - Write Dockerfile for frontend service
    - Create docker-compose.yml with all services (backend, frontend, PostgreSQL, Redis, Celery)
    - Document Docker deployment process
    - _Requirements: 23.3, 23.5_

  - [x] 35.4 Write API documentation
    - Document all API endpoints with request/response examples
    - Add authentication requirements for each endpoint
    - Document error codes and responses
    - Generate OpenAPI/Swagger documentation
    - _Requirements: 9.1, 25.1, 25.2, 25.3_

  - [x] 35.5 Write user manual
    - Document data lifecycle workflow
    - Document each management interface with screenshots
    - Add troubleshooting guide
    - Document permission requirements for each operation
    - _Requirements: 11.1, 12.1, 13.1, 14.1, 15.1, 16.1, 17.1, 18.1_

- [ ] 36. Final integration and system testing
  - [ ] 36.1 Run full system test suite
    - Execute all unit tests (target 80% coverage)
    - Execute all property-based tests
    - Execute all integration tests
    - Verify all tests pass
    - _Requirements: All requirements_

  - [ ] 36.2 Perform manual testing of UI workflows
    - Test complete data lifecycle from upload to enhancement
    - Test all state transitions
    - Test permission enforcement in UI
    - Test internationalization (switch between Chinese and English)
    - Verify no hardcoded strings in UI
    - _Requirements: 11.5, 19.1, 19.3, 19.5, 19.6_

  - [ ] 36.3 Verify security requirements
    - Test authentication and authorization
    - Test input sanitization
    - Test rate limiting
    - Test data encryption at rest
    - Review audit logs for completeness
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6_

- [-] 37. Final checkpoint - System ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Backend uses Python FastAPI with PostgreSQL and Celery for async processing
- Frontend uses React + TypeScript with Ant Design and react-i18next
- All user-facing text must use t() function with 'dataLifecycle' namespace
- Translation files must maintain identical key structures in zh and en

