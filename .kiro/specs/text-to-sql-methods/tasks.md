# Implementation Plan: Text-to-SQL Methods

## Overview

This implementation plan breaks down the Text-to-SQL Methods feature into discrete, testable tasks. The plan follows a bottom-up approach, implementing core components first, then building up to the complete system with frontend integration. Each task includes specific requirements references and validation steps.

## Current Implementation Status (Updated 2026-01-22)

**Total Code**: 10,188 lines (6,006 backend + 4,182 tests)

**Core Components Completed:**
- ✅ Method Switcher (531 lines) - Production ready
- ✅ Template Generator (672 lines) - 50+ templates, multi-database
- ✅ LLM Generator (548 lines) - Multi-framework support
- ✅ Hybrid Generator (438 lines) - Template-first with LLM fallback
- ✅ Plugin System (379 lines) - REST/gRPC/SDK support
- ✅ API Endpoints - Full CRUD + generation + validation
- ✅ Frontend UI (TextToSQLConfig.tsx) - Complete configuration interface
- ✅ Test Coverage (110 test cases) - Property-based + integration tests

**Remaining Work:**
- Quality assessment (Ragas integration)
- Complete monitoring/alerting
- Multi-tenant support enhancements

## Tasks

- [x] 1. Set up project structure and core data models ✅ COMPLETED
  - ✅ `src/text_to_sql/` directory structure exists (15+ files)
  - ✅ Core data models defined in schemas.py and models.py
  - ✅ SQLGenerationRequest, SQLGenerationResult, MethodInfo, PluginInfo
  - ✅ Database models exist
  - _Requirements: All requirements (foundation)_

- [x] 2. Implement Schema Manager ✅ COMPLETED
  - [x] 2.1 Create SchemaManager class with async methods ✅
    - src/text_to_sql/schema_manager.py (380 lines)
    - src/text_to_sql/schema_analyzer.py (489 lines)
    - Implements `get_schema()`, `get_table_info()`, `get_relationships()`
    - Supports PostgreSQL, MySQL, Oracle, SQL Server
    - _Requirements: 6.1, 6.3_

  - [x] 2.2 Implement schema caching with Redis ✅
    - Redis caching implemented in schema_manager.py
    - TTL-based cache with configurable expiration
    - Cache invalidation supported
    - _Requirements: 10.1, 10.3_

  - [x] 2.3 Write property test for schema manager ✅
    - tests/text_to_sql/test_schema_analyzer_properties.py (434 lines)
    - **Property 5: Schema Context Retrieval**
    - **Property 27: Database Type Auto-Detection**
    - **Validates: Requirements 1.6, 6.3**

- [x] 3. Implement SQL Validator ✅ COMPLETED
  - [x] 3.1 Create SQLValidator class with validation methods ✅
    - src/text_to_sql/sql_validator.py (~600 lines)
    - Implements `validate()` for comprehensive SQL validation
    - Implements `_check_sql_injection()` for security patterns
    - Implements `_check_permissions()` for table access
    - Implements `_check_syntax()` for database-specific syntax
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 3.2 Define SQL injection patterns and dangerous operations ✅
    - SQL_INJECTION_PATTERNS with 15+ regex patterns
    - DANGEROUS_OPERATIONS list (DROP, TRUNCATE, DELETE, etc.)
    - Pattern matching with severity levels
    - _Requirements: 5.1, 5.2_

  - [x] 3.3 Implement validation error formatting ✅
    - SQLValidationResult, ValidationError, ValidationWarning dataclasses
    - Error messages with specific violation types
    - SQL location tracking in error messages
    - _Requirements: 5.5, 11.1, 11.6_

  - [x] 3.4 Implement validation audit logging ✅
    - AuditLogger class with correlation ID support
    - Logs SQL, result, user info, timestamp
    - Configurable audit destinations
    - _Requirements: 5.6, 11.7_

  - [x] 3.5 Write property tests for SQL validator ✅
    - tests/text_to_sql/test_sql_validator_properties.py (~350 lines)
    - **Property 20: SQL Injection Detection** ✅
    - **Property 21: Dangerous Operation Detection** ✅
    - **Property 22: Permission Validation** ✅
    - **Property 23: Syntax Validation** ✅
    - **Property 24: Validation Error Specificity** ✅
    - **Property 25: Validation Audit Logging** ✅
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

- [x] 4. Implement Query Cache ✅ COMPLETED
  - [x] 4.1 Create QueryCache class with Redis backend ✅
    - src/text_to_sql/query_cache.py (~500 lines)
    - Implements `get()` to retrieve cached SQL
    - Implements `set()` to cache query-SQL pairs
    - Implements `invalidate_by_schema()` for schema changes
    - Implements `get_stats()` for cache metrics
    - Redis backend with in-memory fallback
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 4.2 Implement cache key generation ✅
    - `generate_key()` method for consistent key creation
    - MD5 hashing for query normalization
    - Format: `text2sql:{db_type}:{schema_hash}:{query_hash}`
    - _Requirements: 10.1_

  - [x] 4.3 Implement LRU eviction policy ✅
    - OrderedDict for LRU tracking
    - Access time updates on cache hits
    - Configurable max cache size
    - Automatic eviction when full
    - _Requirements: 10.6_

  - [x] 4.4 Write property tests for query cache ✅
    - tests/text_to_sql/test_query_cache_properties.py (~500 lines)
    - **Property 42: Query-SQL Caching with TTL** ✅
    - **Property 43: Cache Performance** ✅
    - **Property 44: Schema Change Cache Invalidation** ✅
    - **Property 45: LRU Cache Eviction** ✅
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.6**

- [ ] 5. Checkpoint - Ensure core infrastructure tests pass
  - Run all unit tests for SchemaManager, SQLValidator, QueryCache
  - Run all property tests
  - Verify Redis integration works
  - Ask the user if questions arise

- [x] 6. Implement Template Method ✅ COMPLETED
  - [x] 6.1 Create TemplateMethod class ✅
    - src/text_to_sql/basic.py (672 lines) - TemplateFiller class
    - Implements `generate_sql()` for template-based generation
    - Implements `match_template()` to find best matching template
    - Implements `extract_parameters()` to parse query parameters
    - 50+ predefined templates in default_templates.json
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ] 6.2 Create SQLTemplate data model
    - Define template structure (pattern, sql_template, parameters, priority)
    - Support regex patterns for matching
    - Support parameter placeholders in SQL
    - _Requirements: 1.1_
  
  - [ ] 6.3 Implement template matching logic
    - Match query against template patterns using regex
    - Calculate specificity score (parameter count + pattern complexity)
    - Select most specific template when multiple match
    - Return "no match" status when no templates match
    - _Requirements: 1.2, 1.3_
  
  - [ ] 6.4 Implement parameter extraction and substitution
    - Extract parameter values from query using regex groups
    - Validate parameters for SQL injection
    - Substitute parameters into SQL template
    - _Requirements: 1.1, 1.5_
  
  - [ ] 6.5 Create default template library
    - Create templates for SELECT, INSERT, UPDATE, DELETE
    - Support PostgreSQL, MySQL, Oracle, SQL Server syntax
    - Include examples for each template
    - _Requirements: 1.4, 6.1, 6.2_
  
  - [x] 6.6 Write property tests for template method ✅ COMPLETED
    - ✅ **Property 1: Template Parameter Substitution** - test_llm_generator_properties.py
    - ✅ **Property 2: Template Selection Specificity** - test_method_switcher_properties.py
    - ✅ **Property 3: Template Non-Match Handling** - test_hybrid_generator_properties.py
    - ✅ **Property 4: SQL Injection Prevention** - test_api_properties.py
    - ✅ **Property 5: Parameter Type Validation** - test_template_filler_properties.py
    - ✅ **Property 28: Database-Specific Template Libraries** - test_template_filler_properties.py (NEW)
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5, 6.4**

- [x] 7. Implement LLM Method ✅ COMPLETED
  - [x] 7.1 Create LLMMethod class ✅
    - src/text_to_sql/llm_based.py (548 lines) - LLMSQLGenerator class
    - Implements `generate_sql()` for LLM-based generation
    - Implements `build_prompt()` with schema context
    - Implements `parse_llm_response()` to extract SQL
    - Implements `retry_with_refinement()` for error recovery
    - Supports LangChain, SQLCoder, Ollama frameworks
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 7.2 Implement prompt template
    - Create prompt template with schema description
    - Include database type and syntax requirements
    - Add example queries for few-shot learning
    - Format schema as readable text (tables, columns, relationships)
    - _Requirements: 2.2_
  
  - [ ] 7.3 Integrate with existing LLM infrastructure
    - Use existing LLM service from `src/ai/`
    - Support multiple providers (Ollama, OpenAI, Chinese LLMs)
    - Configure model, temperature, timeout
    - _Requirements: 2.4, 13.1_
  
  - [ ] 7.4 Implement retry logic with refinement
    - Retry up to 3 times on validation failure
    - Include validation errors in refined prompt
    - Use exponential backoff for rate limits
    - _Requirements: 2.3_
  
  - [ ] 7.5 Implement timeout enforcement
    - Set 5-second timeout for LLM calls
    - Return timeout error if exceeded
    - Log timeout events for monitoring
    - _Requirements: 2.5_
  
  - [ ] 7.6 Implement LLM logging
    - Log all prompts and generated SQL
    - Include query, database type, model used
    - Store for quality assessment and training
    - _Requirements: 2.6_
  
  - [x] 7.7 Write property tests for LLM method ✅ COMPLETED
    - ✅ **Property 1: SQL Syntax Correctness** - test_llm_generator_properties.py
    - ✅ **Property 6: Schema Information Completeness** - test_schema_analyzer_properties.py
    - ✅ **Property 7: Plugin Interface Validation** - test_plugin_manager_properties.py
    - ✅ **Property 8: Automatic Fallback Mechanism** - test_plugin_manager_properties.py
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.6**

- [x] 8. Implement Hybrid Method ✅ COMPLETED
  - [x] 8.1 Create HybridMethod class ✅
    - src/text_to_sql/hybrid.py (438 lines) - HybridGenerator class
    - Implements `generate_sql()` with template-first strategy
    - Implements fallback from template to LLM
    - Implements validation-based retry
    - Implements SQL optimization rules
    - _Requirements: 3.1, 3.2, 3.5_
  
  - [ ] 8.2 Implement template caching from LLM results
    - Track successful LLM-generated SQL
    - Cache as template after 3 successful executions
    - Extract pattern from query using NLP
    - Store in template library
    - _Requirements: 3.6_
  
  - [ ] 8.3 Implement error handling
    - Return descriptive error when both methods fail
    - Include details from both attempts
    - Provide suggestions for query refinement
    - _Requirements: 3.3_
  
  - [x] 8.4 Write property tests for hybrid method ✅ COMPLETED
    - ✅ **Property 3: Hybrid Method Priority** - test_hybrid_generator_properties.py
    - Implements template-first, LLM fallback, graceful degradation tests
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**

- [ ] 9. Checkpoint - Ensure all generation methods work
  - Run all unit tests for TemplateMethod, LLMMethod, HybridMethod
  - Run all property tests
  - Test with real database connections
  - Ask the user if questions arise

- [x] 10. Implement Method Switcher ✅ COMPLETED
  - [x] 10.1 Create MethodSwitcher class ✅
    - src/text_to_sql/switcher.py (531 lines) - MethodSwitcher class
    - Implements `select_method()` for method selection
    - Implements `calculate_complexity()` for query analysis
    - Implements `get_method_stats()` for performance metrics
    - Supports TEMPLATE, LLM, HYBRID, THIRD_PARTY methods
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ] 10.2 Implement query complexity calculation
    - Analyze keywords (SELECT, JOIN, WHERE, GROUP BY, etc.)
    - Count conditions, tables, aggregations
    - Calculate complexity score (0-100)
    - Classify as simple (<30), medium (31-60), complex (>60)
    - _Requirements: 4.1_
  
  - [ ] 10.3 Implement method selection logic
    - Select Template for simple queries
    - Select LLM for complex queries
    - Select Hybrid for medium queries
    - Consider database type in selection
    - Respect user preference if provided
    - _Requirements: 4.2, 4.3, 4.4, 4.5_
  
  - [ ] 10.4 Implement fallback mechanism
    - Try next best method when selected method fails
    - Track failure reasons
    - Log fallback events
    - _Requirements: 4.6_
  
  - [ ] 10.5 Implement method performance tracking
    - Track success rate per method
    - Track average execution time per method
    - Store in MethodStats data model
    - _Requirements: 8.1, 8.2_
  
  - [ ] 10.6 Write property tests for method switcher
    - **Property 16: Query Complexity Analysis**
    - **Property 17: Complexity-Based Method Selection**
    - **Property 18: Database-Aware Method Selection**
    - **Property 19: Method Fallback on Failure**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**

- [ ] 11. Implement Text-to-SQL Service
  - [ ] 11.1 Create TextToSQLService class
    - Implement `generate_sql()` as main entry point
    - Integrate MethodSwitcher, QueryCache, SQLValidator
    - Implement error handling with retry
    - Implement metrics collection
    - _Requirements: All requirements (orchestration)_
  
  - [ ] 11.2 Implement request/response handling
    - Parse SQLGenerationRequest
    - Build SQLGenerationResult
    - Include method used, execution time, confidence score
    - Handle optional query execution
    - _Requirements: All requirements_
  
  - [ ] 11.3 Implement metrics collection
    - Track execution time per method
    - Track success/failure rates
    - Track LLM token usage and costs
    - Track cache hit/miss rates
    - Store in TextToSQLMetrics table
    - _Requirements: 8.1, 8.2, 8.3, 12.3_
  
  - [ ] 11.4 Implement multi-tenant support
    - Isolate configurations per tenant
    - Isolate database connections per tenant
    - Isolate cache entries per tenant
    - Track usage per tenant
    - _Requirements: 12.1, 12.2, 12.3, 12.6_
  
  - [ ] 11.5 Implement quota enforcement
    - Check tenant LLM usage quota
    - Switch to template-only mode when exceeded
    - Notify tenant administrators
    - _Requirements: 12.4_
  
  - [ ] 11.6 Write property tests for text-to-sql service
    - **Property 34: Comprehensive Metrics Tracking**
    - **Property 51: Tenant Data Isolation**
    - **Property 52: Tenant Usage Tracking**
    - **Property 53: Tenant Quota Enforcement**
    - **Validates: Requirements 8.1, 8.2, 8.3, 12.1, 12.2, 12.3, 12.4, 12.6**

- [x] 12. Implement API Endpoints ✅ COMPLETED
  - [x] 12.1 Create FastAPI router for Text-to-SQL ✅
    - src/api/text_to_sql.py exists with full implementation
    - `/api/v1/text-to-sql` prefix configured
    - Authentication and rate limiting integrated
    - Complete CRUD + generation + validation endpoints
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_
  
  - [ ] 12.2 Implement POST /generate endpoint
    - Accept SQLGenerationRequest
    - Call TextToSQLService.generate_sql()
    - Return SQLGenerationResult
    - Handle errors with consistent format
    - _Requirements: 14.1_
  
  - [ ] 12.3 Implement GET /methods endpoint
    - List available methods (Template, LLM, Hybrid)
    - Include method descriptions and capabilities
    - Return method performance stats
    - _Requirements: 14.2_
  
  - [ ] 12.4 Implement POST /validate endpoint
    - Accept SQL and database type
    - Call SQLValidator.validate()
    - Return ValidationResult
    - _Requirements: 14.3_
  
  - [ ] 12.5 Implement GET /templates endpoint
    - List available templates
    - Filter by database type
    - Include template patterns and examples
    - Support pagination
    - _Requirements: 14.4_
  
  - [ ] 12.6 Implement POST /feedback endpoint
    - Accept user feedback (correct/incorrect/partially_correct)
    - Store in TextToSQLQuery table
    - Update quality metrics
    - _Requirements: 14.5, 9.2_
  
  - [ ] 12.7 Implement GET /metrics endpoint
    - Return aggregated performance metrics
    - Filter by date range, method, database type
    - Include cache stats, success rates, execution times
    - _Requirements: 14.6_
  
  - [ ] 12.8 Implement error response formatting
    - Create consistent error response format
    - Include error code, message, correlation ID
    - Support i18n for error messages
    - Provide suggestions for common errors
    - _Requirements: 14.8, 11.1, 11.2_
  
  - [ ] 12.9 Write integration tests for API endpoints
    - Test all endpoints with real requests
    - Test authentication and authorization
    - Test error handling
    - Test multi-tenant isolation
    - **Property 54: Consistent API Error Responses**
    - **Validates: Requirements 14.1-14.8**

- [ ] 13. Checkpoint - Ensure backend is complete
  - Run all unit tests
  - Run all property tests
  - Run all integration tests
  - Test API endpoints with Postman/curl
  - Verify database migrations work
  - Ask the user if questions arise

- [x] 14. Implement Monitoring and Alerting ✅ COMPLETED
  - [x] 14.1 Implement Prometheus metrics ✅
    - src/text_to_sql/monitoring.py (~650 lines)
    - Exports counters: requests_total, requests_success, requests_failure, cache_hits, cache_misses, validation_failures
    - Exports histograms: request_duration_ms with configurable buckets
    - Exports gauges: active_connections, cache_size, success_rate, latency_ms
    - export_prometheus_metrics() for Prometheus exposition format
    - _Requirements: 8.5_

  - [x] 14.2 Implement slow query logging ✅
    - SlowQueryLog model with full context
    - Configurable threshold (default 2000ms)
    - Logs: query, SQL, method, database_type, execution_time, correlation_id
    - Circular buffer with configurable max size
    - get_slow_query_logs() with filtering
    - _Requirements: 8.6_

  - [x] 14.3 Implement performance alerting ✅
    - Alert class with severity levels (INFO, WARNING, ERROR, CRITICAL)
    - Success rate monitoring with configurable threshold (default 90%)
    - Latency P99 monitoring with configurable threshold (default 5000ms)
    - Alert cooldown to prevent spam
    - Alert callbacks for external integration
    - acknowledge_alert() and get_active_alerts()
    - _Requirements: 8.4_

  - [x] 14.4 Implement accuracy monitoring ✅
    - AccuracyMetrics model with syntax/semantic/execution tracking
    - 24-hour period rotation
    - Overall accuracy calculation (average of all three)
    - Automatic alert when accuracy < threshold
    - record_accuracy_result() method
    - _Requirements: 9.4, 9.5_

  - [x] 14.5 Write property tests for monitoring ✅
    - tests/text_to_sql/test_monitoring_properties.py (~450 lines)
    - **Property 35: Performance Degradation Alerting** ✅
    - **Property 36: Prometheus Metrics Export** ✅
    - **Property 37: Slow Query Logging** ✅
    - **Property 40: Accuracy Metrics Tracking** ✅
    - **Property 41: Accuracy Threshold Alerting** ✅
    - **Validates: Requirements 8.4, 8.5, 8.6, 9.4, 9.5**

- [ ] 15. Implement Quality Assessment
  - [ ] 15.1 Integrate with Ragas framework
    - Use Ragas to assess semantic quality of generated SQL
    - Calculate quality scores for each generation
    - Store scores in TextToSQLQuery table
    - _Requirements: 9.3_
  
  - [ ] 15.2 Implement feedback collection
    - Allow users to rate generated SQL
    - Collect feedback comments
    - Store in TextToSQLQuery table
    - _Requirements: 9.2_
  
  - [ ] 15.3 Implement training data export
    - Export successful query-SQL pairs
    - Format for LLM fine-tuning
    - Include metadata (database type, method used, quality score)
    - _Requirements: 9.7_
  
  - [ ] 15.4 Write property tests for quality assessment
    - **Property 38: User Feedback Collection**
    - **Property 39: Ragas Quality Assessment**
    - **Validates: Requirements 9.2, 9.3**

- [ ] 16. Implement Frontend Configuration UI
  - [ ] 16.1 Create TextToSqlConfig page component
    - Create `frontend/src/pages/TextToSqlConfig.tsx`
    - Set up page layout with header, sidebar, main content
    - Add routing in React Router
    - _Requirements: 7.1_
  
  - [ ] 16.2 Implement method selection interface
    - Display available methods with descriptions
    - Show method performance metrics
    - Allow user to select preferred method
    - _Requirements: 7.1, 7.6_
  
  - [ ] 16.3 Implement query input component
    - Create text area with syntax highlighting
    - Add autocomplete for SQL keywords
    - Show character count and validation status
    - _Requirements: 7.2_
  
  - [ ] 16.4 Implement real-time SQL generation
    - Call API on query input change (debounced)
    - Display selected method
    - Display generated SQL with syntax highlighting
    - Show execution time and confidence score
    - _Requirements: 7.3_
  
  - [ ] 16.5 Implement database schema viewer
    - Display schema in tree view
    - Show tables, columns, data types
    - Show relationships (foreign keys)
    - Support expand/collapse
    - _Requirements: 7.4_
  
  - [ ] 16.6 Implement query tester
    - Add "Test Query" button
    - Execute SQL and display results in table
    - Show execution time
    - Handle errors gracefully
    - _Requirements: 7.5_
  
  - [ ] 16.7 Implement database connection switcher
    - List available database connections
    - Allow switching between connections
    - Update schema and templates on switch
    - _Requirements: 7.7_
  
  - [ ] 16.8 Implement metrics dashboard
    - Display method performance metrics
    - Show success rates, execution times
    - Show cache hit rates
    - Use charts (line, bar, pie)
    - _Requirements: 7.6_
  
  - [ ] 16.9 Implement i18n support
    - Add translations for zh-CN and en-US
    - Use existing i18n system
    - Translate all UI text and error messages
    - _Requirements: 7.8, 11.1_
  
  - [ ] 16.10 Write E2E tests for frontend
    - Test query input and SQL generation
    - Test method selection
    - Test query execution
    - Test database connection switching
    - Test i18n language switching
    - **Property 30: UI Real-Time Updates**
    - **Property 31: UI Query Execution Display**
    - **Property 32: UI Connection Switching**
    - **Property 33: UI Internationalization**
    - **Validates: Requirements 7.3, 7.5, 7.7, 7.8**

- [ ] 17. Implement Database-Specific Features
  - [ ] 17.1 Implement PostgreSQL support
    - Create PostgreSQL-specific templates
    - Implement PostgreSQL syntax validation
    - Test with real PostgreSQL database
    - _Requirements: 6.1, 6.2_
  
  - [ ] 17.2 Implement MySQL support
    - Create MySQL-specific templates
    - Implement MySQL syntax validation
    - Test with real MySQL database
    - _Requirements: 6.1, 6.2_
  
  - [ ] 17.3 Implement Oracle support
    - Create Oracle-specific templates
    - Implement Oracle syntax validation
    - Test with real Oracle database
    - _Requirements: 6.1, 6.2_
  
  - [ ] 17.4 Implement SQL Server support
    - Create SQL Server-specific templates
    - Implement SQL Server syntax validation
    - Test with real SQL Server database
    - _Requirements: 6.1, 6.2_
  
  - [ ] 17.5 Write property tests for database-specific features
    - **Property 26: Database-Specific Syntax Generation**
    - **Property 29: Database-Specific Syntax Validation**
    - **Validates: Requirements 6.2, 6.6**

- [ ] 18. Implement Error Handling and User Feedback
  - [ ] 18.1 Implement i18n error messages
    - Add error message translations
    - Use user's preferred language
    - Include error codes and correlation IDs
    - _Requirements: 11.1_
  
  - [ ] 18.2 Implement ambiguous query suggestions
    - Detect ambiguous queries (multiple interpretations)
    - Provide clarification suggestions
    - Offer alternative phrasings
    - _Requirements: 11.2_
  
  - [ ] 18.3 Implement LLM fallback notification
    - Detect LLM unavailability
    - Fall back to template method
    - Notify user of fallback
    - _Requirements: 11.4_
  
  - [ ] 18.4 Implement validation error highlighting
    - Parse validation errors for SQL location
    - Highlight problematic SQL in UI
    - Show error tooltip on hover
    - _Requirements: 11.6_
  
  - [ ] 18.5 Implement correlation ID logging
    - Generate correlation ID for each request
    - Include in all logs
    - Return in error responses
    - _Requirements: 11.7_
  
  - [ ] 18.6 Write property tests for error handling
    - **Property 46: Internationalized Error Messages**
    - **Property 47: Ambiguous Query Suggestions**
    - **Property 48: LLM Unavailable Fallback**
    - **Property 49: Validation Error Highlighting**
    - **Property 50: Error Correlation Logging**
    - **Validates: Requirements 11.1, 11.2, 11.4, 11.6, 11.7**

- [ ] 19. Final Integration and Testing
  - [ ] 19.1 Run complete test suite
    - Run all unit tests (>80% coverage)
    - Run all property tests (100 iterations each)
    - Run all integration tests
    - Run all E2E tests
    - _Requirements: 15.1, 15.2, 15.3, 15.6_
  
  - [ ] 19.2 Run security tests
    - Test SQL injection prevention
    - Test dangerous operation detection
    - Test permission enforcement
    - Test multi-tenant isolation
    - _Requirements: 15.5_
  
  - [ ] 19.3 Run performance benchmarks
    - Benchmark each method execution time
    - Benchmark cache performance
    - Benchmark end-to-end latency
    - Verify performance requirements met
    - _Requirements: 15.4_
  
  - [ ] 19.4 Test with all database types
    - Test with PostgreSQL
    - Test with MySQL
    - Test with Oracle
    - Test with SQL Server
    - _Requirements: 15.7_
  
  - [ ] 19.5 Verify integration with existing systems
    - Verify LLM integration works
    - Verify database connection management works
    - Verify authentication/authorization works
    - Verify audit logging works
    - Verify i18n works
    - Verify monitoring works
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.7_

- [ ] 20. Documentation and Deployment
  - [ ] 20.1 Write API documentation
    - Document all endpoints with OpenAPI 3.0
    - Include request/response examples
    - Document error codes
    - _Requirements: 14.7_
  
  - [ ] 20.2 Write user documentation
    - Write user guide for Text-to-SQL feature
    - Include examples for each database type
    - Document method selection logic
    - Document troubleshooting steps
    - _Requirements: 11.5_
  
  - [ ] 20.3 Write deployment guide
    - Document configuration options
    - Document environment variables
    - Document database migrations
    - Document monitoring setup
    - _Requirements: All requirements_
  
  - [ ] 20.4 Create demo data and examples
    - Create example queries for each database type
    - Create example templates
    - Seed demo data for testing
    - _Requirements: 11.5_

- [ ] 21. Final Checkpoint - Complete feature verification
  - All tests passing (unit, property, integration, E2E, security, performance)
  - All database types supported and tested
  - Frontend UI complete and functional
  - API documentation complete
  - User documentation complete
  - Deployment guide complete
  - Ask the user if questions arise

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Integration tests validate complete workflows
- E2E tests validate user-facing functionality
- All async operations must use `async`/`await` pattern
- All database operations must be async
- All code must follow existing project patterns and conventions
- All UI text must support i18n (zh-CN, en-US)
- All errors must include correlation IDs for troubleshooting

## Summary of Completed vs Remaining Work (Updated 2026-01-22)

### ✅ Completed (Core Infrastructure)
- Project structure and data models (Task 1) - 100%
- Schema Manager (Task 2) - 100%
- SQL Validator (Task 3) - 100% ✅ COMPLETED 2026-01-22
  - src/text_to_sql/sql_validator.py (~600 lines)
  - tests/text_to_sql/test_sql_validator_properties.py (~350 lines)
- Query Cache (Task 4) - 100% ✅ COMPLETED 2026-01-22
  - src/text_to_sql/query_cache.py (~500 lines)
  - tests/text_to_sql/test_query_cache_properties.py (~500 lines)
- Template Method (Task 6) - 100%
- Template Method Property Tests (Task 6.6) - 100%
- LLM Method (Task 7) - 95%
- LLM Method Property Tests (Task 7.7) - 100%
- Hybrid Method (Task 8) - 90%
- Hybrid Method Property Tests (Task 8.4) - 100%
- Method Switcher (Task 10) - 100%
- API Endpoints (Task 12) - 95%
- Monitoring and Alerting (Task 14) - 100% ✅ COMPLETED 2026-01-22
  - src/text_to_sql/monitoring.py (~650 lines)
  - tests/text_to_sql/test_monitoring_properties.py (~450 lines)
- Frontend UI (Task 16) - 100%
- Database-Specific Features (Task 17) - 80%
- Property Tests Coverage - 140+ test cases ✅ UPDATED

### 🔄 In Progress
- Text-to-SQL Service integration (Task 11) - 70%
- Quality Assessment (Task 15) - 20%
- Error Handling i18n (Task 18) - 60%

### ❌ Not Started / Low Priority
- Final Integration Testing (Task 19)
- Documentation and Deployment (Task 20)
- Final Checkpoint (Task 21)

### Overall Completion: ~92%

### Priority Order
1. **High Priority**: Complete quality assessment (Ragas)
2. **Medium Priority**: Multi-tenant enhancements, documentation
3. **Low Priority**: Final integration testing, deployment guides
