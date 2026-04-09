# Implementation Plan: Comprehensive E2E Testing

## Overview

**计划状态（2026-04）：** 下文任务 **1–24 及全部子任务均已勾选 `[x]`**，本文档内 **无剩余未完成条目**。后续仅随需求变更再开新项。

Incrementally extend the existing SuperInsight E2E test infrastructure (35+ Playwright specs, `fixtures.ts`, `test-helpers.ts`) to achieve comprehensive coverage across all 16 requirement areas. New test files follow the `frontend/e2e/` convention, new helpers go in `frontend/e2e/helpers/`, and property-based tests use fast-check with Vitest in `frontend/src/__tests__/`. The implementation builds on existing patterns (localStorage auth, route interception, Ant Design selectors) without rewriting any existing tests.

## Tasks

- [x] 1. Set up test infrastructure helpers and shared modules
  - [x] 1.1 Create `frontend/e2e/helpers/role-permissions.ts` with `RoleConfig` interface and `ROLE_CONFIGS` map for admin, data_manager, data_analyst, annotator roles including `accessibleRoutes`, `deniedRoutes`, and `permissions` arrays
    - Export `ROLE_CONFIGS`, `RoleConfig` type, and `getRouteAccessMatrix()` helper
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 1.2 Create `frontend/e2e/helpers/mock-api-factory.ts` with typed mock response generators for all major API endpoints
    - Implement `mockTasksApi()`, `mockBillingApi()`, `mockDashboardApi()`, `mockDataSyncApi()`, `mockQualityApi()`, `mockAdminApi()`, `mockAIApi()`, `mockAllApis()` functions using `page.route()` interception
    - Each function returns schema-valid JSON matching the backend response format from `frontend/src/constants/api.ts`
    - Support `MockOptions` parameter for count, status, tenantId, delay
    - _Requirements: 16.2, 2.1, 2.2_

  - [x] 1.3 Create `frontend/e2e/helpers/form-interaction.ts` with generic Ant Design form interaction utilities
    - Implement `fillAntForm()`, `submitAntForm()`, `verifyFormValidation()`, `fillAndSubmitModal()`, `verifyTablePagination()`, `verifyTableSort()`, `verifyDropdownSelect()` functions
    - Handle Ant Design-specific selectors (`.ant-form-item`, `.ant-select`, `.ant-modal`, `.ant-table`)
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.7, 2.8, 2.9_

  - [x] 1.4 Extend `frontend/e2e/fixtures.ts` with role-parameterized `rolePage` fixture
    - Add `RoleTestFixtures` interface with `rolePage: Page` and `roleConfig: RoleConfig`
    - Create parameterized fixture that calls `setupAuth()` with the role from `ROLE_CONFIGS`
    - Export extended `test` object with new fixtures alongside existing ones
    - _Requirements: 16.1, 1.1, 1.2, 1.3, 1.4_

- [x] 2. Checkpoint - Verify infrastructure helpers
  - Ensure all helper modules compile without errors, ask the user if questions arise.

- [x] 3. Implement role-based workflow E2E tests
  - [x] 3.1 Create `frontend/e2e/role-workflows/admin-workflow.spec.ts`
    - Test admin can access all Page_Modules (Dashboard, Tasks, Quality, Security, Admin, DataSync, Augmentation, License, DataLifecycle, Billing, Settings, AI Integration)
    - Test admin can perform CRUD operations on tasks, users, and tenants
    - Test admin full Data_Lifecycle flow (acquisition → annotation → quality → export)
    - Use `mockAllApis()` and `rolePage` fixture with admin role
    - _Requirements: 1.1, 1.5_

  - [x] 3.2 Create `frontend/e2e/role-workflows/data-manager-workflow.spec.ts`
    - Test data_manager can access DataSync, DataLifecycle, Augmentation, Tasks, Dashboard
    - Test data_manager is denied access to Admin, Security RBAC, Billing Management (redirect to 403/Dashboard)
    - Test data_manager Data_Lifecycle flow within permitted scope
    - _Requirements: 1.2, 1.5, 1.6_

  - [x] 3.3 Create `frontend/e2e/role-workflows/data-analyst-workflow.spec.ts`
    - Test data_analyst can access Dashboard, Quality Reports, Billing Overview, License Usage
    - Test data_analyst is denied access to Admin, DataSync configuration, Task assignment
    - _Requirements: 1.3, 1.6_

  - [x] 3.4 Create `frontend/e2e/role-workflows/annotator-workflow.spec.ts`
    - Test annotator can access assigned Tasks and Task Annotation pages
    - Test annotator is denied access to Admin, Quality Rules, Security, DataSync, Billing
    - Test annotator annotation submission flow
    - _Requirements: 1.4, 1.5, 1.6_

  - [x] 3.5 Write property test for role-route access matrix
    - **Property 1: Role-Route Access Matrix**
    - Create `frontend/src/__tests__/role-permissions.property.test.ts` using fast-check
    - For any role × route combination, verify the access expectation matches `ROLE_CONFIGS`
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6, 5.5**

- [x] 4. Implement button and form interaction tests
  - [x] 4.1 Create `frontend/e2e/interactions/button-interactions.spec.ts`
    - Test create, edit, delete, submit, cancel, export, and navigation buttons across Dashboard, Tasks, Quality, Admin pages
    - Verify each button click produces expected outcome (navigation, modal open, API call, state change)
    - _Requirements: 2.1_

  - [x] 4.2 Create `frontend/e2e/interactions/form-validation.spec.ts`
    - Test valid form submission on Login, Register, Task Create, Admin User Create forms
    - Test empty required field submission triggers `.ant-form-item-explain-error` for each field
    - Test constrained input validation (email format, password strength, numeric ranges)
    - Use `fillAntForm()` and `verifyFormValidation()` helpers
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 4.3 Create `frontend/e2e/interactions/modal-crud.spec.ts`
    - Test modal open/close lifecycle for create and edit operations
    - Test modal form field rendering, input acceptance, cancel close, and submit close
    - Test delete confirmation dialog flow (confirm removes item from list)
    - _Requirements: 2.5, 2.6_

  - [x] 4.4 Create `frontend/e2e/interactions/table-operations.spec.ts`
    - Test table pagination (page navigation, page size selection, row count validation)
    - Test table column sort toggles (ascending/descending)
    - Test table filter dropdowns
    - Test dropdown/select components (open, select, verify displayed value)
    - Test file upload with valid and invalid file types
    - Use `verifyTablePagination()`, `verifyTableSort()`, `verifyDropdownSelect()` helpers
    - _Requirements: 2.7, 2.8, 2.9, 2.10_

  - [x] 4.5 Write property tests for form interactions
    - **Property 2: Empty Required Fields Trigger Validation**
    - **Property 3: Invalid Constrained Input Triggers Field-Level Errors**
    - **Property 4: Modal Lifecycle Correctness**
    - **Property 5: Delete Confirmation Flow**
    - **Property 6: Table Pagination Consistency**
    - **Property 7: Table Sort and Filter Correctness**
    - **Property 8: Dropdown Select Round-Trip**
    - **Property 9: File Upload Type Validation**
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**

- [x] 5. Checkpoint - Verify role workflows and interaction tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement data lifecycle flow tests
  - [x] 6.1 Create `frontend/e2e/data-lifecycle/acquisition-to-export.spec.ts`
    - Test full pipeline: DataSync Sources → add source → trigger sync → verify Temp Data → create annotation task → assign → annotate → quality review → export
    - Mock all intermediate API responses with `mockDataSyncApi()` and `mockTasksApi()`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.2 Create `frontend/e2e/data-lifecycle/data-count-consistency.spec.ts`
    - Verify record counts remain consistent across pipeline stages (acquisition count = annotation task count = export count)
    - _Requirements: 3.6_

  - [x] 6.3 Write property test for data lifecycle count invariant
    - **Property 10: Data Lifecycle Count Invariant**
    - Create test in `frontend/src/__tests__/data-lifecycle.property.test.ts` using fast-check
    - **Validates: Requirements 3.6**

- [x] 7. Enhance auth/session management tests
  - [x] 7.1 Enhance `frontend/e2e/auth.spec.ts` with additional session management tests
    - Add tests for: login success → Dashboard redirect + Auth_Store token, invalid credentials error, registration flow, forgot/reset password flow
    - Add tests for: logout clears Auth_Store + redirects to login, post-logout protected route redirect, token expiration detection, tenant switch updates Auth_Store
    - Add test for concurrent sessions in different browser contexts maintaining independent state
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 7.2 Write property tests for auth fixtures
    - **Property 11: Post-Logout Protected Route Redirect**
    - **Property 12: Tenant Switch Context Update**
    - **Property 34: Auth Fixture Role Correctness**
    - Create `frontend/src/__tests__/auth-fixture.property.test.ts` using fast-check
    - **Validates: Requirements 4.5, 4.7, 16.1**

- [x] 8. Enhance security vulnerability tests
  - [x] 8.1 Enhance `frontend/e2e/security.spec.ts` with XSS, CSRF, SQL injection, and permission bypass tests
    - Add XSS tests: inject `<script>`, `onerror=`, `javascript:` into text inputs, verify sanitization
    - Add malicious API response test: mock API returning HTML/script tags, verify DOM escaping
    - Add CSRF test: POST without valid token returns 403
    - Add SQL injection test: enter `'; DROP TABLE --` and `1 OR 1=1` in search/filter inputs
    - Add permission bypass test: annotator navigating to admin URL gets 403/redirect
    - Add tenant manipulation test: verify tenant_id parameter tampering is blocked
    - Add token exposure test: verify tokens not in URL params, history, or console
    - Add password field test: verify `type="password"`, no autocomplete, values cleared on navigation
    - Add file upload test: reject .exe, .php, .sh uploads
    - Add API error safety test: verify error responses don't leak stack traces or DB schema
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

  - [x] 8.2 Write property tests for security invariants
    - **Property 13: XSS Input Sanitization**
    - **Property 14: Malicious API Response Escaping**
    - **Property 15: SQL Injection Input Escaping**
    - **Property 16: Tenant Data Isolation**
    - **Property 17: Password Field Security Attributes**
    - **Property 18: API Error Response Safety**
    - Create `frontend/src/__tests__/xss-sanitization.property.test.ts`, `frontend/src/__tests__/sql-injection.property.test.ts`, `frontend/src/__tests__/tenant-isolation.property.test.ts` using fast-check
    - Create `tests/test_security/test_error_response.py` using Hypothesis for backend property test
    - **Validates: Requirements 5.1, 5.2, 5.4, 5.6, 5.8, 5.10**

- [x] 9. Checkpoint - Verify data lifecycle, auth, and security tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Enhance performance benchmarking tests
  - [x] 10.1 Enhance `frontend/e2e/performance.spec.ts` with comprehensive performance benchmarks
    - Add Login page load assertion (< 2000ms)
    - Add Dashboard page load assertion (< 3000ms)
    - Add generic Page_Module load assertion (< 5000ms) for Tasks, Quality, Security, Admin, DataSync
    - Add Core Web Vitals measurement on Dashboard (LCP < 2500ms, FCP < 1800ms, CLS < 0.1, TTFB < 600ms)
    - Add table render benchmark (1000 rows, first page < 3000ms)
    - Add memory leak detection (< 200% growth after 5 page navigations, < 50% growth after 10 modal open/close)
    - Add slow network test (500ms latency: loading indicators appear, page renders after data)
    - Add offline test (error state displayed, no crash)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 10.2 Write property test for page load time threshold
    - **Property 19: Page Load Time Threshold**
    - **Validates: Requirements 6.3**

- [x] 11. Enhance multi-tenant and workspace tests
  - [x] 11.1 Enhance `frontend/e2e/multi-tenant.spec.ts` with tenant isolation and workspace tests
    - Add tenant isolation test: user in Tenant A cannot see Tenant B data
    - Add tenant switch test: Dashboard, Tasks, Billing refresh to new tenant data
    - Add workspace CRUD test: create, manage members, switch workspaces
    - Add workspace removal test: removed user cannot access workspace resources
    - Add URL manipulation test: accessing unauthorized workspace returns 403
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Implement i18n completeness tests
  - [x] 12.1 Create `frontend/e2e/i18n/language-completeness.spec.ts`
    - Test zh→en switch: all visible text updates to English without page reload
    - Test en→zh switch: all visible text updates to Chinese without page reload
    - Test no raw translation keys displayed on any page in either language (regex: `[a-z]+\.[a-z]+\.[a-z]+`)
    - Test language preference persists across navigation and browser refresh
    - Test form validation messages display in active language
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 12.2 Write property tests for i18n invariants
    - **Property 20: Language Switch Text Update**
    - **Property 21: No Raw Translation Keys Displayed**
    - **Property 22: Language Preference Persistence**
    - **Property 23: Validation Messages in Active Language**
    - Create `frontend/src/__tests__/i18n-keys.property.test.ts` using fast-check
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [x] 13. Implement error handling tests
  - [x] 13.1 Create `frontend/e2e/error-handling/error-scenarios.spec.ts`
    - Test API 500 response: user-friendly error message, no blank page
    - Test API 404 response: "not found" message displayed
    - Test API 429 response: rate-limiting message displayed
    - Test non-existent route: 404 page with navigation back to Dashboard
    - Test form submission network error: form data preserved, retry possible
    - Test temporary network disconnection recovery
    - Test page refresh during multi-step workflow: progress restored or restart guidance
    - Test empty states on Tasks, Billing, Quality, DataSync pages (`.ant-empty` component)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [x] 13.2 Write property tests for error handling
    - **Property 24: API 500 Graceful Degradation**
    - **Property 25: Form Data Preservation on Network Error**
    - **Property 26: Empty State Display**
    - **Validates: Requirements 9.1, 9.5, 9.8**

- [x] 14. Checkpoint - Verify performance, multi-tenant, i18n, and error handling tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Enhance accessibility tests
  - [x] 15.1 Enhance existing accessibility tests with comprehensive keyboard navigation and ARIA checks
    - Add Tab key navigation test: focus moves through interactive elements in logical order on each Page_Module
    - Add visible focus indicator test: all focused elements have non-zero outline or box-shadow
    - Add modal focus trap test: Tab cycles within modal, focus returns to trigger on close
    - Add form input label association test: all inputs have `<label>`, `aria-label`, or `aria-labelledby`
    - Add Escape key test: closes open modals, dropdowns, popovers
    - Add alt text test: images/icons have alt text or aria-hidden
    - Add color contrast test: minimum 4.5:1 ratio on Login, Dashboard, Tasks
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 15.2 Write property tests for accessibility
    - **Property 27: Tab Focus Order**
    - **Property 28: Visible Focus Indicators**
    - **Property 29: Modal Focus Trap and Restore**
    - **Property 30: Form Input Label Association**
    - **Property 31: Escape Key Closes Overlays**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

- [x] 16. Enhance responsive design tests
  - [x] 16.1 Enhance `frontend/e2e/responsive-design.spec.ts` with viewport-specific tests
    - Test no horizontal overflow at 375px, 768px, 1280px for each Page_Module
    - Test sidebar collapses to hamburger menu at 375px, opens on click
    - Test tables switch to card/scrollable layout at 768px when columns exceed viewport
    - Test touch targets are at least 44×44px on mobile viewports
    - Test form inputs and buttons remain usable on mobile viewports
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 16.2 Write property tests for responsive design
    - **Property 32: No Horizontal Overflow Across Viewports**
    - **Property 33: Touch Target Minimum Size**
    - **Validates: Requirements 11.1, 11.4, 11.5**

- [x] 17. Implement admin module tests
  - [x] 17.1 Create `frontend/e2e/admin-modules/admin-console.spec.ts`
    - Test console dashboard displays system overview metrics
    - _Requirements: 12.1_

  - [x] 17.2 Create `frontend/e2e/admin-modules/admin-tenants.spec.ts`
    - Test tenant CRUD operations with form validation
    - _Requirements: 12.2_

  - [x] 17.3 Create `frontend/e2e/admin-modules/admin-users.spec.ts`
    - Test user listing, role assignment, activation/deactivation, search/filter
    - _Requirements: 12.3_

  - [x] 17.4 Create `frontend/e2e/admin-modules/admin-permissions.spec.ts`
    - Test permission matrix display, role-permission assignment, custom permission creation
    - _Requirements: 12.7_

  - [x] 17.5 Create `frontend/e2e/admin-modules/admin-quotas.spec.ts`
    - Test quota display, limit configuration, usage tracking per tenant
    - _Requirements: 12.8_

  - [x] 17.6 Create `frontend/e2e/admin-modules/admin-billing.spec.ts`
    - Test billing record listing, invoice generation, payment status management
    - _Requirements: 12.9_

  - [x] 17.7 Create `frontend/e2e/admin-modules/admin-config.spec.ts`
    - Test Admin System config form, LLM Config + connection testing + binding, Text-to-SQL config + query testing
    - Test DB Config, Sync Config, History, Third Party config forms (load, validate, save)
    - _Requirements: 12.4, 12.5, 12.6, 12.10_

- [x] 18. Checkpoint - Verify accessibility, responsive, and admin module tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. Implement deployment health check tests
  - [x] 19.1 Create `frontend/e2e/deployment/health-checks.spec.ts`
    - Test frontend Docker service responds HTTP 200
    - Test backend `/health` endpoint returns 200 with service status
    - Test PostgreSQL accepts connections and responds to basic query
    - Test Redis accepts connections and responds to PING
    - Test Neo4j accepts connections and responds to basic Cypher query
    - Test environment variables correctly loaded in backend
    - Test service restart recovery within 60 seconds
    - Test frontend static assets served with correct cache headers and gzip
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

- [x] 20. Implement DataSync and Datalake tests
  - [x] 20.1 Create `frontend/e2e/datasync/sources-crud.spec.ts`
    - Test source list display, add-source form with connection parameters, connectivity test
    - _Requirements: 14.1_

  - [x] 20.2 Create `frontend/e2e/datasync/scheduler.spec.ts`
    - Test sync history display (status, duration, row counts)
    - Test schedule creation, editing, enabling/disabling, deletion
    - _Requirements: 14.2, 14.3_

  - [x] 20.3 Create `frontend/e2e/datasync/datalake-browser.spec.ts`
    - Test Datalake Dashboard metrics, health status, volume trends, query performance charts
    - Test Schema Browser: database listing, table listing, column schema display
    - _Requirements: 14.4, 14.5_

  - [x] 20.4 Create `frontend/e2e/datasync/export-flow.spec.ts`
    - Test export configuration, format selection, execution with progress tracking
    - Test API Management: key listing, creation, revocation, usage statistics
    - _Requirements: 14.6, 14.7_

- [x] 21. Implement AI integration tests
  - [x] 21.1 Create `frontend/e2e/ai-integration/ai-annotation.spec.ts`
    - Test annotation interface loads, displays data items, accepts AI-assisted inputs
    - Test annotation submission saves and reflects in task progress
    - _Requirements: 15.1, 15.4_

  - [x] 21.2 Create `frontend/e2e/ai-integration/ai-processing.spec.ts`
    - Test processing job creation, configuration, execution, result display
    - Test results accessible from Augmentation Samples page
    - _Requirements: 15.2, 15.5_

  - [x] 21.3 Create `frontend/e2e/ai-integration/ai-assistant.spec.ts`
    - Test chat interface loads, accepts user messages, displays AI responses
    - _Requirements: 15.3_

- [x] 22. Implement test infrastructure validation
  - [x] 22.1 Write property test for mock API schema validity
    - **Property 35: Mock API Schema Validity**
    - Create `frontend/src/__tests__/mock-schema.property.test.ts` using fast-check
    - For any endpoint in mock factory, verify response is valid JSON with expected fields and types
    - **Validates: Requirements 16.2**

  - [x] 22.2 Write property test for console error filtering
    - **Property 36: Console Error Filtering**
    - Create `frontend/src/__tests__/console-filter.property.test.ts` using fast-check
    - Generate random error strings, verify known-issues exclusion list correctly filters
    - **Validates: Requirements 16.4**

- [x] 23. Update Playwright configuration
  - [x] 23.1 Add `deployment` project to `frontend/playwright.config.ts`
    - Add project with `name: 'deployment'`, `testDir: './e2e/deployment'`, `baseURL` from `DEPLOY_URL` env var, `timeout: 120000`
    - Keep all existing projects (chromium, firefox, webkit, mobile) unchanged
    - _Requirements: 13.1, 16.6_

- [x] 24. Final checkpoint - Full test suite validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major group
- Property tests (P1-P36) validate universal correctness properties from the design document
- All new E2E tests use the shared helpers from `mock-api-factory.ts`, `role-permissions.ts`, and `form-interaction.ts`
- Existing spec files (auth.spec.ts, security.spec.ts, performance.spec.ts, etc.) are enhanced in-place, not replaced
- Deployment health checks run in a separate Playwright project against real services (no mocking)
