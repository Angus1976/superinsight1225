# Requirements Document

## Introduction

This document defines the requirements for implementing a flexible LLM-Application binding system that enables many-to-many relationships between LLM configurations and applications. The system will allow each application (e.g., data structuring, knowledge graph, AI assistant) to configure multiple LLM providers with priority-based failover, while maintaining backward compatibility with existing single-LLM configurations.

## Glossary

- **LLM_Config**: A Large Language Model configuration containing provider details (API key, base URL, model name, parameters)
- **Application**: A functional module in the system that uses LLM services (e.g., structuring, knowledge_graph, ai_assistant)
- **Binding**: The association between an LLM_Config and an Application with priority and policy settings
- **Failover**: Automatic switching to a backup LLM when the primary LLM fails or times out
- **Hot_Reload**: Updating configuration without restarting the service
- **CloudConfig**: The existing configuration object used by SchemaInferrer and EntityExtractor
- **Structuring_Pipeline**: The current data structuring workflow that loads LLM configuration from environment variables

## Requirements

### Requirement 1: LLM Configuration Management

**User Story:** As a system administrator, I want to manage multiple LLM configurations centrally, so that I can use different LLM providers for different purposes.

#### Acceptance Criteria

1. THE System SHALL store LLM configurations in a database table with fields: id, name, provider, api_key, base_url, model_name, parameters, is_active, created_at, updated_at
2. WHEN an administrator creates an LLM configuration, THE System SHALL validate that the provider is supported (openai, azure, anthropic, custom)
3. WHEN an administrator creates an LLM configuration, THE System SHALL encrypt the api_key before storage
4. THE System SHALL support CRUD operations for LLM configurations via REST API
5. WHEN an LLM configuration is deleted, THE System SHALL check if it is bound to any application and prevent deletion if bindings exist

### Requirement 2: Application Registry

**User Story:** As a system administrator, I want to register applications that use LLM services, so that I can configure LLM bindings for each application.

#### Acceptance Criteria

1. THE System SHALL store application definitions in a database table with fields: id, code, name, description, llm_usage_pattern, is_active, created_at, updated_at
2. THE System SHALL pre-populate the application registry with existing applications: structuring, knowledge_graph, ai_assistant, semantic_analysis, rag_agent, text_to_sql
3. WHEN an application is registered, THE System SHALL ensure the application code is unique
4. THE System SHALL support querying applications via REST API
5. WHEN an application is deactivated, THE System SHALL retain its LLM bindings but mark them as inactive

### Requirement 3: LLM-Application Binding

**User Story:** As a system administrator, I want to bind multiple LLMs to each application with priority settings, so that applications can use primary and backup LLM providers.

#### Acceptance Criteria

1. THE System SHALL store bindings in a database table with fields: id, llm_config_id, application_id, priority, max_retries, timeout_seconds, is_active, created_at, updated_at
2. WHEN a binding is created, THE System SHALL validate that the LLM configuration and application exist
3. WHEN a binding is created, THE System SHALL ensure priority values are unique within the same application
4. THE System SHALL support priority values from 1 (highest) to 99 (lowest)
5. WHEN multiple bindings exist for an application, THE System SHALL order them by priority ascending
6. THE System SHALL support CRUD operations for bindings via REST API

### Requirement 4: Configuration Retrieval Service

**User Story:** As an application developer, I want to retrieve LLM configurations for my application, so that I can use the appropriate LLM provider.

#### Acceptance Criteria

1. WHEN an application requests LLM configuration, THE System SHALL return all active bindings ordered by priority
2. WHEN no bindings exist for an application, THE System SHALL fall back to environment variable configuration (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
3. THE System SHALL decrypt api_key values before returning them to applications
4. THE System SHALL cache LLM configurations in memory with a configurable TTL (default 300 seconds)
5. WHEN configuration is retrieved from cache, THE System SHALL validate that the cached entry has not expired

### Requirement 5: Failover and Retry Logic

**User Story:** As an application, I want to automatically failover to backup LLMs when the primary LLM fails, so that my service remains available.

#### Acceptance Criteria

1. WHEN an LLM request fails, THE System SHALL retry up to max_retries times with exponential backoff
2. WHEN all retries for an LLM fail, THE System SHALL attempt the next LLM in priority order
3. WHEN an LLM request exceeds timeout_seconds, THE System SHALL treat it as a failure and trigger failover
4. WHEN all LLMs for an application fail, THE System SHALL raise an exception with details of all attempted LLMs
5. THE System SHALL log each failover event with timestamp, application, failed LLM, and reason

### Requirement 6: Hot Configuration Reload

**User Story:** As a system administrator, I want configuration changes to take effect immediately, so that I don't need to restart services when updating LLM settings.

#### Acceptance Criteria

1. WHEN an LLM configuration is created, updated, or deleted, THE System SHALL invalidate the configuration cache
2. WHEN a binding is created, updated, or deleted, THE System SHALL invalidate the configuration cache for the affected application
3. WHEN cache is invalidated, THE System SHALL reload configuration from database on the next request
4. IF Redis is available, THE System SHALL publish cache invalidation events to a Redis channel
5. IF Redis is available, THE System SHALL subscribe to cache invalidation events and update local cache accordingly

### Requirement 7: Backward Compatibility

**User Story:** As an existing application, I want to continue working without code changes, so that the system upgrade does not break existing functionality.

#### Acceptance Criteria

1. WHEN an application has no database bindings, THE System SHALL load configuration from environment variables
2. THE System SHALL maintain the existing CloudConfig interface for SchemaInferrer and EntityExtractor
3. WHEN Structuring_Pipeline calls _load_cloud_config(), THE System SHALL check database bindings first, then fall back to environment variables
4. THE System SHALL support the existing environment variables: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
5. WHEN both database bindings and environment variables exist, THE System SHALL prioritize database bindings
6. THE System SHALL keep the _load_cloud_config() function signature unchanged
7. THE System SHALL allow gradual migration where some applications use database bindings while others continue using environment variables
8. WHEN upgrading the system, THE System SHALL not require any code changes in existing application modules

### Requirement 8: REST API Endpoints

**User Story:** As a frontend developer, I want REST API endpoints to manage LLM configurations and bindings, so that I can build a configuration UI.

#### Acceptance Criteria

1. THE System SHALL provide endpoint POST /api/llm-configs to create LLM configurations
2. THE System SHALL provide endpoint GET /api/llm-configs to list all LLM configurations
3. THE System SHALL provide endpoint PUT /api/llm-configs/{id} to update LLM configurations
4. THE System SHALL provide endpoint DELETE /api/llm-configs/{id} to delete LLM configurations
5. THE System SHALL provide endpoint GET /api/applications to list all applications
6. THE System SHALL provide endpoint POST /api/llm-bindings to create bindings
7. THE System SHALL provide endpoint GET /api/llm-bindings to list bindings with optional application_id filter
8. THE System SHALL provide endpoint PUT /api/llm-bindings/{id} to update bindings
9. THE System SHALL provide endpoint DELETE /api/llm-bindings/{id} to delete bindings
10. THE System SHALL provide endpoint POST /api/llm-configs/{id}/test to test LLM connectivity

### Requirement 9: Frontend Configuration Interface

**User Story:** As a system administrator, I want a web interface to manage LLM configurations and bindings, so that I can configure the system without writing code.

#### Acceptance Criteria

1. THE Frontend SHALL display a list of LLM configurations with columns: name, provider, model, status, actions
2. THE Frontend SHALL provide a form to create and edit LLM configurations with fields: name, provider, api_key, base_url, model_name, parameters
3. THE Frontend SHALL display a list of applications with their bound LLMs
4. THE Frontend SHALL provide a form to create and edit bindings with fields: application, LLM configuration, priority, max_retries, timeout
5. THE Frontend SHALL display bindings in priority order for each application
6. THE Frontend SHALL provide a "Test Connection" button for each LLM configuration
7. THE Frontend SHALL use Ant Design components for consistent UI
8. THE Frontend SHALL support drag-and-drop to reorder binding priorities

### Requirement 10: Internationalization Support

**User Story:** As a user, I want the configuration interface in my preferred language, so that I can understand and use the system effectively.

#### Acceptance Criteria

1. THE Frontend SHALL use i18n for all user-visible text in the LLM configuration interface
2. THE Frontend SHALL provide translations for Chinese and English
3. THE Frontend SHALL store translation keys in frontend/src/locales/zh/llmConfig.json and frontend/src/locales/en/llmConfig.json
4. WHEN displaying LLM provider names, THE Frontend SHALL use translated labels (e.g., "OpenAI" → "OpenAI", "Azure" → "Azure OpenAI 服务")
5. WHEN displaying error messages, THE Frontend SHALL use translated error messages
6. THE Frontend SHALL use useTranslation('llmConfig') hook to access translations
7. THE Frontend SHALL wrap all user-visible strings with t() function
8. WHEN rendering JSX child elements, THE Frontend SHALL use {t('key')} expression syntax
9. WHEN setting HTML/component attributes, THE Frontend SHALL use string syntax: title={t('key')}
10. THE Frontend SHALL translate the following content categories: provider names, application names and descriptions, form labels and placeholders, error messages and validation hints, operation button text
11. THE Frontend SHALL keep Chinese and English translation files synchronized
12. THE Frontend SHALL NOT translate: code comments, console.log messages, mock data name fields

### Requirement 11: Database Schema and Migration

**User Story:** As a database administrator, I want database migrations to create the necessary tables, so that the schema is properly versioned and can be rolled back if needed.

#### Acceptance Criteria

1. THE System SHALL create an Alembic migration script to add the llm_configs table
2. THE System SHALL create an Alembic migration script to add the llm_applications table
3. THE System SHALL create an Alembic migration script to add the llm_application_bindings table
4. THE Migration SHALL create foreign key constraints from llm_application_bindings to llm_configs and llm_applications
5. THE Migration SHALL create indexes on frequently queried columns: application_id, priority, is_active
6. THE Migration SHALL be reversible (support downgrade)

### Requirement 12: Security and Access Control

**User Story:** As a security administrator, I want LLM API keys to be encrypted and access-controlled, so that sensitive credentials are protected.

#### Acceptance Criteria

1. WHEN an API key is stored, THE System SHALL encrypt it using AES-256 encryption
2. THE System SHALL store the encryption key in environment variables, not in the database
3. WHEN an API key is retrieved, THE System SHALL decrypt it only for authorized requests
4. THE System SHALL require authentication for all LLM configuration API endpoints
5. THE System SHALL log all access to LLM configurations with user_id and timestamp

### Requirement 13: Monitoring and Logging

**User Story:** As a system operator, I want to monitor LLM usage and failures, so that I can identify and resolve issues quickly.

#### Acceptance Criteria

1. WHEN an LLM request is made, THE System SHALL log the application, LLM configuration, and request timestamp
2. WHEN an LLM request succeeds, THE System SHALL log the response time and token usage
3. WHEN an LLM request fails, THE System SHALL log the error message and stack trace
4. WHEN a failover occurs, THE System SHALL log the failover event with details
5. THE System SHALL expose metrics for LLM request count, success rate, and average response time per application and LLM configuration

### Requirement 14: Configuration Validation

**User Story:** As a system administrator, I want to validate LLM configurations before saving, so that I can catch configuration errors early.

#### Acceptance Criteria

1. WHEN an LLM configuration is created or updated, THE System SHALL validate that required fields are present: name, provider, api_key, model_name
2. WHEN an LLM configuration is created or updated, THE System SHALL validate that the base_url is a valid URL format
3. WHEN a binding is created or updated, THE System SHALL validate that priority is between 1 and 99
4. WHEN a binding is created or updated, THE System SHALL validate that timeout_seconds is greater than 0
5. WHEN a binding is created or updated, THE System SHALL validate that max_retries is between 0 and 10

### Requirement 15: Performance Requirements

**User Story:** As an application, I want LLM configuration retrieval to be fast, so that my response time is not impacted.

#### Acceptance Criteria

1. WHEN configuration is cached, THE System SHALL retrieve it in less than 1 millisecond
2. WHEN configuration is not cached, THE System SHALL retrieve it from database in less than 50 milliseconds
3. THE System SHALL support at least 1000 concurrent LLM requests without performance degradation
4. THE System SHALL limit cache memory usage to less than 100 MB
5. WHEN cache is full, THE System SHALL evict least recently used entries

### Requirement 16: Application Auto-Registration

**User Story:** As a system administrator, I want applications to be automatically registered at system startup, so that I don't need to manually register each LLM-consuming application.

#### Acceptance Criteria

1. WHEN the system starts, THE System SHALL automatically register all LLM-consuming applications
2. THE System SHALL register applications with metadata: code (unique identifier), name (display name), description (purpose), llm_usage_pattern (usage pattern)
3. THE System SHALL register the following initial applications: structuring (data structuring with SchemaInferrer and EntityExtractor), knowledge_graph (knowledge graph construction), ai_assistant (AI intelligent assistant), semantic_analysis (semantic analysis services), rag_agent (RAG intelligent agent), text_to_sql (text to SQL conversion)
4. WHEN an application is already registered, THE System SHALL update its metadata without creating duplicates
5. WHEN a new application is registered, THE System SHALL automatically inherit global default LLM bindings

### Requirement 17: Configuration Synchronization and Hot Reload

**User Story:** As a system operator, I want configuration changes to take effect immediately without service restart, so that I can update LLM settings with zero downtime.

#### Acceptance Criteria

1. WHEN loading LLM configuration, THE System SHALL prioritize database bindings over environment variables
2. WHEN no database binding exists for an application, THE System SHALL fall back to environment variable configuration
3. WHEN an LLM configuration is created, updated, or deleted, THE System SHALL immediately invalidate all related cache entries
4. WHEN a binding is modified, THE System SHALL invalidate the configuration cache for the affected application
5. WHEN cache is invalidated, THE System SHALL reload configuration from database on the next request
6. THE System SHALL use local memory cache with TTL of 300 seconds
7. IF Redis is available, THE System SHALL use Redis cache as a secondary cache layer
8. IF Redis is available, THE System SHALL publish cache invalidation notifications to Redis pub/sub channel
9. WHEN receiving cache invalidation notification, THE System SHALL update local cache immediately

### Requirement 18: Global and Application-Level Configuration Override

**User Story:** As a system administrator, I want to set global default LLM configurations and allow per-application overrides, so that I can manage configurations efficiently while supporting application-specific needs.

#### Acceptance Criteria

1. THE System SHALL support global default LLM configurations with tenant_id = NULL
2. THE System SHALL support tenant-specific LLM configurations with tenant_id set
3. THE System SHALL support application-specific LLM bindings with priority settings
4. WHEN resolving LLM configuration for an application, THE System SHALL apply override priority: application binding > tenant configuration > global configuration
5. WHEN a new application is registered, THE System SHALL automatically create bindings to global default LLM configurations
6. WHEN no application-specific binding exists, THE System SHALL use tenant-level configuration
7. WHEN no tenant-level configuration exists, THE System SHALL use global default configuration
8. WHEN multiple LLMs are bound to an application, THE System SHALL order them by priority for failover
9. THE System SHALL allow administrators to override global settings at tenant level without affecting other tenants
10. THE System SHALL allow administrators to override tenant settings at application level without affecting other applications
