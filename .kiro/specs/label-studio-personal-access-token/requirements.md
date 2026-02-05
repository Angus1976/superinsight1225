# Requirements Document - Label Studio Personal Access Token Authentication

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-01-27  
**Feature Name**: label-studio-personal-access-token

## Introduction

This document specifies the requirements for implementing Personal Access Token (PAT) authentication support for Label Studio open-source edition. Unlike JWT authentication (which uses username/password login), PAT authentication uses a pre-generated refresh token from Label Studio's UI that must be exchanged for short-lived access tokens.

## Problem Statement

Label Studio open-source edition provides Personal Access Token as the primary authentication method for API access. The token is a JWT refresh token that:
- Is generated in Label Studio's UI (Account & Settings → Personal Access Token)
- Must be exchanged for access tokens via `/api/token/refresh` endpoint
- Access tokens expire after ~5 minutes and must be automatically refreshed
- Provides a simpler alternative to username/password authentication

## Glossary

- **Personal Access Token (PAT)**: JWT refresh token generated in Label Studio UI, used to obtain access tokens
- **Refresh Token**: Long-lived JWT token used to obtain short-lived access tokens
- **Access Token**: Short-lived JWT token (valid ~5 minutes) used for API authentication
- **Token Refresh**: Process of exchanging a refresh token for a new access token
- **Auto-refresh**: Automatic process of refreshing tokens before expiration
- **JWT**: JSON Web Token format with three parts separated by dots (header.payload.signature)
- **Bearer Token**: Authentication method using `Authorization: Bearer <token>` header

## Requirements

### Requirement 1: Personal Access Token Detection

**User Story:** As a system administrator, I want the system to automatically detect and handle Personal Access Token format, so that I don't need to specify the authentication method.

#### Acceptance Criteria

1. WHEN a token is provided in `LABEL_STUDIO_API_TOKEN`, THEN the system SHALL detect if it's a JWT format (3 parts separated by dots)
2. WHEN a JWT token is detected, THEN the system SHALL treat it as a Personal Access Token (refresh token)
3. WHEN a non-JWT token is detected, THEN the system SHALL treat it as a legacy API token
4. WHEN token type is determined, THEN the system SHALL log the detected authentication method
5. WHEN switching between token types, THEN the system SHALL not require code changes

### Requirement 2: Token Refresh Mechanism

**User Story:** As a developer, I want the system to automatically exchange Personal Access Tokens for access tokens, so that API calls work seamlessly.

#### Acceptance Criteria

1. WHEN a Personal Access Token is configured, THEN the system SHALL call `/api/token/refresh` endpoint to obtain an access token
2. WHEN calling `/api/token/refresh`, THEN the system SHALL send `{"refresh": "<personal-access-token>"}` in request body
3. WHEN token refresh succeeds, THEN the system SHALL extract the access token from response
4. WHEN token refresh succeeds, THEN the system SHALL parse the JWT to extract expiration time
5. WHEN token refresh fails, THEN the system SHALL raise `LabelStudioAuthenticationError` with clear error message

### Requirement 3: Automatic Token Renewal

**User Story:** As a developer, I want tokens to be automatically refreshed before expiration, so that API calls never fail due to token expiration.

#### Acceptance Criteria

1. WHEN an access token is obtained, THEN the system SHALL track its expiration time
2. WHEN an API call is about to be made, THEN the system SHALL check if token expires within 30 seconds
3. WHEN token is expiring soon, THEN the system SHALL refresh it before making the API call
4. WHEN token refresh is in progress, THEN other API calls SHALL wait for refresh to complete
5. WHEN token refresh completes, THEN all waiting API calls SHALL use the new token

### Requirement 4: Bearer Token Authentication

**User Story:** As a developer, I want API requests to use the correct authentication header format, so that Label Studio accepts the requests.

#### Acceptance Criteria

1. WHEN using Personal Access Token authentication, THEN all API requests SHALL use `Authorization: Bearer <access-token>` header
2. WHEN using legacy API token authentication, THEN all API requests SHALL use `Authorization: Token <api-token>` header
3. WHEN switching between authentication methods, THEN the header format SHALL change automatically
4. WHEN making API calls, THEN the system SHALL use the current valid token
5. WHEN token is refreshed, THEN subsequent API calls SHALL use the new token

### Requirement 5: Concurrent Request Handling

**User Story:** As a developer, I want concurrent API calls to be handled safely, so that token refresh doesn't cause race conditions.

#### Acceptance Criteria

1. WHEN multiple API calls occur concurrently, THEN only one token refresh operation SHALL execute at a time
2. WHEN a token refresh is in progress, THEN other API calls SHALL wait for the refresh to complete
3. WHEN using async operations, THEN the system SHALL use `asyncio.Lock()` for synchronization
4. WHEN token refresh completes, THEN all waiting API calls SHALL use the new token
5. WHEN token refresh fails, THEN all waiting API calls SHALL receive the same error

### Requirement 6: Project Title Length Handling

**User Story:** As a developer, I want project titles to comply with Label Studio's 50-character limit, so that project creation doesn't fail.

#### Acceptance Criteria

1. WHEN creating a Label Studio project, THEN the system SHALL enforce a maximum title length of 50 characters
2. WHEN a task name exceeds the limit, THEN the system SHALL truncate it intelligently
3. WHEN truncating, THEN the system SHALL include the task ID for uniqueness
4. WHEN truncating, THEN the system SHALL use format: `{task_name[:N]}... ({task_id[:8]})`
5. WHEN a project is created, THEN the title SHALL be exactly 50 characters or less

### Requirement 7: Error Handling

**User Story:** As a developer, I want clear error messages when authentication fails, so that I can troubleshoot issues quickly.

#### Acceptance Criteria

1. WHEN token refresh fails with 401, THEN the system SHALL raise `LabelStudioAuthenticationError` with "Invalid token" message
2. WHEN token refresh fails with 400, THEN the system SHALL raise `LabelStudioAuthenticationError` with "Malformed request" message
3. WHEN token refresh fails with network error, THEN the system SHALL retry with exponential backoff
4. WHEN token is invalid or expired, THEN the system SHALL provide clear instructions to generate a new token
5. WHEN authentication fails, THEN the system SHALL log the error with status code and reason

### Requirement 8: Backward Compatibility

**User Story:** As a system administrator, I want existing API token authentication to continue working, so that I don't need to migrate immediately.

#### Acceptance Criteria

1. WHEN only `LABEL_STUDIO_API_TOKEN` is configured, THEN the system SHALL use legacy API token authentication
2. WHEN the token is not in JWT format, THEN the system SHALL treat it as a legacy API token
3. WHEN using legacy API token, THEN the system SHALL use `Authorization: Token <api-token>` header
4. WHEN switching from legacy to PAT, THEN the system SHALL not require code changes
5. WHEN both authentication methods are available, THEN the system SHALL prefer PAT (JWT format)

### Requirement 9: Configuration Management

**User Story:** As a system administrator, I want to configure Personal Access Token via environment variables, so that I can manage credentials securely.

#### Acceptance Criteria

1. WHEN `LABEL_STUDIO_API_TOKEN` is set in `.env`, THEN the system SHALL read it on startup
2. WHEN the token is in JWT format, THEN the system SHALL automatically detect it as PAT
3. WHEN the token is invalid, THEN the system SHALL raise configuration error on startup
4. WHEN environment variables change, THEN the system SHALL reload configuration on container restart
5. WHEN configuration is loaded, THEN the system SHALL log the authentication method being used

### Requirement 10: Security Best Practices

**User Story:** As a security engineer, I want tokens to be handled securely, so that credentials are not exposed.

#### Acceptance Criteria

1. WHEN storing tokens, THEN the system SHALL store them in memory only (not persistent storage)
2. WHEN logging authentication events, THEN the system SHALL NOT log tokens or sensitive data
3. WHEN passing tokens in URLs, THEN the system SHALL use secure HTTPS connections
4. WHEN tokens expire, THEN the system SHALL clear them from memory
5. WHEN the application restarts, THEN the system SHALL re-authenticate to obtain new tokens

### Requirement 11: Integration with Existing Features

**User Story:** As a developer, I want Personal Access Token authentication to work with all existing features, so that no functionality is broken.

#### Acceptance Criteria

1. WHEN creating a project via `create_project()`, THEN the system SHALL use PAT authentication if configured
2. WHEN importing tasks via `import_tasks()`, THEN the system SHALL use PAT authentication if configured
3. WHEN exporting annotations via `export_annotations()`, THEN the system SHALL use PAT authentication if configured
4. WHEN validating projects via `validate_project()`, THEN the system SHALL use PAT authentication if configured
5. WHEN testing connection via `test_connection()`, THEN the system SHALL use PAT authentication if configured

### Requirement 12: Logging and Monitoring

**User Story:** As a system administrator, I want comprehensive logging of authentication events, so that I can troubleshoot issues.

#### Acceptance Criteria

1. WHEN Personal Access Token is detected, THEN the system SHALL log "Detected Personal Access Token (JWT refresh token)"
2. WHEN token refresh occurs, THEN the system SHALL log "Refreshing Personal Access Token"
3. WHEN token refresh succeeds, THEN the system SHALL log "Access token refreshed, expires at {timestamp}"
4. WHEN token refresh fails, THEN the system SHALL log error with status code and reason
5. WHEN authentication method is determined, THEN the system SHALL log which method is being used

## Non-Functional Requirements

### Performance

- Token refresh operations SHALL complete within 500ms
- Token detection SHALL add less than 1ms overhead
- Concurrent API calls SHALL not be blocked by token refresh (max 100ms wait)

### Reliability

- Token refresh SHALL succeed 99% of the time when token is valid
- System SHALL handle concurrent API calls without race conditions
- System SHALL recover from transient network errors automatically

### Security

- Tokens SHALL never be logged or exposed in error messages
- Tokens SHALL be cleared from memory on expiration
- HTTPS SHALL be enforced for token refresh endpoints

### Compatibility

- System SHALL support Label Studio open-source edition (all versions with PAT support)
- System SHALL maintain backward compatibility with legacy API token authentication
- System SHALL work with existing retry and error handling mechanisms

## Dependencies

### Internal Dependencies

- `src/label_studio/integration.py` - Main integration class to be extended
- `src/label_studio/config.py` - Configuration management
- `src/label_studio/exceptions.py` - Exception definitions
- `src/api/label_studio_sync.py` - Task sync functionality

### External Dependencies

- `httpx` - HTTP client for API calls
- `PyJWT` - JWT token parsing
- `asyncio` - Async/await support and locking
- Label Studio open-source edition - Target platform

## Constraints

- MUST NOT modify Label Studio source code
- MUST maintain backward compatibility with existing API
- MUST follow async/sync safety rules (use `asyncio.Lock()`, not `threading.Lock()`)
- MUST NOT retry authentication errors (401/403)
- MUST NOT log tokens or sensitive data

## Assumptions

- Label Studio open-source edition provides `/api/token/refresh` endpoint
- Personal Access Token is a JWT refresh token with `token_type: "refresh"`
- Access tokens expire after ~5 minutes
- Refresh tokens are long-lived (valid for ~100 years)
- JWT tokens use standard format with `exp` claim for expiration time
- Token refresh endpoint returns `{"access": "<access-token>"}` on success

## Success Criteria

- ✅ Personal Access Token authentication works with Label Studio
- ✅ Automatic token refresh prevents API call failures
- ✅ Backward compatibility with legacy API token authentication
- ✅ No deadlocks with concurrent requests
- ✅ Project title length limit handled correctly
- ✅ Clear error messages for troubleshooting
- ✅ Comprehensive logging of authentication events
- ✅ All integration tests pass (8/9 = 89%)
- ✅ Documentation complete and accurate

</content>
