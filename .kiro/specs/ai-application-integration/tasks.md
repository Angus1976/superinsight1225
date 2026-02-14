# Implementation Plan: AI Application Integration System

## Overview

This implementation plan breaks down the AI Application Integration System into incremental, testable steps. The system enables OpenClaw and other AI gateways to access SuperInsight's governed data through secure APIs and custom skills, with full multi-tenant isolation, auditing, and monitoring.

**Key Reuse Strategy**:
- **LLM Infrastructure**: Reuses existing `LLMConfigManager`, `LLMSwitcher`, and `ChinaLLMProvider` from `src/ai/`
- **Data Access APIs**: Reuses existing `ExportService`, `AIFriendlyExporter`, and dataset APIs from `src/api/export.py`, `src/api/sync_pipeline.py`, and `src/api/sync_datasets.py`
- **Monitoring**: Extends existing health monitoring, audit service, and Prometheus metrics
- **i18n**: Uses existing `TranslationManager` and translation infrastructure

This approach minimizes duplication and ensures consistency with the existing platform.

## Tasks

- [x] 1. Set up database schema and core models
  - Create database migration for ai_gateways, ai_skills, and ai_audit_logs tables
  - Implement SQLAlchemy models with proper relationships and indexes
  - Add tenant_id indexes for multi-tenant queries
  - _Requirements: 2.1, 4.1, 8.1_

- [x] 1.1 Write property test for gateway model
  - **Property 1: Gateway Registration Completeness**
  - **Validates: Requirements 2.1**

- [x] 2. Implement authentication and credential management
  - [x] 2.1 Create APICredentials model and generation logic
    - Implement secure API key/secret generation using secrets module
    - Add bcrypt hashing for credential storage
    - Create credential validation functions
    - _Requirements: 2.2, 7.1_

  - [x] 2.2 Write property test for credential uniqueness
    - **Property 2: API Credential Uniqueness**
    - **Validates: Requirements 2.2**

  - [x] 2.3 Implement JWT token service
    - Create JWT token generation with RS256 signing
    - Add token validation and expiration checking
    - Implement token claims (tenant_id, permissions)
    - _Requirements: 7.2, 7.3_

  - [x] 2.4 Write property test for JWT token issuance
    - **Property 20: JWT Token Issuance**
    - **Validates: Requirements 7.2**

  - [x] 2.5 Write property test for expired token rejection
    - **Property 21: Expired Token Rejection**
    - **Validates: Requirements 7.3**

- [x] 3. Implement Gateway Manager service
  - [x] 3.1 Create GatewayManager class
    - Implement register_gateway method with validation
    - Add update_configuration with versioning
    - Implement deactivate_gateway with credential revocation
    - _Requirements: 2.1, 2.3, 2.4, 2.5_

  - [x] 3.2 Write property test for configuration validation
    - **Property 3: Configuration Validation**
    - **Validates: Requirements 2.3, 9.1**

  - [x] 3.3 Write property test for configuration versioning
    - **Property 4: Configuration Versioning**
    - **Validates: Requirements 2.4, 9.5**

  - [x] 3.4 Write property test for gateway deactivation
    - **Property 5: Gateway Deactivation Completeness**
    - **Validates: Requirements 2.5**

- [x] 4. Implement multi-tenant authorization service
  - [x] 4.1 Create AuthorizationService class
    - Implement check_permission method
    - Add apply_tenant_filter for query injection
    - Create validate_cross_tenant_access
    - _Requirements: 4.2, 4.3, 4.4_

  - [x] 4.2 Write property test for multi-tenant data isolation
    - **Property 12: Multi-Tenant Data Isolation**
    - **Validates: Requirements 4.2, 4.4**

  - [x] 4.3 Write property test for cross-tenant access rejection
    - **Property 13: Cross-Tenant Access Rejection**
    - **Validates: Requirements 4.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Integrate existing data access APIs
  - [x] 6.1 Create OpenClawDataBridge class
    - Implement query_governed_data wrapping existing ExportService
    - Add export_for_skill using existing AIFriendlyExporter
    - Create get_quality_metrics wrapping dataset quality API
    - Add format_for_openclaw to adapt responses for OpenClaw
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.1, 11.2_
    - _Reuses: ExportService, AIFriendlyExporter, sync_datasets API_

  - [x] 6.2 Write property test for authenticated data access
    - **Property 6: Authenticated and Authorized Data Access**
    - **Validates: Requirements 3.1, 3.2**

  - [x] 6.3 Write property test for JSON response format
    - **Property 7: JSON Response Format**
    - **Validates: Requirements 3.3**

  - [x] 6.4 Write property test for data filtering
    - **Property 8: Data Filtering Functionality**
    - **Validates: Requirements 3.4**

  - [x] 6.5 Write property test for pagination consistency
    - **Property 9: Pagination Consistency**
    - **Validates: Requirements 3.5**

  - [x] 6.6 Write property test for format transformation
    - **Property 29: Data Format Transformation with Preservation**
    - **Validates: Requirements 11.2**

- [x] 7. Implement API endpoints for gateway management
  - [x] 7.1 Create FastAPI router for /api/v1/ai-integration/gateways
    - POST /gateways - Register gateway
    - GET /gateways - List gateways with tenant filtering
    - GET /gateways/{id} - Get gateway details
    - PUT /gateways/{id} - Update gateway configuration
    - DELETE /gateways/{id} - Deactivate gateway
    - POST /gateways/{id}/deploy - Deploy gateway
    - GET /gateways/{id}/health - Health check
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 6.1_

  - [x] 7.2 Write unit tests for gateway API endpoints
    - Test registration with valid/invalid data
    - Test tenant isolation in list endpoint
    - Test configuration update validation
    - _Requirements: 2.1, 2.3, 2.4_

- [x] 8. Create API endpoints for data access
  - [x] 8.1 Create FastAPI router for /api/v1/ai-integration/data
    - GET /data/query - Query governed data (wraps existing export API)
    - POST /data/export-for-skill - Export for OpenClaw skill (wraps AIFriendlyExporter)
    - GET /data/quality-metrics - Get quality metrics (wraps dataset quality API)
    - Add authentication and authorization middleware
    - Add tenant filtering for all endpoints
    - _Requirements: 3.3, 3.4, 3.5, 11.1_
    - _Reuses: /api/v1/export/*, /api/v1/sync/export, /api/v1/sync/datasets/*_

  - [x] 8.2 Write unit tests for data access endpoints
    - Test authentication middleware
    - Test tenant filtering
    - Test format conversion
    - Test integration with existing export APIs
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 9. Implement rate limiting service
  - [x] 9.1 Create RateLimiter class using Redis
    - Implement check_rate_limit with sliding window
    - Add check_quota for daily/monthly limits
    - Create record_request for tracking
    - Implement counter reset logic
    - _Requirements: 12.1, 12.2, 12.5_

  - [x] 9.2 Write property test for rate limit enforcement
    - **Property 33: Rate Limit Enforcement**
    - **Validates: Requirements 12.2**

  - [x] 9.3 Write property test for usage counter management
    - **Property 35: Usage Counter Management**
    - **Validates: Requirements 12.5**

- [x] 10. Implement audit logging service
  - [x] 10.1 Create AuditService class
    - Implement log_data_access with signature generation
    - Add log_security_event for security monitoring
    - Create query_audit_logs with filtering
    - Implement HMAC-SHA256 signature for tamper detection
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 10.2 Write property test for comprehensive audit logging
    - **Property 23: Comprehensive Audit Logging**
    - **Validates: Requirements 8.1, 8.2**

  - [x] 10.3 Write property test for audit log immutability
    - **Property 24: Audit Log Immutability**
    - **Validates: Requirements 8.3**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Docker Compose integration
  - [x] 12.1 Create docker-compose.ai-integration.yml
    - Define openclaw-gateway service
    - Define openclaw-agent service
    - Configure network connectivity
    - Add volume mounts for config, skills, and memory
    - Set environment variables for SuperInsight API
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 12.2 Create deployment script
    - Implement gateway deployment using docker-compose
    - Add environment variable injection
    - Create health check verification
    - _Requirements: 1.1, 1.3, 1.4_

  - [x] 12.3 Write integration test for Docker deployment
    - Test container startup
    - Test network connectivity
    - Test environment variable injection
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 13. Implement Skill Manager service
  - [x] 13.1 Create SkillManager class
    - Implement package_skill for creating skill packages
    - Add deploy_skill for installing to OpenClaw
    - Create hot_reload_skill for updates without restart
    - Implement list_skills for gateway
    - _Requirements: 5.1, 5.6_

  - [x] 13.2 Create API endpoints for skill management
    - POST /api/v1/ai-integration/skills - Create skill package
    - GET /api/v1/ai-integration/skills - List skills
    - POST /api/v1/ai-integration/skills/{id}/deploy - Deploy skill
    - POST /api/v1/ai-integration/skills/{id}/reload - Hot reload
    - _Requirements: 5.1, 5.6_

  - [x] 13.3 Write unit tests for skill management
    - Test skill packaging
    - Test deployment to gateway
    - Test hot reload functionality
    - _Requirements: 5.1, 5.6_

- [x] 14. Implement SuperInsight skill for OpenClaw
  - [x] 14.1 Create Node.js skill package
    - Implement authentication with SuperInsight API
    - Add natural language query parsing
    - Create Data Access API client
    - Implement result formatting for channels
    - Add error handling with user-friendly messages
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

  - [x] 14.2 Write property test for skill authentication
    - **Property 15: Skill Authentication**
    - **Validates: Requirements 5.2**

  - [x] 14.3 Write property test for query translation
    - **Property 16: Natural Language Query Translation**
    - **Validates: Requirements 5.3**

  - [x] 14.4 Write unit tests for result formatting
    - Test formatting for different channels
    - Test text length constraints
    - _Requirements: 5.4_

- [x] 15. Implement monitoring service
  - [x] 15.1 Create MonitoringService class
    - Implement record_metric for Prometheus
    - Add health_check_gateway method
    - Create get_gateway_metrics for dashboard
    - Define Prometheus metric collectors
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 15.2 Create health check endpoints
    - GET /health - Overall system health
    - GET /health/gateway/{id} - Gateway health
    - GET /health/database - Database connectivity
    - GET /health/docker - Docker daemon connectivity
    - _Requirements: 6.1, 6.2_

  - [x] 15.3 Write unit tests for monitoring
    - Test metric recording
    - Test health check logic
    - Test alert triggering
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 16. Implement internationalization and OpenClaw language integration
  - [x] 16.1 Add backend translation keys
    - Add aiIntegration keys to existing src/i18n/translations.py TRANSLATIONS dict
    - Add Chinese (zh) translations for all error messages and UI text
    - Add English (en) translations for all error messages and UI text
    - Follow existing key structure: 'aiIntegration.gateway.title'
    - _Requirements: 13.1, 13.3, 13.4, 13.5_
    - _Reuses: TranslationManager, existing TRANSLATIONS dict_

  - [x] 16.2 Create frontend translation files
    - Create frontend/src/locales/zh/aiIntegration.json
    - Create frontend/src/locales/en/aiIntegration.json
    - Add all UI labels and messages
    - Follow existing naming convention (camelCase namespace)
    - Ensure key structure consistency with other namespaces
    - _Requirements: 13.1, 13.3, 13.4, 13.5_
    - _Reuses: react-i18next setup, existing locale structure_

  - [x] 16.3 Integrate i18n in API responses
    - Use existing TranslationManager for error messages
    - Add Accept-Language header handling using existing middleware
    - Implement localized audit log display
    - _Requirements: 13.4, 13.5_
    - _Reuses: language_middleware, detect_language_from_request_

  - [x] 16.4 Implement OpenClaw language adapter
    - Create OpenClawLanguageAdapter class
    - Implement get_system_prompt_for_language for Chinese and English
    - Add inject_language_context to generate environment variables
    - Create language-specific system prompts with Chinese terminology
    - _Requirements: 13.1, 13.2, 13.3_
    - _Note: OpenClaw has no built-in i18n, using system prompt injection_

  - [x] 16.5 Implement OpenClaw response translator
    - Create OpenClawResponseTranslator class
    - Add translate_response using LLM for technical content
    - Implement localize_data_format using existing formatters
    - Preserve code blocks, file paths, and technical terms during translation
    - _Requirements: 13.3, 13.4_
    - _Reuses: src/i18n/formatters.py (format_date, format_number, format_currency)_

  - [x] 16.6 Add language support to SuperInsight skill
    - Update SuperInsight OpenClaw skill to detect user language
    - Add Accept-Language header to all API requests
    - Implement formatResponse with Chinese and English templates
    - Add locale-specific data formatting
    - _Requirements: 13.1, 13.3, 13.4_

  - [x] 16.7 Update gateway deployment with language settings
    - Add OPENCLAW_SYSTEM_PROMPT environment variable injection
    - Add OPENCLAW_USER_LANGUAGE from user profile
    - Add OPENCLAW_LOCALE configuration
    - Update docker-compose to pass language settings
    - _Requirements: 13.1, 13.2_

  - [x] 16.8 Write property test for localized error messages
    - **Property 38: Localized Error Messages**
    - **Validates: Requirements 13.4**

  - [x] 16.9 Write unit tests for i18n and OpenClaw language integration
    - Test language preference persistence
    - Test UI language switching
    - Test default language (Chinese)
    - Test integration with existing TranslationManager
    - Test OpenClaw system prompt generation for both languages
    - Test response translation and formatting
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Implement frontend dashboard
  - [x] 18.1 Create gateway management page
    - Build gateway list view with Ant Design table
    - Add gateway registration form
    - Implement configuration editor
    - Add deployment controls
    - Use react-i18next for translations
    - _Requirements: 2.1, 2.3, 2.4, 13.3_

  - [x] 18.2 Create monitoring dashboard
    - Build metrics visualization with charts
    - Add health status indicators
    - Implement real-time updates
    - Create alert notifications
    - _Requirements: 6.3, 6.4, 6.5_

  - [x] 18.3 Create audit log viewer
    - Build audit log table with filtering
    - Add search functionality
    - Implement export feature
    - Use localized display
    - _Requirements: 8.4, 13.5_

  - [x] 18.4 Write integration tests for frontend
    - Test gateway registration flow
    - Test configuration updates
    - Test monitoring dashboard
    - _Requirements: 2.1, 2.3, 6.5_

- [x] 19. Implement error handling and validation
  - [x] 19.1 Create error response middleware
    - Implement standardized error response format
    - Add localized error messages
    - Create error logging
    - Add request_id tracking
    - _Requirements: 3.6, 13.4_

  - [x] 19.2 Write property test for error response completeness
    - **Property 10: Error Response Completeness**
    - **Validates: Requirements 3.6**

  - [x] 19.3 Add input validation
    - Implement Pydantic schemas for all endpoints
    - Add configuration schema validation
    - Create custom validators
    - _Requirements: 2.3, 9.1_

- [x] 20. Implement security features
  - [x] 20.1 Add authentication middleware
    - Create JWT validation middleware
    - Implement API key authentication
    - Add rate limiting middleware
    - Create security event logging
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

  - [x] 20.2 Write property test for authentication failure rate limiting
    - **Property 22: Authentication Failure Rate Limiting**
    - **Validates: Requirements 7.5**

  - [x] 20.3 Implement credential rotation
    - Create rotate_credentials endpoint
    - Add zero-downtime rotation logic
    - Implement notification system
    - _Requirements: 7.4_

  - [x] 20.4 Add secret encryption
    - Implement AES-256-GCM encryption for secrets
    - Create key management system
    - Add decryption on-demand
    - _Requirements: 9.4_

  - [x] 20.5 Write property test for secret encryption
    - **Property 28: Secret Encryption**
    - **Validates: Requirements 9.4**

- [x] 21. Integration and wiring
  - [x] 21.1 Wire all services together
    - Register all routers in main FastAPI app
    - Configure dependency injection
    - Add middleware stack
    - Initialize monitoring
    - _Requirements: All_

  - [x] 21.2 Create database migrations
    - Generate Alembic migration scripts
    - Add upgrade and downgrade functions
    - Test migration on clean database
    - _Requirements: 2.1, 4.1, 8.1_

  - [x] 21.3 Update docker-compose.yml
    - Integrate ai-integration services
    - Add environment variables
    - Configure service dependencies
    - _Requirements: 1.1, 1.2_

  - [x] 21.4 Write end-to-end integration tests
    - Test complete gateway registration and deployment flow
    - Test data access with authentication and authorization
    - Test skill deployment and execution
    - Test audit logging and monitoring
    - _Requirements: All major requirements_

- [x] 22. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 23. Implement Workflow Designer service
  - [x] 23.1 Create WorkflowDesigner class
    - Implement parse_workflow_description using NLP
    - Add validate_workflow against datasets and permissions
    - Create execute_workflow with governed/raw data toggle
    - Implement compare_results for quality comparison
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 23.2 Create workflow API endpoints
    - POST /api/v1/ai-integration/workflows/parse - Parse natural language
    - POST /api/v1/ai-integration/workflows - Save workflow
    - GET /api/v1/ai-integration/workflows - List workflows
    - GET /api/v1/ai-integration/workflows/{id} - Get workflow details
    - POST /api/v1/ai-integration/workflows/{id}/execute - Execute workflow
    - POST /api/v1/ai-integration/workflows/{id}/compare - Compare results
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 23.3 Write unit tests for workflow designer
    - Test natural language parsing
    - Test workflow validation
    - Test execution with both data types
    - Test comparison logic
    - _Requirements: 14.1, 14.2, 14.3_

- [x] 24. Implement Quality Comparison service
  - [x] 24.1 Create QualityComparisonService class
    - Implement evaluate_quality using Ragas framework
    - Add compare_datasets for side-by-side comparison
    - Create generate_comparison_report with visualizations
    - Calculate completeness, accuracy, consistency metrics
    - _Requirements: 15.2, 15.3, 15.4, 15.5_

  - [x] 24.2 Integrate with existing Ragas quality system
    - Use existing quality evaluation infrastructure
    - Add comparison-specific metrics
    - Implement lineage tracking for governed data
    - _Requirements: 15.5, 15.6_

  - [x] 24.3 Write unit tests for quality comparison
    - Test quality metric calculation
    - Test comparison logic
    - Test report generation
    - _Requirements: 15.2, 15.3, 15.4_

- [x] 25. Enhance SuperInsight OpenClaw skill
  - [x] 25.1 Add workflow design capabilities to skill
    - Implement natural language workflow parsing
    - Add workflow execution commands
    - Create comparison result formatting for chat
    - Add error handling with user-friendly messages
    - _Requirements: 14.1, 14.2, 14.3, 14.5_

  - [x] 25.2 Create skill documentation
    - Write SKILL.md with examples
    - Document conversation patterns
    - Add troubleshooting guide
    - _Requirements: 14.1, 14.5_

  - [x] 25.3 Write integration tests for enhanced skill
    - Test workflow design conversation flow
    - Test execution and comparison
    - Test error scenarios
    - _Requirements: 14.1, 14.2, 14.5_

- [x] 26. Implement Workflow Playground frontend
  - [x] 26.1 Create WorkflowPlayground page component
    - Build three-panel layout (chat, workflow, results)
    - Implement ChatPanel with OpenClaw integration
    - Create WorkflowPanel with definition display
    - Build ResultsPanel with quality metrics
    - Add execution history panel
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

  - [x] 26.2 Implement real-time workflow generation
    - Connect chat to workflow parser API
    - Display workflow definition as it's generated
    - Add visual workflow editor
    - Implement data source toggle (governed/raw)
    - _Requirements: 16.2, 16.3_

  - [x] 26.3 Add execution and comparison features
    - Implement "Execute" button with loading states
    - Display results with quality metrics
    - Show side-by-side comparison
    - Add "Save to Production" functionality
    - _Requirements: 16.4, 16.5, 16.6_

  - [x] 26.4 Write component tests for playground
    - Test chat interaction
    - Test workflow display
    - Test execution flow
    - Test save functionality
    - _Requirements: 16.1, 16.2, 16.4, 16.6_

- [x] 27. Implement Quality Comparison Dashboard frontend
  - [x] 27.1 Create QualityComparison page component
    - Build split-view layout
    - Implement DataPanel for governed data
    - Implement DataPanel for raw data
    - Create MetricsComparison component
    - Add visual difference highlighting
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [x] 27.2 Add quality metrics visualizations
    - Implement radar chart for quality metrics
    - Create completeness/accuracy bar charts
    - Add lineage visualization
    - Implement color-coded difference indicators
    - _Requirements: 15.3, 15.4, 15.6_

  - [x] 27.3 Add export and sharing features
    - Implement PDF export for comparison report
    - Add Excel export for detailed data
    - Create shareable comparison links
    - Add email sharing functionality
    - _Requirements: 15.1, 15.3_

  - [x] 27.4 Write component tests for comparison dashboard
    - Test split-view rendering
    - Test metrics visualization
    - Test export functionality
    - Test difference highlighting
    - _Requirements: 15.1, 15.3, 15.4_

- [x] 28. Implement Workflow Library frontend
  - [x] 28.1 Create WorkflowLibrary page component
    - Build workflow list with Ant Design table
    - Add filtering and search functionality
    - Implement quick execute button
    - Create workflow detail modal
    - Add clone and modify features
    - _Requirements: 16.5, 16.6_

  - [x] 28.2 Add workflow templates
    - Create template gallery
    - Implement template preview
    - Add "Use Template" functionality
    - Create custom template saving
    - _Requirements: 16.1, 16.6_

  - [x] 28.3 Write component tests for workflow library
    - Test list rendering
    - Test filtering and search
    - Test execute functionality
    - Test template usage
    - _Requirements: 16.5, 16.6_

- [x] 29. Add workflow-related translations
  - [x] 29.1 Update backend translation files
    - Add workflow-related keys to zh/ai_integration.json
    - Add workflow-related keys to en/ai_integration.json
    - Add quality comparison keys
    - Add error messages for workflow operations
    - _Requirements: 13.1, 13.3, 13.4_

  - [x] 29.2 Update frontend translation files
    - Add workflow playground keys to zh/aiIntegration.json
    - Add workflow playground keys to en/aiIntegration.json
    - Add quality comparison dashboard keys
    - Add workflow library keys
    - _Requirements: 13.1, 13.3_

  - [x] 29.3 Write i18n tests for workflow features
    - Test workflow-related translations
    - Test language switching in new pages
    - Test error message localization
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 30. Integration testing for workflow features
  - [x] 30.1 Write end-to-end workflow tests
    - Test complete workflow design flow via OpenClaw
    - Test workflow execution with both data types
    - Test quality comparison generation
    - Test workflow saving and retrieval
    - _Requirements: 14.1-14.6, 15.1-15.6, 16.1-16.6_

  - [x] 30.2 Write frontend integration tests
    - Test Workflow Playground complete flow
    - Test Quality Comparison Dashboard
    - Test Workflow Library operations
    - Test cross-component interactions
    - _Requirements: 15.1-15.6, 16.1-16.6_

- [x] 31. Final checkpoint - Ensure all workflow features work
  - Ensure all tests pass, ask the user if questions arise.
  - Test complete user journey from design to comparison
  - Verify quality metrics are accurate
  - Confirm OpenClaw integration works end-to-end

- [x] 32. Integrate existing LLM system with OpenClaw
  - [x] 32.1 Create OpenClawLLMBridge class
    - Implement get_openclaw_env_vars to map LLMConfig to environment variables
    - Add _map_provider to convert LLMMethod to OpenClaw provider names
    - Create handle_llm_request using existing LLMSwitcher
    - Implement monitor_usage extending existing log_usage
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_
    - _Reuses: LLMConfigManager, LLMSwitcher, ChinaLLMProvider_

  - [x] 32.2 Create gateway-LLM linking API endpoints
    - POST /api/v1/ai-integration/gateways/{id}/llm-config - Link gateway to LLM config
    - GET /api/v1/ai-integration/gateways/{id}/llm-status - Get LLM status
    - _Requirements: 17.3, 17.4_
    - _Reuses: Existing admin LLM config endpoints_

  - [x] 32.3 Write unit tests for LLM bridge
    - Test environment variable mapping
    - Test provider name conversion
    - Test LLM request handling
    - Test usage monitoring
    - _Requirements: 17.1, 17.4, 17.5_

- [x] 33. Extend LLM monitoring for OpenClaw
  - [x] 33.1 Create OpenClawLLMMonitor class
    - Implement record_gateway_usage extending existing audit service
    - Add get_gateway_stats querying existing audit logs
    - Create cost estimation using existing token tracking
    - _Requirements: 19.1, 19.2, 19.6_
    - _Reuses: HealthMonitor, AuditService from src/ai/llm/_

  - [x] 33.2 Add OpenClaw-specific Prometheus metrics
    - Extend llm_requests_total with gateway_id and skill_name labels
    - Extend llm_tokens_total with gateway_id and skill_name labels
    - Add llm_cost_total{gateway_id, skill_name, provider} metric
    - Add openclaw_skill_executions_total{gateway_id, skill_name} metric
    - _Requirements: 19.1_

  - [x] 33.3 Write unit tests for OpenClaw monitoring
    - Test gateway usage recording
    - Test stats aggregation
    - Test cost calculation
    - _Requirements: 19.1, 19.2_

- [x] 34. Update gateway deployment with LLM config
  - [x] 34.1 Update gateway deployment script
    - Fetch LLM config using existing LLMConfigManager
    - Generate OpenClaw environment variables via OpenClawLLMBridge
    - Inject LLM settings into docker-compose environment
    - _Requirements: 17.4, 17.5_
    - _Reuses: Existing hot-reload functionality_

  - [x] 34.2 Update docker-compose configuration
    - Add LLM environment variable placeholders
    - Configure network access to existing Ollama service
    - Link to existing LLM services (ollama, docker-llm)
    - _Requirements: 17.1, 17.4_

  - [x] 34.3 Write integration tests for LLM deployment
    - Test OpenClaw with different LLM providers (reuse existing configs)
    - Test hot-reload using existing LLMConfigManager.hot_reload
    - Test failover using existing LLMSwitcher fallback
    - _Requirements: 17.4, 17.5, 18.3_

- [x] 35. Create LLM configuration frontend for OpenClaw
  - [x] 35.1 Add gateway-LLM linking UI
    - Add LLM config selector to gateway registration form
    - Reuse existing LLM provider list from admin API
    - Show current LLM status in gateway details
    - Add "Test LLM Connection" button
    - _Requirements: 17.3, 17.4_
    - _Reuses: Existing admin LLM config UI components_

  - [x] 35.2 Create OpenClaw LLM monitoring dashboard
    - Build usage statistics charts for gateways
    - Add cost breakdown by gateway and skill
    - Show provider health status from existing health checks
    - Display real-time metrics from Prometheus
    - _Requirements: 19.2, 19.4_
    - _Reuses: Existing LLM monitoring components_

  - [x] 35.3 Write component tests for LLM UI
    - Test gateway-LLM linking flow
    - Test monitoring dashboard
    - _Requirements: 17.3, 19.2_

- [x] 36. Add LLM-related translations
  - [x] 36.1 Extend existing LLM translation keys
    - Add OpenClaw-specific keys to existing zh/llm.json
    - Add OpenClaw-specific keys to existing en/llm.json
    - Add gateway-LLM linking keys
    - Add monitoring dashboard keys
    - _Requirements: 13.1, 13.3, 13.4_
    - _Reuses: Existing llm.provider.*, llm.config.*, llm.error.* keys_

  - [x] 36.2 Write i18n tests for LLM features
    - Test OpenClaw-specific translations
    - Test language switching in LLM pages
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 37. Final integration testing for LLM features
  - [x] 37.1 Write end-to-end LLM tests
    - Test gateway with existing LLM providers (OpenAI, Qwen, Zhipu, Ollama)
    - Test automatic failover using existing LLMSwitcher
    - Test cost tracking with existing usage logs
    - Test hot-reload using existing config manager
    - _Requirements: 17.1-17.6, 18.1-18.6, 19.1-19.6_
    - _Reuses: All existing LLM infrastructure_

  - [x] 37.2 Write performance tests for LLM
    - Test LLM request latency through OpenClaw
    - Test concurrent request handling
    - Test failover performance
    - _Requirements: 18.3, 19.1, 19.5_

- [x] 39. Final checkpoint - Complete system verification
  - Ensure all tests pass, ask the user if questions arise.
  - Test complete user journey: gateway setup → LLM config → workflow design → execution
  - Verify LLM failover works correctly
  - Confirm cost tracking is accurate
  - Test with both cloud and private LLM providers

## Notes

- Tasks marked with `*` are optional property-based and unit tests
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end flows
- All code should follow project conventions: functions 20-40 lines, classes 200-400 lines
- Use卫语句 (guard clauses) for early returns
- Follow existing project structure: `src/ai_integration/` for backend code
- Use existing i18n infrastructure: TranslationManager for backend, react-i18next for frontend
- All API endpoints must include authentication, authorization, and audit logging
- All database queries must include tenant filtering for multi-tenant isolation

## New Feature Highlights

### Conversational Workflow Design (Tasks 23-25)
- Users can design data workflows through natural language conversations with OpenClaw
- Workflows are automatically parsed, validated, and executed
- Supports comparison between governed and raw data results
- Provides quality metrics and improvement percentages

### Quality Comparison Dashboard (Tasks 24, 27)
- Side-by-side visualization of governed vs. raw data results
- Quality metrics including completeness, accuracy, consistency
- Visual difference highlighting with color coding
- Lineage visualization showing governance steps applied
- Export functionality for reports and detailed data

### Workflow Playground (Task 26)
- Interactive three-panel interface: chat, workflow definition, results
- Real-time workflow generation from natural language
- Toggle between governed and raw data modes
- Execution history with comparison metrics
- Save workflows to production library

### Workflow Library (Task 28)
- Centralized repository of saved workflows
- Quick execute, clone, and modify capabilities
- Workflow templates gallery
- Sharing and collaboration features

### Enhanced OpenClaw Skill (Task 25)
- Workflow design capabilities via conversational interface
- Automatic quality comparison and reporting
- User-friendly result formatting for different channels
- Comprehensive error handling with suggestions

## Implementation Priority

**Phase 1 (Core Infrastructure)**: Tasks 1-11
**Phase 2 (OpenClaw Integration)**: Tasks 12-15
**Phase 3 (Frontend & i18n)**: Tasks 16-22
**Phase 4 (Workflow Features)**: Tasks 23-31
**Phase 5 (LLM Configuration)**: Tasks 32-39

The workflow features (Phase 4) build on the foundation established in Phases 1-3 and demonstrate the value of AI-friendly data through direct comparison.

The LLM configuration features (Phase 5) provide flexible model management, supporting both cloud providers and private deployments with automatic failover and cost tracking.
