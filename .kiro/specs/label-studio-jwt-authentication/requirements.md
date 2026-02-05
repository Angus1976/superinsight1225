# Requirements Document - Label Studio JWT Authentication

## Introduction

This document specifies the requirements for implementing JWT-based authentication support for Label Studio 1.22.0+. Label Studio has transitioned from legacy API token authentication to JWT-based authentication via the `/api/sessions/` endpoint. This feature will enable SuperInsight to authenticate with Label Studio using username/password credentials and manage JWT tokens automatically.

## Glossary

- **JWT (JSON Web Token)**: A compact, URL-safe means of representing claims to be transferred between two parties
- **Access Token**: Short-lived JWT token used for API authentication (typically expires in 1 hour)
- **Refresh Token**: Long-lived JWT token used to obtain new access tokens (typically expires in 7 days)
- **Label Studio**: Open-source data labeling platform integrated with SuperInsight
- **LabelStudioIntegration**: Python class that manages Label Studio API interactions
- **Authentication Error**: HTTP 401/403 error indicating invalid or expired credentials
- **Network Error**: Transient errors like timeouts, connection failures that should be retried
- **Token Expiration**: When a JWT token's validity period has ended
- **Auto-refresh**: Automatic process of obtaining a new access token using a refresh token

## Requirements

### Requirement 1: JWT Authentication Support

**User Story:** As a system administrator, I want SuperInsight to authenticate with Label Studio using JWT tokens, so that I can use Label Studio 1.22.0+ without downgrading.

#### Acceptance Criteria

1. WHEN the system is configured with `LABEL_STUDIO_USERNAME` and `LABEL_STUDIO_PASSWORD`, THEN the system SHALL authenticate using JWT tokens via `/api/sessions/` endpoint
2. WHEN authentication succeeds, THEN the system SHALL store both access token and refresh token in memory
3. WHEN authentication fails with invalid credentials, THEN the system SHALL raise `LabelStudioAuthenticationError` with clear error message
4. WHERE JWT authentication is configured, THEN all API requests SHALL use `Authorization: Bearer <ACCESS_TOKEN>` header
5. WHEN the system starts, THEN the system SHALL automatically authenticate and obtain JWT tokens before making any API calls

### Requirement 2: Automatic Token Refresh

**User Story:** As a developer, I want the system to automatically refresh expired tokens, so that API calls don't fail due to token expiration.

#### Acceptance Criteria

1. WHEN an access token expires, THEN the system SHALL automatically refresh it using the refresh token
2. WHEN refreshing a token, THEN the system SHALL use the `/api/sessions/refresh/` endpoint with the refresh token
3. WHEN token refresh succeeds, THEN the system SHALL update the stored access token and refresh token
4. WHEN token refresh fails, THEN the system SHALL re-authenticate using username/password
5. WHILE an API call is in progress, IF the access token expires, THEN the system SHALL refresh the token and retry the API call automatically

### Requirement 3: Backward Compatibility

**User Story:** As a system administrator, I want to maintain backward compatibility with API token authentication, so that existing deployments continue to work.

#### Acceptance Criteria

1. WHERE only `LABEL_STUDIO_API_TOKEN` is configured, THEN the system SHALL use legacy API token authentication
2. WHERE both JWT credentials and API token are configured, THEN the system SHALL prefer JWT authentication
3. WHEN using API token authentication, THEN the system SHALL use `Authorization: Token <API_TOKEN>` header
4. WHEN switching between authentication methods, THEN the system SHALL not require code changes
5. WHEN authentication method is determined, THEN the system SHALL log which method is being used

### Requirement 4: Thread-Safe Token Management

**User Story:** As a developer, I want token refresh operations to be thread-safe, so that concurrent API calls don't cause race conditions.

#### Acceptance Criteria

1. WHEN multiple API calls occur concurrently, THEN only one token refresh operation SHALL execute at a time
2. WHEN a token refresh is in progress, THEN other API calls SHALL wait for the refresh to complete
3. WHEN using async operations, THEN the system SHALL use `asyncio.Lock()` for synchronization
4. WHEN token refresh completes, THEN all waiting API calls SHALL use the new token
5. WHEN token refresh fails, THEN all waiting API calls SHALL receive the same error

### Requirement 5: Error Handling and Retry Logic

**User Story:** As a developer, I want clear distinction between authentication errors and network errors, so that the system handles them appropriately.

#### Acceptance Criteria

1. WHEN authentication fails (401/403), THEN the system SHALL raise `LabelStudioAuthenticationError` and NOT retry
2. WHEN network errors occur (timeout, connection error), THEN the system SHALL retry with exponential backoff
3. WHEN token expiration is detected (401 with specific error message), THEN the system SHALL attempt token refresh before raising error
4. WHEN refresh token expires, THEN the system SHALL re-authenticate using username/password
5. WHEN re-authentication fails, THEN the system SHALL raise `LabelStudioAuthenticationError` with clear error message

### Requirement 6: Configuration Management

**User Story:** As a system administrator, I want to configure JWT authentication via environment variables, so that I can easily manage credentials.

#### Acceptance Criteria

1. WHEN `LABEL_STUDIO_USERNAME` is set in environment, THEN the system SHALL read it from `.env` file
2. WHEN `LABEL_STUDIO_PASSWORD` is set in environment, THEN the system SHALL read it from `.env` file
3. WHEN JWT credentials are missing, THEN the system SHALL fall back to API token authentication
4. WHEN both authentication methods are unavailable, THEN the system SHALL raise configuration error
5. WHEN configuration is validated, THEN the system SHALL log the authentication method being used

### Requirement 7: Integration with Existing Features

**User Story:** As a developer, I want JWT authentication to work seamlessly with existing features, so that no functionality is broken.

#### Acceptance Criteria

1. WHEN creating a project via `create_project()`, THEN the system SHALL use JWT authentication if configured
2. WHEN importing tasks via `import_tasks()`, THEN the system SHALL use JWT authentication if configured
3. WHEN generating authenticated URLs via `generate_authenticated_url()`, THEN the system SHALL include JWT token in URL
4. WHEN using iframe integration, THEN the system SHALL pass JWT token to iframe for authentication
5. WHEN validating projects via `validate_project()`, THEN the system SHALL use JWT authentication if configured

### Requirement 8: Token Expiration Handling

**User Story:** As a developer, I want the system to detect and handle token expiration gracefully, so that API calls don't fail unexpectedly.

#### Acceptance Criteria

1. WHEN an API call returns 401 with "token expired" message, THEN the system SHALL attempt token refresh
2. WHEN token refresh succeeds, THEN the system SHALL retry the original API call with new token
3. WHEN token refresh fails, THEN the system SHALL re-authenticate and retry the original API call
4. WHEN re-authentication fails, THEN the system SHALL raise `LabelStudioAuthenticationError`
5. WHEN checking token expiration, THEN the system SHALL parse JWT token to check `exp` claim

### Requirement 9: Logging and Monitoring

**User Story:** As a system administrator, I want comprehensive logging of authentication events, so that I can troubleshoot issues.

#### Acceptance Criteria

1. WHEN authentication succeeds, THEN the system SHALL log "JWT authentication successful"
2. WHEN authentication fails, THEN the system SHALL log error with status code and message
3. WHEN token refresh occurs, THEN the system SHALL log "Refreshing access token"
4. WHEN token refresh succeeds, THEN the system SHALL log "Token refresh successful"
5. WHEN switching authentication methods, THEN the system SHALL log "Using JWT authentication" or "Using API token authentication"

### Requirement 10: Security Best Practices

**User Story:** As a security engineer, I want JWT tokens to be handled securely, so that credentials are not exposed.

#### Acceptance Criteria

1. WHEN storing tokens, THEN the system SHALL store them in memory only (not persistent storage)
2. WHEN logging authentication events, THEN the system SHALL NOT log tokens or passwords
3. WHEN passing tokens in URLs, THEN the system SHALL use secure HTTPS connections
4. WHEN tokens expire, THEN the system SHALL clear them from memory
5. WHEN the application restarts, THEN the system SHALL re-authenticate to obtain new tokens

## Non-Functional Requirements

### Performance

- Token refresh operations SHALL complete within 2 seconds
- Authentication SHALL complete within 5 seconds
- Token validation SHALL add less than 10ms overhead to API calls

### Reliability

- Token refresh SHALL succeed 99% of the time when refresh token is valid
- System SHALL handle concurrent API calls without race conditions
- System SHALL recover from transient network errors automatically

### Maintainability

- JWT authentication code SHALL be isolated in dedicated methods
- Configuration SHALL be centralized in `LabelStudioConfig` class
- Error messages SHALL be clear and actionable

### Compatibility

- System SHALL support Label Studio 1.22.0 and later versions
- System SHALL maintain backward compatibility with API token authentication
- System SHALL work with existing retry and error handling mechanisms

## Dependencies

### Internal Dependencies

- `src/label_studio/integration.py` - Main integration class to be extended
- `src/label_studio/config.py` - Configuration management to be extended
- `src/label_studio/retry.py` - Retry decorator to be reused
- `src/config/settings.py` - Settings management for environment variables

### External Dependencies

- `httpx` - HTTP client for API calls
- `PyJWT` - JWT token parsing and validation
- `asyncio` - Async/await support and locking
- Label Studio 1.22.0+ - Target authentication API

## Constraints

- MUST NOT modify Label Studio source code
- MUST maintain backward compatibility with existing API
- MUST follow async/sync safety rules (use `asyncio.Lock()`, not `threading.Lock()`)
- MUST use existing retry decorator for network errors
- MUST NOT retry authentication errors (401/403)

## Assumptions

- Label Studio 1.22.0+ uses `/api/sessions/` for login
- Label Studio 1.22.0+ uses `/api/sessions/refresh/` for token refresh
- Access tokens expire after 1 hour (configurable)
- Refresh tokens expire after 7 days (configurable)
- JWT tokens use standard format with `exp` claim
