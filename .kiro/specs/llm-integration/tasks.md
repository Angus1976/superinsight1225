# Implementation Plan: LLM Integration

## Overview

This implementation plan breaks down the LLM Integration module into discrete, testable tasks. The approach follows a bottom-up strategy: building core abstractions first, then provider implementations, then integration layers, and finally the frontend interface.

**Current Status**: The LLM integration module has significant existing implementation. Core abstractions, provider implementations, configuration management, and database models already exist. This task list focuses on completing missing features and aligning with the design specification.

## Tasks

- [x] 1. Set up project structure and base abstractions (Est: 2h)
  - ✅ `src/ai/llm_switcher.py` - LLMProvider abstract class exists
  - ✅ `src/ai/llm_schemas.py` - Enums and schemas exist
  - ✅ Exception classes exist (LLMError, LLMErrorCode)
  - ✅ Logging configuration in place
  - _Requirements: 1.1, 1.2_

- [x] 1.1 Write property test for provider type support
  - **Property 1: Provider Type Support**
  - **Validates: Requirements 1.1, 1.2**

- [x] 2. Implement database models and migrations (Est: 2h)
  - [x] 2.1 Create `LLMProviderConfig` SQLAlchemy model
    - ✅ `LLMConfiguration` model exists in `src/models/llm_configuration.py`
    - ✅ Indexes for tenant_id, is_active, default_method exist
    - _Requirements: 1.3, 1.4, 1.5_
  
  - [x] 2.2 Create `LLMRequestLog` SQLAlchemy model
    - ✅ `LLMUsageLog` model exists in `src/models/llm_configuration.py`
    - ✅ Indexes for performance exist
    - _Requirements: 3.5, 7.5_
  
  - [x] 2.3 Create `LLMHealthStatus` SQLAlchemy model
    - ⚠️ Model does not exist yet - needs to be created
    - Define table schema for health tracking
    - Add unique constraint on provider_id
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 2.4 Create Alembic migration script
    - Generate migration for LLMHealthStatus table
    - Test migration up and down
    - _Requirements: All database-related requirements_

- [x] 2.5 Write property test for configuration validation
  - **Property 2: Configuration Validation**
  - **Validates: Requirements 1.3, 6.4**

- [x] 3. Implement API schemas (Est: 1h)
  - ✅ Pydantic schemas exist in `src/ai/llm_schemas.py`
  - ✅ `LLMConfig`, `GenerateOptions`, `LLMResponse`, `EmbeddingResponse` defined
  - ✅ `HealthStatus`, `MethodInfo` defined
  - ✅ Validation rules and field constraints in place
  - _Requirements: 1.3, 6.2, 6.4_

- [x] 3.1 Write property test for provider metadata completeness
  - **Property 3: Provider Metadata Completeness**
  - **Validates: Requirements 1.4**

- [x] 4. Implement encryption service (Est: 2h)
  - [x] 4.1 API key encryption
    - ✅ Encryption handled by existing `src/security/encryption.py`
    - ✅ `LLMConfigManager` uses `mask_api_key` utility
    - ✅ API keys stored encrypted in database JSONB config
    - _Requirements: 1.5, 9.1_
  
  - [x] 4.2 Write property test for API key encryption round-trip
    - **Property 4: API Key Encryption Round-Trip**
    - **Validates: Requirements 1.5, 9.1**

- [x] 5. Implement Provider Manager (Est: 4h)
  - [x] 5.1 Provider Manager implementation
    - ✅ `LLMConfigManager` exists in `src/ai/llm_config_manager.py`
    - ✅ Implements get_config, save_config, delete_config with validation
    - ✅ Uses asyncio.Lock for thread safety
    - ✅ Redis caching and hot reload support
    - ✅ Configuration change watchers
    - _Requirements: 1.3, 1.4, 3.1, 6.1, 6.4, 6.5_
  
  - [x] 5.2 Write property test for deployment mode preservation
    - **Property 5: Deployment Mode Preservation**
    - **Validates: Requirements 2.4**
  
  - [x] 5.3 Write property test for active provider deletion prevention
    - **Property 16: Active Provider Deletion Prevention**
    - **Validates: Requirements 6.5**

- [x] 6. Implement provider implementations (Est: 6h)
  - [x] 6.1 OpenAI provider
    - ✅ `CloudLLMProvider` exists in `src/ai/llm_cloud.py`
    - ✅ Supports OpenAI and Azure OpenAI
    - ✅ Implements generate, stream_generate, embed, health_check
    - ✅ Error handling and rate limit detection
    - _Requirements: 1.1, 2.3_
  
  - [x] 6.2 Qwen provider
    - ✅ `ChinaLLMProvider` exists in `src/ai/china_llm_adapter.py`
    - ✅ Supports Qwen, Zhipu, Baidu, Hunyuan
    - ✅ Uses run_in_executor for sync SDK calls
    - _Requirements: 1.2, 2.3_
  
  - [x] 6.3 Zhipu provider
    - ✅ Included in `ChinaLLMProvider`
    - _Requirements: 1.2, 2.3_
  
  - [x] 6.4 Ollama provider
    - ✅ `LocalLLMProvider` exists in `src/ai/llm_docker.py`
    - ✅ Implements all required methods
    - ✅ Uses httpx AsyncClient for Ollama API
    - _Requirements: 1.2, 2.1, 2.5_
  
  - [x] 6.5 Write unit tests for each provider implementation
    - Test generate method with mock responses
    - Test health_check with success and failure scenarios
    - Test validate_config with valid and invalid configs
    - _Requirements: 1.1, 1.2, 2.1, 2.3_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Enhance LLM Switcher with failover (Est: 3h)
  - [x] 8.1 Add explicit failover logic to LLMSwitcher
    - ✅ `LLMSwitcher` exists in `src/ai/llm_switcher.py`
    - ✅ Implements generate, stream_generate, embed
    - ✅ Provider switching and method management
    - ✅ Usage statistics tracking
    - ⚠️ Missing: Explicit fallback provider configuration
    - ⚠️ Missing: Automatic failover on primary failure
    - ⚠️ Missing: Exponential backoff retry wrapper
    - Implement `set_fallback_provider` method
    - Add failover logic in generate method
    - Add exponential backoff retry with 3 attempts
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 8.2 Write property test for provider switching validation
    - **Property 6: Provider Switching Validation**
    - **Validates: Requirements 3.2**
  
  - [x] 8.3 Write property test for automatic failover
    - **Property 7: Automatic Failover**
    - **Validates: Requirements 3.3, 4.2**
  
  - [x] 8.4 Write property test for request context preservation
    - **Property 8: Request Context Preservation**
    - **Validates: Requirements 3.4**
  
  - [x] 8.5 Write property test for usage statistics tracking
    - **Property 9: Usage Statistics Tracking**
    - **Validates: Requirements 3.5**
  
  - [x] 8.6 Write property test for exponential backoff retry
    - **Property 10: Exponential Backoff Retry**
    - **Validates: Requirements 4.1**
  
  - [x] 8.7 Write property test for comprehensive error reporting
    - **Property 11: Comprehensive Error Reporting**
    - **Validates: Requirements 4.3**
  
  - [x] 8.8 Write property test for timeout enforcement
    - **Property 12: Timeout Enforcement**
    - **Validates: Requirements 4.4**
  
  - [x] 8.9 Write property test for rate limit handling
    - **Property 13: Rate Limit Handling**
    - **Validates: Requirements 4.5**

- [x] 9. Implement Health Monitor (Est: 3h)
  - [x] 9.1 Create `src/ai/llm/health_monitor.py`
    - Implement `HealthMonitor` class
    - Implement `start` and `stop` methods
    - Implement `_monitor_loop` with 60-second interval
    - Implement `_update_health_status` with alert triggering
    - Implement `get_health_status` and `get_healthy_providers`
    - Integrate with Prometheus metrics
    - Store health status in LLMHealthStatus database table
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 9.2 Write property test for health check scheduling
    - **Property 14: Health Check Scheduling**
    - **Validates: Requirements 5.1**
  
  - [x] 9.3 Write property test for health status management
    - **Property 15: Health Status Management**
    - **Validates: Requirements 5.2, 5.3, 5.4**

- [x] 10. Verify and enhance caching layer (Est: 1h)
  - [x] 10.1 Verify response caching in LLMSwitcher
    - ✅ Redis caching exists in `LLMConfigManager` for config
    - ⚠️ Need to verify response caching in `LLMSwitcher.generate()`
    - Ensure cache key generation from prompt and parameters
    - Verify TTL is set to 1 hour (3600 seconds)
    - Ensure cache misses are handled gracefully
    - _Requirements: 10.2_
  
  - [x] 10.2 Write property test for response caching round-trip
    - **Property 28: Response Caching Round-Trip**
    - **Validates: Requirements 10.2**

- [x] 11. Implement request batching (Est: 3h)
  - [x] 11.1 Review and align batch_processor.py with design
    - ⚠️ `src/ai/batch_processor.py` exists but may not match design spec
    - Review existing implementation
    - Align with design: group compatible requests by provider
    - Implement async batch processing with progress tracking
    - _Requirements: 10.1, 10.5_
  
  - [x] 11.2 Write property test for request batching
    - **Property 27: Request Batching**
    - **Validates: Requirements 10.1**
  
  - [x] 11.3 Write property test for async progress tracking
    - **Property 30: Async Progress Tracking**
    - **Validates: Requirements 10.5**

- [x] 12. Implement rate limiting (Est: 2h)
  - [x] 12.1 Create `src/ai/llm/rate_limiter.py`
    - Implement token bucket or sliding window rate limiter
    - Configure per-provider rate limits
    - Integrate with switcher
    - _Requirements: 10.3_
  
  - [x] 12.2 Write property test for rate limiting
    - **Property 29: Rate Limiting**
    - **Validates: Requirements 10.3**

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Review and enhance API endpoints (Est: 2h)
  - [x] 14.1 Review existing LLM API endpoints in `src/api/admin.py`
    - ✅ Basic CRUD endpoints exist for LLM config
    - ✅ GET `/admin/config/llm` - List configs
    - ✅ GET `/admin/config/llm/{id}` - Get config
    - ✅ POST `/admin/config/llm` - Create config
    - ✅ PUT `/admin/config/llm/{id}` - Update config
    - ✅ DELETE `/admin/config/llm/{id}` - Delete config
    - ✅ POST `/admin/config/llm/{id}/test` - Test connection
    - ⚠️ Missing: POST `/api/v1/llm/generate` - Generate completion endpoint
    - ⚠️ Missing: GET `/api/v1/llm/health` - Health status endpoint
    - ⚠️ Missing: POST `/api/v1/llm/providers/{id}/activate` - Set active provider
    - Add missing endpoints
    - Ensure authentication and authorization checks
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 9.3_
  
  - [x] 14.2 Write property test for pre-annotation routing
    - **Property 17: Pre-Annotation Routing**
    - **Validates: Requirements 7.1**
  
  - [x] 14.3 Write property test for authorization enforcement
    - **Property 25: Authorization Enforcement**
    - **Validates: Requirements 9.3**

- [x] 15. Implement pre-annotation integration (Est: 3h)
  - [x] 15.1 Review existing pre-annotation in `src/ai/pre_annotation.py`
    - ⚠️ File exists but may not be aligned with LLM integration design
    - Review and align with design spec
    - Implement pre-annotation request handler using LLMSwitcher
    - Parse LLM responses into annotation schema
    - Handle errors gracefully without blocking manual annotation
    - Store annotations with confidence scores
    - Track accuracy metrics
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 15.2 Write property test for response schema compliance
    - **Property 18: Response Schema Compliance**
    - **Validates: Requirements 7.2**
  
  - [x] 15.3 Write property test for pre-annotation error isolation
    - **Property 19: Pre-Annotation Error Isolation**
    - **Validates: Requirements 7.3**
  
  - [x] 15.4 Write property test for confidence score storage
    - **Property 20: Confidence Score Storage**
    - **Validates: Requirements 7.4**

- [x] 16. Implement audit logging (Est: 2h)
  - [x] 16.1 Verify configuration change audit logging
    - ✅ `LLMUsageLog` exists for request logging
    - ⚠️ Need to verify audit logging for config changes
    - Log all create, update, delete operations
    - Include user ID, timestamp, and change details
    - Integrate with existing audit system
    - _Requirements: 9.4_
  
  - [x] 16.2 Implement log sanitization
    - Remove API keys from logs
    - Remove PII patterns from logs
    - Test with various sensitive data patterns
    - _Requirements: 9.2_
  
  - [x] 16.3 Write property test for log sanitization
    - **Property 24: Log Sanitization**
    - **Validates: Requirements 9.2**
  
  - [x] 16.4 Write property test for configuration audit logging
    - **Property 26: Configuration Audit Logging**
    - **Validates: Requirements 9.4**

- [x] 17. Verify internationalization (Est: 1h)
  - [x] 17.1 Verify i18n keys in `src/i18n/translations.py`
    - ⚠️ Need to verify LLM-specific i18n keys exist
    - Add Chinese (zh-CN) translations for all UI strings
    - Add English (en-US) translations for all UI strings
    - Add error message keys
    - Add provider name translations
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 17.2 Write property test for internationalization completeness
    - **Property 21: Internationalization Completeness**
    - **Validates: Requirements 8.1**
  
  - [x] 17.3 Write property test for error message localization
    - **Property 22: Error Message Localization**
    - **Validates: Requirements 8.2**

- [x] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. Review and enhance frontend configuration page (Est: 4h)
  - [x] 19.1 Review existing LLM config pages
    - ✅ `frontend/src/pages/Admin/LLMConfig.tsx` exists
    - ✅ `frontend/src/pages/Admin/ConfigLLM.tsx` exists
    - ⚠️ Need to verify alignment with design spec
    - Review page layout with provider list table
    - Verify "Add Provider" button and modal exist
    - Verify provider status with health indicators
    - Verify edit and delete actions
    - _Requirements: 6.1, 6.2_
  
  - [x] 19.2 Review/Create `frontend/src/components/llm/ProviderForm.tsx`
    - Create form with fields: name, type, deployment mode, endpoint, API key
    - Add form validation
    - Add provider type selector with icons
    - Add deployment mode toggle
    - _Requirements: 6.2_
  
  - [x] 19.3 Review/Create `frontend/src/components/llm/ProviderTestButton.tsx`
    - Implement connection test button
    - Show loading state during test
    - Display test result (success/error)
    - _Requirements: 6.3_
  
  - [x] 19.4 Review/Create `frontend/src/services/llm.ts`
    - Implement API client functions for all LLM endpoints
    - Use TanStack Query for data fetching
    - Handle errors with localized messages
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 19.5 Review/Create `frontend/src/hooks/useLLMProviders.ts`
    - Implement custom hook for provider list
    - Implement custom hook for provider CRUD operations
    - Implement custom hook for connection testing
    - Use TanStack Query for caching and refetching
    - _Requirements: 6.1, 6.3_

- [x] 20. Verify frontend internationalization (Est: 1h)
  - [x] 20.1 Verify i18n keys in `frontend/src/locales/zh-CN.json`
    - Add Chinese translations for LLM config page
    - Add provider type names
    - Add error messages
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 20.2 Verify i18n keys in `frontend/src/locales/en-US.json`
    - Add English translations for LLM config page
    - Add provider type names
    - Add error messages
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 20.3 Verify language preference persistence
    - Verify language preference stored in localStorage
    - Verify preference restored on app load
    - _Requirements: 8.4_
  
  - [x] 20.4 Write property test for language preference persistence
    - **Property 23: Language Preference Persistence**
    - **Validates: Requirements 8.4**

- [x] 21. Integration and wiring (Est: 2h)
  - [x] 21.1 Verify LLM module wiring in FastAPI app
    - ✅ LLM endpoints exist in `src/api/admin.py`
    - ⚠️ Need to verify initialization in app startup
    - Initialize ProviderManager on app startup
    - Initialize LLMSwitcher with cache client
    - Start HealthMonitor background task
    - Verify LLM router registered in main app
    - _Requirements: All backend requirements_
  
  - [x] 21.2 Verify LLM config page in frontend navigation
    - ✅ Routes exist in `frontend/src/router/routes.tsx`
    - Verify menu item in admin section
    - Verify route in React Router
    - Verify permission check for admin users
    - _Requirements: 6.1_
  
  - [x] 21.3 Integrate pre-annotation with Label Studio
    - Connect pre-annotation service to annotation workflow
    - Add UI button for triggering pre-annotation
    - Display AI-generated annotations in Label Studio
    - _Requirements: 7.1, 7.2, 7.4_

- [x] 21.4 Write integration tests
  - Test end-to-end flow from API to provider
  - Test provider switching during active requests
  - Test health monitoring integration
  - Test cache integration
  - _Requirements: All requirements_

- [x] 22. Final checkpoint - Ensure all tests pass
  - Run full test suite (unit + property + integration)
  - Verify test coverage >80%
  - Fix any failing tests
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (100+ iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- All async code must use `asyncio.Lock` instead of `threading.Lock` (see async-sync-safety.md)
- All API endpoints must include proper error handling and localization
- All database operations must be async using AsyncSession
- Frontend must use TypeScript with strict type checking
- ✅ = Completed, ⚠️ = Partially complete or needs review, ❌ = Not started

## Summary of Existing Implementation

**Completed Components:**
- Core abstractions (LLMProvider, LLMSwitcher, schemas)
- Database models (LLMConfiguration, LLMUsageLog, LLMModelRegistry)
- Provider implementations (OpenAI, Azure, Qwen, Zhipu, Baidu, Hunyuan, Ollama)
- Configuration manager with Redis caching and hot reload
- Basic API endpoints for CRUD operations
- Frontend pages and routes

**Missing/Incomplete Components:**
- LLMHealthStatus database model and migration
- Explicit failover logic in LLMSwitcher
- Health Monitor background service
- Rate limiter
- Property-based tests for all correctness properties
- Unit tests for provider implementations
- Integration tests
- Complete API endpoints (generate, health, activate)
- Frontend components (ProviderForm, ProviderTestButton)
- Frontend services and hooks
- Pre-annotation integration alignment
- Audit logging for configuration changes
- Log sanitization
- I18n completeness verification
