# Requirements Document

## Introduction

SuperInsight is a multi-tenant AI data governance and annotation platform. This spec defines comprehensive E2E testing requirements to achieve full workflow coverage, button/form interaction testing, security validation, performance benchmarking, and deployment verification. The existing test suite (35+ Playwright spec files) covers auth, dashboard, basic permissions, security, and performance, but has significant gaps in cross-role boundary testing, complete data lifecycle flows, error scenarios, accessibility, and deployment health checks.

## Glossary

- **Test_Runner**: The Playwright E2E test execution engine configured in `frontend/playwright.config.ts`
- **Test_Fixture**: Reusable test setup utilities defined in `frontend/e2e/fixtures.ts` providing authenticated pages, console log collection, and screenshot helpers
- **Test_Helper**: Shared utility functions in `frontend/e2e/test-helpers.ts` for auth setup, API mocking, performance measurement, and accessibility checks
- **Mock_API**: Playwright route interception layer that simulates backend API responses for isolated frontend testing
- **Auth_Store**: Zustand-based authentication state persisted in localStorage under key `auth-storage`
- **Role**: One of four user roles — `admin` (full access), `data_manager` (data management), `data_analyst` (analysis/reporting), `annotator` (task annotation)
- **Protected_Route**: A frontend route wrapped in `ProtectedRoute` component requiring valid Auth_Store state
- **Data_Lifecycle**: The end-to-end data flow: acquisition → annotation → quality review → export
- **Tenant**: An isolated organizational unit in the multi-tenant system, identified by `tenant_id`
- **Page_Module**: A distinct frontend page or route group (e.g., Dashboard, Tasks, Quality, Security, Admin, DataSync, Augmentation, License, DataLifecycle, AI Integration)
- **Form_Interaction**: A simulated user action on form elements including text input, select dropdown, checkbox, radio, date picker, file upload, and form submission
- **Button_Interaction**: A simulated user click on any actionable button including create, edit, delete, submit, cancel, export, and navigation buttons
- **Web_Vital**: A Core Web Vital metric — LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift), FCP (First Contentful Paint), TTFB (Time to First Byte)
- **Docker_Service**: A containerized service in the deployment stack (frontend, backend, PostgreSQL, Redis, Neo4j)

## Requirements

### Requirement 1: Role-Based Full Workflow E2E Testing

**User Story:** As a QA engineer, I want every user-facing workflow tested per role, so that I can verify all four roles can complete their authorized workflows end-to-end.

#### Acceptance Criteria

1. WHEN an admin user is authenticated, THE Test_Runner SHALL verify the admin can access and interact with all Page_Modules including Dashboard, Tasks, Quality, Security, Admin, DataSync, Augmentation, License, DataLifecycle, Billing, Settings, and AI Integration
2. WHEN a data_manager user is authenticated, THE Test_Runner SHALL verify the data_manager can access DataSync, DataLifecycle, Augmentation, Tasks, and Dashboard, and SHALL verify the data_manager cannot access Admin, Security RBAC, or Billing Management pages
3. WHEN a data_analyst user is authenticated, THE Test_Runner SHALL verify the data_analyst can access Dashboard, Quality Reports, Billing Overview, and License Usage, and SHALL verify the data_analyst cannot access Admin, DataSync configuration, or Task assignment pages
4. WHEN an annotator user is authenticated, THE Test_Runner SHALL verify the annotator can access assigned Tasks and Task Annotation pages, and SHALL verify the annotator cannot access Admin, Quality Rules, Security, DataSync, or Billing pages
5. FOR EACH Role, THE Test_Runner SHALL execute a complete Data_Lifecycle flow covering data acquisition, annotation task creation, annotation execution, quality review, and data export within the permissions of that Role
6. IF a Role attempts to access a page outside its permission scope, THEN THE Test_Runner SHALL verify the application redirects to a 403 Forbidden page or the Dashboard

### Requirement 2: Button and Form Interaction Testing

**User Story:** As a QA engineer, I want every button, form input, and interactive element tested with simulated human interactions, so that I can confirm all UI controls function correctly.

#### Acceptance Criteria

1. FOR EACH Page_Module, THE Test_Runner SHALL identify and click every visible Button_Interaction element and verify the expected outcome (navigation, modal open, API call, or state change)
2. FOR EACH form in the application, THE Test_Runner SHALL fill all input fields with valid data, submit the form, and verify a success response or state change
3. FOR EACH form in the application, THE Test_Runner SHALL submit the form with empty required fields and verify that Ant Design validation error messages appear for each required field
4. FOR EACH form with constrained inputs (email format, password strength, numeric ranges), THE Test_Runner SHALL submit invalid values and verify field-level validation error messages
5. WHEN a modal dialog is opened via a create or edit button, THE Test_Runner SHALL verify the modal renders with correct fields, accepts input, and closes on cancel or successful submission
6. WHEN a delete button is clicked, THE Test_Runner SHALL verify a confirmation dialog appears, and SHALL verify the item is removed from the list after confirmation
7. FOR EACH table with pagination, THE Test_Runner SHALL verify page navigation, page size selection, and that row counts match the selected page size
8. FOR EACH table with sorting and filtering, THE Test_Runner SHALL verify column sort toggles and filter dropdowns produce correctly ordered and filtered results
9. FOR EACH dropdown/select component, THE Test_Runner SHALL open the dropdown, select an option, and verify the selected value is displayed and persisted
10. WHEN a file upload component is present, THE Test_Runner SHALL simulate file selection with valid and invalid file types and verify acceptance or rejection messages

### Requirement 3: Data Lifecycle End-to-End Flow Testing

**User Story:** As a QA engineer, I want the complete data lifecycle tested from acquisition through export, so that I can verify data integrity across the entire pipeline.

#### Acceptance Criteria

1. THE Test_Runner SHALL execute a complete flow: navigate to DataSync Sources → add a data source → trigger sync → verify data appears in DataLifecycle Temp Data
2. WHEN data is available in Temp Data, THE Test_Runner SHALL create an annotation task from the data, assign it to an annotator, and verify the task appears in the Tasks list
3. WHEN an annotation task is assigned, THE Test_Runner SHALL navigate to the Task Annotation page, complete an annotation, submit it, and verify the task status changes to completed
4. WHEN annotations are completed, THE Test_Runner SHALL navigate to Quality Overview, verify quality metrics reflect the new annotations, and run quality rules against the annotated data
5. WHEN quality review passes, THE Test_Runner SHALL navigate to DataSync Export, select the reviewed data, execute an export, and verify the export completes with a success status
6. THE Test_Runner SHALL verify that data counts remain consistent across each stage of the Data_Lifecycle (acquisition count matches annotation task count matches export count)

### Requirement 4: Authentication and Session Management Testing

**User Story:** As a QA engineer, I want authentication flows and session management thoroughly tested, so that I can verify secure access control.

#### Acceptance Criteria

1. THE Test_Runner SHALL verify login with valid credentials redirects to Dashboard and stores a valid token in Auth_Store
2. WHEN invalid credentials are submitted, THE Test_Runner SHALL verify an error message is displayed and the user remains on the login page
3. THE Test_Runner SHALL verify registration with valid data creates an account and redirects to the login page
4. WHEN a password reset is requested, THE Test_Runner SHALL verify the forgot-password flow sends a reset email confirmation and the reset-password form accepts a new password with a valid token
5. WHEN a user logs out, THE Test_Runner SHALL verify Auth_Store is cleared, the user is redirected to the login page, and subsequent access to Protected_Routes redirects to login
6. WHEN a session token expires, THE Test_Runner SHALL verify the application detects the expiration and redirects to the login page
7. WHEN a user switches Tenant, THE Test_Runner SHALL verify the Auth_Store updates with the new tenant_id and all subsequent API calls include the new tenant context
8. THE Test_Runner SHALL verify that concurrent sessions from the same user in different browser contexts maintain independent Auth_Store states

### Requirement 5: Security Vulnerability Testing

**User Story:** As a security engineer, I want automated security tests covering common vulnerabilities, so that I can verify the platform resists XSS, CSRF, SQL injection, and permission bypass attacks.

#### Acceptance Criteria

1. WHEN a script tag is injected into any text input field, THE Test_Runner SHALL verify the script is not executed and the content is sanitized in the rendered DOM
2. WHEN an API response contains malicious HTML or JavaScript, THE Test_Runner SHALL verify the content is escaped before rendering
3. WHEN a POST request is made without a valid CSRF token, THE Test_Runner SHALL verify the request is rejected with a 403 status
4. WHEN a SQL injection payload is entered into search or filter inputs, THE Test_Runner SHALL verify the payload is escaped and does not produce unexpected query results
5. WHEN a user with Role `annotator` directly navigates to an admin URL path, THE Test_Runner SHALL verify the application returns a 403 response or redirects to an authorized page
6. WHEN a user manipulates the tenant_id parameter in API requests, THE Test_Runner SHALL verify the backend enforces Tenant isolation and returns only authorized data
7. THE Test_Runner SHALL verify that authentication tokens are not exposed in URL parameters, browser history, or console logs
8. THE Test_Runner SHALL verify that password fields mask input, do not allow browser autocomplete for sensitive fields, and clear values on page navigation
9. WHEN a file upload is attempted with an executable file type (.exe, .php, .sh), THE Test_Runner SHALL verify the upload is rejected with a validation error
10. THE Test_Runner SHALL verify that API error responses do not leak internal server details, stack traces, or database schema information

### Requirement 6: Performance Benchmarking Testing

**User Story:** As a QA engineer, I want automated performance benchmarks for page loads and API responses, so that I can detect performance regressions.

#### Acceptance Criteria

1. THE Test_Runner SHALL measure and assert that the Login page loads within 2000 milliseconds
2. THE Test_Runner SHALL measure and assert that the Dashboard page loads within 3000 milliseconds
3. FOR EACH Page_Module, THE Test_Runner SHALL measure and assert that initial page load completes within 5000 milliseconds
4. THE Test_Runner SHALL measure Core Web_Vitals (LCP < 2500ms, FCP < 1800ms, CLS < 0.1, TTFB < 600ms) on the Dashboard page
5. WHEN a table displays 1000 rows with pagination, THE Test_Runner SHALL verify the table renders the first page within 3000 milliseconds and scrolling remains smooth (frame time < 16ms)
6. THE Test_Runner SHALL verify that memory usage does not increase by more than 200% of the initial heap size after navigating through 5 different Page_Modules
7. WHEN 10 repeated modal open/close operations are performed, THE Test_Runner SHALL verify memory usage does not increase by more than 50% of the baseline
8. WHEN network latency is simulated at 500ms per request, THE Test_Runner SHALL verify loading indicators appear and the page renders correctly after data arrives
9. WHEN the network is offline, THE Test_Runner SHALL verify the application displays an appropriate error state and does not crash

### Requirement 7: Multi-Tenant and Workspace Testing

**User Story:** As a QA engineer, I want multi-tenant isolation and workspace switching tested, so that I can verify data boundaries between tenants.

#### Acceptance Criteria

1. THE Test_Runner SHALL verify that a user in Tenant A cannot see or access data belonging to Tenant B through the UI
2. WHEN a user switches from Tenant A to Tenant B, THE Test_Runner SHALL verify the Dashboard, Tasks, and Billing data refresh to show only Tenant B data
3. THE Test_Runner SHALL verify that workspace creation, member management, and workspace switching function correctly within a single Tenant
4. WHEN a user is removed from a workspace, THE Test_Runner SHALL verify the user can no longer access that workspace's resources
5. IF a user attempts to access a workspace they do not belong to via URL manipulation, THEN THE Test_Runner SHALL verify the application returns a 403 response

### Requirement 8: Internationalization (i18n) Testing

**User Story:** As a QA engineer, I want language switching tested across all pages, so that I can verify all visible text is properly translated.

#### Acceptance Criteria

1. WHEN the language is switched from Chinese (zh) to English (en), THE Test_Runner SHALL verify all visible text on the current page updates to English without page reload
2. WHEN the language is switched from English (en) to Chinese (zh), THE Test_Runner SHALL verify all visible text on the current page updates to Chinese without page reload
3. FOR EACH Page_Module, THE Test_Runner SHALL verify no raw translation keys (strings matching the pattern `[a-z]+\.[a-z]+\.[a-z]+`) are displayed in either language
4. THE Test_Runner SHALL verify that the selected language preference persists across page navigation and browser refresh
5. THE Test_Runner SHALL verify that form validation error messages display in the currently selected language

### Requirement 9: Error Handling and Edge Case Testing

**User Story:** As a QA engineer, I want error scenarios and edge cases tested, so that I can verify the application handles failures gracefully.

#### Acceptance Criteria

1. WHEN an API returns a 500 Internal Server Error, THE Test_Runner SHALL verify the application displays a user-friendly error message and does not show a blank page
2. WHEN an API returns a 404 Not Found, THE Test_Runner SHALL verify the application displays an appropriate "not found" message
3. WHEN an API returns a 429 Too Many Requests, THE Test_Runner SHALL verify the application displays a rate-limiting message
4. WHEN the user navigates to a non-existent route, THE Test_Runner SHALL verify the 404 error page is displayed with navigation back to Dashboard
5. WHEN a form submission fails due to a network error, THE Test_Runner SHALL verify the form data is preserved and the user can retry submission
6. THE Test_Runner SHALL verify that the application recovers gracefully from a temporary network disconnection without requiring a full page reload
7. WHEN a page is refreshed during a multi-step workflow, THE Test_Runner SHALL verify the application restores the user's progress or provides clear guidance to restart
8. THE Test_Runner SHALL verify that empty states (no data) display appropriate placeholder messages and action prompts on Tasks, Billing, Quality, and DataSync pages

### Requirement 10: Accessibility and Keyboard Navigation Testing

**User Story:** As a QA engineer, I want accessibility and keyboard navigation tested, so that I can verify the application is usable without a mouse.

#### Acceptance Criteria

1. FOR EACH Page_Module, THE Test_Runner SHALL verify that Tab key navigation moves focus through all interactive elements in a logical order
2. THE Test_Runner SHALL verify that all focused elements display a visible focus indicator (outline or box-shadow)
3. THE Test_Runner SHALL verify that modal dialogs trap focus within the modal and return focus to the trigger element on close
4. THE Test_Runner SHALL verify that all form inputs have associated labels or aria-label attributes
5. THE Test_Runner SHALL verify that the Escape key closes open modals, dropdowns, and popover menus
6. THE Test_Runner SHALL verify that all images and icons have appropriate alt text or aria-hidden attributes
7. THE Test_Runner SHALL verify that color contrast ratios meet a minimum of 4.5:1 for normal text on key pages (Login, Dashboard, Tasks)

### Requirement 11: Responsive Design Testing

**User Story:** As a QA engineer, I want responsive behavior tested across mobile, tablet, and desktop viewports, so that I can verify the layout adapts correctly.

#### Acceptance Criteria

1. FOR EACH Page_Module, THE Test_Runner SHALL verify the page renders without horizontal overflow at viewport widths of 375px (mobile), 768px (tablet), and 1280px (desktop)
2. WHEN the viewport is 375px wide, THE Test_Runner SHALL verify the sidebar navigation collapses to a hamburger menu and the menu opens on click
3. WHEN the viewport is 768px wide, THE Test_Runner SHALL verify tables switch to a card or scrollable layout if columns exceed the viewport width
4. THE Test_Runner SHALL verify that touch-target sizes are at least 44x44 pixels on mobile viewports for all interactive elements
5. THE Test_Runner SHALL verify that form inputs and buttons remain usable and properly sized on mobile viewports

### Requirement 12: Admin Module Comprehensive Testing

**User Story:** As a QA engineer, I want all admin sub-pages tested, so that I can verify tenant management, user management, system configuration, LLM config, and permission management work correctly.

#### Acceptance Criteria

1. WHEN an admin navigates to Admin Console, THE Test_Runner SHALL verify the console dashboard displays system overview metrics
2. WHEN an admin navigates to Admin Tenants, THE Test_Runner SHALL verify tenant CRUD operations (create, read, update, delete) function correctly with form validation
3. WHEN an admin navigates to Admin Users, THE Test_Runner SHALL verify user listing, role assignment, activation/deactivation, and search/filter functionality
4. WHEN an admin navigates to Admin System, THE Test_Runner SHALL verify system configuration form loads current values, accepts changes, and saves successfully
5. WHEN an admin navigates to Admin LLM Config, THE Test_Runner SHALL verify LLM provider configuration, connection testing, and application binding workflows
6. WHEN an admin navigates to Admin Text-to-SQL, THE Test_Runner SHALL verify SQL builder configuration and query testing functionality
7. WHEN an admin navigates to Admin Permissions, THE Test_Runner SHALL verify permission matrix display, role-permission assignment, and custom permission creation
8. WHEN an admin navigates to Admin Quotas, THE Test_Runner SHALL verify quota display, limit configuration, and usage tracking per Tenant
9. WHEN an admin navigates to Admin Billing Management, THE Test_Runner SHALL verify billing record listing, invoice generation, and payment status management
10. WHEN an admin navigates to Admin Config pages (DB Config, Sync Config, History, Third Party), THE Test_Runner SHALL verify each configuration form loads, validates, and saves correctly

### Requirement 13: Deployment and Infrastructure Testing

**User Story:** As a DevOps engineer, I want deployment health checks automated, so that I can verify all services are running and connected after deployment.

#### Acceptance Criteria

1. THE Test_Runner SHALL verify the frontend Docker_Service responds to HTTP requests on the configured port with a 200 status
2. THE Test_Runner SHALL verify the backend Docker_Service health endpoint (`/health`) returns a 200 status with service status details
3. THE Test_Runner SHALL verify the PostgreSQL Docker_Service accepts connections and responds to a basic query
4. THE Test_Runner SHALL verify the Redis Docker_Service accepts connections and responds to a PING command
5. THE Test_Runner SHALL verify the Neo4j Docker_Service accepts connections and responds to a basic Cypher query
6. THE Test_Runner SHALL verify that environment variables for database URLs, Redis URLs, and API keys are correctly loaded in the backend Docker_Service
7. WHEN a Docker_Service is restarted, THE Test_Runner SHALL verify the service recovers and passes health checks within 60 seconds
8. THE Test_Runner SHALL verify that frontend static assets are served with correct cache headers and gzip compression

### Requirement 14: Data Sync and Datalake Testing

**User Story:** As a QA engineer, I want data sync and datalake features tested end-to-end, so that I can verify data source management, sync execution, and schema browsing work correctly.

#### Acceptance Criteria

1. WHEN a user navigates to DataSync Sources, THE Test_Runner SHALL verify the source list displays, and the add-source form accepts connection parameters and tests connectivity
2. WHEN a data source is configured, THE Test_Runner SHALL verify sync history displays previous sync records with status, duration, and row counts
3. WHEN a user navigates to DataSync Scheduler, THE Test_Runner SHALL verify schedule creation, editing, enabling/disabling, and deletion
4. WHEN a user navigates to Datalake Dashboard, THE Test_Runner SHALL verify overview metrics, health status, volume trends, and query performance charts render correctly
5. WHEN a user navigates to Datalake Schema Browser, THE Test_Runner SHALL verify database listing, table listing, and column schema display for a selected source
6. WHEN a user navigates to DataSync Export, THE Test_Runner SHALL verify export configuration, format selection, and export execution with progress tracking
7. WHEN a user navigates to API Management, THE Test_Runner SHALL verify API key listing, creation, revocation, and usage statistics display

### Requirement 15: AI Integration and Annotation Testing

**User Story:** As a QA engineer, I want AI-powered features tested, so that I can verify AI annotation, AI processing, and AI assistant workflows function correctly.

#### Acceptance Criteria

1. WHEN a user navigates to AI Annotation, THE Test_Runner SHALL verify the annotation interface loads, displays data items, and accepts AI-assisted annotation inputs
2. WHEN a user navigates to AI Processing, THE Test_Runner SHALL verify processing job creation, configuration, execution, and result display
3. WHEN a user navigates to AI Assistant, THE Test_Runner SHALL verify the chat interface loads, accepts user messages, and displays AI responses
4. WHEN an AI annotation is submitted, THE Test_Runner SHALL verify the annotation is saved and reflected in the task progress
5. WHEN AI processing completes, THE Test_Runner SHALL verify results are accessible from the Augmentation Samples page

### Requirement 16: Test Infrastructure and Reporting

**User Story:** As a QA engineer, I want the test infrastructure itself validated, so that I can ensure test fixtures, helpers, and reporting work correctly.

#### Acceptance Criteria

1. THE Test_Runner SHALL verify that the `authenticatedPage` fixture correctly sets Auth_Store state for each Role before test execution
2. THE Test_Runner SHALL verify that Mock_API route handlers return consistent, schema-valid responses for all mocked endpoints
3. THE Test_Runner SHALL verify that test failure screenshots are captured in the `test-results/screenshots/` directory
4. THE Test_Runner SHALL verify that console error collection captures and filters errors according to the known-issues exclusion list
5. THE Test_Runner SHALL generate HTML and JSON test reports after each test run with pass/fail counts, duration, and failure details
6. THE Test_Runner SHALL support parallel test execution across Chromium, Firefox, and WebKit browser engines as configured in `playwright.config.ts`
