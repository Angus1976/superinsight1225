# Requirements Document: Text-to-SQL Methods

## Introduction

The Text-to-SQL Methods feature provides a comprehensive system for converting natural language queries into SQL statements. This system supports multiple conversion methods (template-based, LLM-based, and hybrid) with dynamic switching capabilities to optimize for different query complexities, database types, and user scenarios. The feature integrates with existing LLM infrastructure and provides a user-friendly frontend interface for configuration and testing.

## Glossary

- **Text-to-SQL**: The process of converting natural language queries into executable SQL statements
- **Template_Method**: A rule-based approach using predefined SQL templates with parameter substitution
- **LLM_Method**: A Large Language Model-based approach using AI to generate SQL from natural language
- **Hybrid_Method**: A combined approach using templates for simple queries and LLM for complex queries
- **Method_Switcher**: The component responsible for selecting the appropriate Text-to-SQL method based on query characteristics
- **SQL_Validator**: The component that validates generated SQL for syntax correctness and security
- **Query_Complexity**: A measure of how structured or unstructured a natural language query is
- **Database_Schema**: The structure definition of database tables, columns, and relationships
- **SQL_Injection**: A security vulnerability where malicious SQL code is inserted into queries
- **Ragas**: A framework for assessing the quality of generated responses

## Requirements

### Requirement 1: Template-Based SQL Generation

**User Story:** As a data analyst, I want to use predefined SQL templates for common queries, so that I can quickly generate SQL without waiting for LLM processing.

#### Acceptance Criteria

1. WHEN a user submits a structured query matching a template pattern, THE Template_Method SHALL generate SQL by substituting parameters into the template
2. WHEN multiple templates match a query, THE Template_Method SHALL select the most specific template based on parameter count and pattern complexity
3. WHEN no template matches a query, THE Template_Method SHALL return a "no match" status without generating SQL
4. THE Template_Method SHALL support templates for SELECT, INSERT, UPDATE, and DELETE operations
5. THE Template_Method SHALL validate all parameter values before substitution to prevent SQL injection
6. WHEN a template requires database schema information, THE Template_Method SHALL retrieve current schema metadata from the database connection

### Requirement 2: LLM-Based SQL Generation

**User Story:** As a business user, I want to use natural language to query databases, so that I don't need to know SQL syntax.

#### Acceptance Criteria

1. WHEN a user submits an unstructured natural language query, THE LLM_Method SHALL generate SQL using the configured LLM model
2. WHEN generating SQL, THE LLM_Method SHALL include database schema context in the prompt to improve accuracy
3. WHEN the LLM generates invalid SQL, THE LLM_Method SHALL retry up to 3 times with refined prompts
4. THE LLM_Method SHALL support multiple LLM providers (Ollama, OpenAI, Chinese LLMs)
5. WHEN LLM generation exceeds 5 seconds, THE LLM_Method SHALL timeout and return an error
6. THE LLM_Method SHALL log all generated SQL and prompts for quality assessment and training

### Requirement 3: Hybrid SQL Generation

**User Story:** As a system administrator, I want to combine template and LLM methods, so that I can optimize for both speed and flexibility.

#### Acceptance Criteria

1. WHEN a query is submitted, THE Hybrid_Method SHALL first attempt template matching
2. WHEN template matching fails, THE Hybrid_Method SHALL fall back to LLM generation
3. WHEN both methods fail, THE Hybrid_Method SHALL return a descriptive error message
4. THE Hybrid_Method SHALL track success rates for each method and adjust thresholds dynamically
5. WHEN a template-generated query fails validation, THE Hybrid_Method SHALL retry with LLM generation
6. THE Hybrid_Method SHALL cache successful LLM-generated SQL as new templates for future use

### Requirement 4: Dynamic Method Switching

**User Story:** As a system architect, I want automatic method selection based on query characteristics, so that the system optimizes for accuracy and performance.

#### Acceptance Criteria

1. WHEN a query is submitted, THE Method_Switcher SHALL analyze query complexity using keyword patterns and structure
2. WHEN query complexity is low (simple SELECT with <3 conditions), THE Method_Switcher SHALL select Template_Method
3. WHEN query complexity is high (joins, subqueries, aggregations), THE Method_Switcher SHALL select LLM_Method
4. WHEN query complexity is medium, THE Method_Switcher SHALL select Hybrid_Method
5. THE Method_Switcher SHALL consider database type (PostgreSQL, MySQL, Oracle, SQL Server) when selecting methods
6. WHEN a selected method fails, THE Method_Switcher SHALL automatically try the next best method
7. THE Method_Switcher SHALL track method performance metrics (success rate, execution time) and adjust selection logic

### Requirement 5: SQL Validation and Security

**User Story:** As a security officer, I want all generated SQL to be validated for safety, so that we prevent SQL injection and unauthorized access.

#### Acceptance Criteria

1. WHEN SQL is generated by any method, THE SQL_Validator SHALL check for SQL injection patterns before execution
2. WHEN SQL contains dangerous operations (DROP, TRUNCATE, ALTER), THE SQL_Validator SHALL reject the query unless explicitly allowed
3. WHEN SQL accesses tables outside the user's permissions, THE SQL_Validator SHALL reject the query
4. THE SQL_Validator SHALL validate SQL syntax for the target database type before execution
5. WHEN validation fails, THE SQL_Validator SHALL return specific error messages indicating the violation
6. THE SQL_Validator SHALL log all validation attempts and failures for audit purposes

### Requirement 6: Database Type Support

**User Story:** As a database administrator, I want to support multiple database types, so that users can query different data sources.

#### Acceptance Criteria

1. THE System SHALL support PostgreSQL, MySQL, Oracle, and SQL Server database types
2. WHEN generating SQL, THE System SHALL use database-specific syntax (e.g., LIMIT vs TOP, CONCAT vs ||)
3. WHEN connecting to a database, THE System SHALL detect the database type automatically
4. THE System SHALL maintain separate template libraries for each database type
5. WHEN a database type is not supported, THE System SHALL return a clear error message
6. THE System SHALL validate generated SQL against the specific database type's syntax rules

### Requirement 7: Frontend Configuration UI

**User Story:** As a data analyst, I want a visual interface to configure and test Text-to-SQL methods, so that I can easily experiment with different approaches.

#### Acceptance Criteria

1. WHEN a user accesses the Text-to-SQL configuration page, THE UI SHALL display available methods with descriptions
2. THE UI SHALL provide a query input field with syntax highlighting and autocomplete
3. WHEN a user enters a query, THE UI SHALL show the selected method and generated SQL in real-time
4. THE UI SHALL display database schema in a tree view with tables, columns, and relationships
5. WHEN a user tests a query, THE UI SHALL execute the SQL and display results with execution time
6. THE UI SHALL show method performance metrics (success rate, average execution time) in a dashboard
7. THE UI SHALL support switching between different database connections
8. THE UI SHALL provide i18n support for Chinese (zh-CN) and English (en-US)

### Requirement 8: Query Performance Monitoring

**User Story:** As a system administrator, I want to monitor Text-to-SQL performance, so that I can identify bottlenecks and optimize the system.

#### Acceptance Criteria

1. THE System SHALL track execution time for each Text-to-SQL method
2. THE System SHALL track success and failure rates for each method
3. THE System SHALL track LLM token usage and costs for LLM-based generation
4. WHEN performance degrades below thresholds, THE System SHALL send alerts to administrators
5. THE System SHALL provide Prometheus metrics for all Text-to-SQL operations
6. THE System SHALL log slow queries (>2 seconds) for analysis
7. THE System SHALL generate daily performance reports comparing method effectiveness

### Requirement 9: Quality Assessment and Improvement

**User Story:** As a data scientist, I want to assess and improve SQL generation quality, so that the system becomes more accurate over time.

#### Acceptance Criteria

1. THE System SHALL integrate with Label Studio for annotating query-SQL pairs
2. WHEN SQL is generated, THE System SHALL allow users to provide feedback (correct/incorrect)
3. THE System SHALL use Ragas framework to assess semantic quality of generated SQL
4. THE System SHALL track accuracy metrics (syntax correctness, semantic correctness, execution success)
5. WHEN accuracy falls below 90%, THE System SHALL trigger a review process
6. THE System SHALL use successful query-SQL pairs to improve templates and LLM prompts
7. THE System SHALL provide a training data export feature for fine-tuning LLM models

### Requirement 10: Caching and Optimization

**User Story:** As a system architect, I want to cache frequently used queries, so that we reduce LLM costs and improve response times.

#### Acceptance Criteria

1. THE System SHALL cache successful query-SQL pairs with a TTL of 24 hours
2. WHEN a cached query is requested, THE System SHALL return the cached SQL within 50ms
3. THE System SHALL invalidate cache entries when database schema changes
4. THE System SHALL track cache hit rates and adjust cache size dynamically
5. THE System SHALL use Redis for distributed caching across multiple instances
6. WHEN cache is full, THE System SHALL evict least recently used entries
7. THE System SHALL provide cache statistics in the monitoring dashboard

### Requirement 11: Error Handling and User Feedback

**User Story:** As a user, I want clear error messages when SQL generation fails, so that I can understand what went wrong and how to fix it.

#### Acceptance Criteria

1. WHEN SQL generation fails, THE System SHALL return error messages in the user's preferred language
2. WHEN a query is ambiguous, THE System SHALL suggest clarifications or alternative phrasings
3. WHEN database schema is missing, THE System SHALL prompt the user to provide schema information
4. WHEN LLM is unavailable, THE System SHALL fall back to template method and notify the user
5. THE System SHALL provide example queries for each supported database type
6. WHEN validation fails, THE System SHALL highlight the problematic part of the generated SQL
7. THE System SHALL log all errors with correlation IDs for troubleshooting

### Requirement 12: Multi-Tenant Support

**User Story:** As a platform administrator, I want to support multiple tenants with isolated configurations, so that different organizations can use the system independently.

#### Acceptance Criteria

1. THE System SHALL isolate Text-to-SQL configurations per tenant
2. THE System SHALL isolate database connections per tenant
3. THE System SHALL track usage metrics per tenant for billing purposes
4. WHEN a tenant exceeds their LLM usage quota, THE System SHALL switch to template-only mode
5. THE System SHALL allow tenant administrators to configure method preferences
6. THE System SHALL ensure tenant data isolation in cache and logs
7. THE System SHALL provide tenant-specific performance reports

### Requirement 13: Integration with Existing Systems

**User Story:** As a developer, I want Text-to-SQL to integrate seamlessly with existing platform features, so that users have a consistent experience.

#### Acceptance Criteria

1. THE System SHALL integrate with existing LLM infrastructure in src/ai/
2. THE System SHALL use existing database connection management in src/database/
3. THE System SHALL use existing authentication and authorization mechanisms
4. THE System SHALL integrate with existing audit logging in src/security/
5. THE System SHALL use existing i18n system for all user-facing text
6. THE System SHALL follow existing API patterns and response formats
7. THE System SHALL use existing monitoring and alerting infrastructure

### Requirement 14: API Design

**User Story:** As an API consumer, I want a RESTful API for Text-to-SQL operations, so that I can integrate the feature into other applications.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/text-to-sql/generate endpoint for SQL generation
2. THE System SHALL provide GET /api/v1/text-to-sql/methods endpoint for listing available methods
3. THE System SHALL provide POST /api/v1/text-to-sql/validate endpoint for SQL validation
4. THE System SHALL provide GET /api/v1/text-to-sql/templates endpoint for listing templates
5. THE System SHALL provide POST /api/v1/text-to-sql/feedback endpoint for quality feedback
6. THE System SHALL provide GET /api/v1/text-to-sql/metrics endpoint for performance metrics
7. THE System SHALL follow OpenAPI 3.0 specification for all endpoints
8. THE System SHALL return consistent error responses with error codes and messages

### Requirement 15: Testing and Quality Assurance

**User Story:** As a QA engineer, I want comprehensive tests for Text-to-SQL functionality, so that we ensure reliability and correctness.

#### Acceptance Criteria

1. THE System SHALL have unit tests for each Text-to-SQL method with >80% coverage
2. THE System SHALL have property-based tests for SQL generation correctness
3. THE System SHALL have integration tests with real database connections
4. THE System SHALL have performance benchmarks comparing method execution times
5. THE System SHALL have security tests for SQL injection prevention
6. THE System SHALL have end-to-end tests for the complete user workflow
7. THE System SHALL have tests for all supported database types
