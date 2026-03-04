# Implementation Plan: LLM Application Binding System

## Overview

This plan implements a flexible many-to-many LLM-application binding system with priority-based failover, hot configuration reload, and backward compatibility. The implementation follows a bottom-up approach: database → services → API → frontend → testing.

## Tasks

- [x] 1. Database Layer Setup
  - [x] 1.1 Create Alembic migration script for three tables
    - Create `llm_configs` table with encryption support
    - Create `llm_applications` table with initial data
    - Create `llm_application_bindings` table with constraints
    - Add indexes: `idx_llm_configs_tenant_active`, `idx_bindings_app_priority`, `idx_bindings_active`
    - Add constraints: `uq_app_priority`, `ck_priority_range`, `ck_max_retries_range`, `ck_timeout_positive`
    - _Requirements: 1.1, 2.1, 3.1, 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [x] 1.2 Insert initial application data in migration
    - Insert 6 applications: structuring, knowledge_graph, ai_assistant, semantic_analysis, rag_agent, text_to_sql
    - Set appropriate descriptions and usage patterns
    - _Requirements: 2.2, 16.3_
  
  - [x] 1.3 Test migration up and down
    - Run `alembic upgrade head` and verify tables created
    - Run `alembic downgrade -1` and verify tables dropped
    - Verify foreign key constraints work correctly
    - _Requirements: 11.6_

- [x] 2. Core Services Layer
  - [x] 2.1 Implement EncryptionService for API key protection
    - Implement AES-256-GCM encryption with `encrypt()` method
    - Implement decryption with `decrypt()` method
    - Load encryption key from `LLM_ENCRYPTION_KEY` environment variable
    - _Requirements: 1.3, 4.3, 12.1, 12.2_
  
  - [x] 2.2 Write property test for EncryptionService
    - **Property 2: API Key Encryption Round-Trip**
    - **Validates: Requirements 1.3, 4.3, 12.1**
  
  - [x] 2.3 Implement CacheManager with two-tier caching
    - Implement local memory cache with TTL (300s) and LRU eviction
    - Implement optional Redis cache integration
    - Implement `get()`, `set()`, and `invalidate()` methods
    - Implement Redis pub/sub for cache invalidation broadcasting
    - _Requirements: 4.4, 4.5, 6.4, 6.5, 15.4, 15.5, 17.6, 17.7, 17.8, 17.9_
  
  - [x] 2.4 Write property test for cache TTL expiration
    - **Property 10: Cache TTL Expiration**
    - **Validates: Requirements 4.4, 4.5**
  
  - [x] 2.5 Implement ApplicationLLMManager service
    - Implement `get_llm_config()` with hierarchy resolution (app → tenant → global → env)
    - Implement `_load_from_database()` with priority ordering
    - Implement `_load_from_env()` for backward compatibility
    - Implement `_to_cloud_config()` with decryption
    - Implement `invalidate_cache()` with broadcast support
    - _Requirements: 4.1, 4.2, 7.1, 7.3, 7.5, 17.1, 17.2, 18.4, 18.6, 18.7_
  
  - [x] 2.6 Write property test for configuration loading hierarchy
    - **Property 9: Configuration Loading Hierarchy**
    - **Validates: Requirements 4.2, 7.1, 7.3, 7.5, 17.1, 18.4**
  
  - [x] 2.7 Implement failover logic in ApplicationLLMManager
    - Implement `execute_with_failover()` with retry and timeout
    - Implement `_execute_with_retry()` with exponential backoff
    - Add failover logging for all events
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 13.4_
  
  - [x] 2.8 Write property tests for failover behavior
    - **Property 11: Retry With Exponential Backoff**
    - **Property 12: Failover On Exhausted Retries**
    - **Property 13: Timeout Triggers Failover**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 3. Checkpoint - Core services complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Database Models and Schemas
  - [x] 4.1 Create SQLAlchemy models
    - Create `LLMConfig` model with relationships and indexes
    - Create `LLMApplication` model with relationships
    - Create `LLMApplicationBinding` model with constraints
    - _Requirements: 1.1, 2.1, 3.1_
  
  - [x] 4.2 Write property test for binding constraints
    - **Property 5: Binding Referential Integrity**
    - **Property 6: Priority Uniqueness Per Application**
    - **Property 7: Priority Range Validation**
    - **Validates: Requirements 3.2, 3.3, 3.4, 14.3**
  
  - [x] 4.3 Create Pydantic schemas for API
    - Create `LLMConfigCreate`, `LLMConfigUpdate`, `LLMConfigResponse`
    - Create `LLMBindingCreate`, `LLMBindingUpdate`, `LLMBindingResponse`
    - Create `ApplicationResponse`
    - Add field validation with Pydantic validators
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [x] 4.4 Write property test for input validation
    - **Property 1: Provider Validation**
    - **Property 17: Input Validation Completeness**
    - **Validates: Requirements 1.2, 14.1, 14.2, 14.3, 14.4, 14.5**

- [-] 5. API Layer Implementation
  - [x] 5.1 Implement LLM configuration management endpoints
    - POST /api/llm-configs - Create configuration
    - GET /api/llm-configs - List configurations with filters
    - GET /api/llm-configs/{id} - Get single configuration
    - PUT /api/llm-configs/{id} - Update configuration
    - DELETE /api/llm-configs/{id} - Delete with binding check
    - POST /api/llm-configs/{id}/test - Test connectivity
    - _Requirements: 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.10_
  
  - [x] 5.2 Write property test for config deletion with bindings
    - **Property 3: Binding Prevents Config Deletion**
    - **Validates: Requirements 1.5**
  
  - [x] 5.3 Implement application management endpoints
    - GET /api/applications - List all applications
    - GET /api/applications/{code} - Get application by code
    - _Requirements: 8.5_
  
  - [x] 5.4 Write property test for application code uniqueness
    - **Property 4: Application Code Uniqueness**
    - **Validates: Requirements 2.3**
  
  - [x] 5.5 Implement binding management endpoints
    - POST /api/llm-bindings - Create binding
    - GET /api/llm-bindings - List bindings with filters
    - GET /api/llm-bindings/{id} - Get single binding
    - PUT /api/llm-bindings/{id} - Update binding
    - DELETE /api/llm-bindings/{id} - Delete binding
    - _Requirements: 3.6, 8.6, 8.7, 8.8, 8.9_
  
  - [x] 5.6 Write property test for bindings ordered by priority
    - **Property 8: Bindings Ordered By Priority**
    - **Validates: Requirements 3.5, 4.1**
  
  - [x] 5.7 Add authentication and authorization middleware
    - Require ADMIN role for create/update/delete operations
    - Require TECHNICAL_EXPERT or ADMIN for read operations
    - Add audit logging for all configuration access
    - _Requirements: 12.3, 12.4, 12.5_
  
  - [x] 5.8 Write unit tests for API endpoints
    - Test successful CRUD operations
    - Test validation error responses
    - Test authorization checks
    - Test cache invalidation triggers

- [x] 6. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend State Management
  - [x] 7.1 Create Zustand store for LLM configuration
    - Define `LLMConfigStore` interface with state and actions
    - Implement `fetchConfigs`, `createConfig`, `updateConfig`, `deleteConfig`
    - Implement `testConnection` action
    - Implement `fetchApplications`, `fetchBindings` actions
    - Implement `createBinding`, `updateBinding`, `deleteBinding` actions
    - Implement `reorderBindings` action for drag-and-drop
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.8_

- [x] 8. Frontend Internationalization
  - [x] 8.1 Create Chinese translation file
    - Create `frontend/src/locales/zh/llmConfig.json`
    - Add translations for: providers, applications, form labels, actions, messages
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.10_
  
  - [x] 8.2 Create English translation file
    - Create `frontend/src/locales/en/llmConfig.json`
    - Add translations matching Chinese file structure
    - Ensure key synchronization with Chinese file
    - _Requirements: 10.1, 10.2, 10.3, 10.11_
  
  - [x] 8.3 Write test for translation key completeness
    - Verify all keys exist in both zh and en files
    - Verify no missing translations
    - _Requirements: 10.11_

- [x] 9. Frontend Components Implementation
  - [x] 9.1 Create LLMConfigList component
    - Display configurations in card layout with provider icons
    - Show name, provider, model, status badge
    - Add Edit, Delete, Test Connection action buttons
    - Use `useTranslation('llmConfig')` hook
    - Wrap all user-visible text with `{t('key')}` for JSX children
    - Use `title={t('key')}` for HTML attributes
    - _Requirements: 9.1, 10.6, 10.7, 10.8, 10.9_
  
  - [x] 9.2 Create LLMConfigForm component
    - Add form fields: name, provider, api_key, base_url, model_name, parameters
    - Implement form validation with error messages
    - Support create and edit modes
    - Use Ant Design Form components
    - Apply i18n to all labels, placeholders, and error messages
    - _Requirements: 9.2, 10.5, 10.7, 10.8, 10.9_
  
  - [x] 9.3 Create ApplicationBindings component
    - Display applications with their bound LLMs
    - Show bindings in priority order (1st, 2nd, 3rd)
    - Implement drag-and-drop for priority reordering
    - Add "Add Binding" button with modal form
    - Apply i18n to all text elements
    - _Requirements: 9.3, 9.5, 9.8, 10.7, 10.8, 10.9_
  
  - [x] 9.4 Create BindingForm component
    - Add form fields: application, LLM config, priority, max_retries, timeout
    - Implement validation for priority (1-99), retries (0-10), timeout (>0)
    - Support create and edit modes
    - Apply i18n to form labels and validation messages
    - _Requirements: 9.4, 10.7, 10.8, 10.9_
  
  - [x] 9.5 Create TestConnectionButton component
    - Implement connection test with loading state
    - Display success/failure feedback with translated messages
    - Show latency on success
    - _Requirements: 9.6, 10.5_
  
  - [x] 9.6 Write component tests for frontend
    - Test LLMConfigList rendering and actions
    - Test form validation and submission
    - Test drag-and-drop reordering
    - Test connection test button

- [x] 10. Backward Compatibility Integration
  - [x] 10.1 Upgrade _load_cloud_config() function
    - Add `application_code` parameter with default "structuring"
    - Call `ApplicationLLMManager.get_llm_config()` first
    - Fall back to environment variables if no database config
    - Maintain existing function signature for compatibility
    - _Requirements: 7.2, 7.3, 7.6, 7.7, 7.8_
  
  - [x] 10.2 Write integration test for backward compatibility
    - Test with database bindings present
    - Test with only environment variables
    - Test with both (database should win)
    - Verify zero code changes needed in existing modules
    - _Requirements: 7.1, 7.4, 7.5, 7.8_

- [x] 11. Checkpoint - Integration complete
  - Ensure all tests pass, ask the user if questions arise.

- [-] 12. Property-Based Testing
  - [x] 12.1 Write property test for cache invalidation
    - **Property 15: Cache Invalidation On Configuration Change**
    - **Property 16: Cache Reload After Invalidation**
    - **Validates: Requirements 6.1, 6.2, 6.3, 17.3, 17.4, 17.5**
  
  - [x] 12.2 Write property test for failover logging
    - **Property 14: Failover Logging**
    - **Validates: Requirements 5.5, 13.4**
  
  - [x] 12.3 Write property test for configuration override priority
    - **Property 18: Configuration Override Priority**
    - **Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8**

- [x] 13. Integration and End-to-End Testing
  - [x] 13.1 Write integration test for complete failover flow
    - Create application with 3 LLM bindings
    - Simulate primary LLM failure
    - Verify automatic failover to secondary
    - Verify logging of failover events
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 13.2 Write integration test for hot reload
    - Load configuration into cache
    - Update configuration via API
    - Verify cache invalidation
    - Verify next request loads new configuration
    - Test with and without Redis
    - _Requirements: 6.1, 6.2, 6.3, 17.3, 17.4, 17.5_
  
  - [x] 13.3 Write integration test for multi-tenant configuration
    - Create global, tenant, and application-level configs
    - Verify correct hierarchy resolution
    - Test override behavior
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.9, 18.10_
  
  - [x] 13.4 Write end-to-end test for frontend workflows
    - Test create LLM configuration workflow
    - Test edit and delete workflows
    - Test binding creation and reordering
    - Test connection testing
    - Verify i18n works in both languages

- [x] 14. Deployment Preparation
  - [x] 14.1 Create environment variable documentation
    - Document `LLM_ENCRYPTION_KEY` requirement (32 bytes, base64)
    - Document optional Redis configuration
    - Document backward-compatible environment variables
    - _Requirements: 12.2_
  
  - [x] 14.2 Add monitoring and metrics
    - Implement metrics for LLM request count per application
    - Implement metrics for success rate and response time
    - Implement cache hit rate monitoring
    - Add alerts for cache hit rate < 90%
    - _Requirements: 13.1, 13.2, 13.3, 13.5, 15.1, 15.2_
  
  - [x] 14.3 Performance testing
    - Test with 1000 concurrent requests
    - Verify cache retrieval < 1ms
    - Verify database retrieval < 50ms
    - Verify memory usage < 100MB
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

- [x] 15. Final checkpoint - System ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from design document
- Integration tests verify end-to-end workflows
- Backward compatibility ensures zero code changes in existing modules
- Hot reload enables zero-downtime configuration updates
