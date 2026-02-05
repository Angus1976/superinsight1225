# Implementation Plan: Label Studio JWT Authentication

## Overview

This implementation plan breaks down the JWT authentication feature into discrete, manageable tasks. Each task builds on previous tasks and includes specific requirements references for traceability.

## Tasks

- [x] 1. Set up JWT authentication infrastructure
  - Create `JWTAuthManager` class with token storage
  - Add JWT token parsing utilities
  - Implement thread-safe token management with `asyncio.Lock()`
  - _Requirements: 1.1, 1.2, 4.3, 10.1_
  - _Estimated time: 4 hours_

- [x] 2. Implement core authentication methods
  - [x] 2.1 Implement `login()` method for username/password authentication
    - Make POST request to `/api/sessions/` endpoint
    - Parse and store access_token and refresh_token
    - Handle authentication errors (401/403)
    - _Requirements: 1.1, 1.2, 1.3_
    - _Estimated time: 2 hours_
  
  - [x] 2.2 Write property test for login method
    - **Property 2: Token Storage After Authentication**
    - **Validates: Requirements 1.2, 2.3**
    - Test that successful login stores both tokens
    - _Estimated time: 1 hour_
  
  - [x] 2.3 Implement `refresh_token()` method
    - Make POST request to `/api/sessions/refresh/` endpoint
    - Update stored tokens on success
    - Fall back to `login()` if refresh token expired
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
    - _Estimated time: 2 hours_
  
  - [x] 2.4 Write property test for token refresh
    - **Property 5: Token Refresh on Expiration**
    - **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
    - Test automatic refresh on expired token
    - _Estimated time: 1 hour_

- [x] 3. Implement token expiration handling
  - [x] 3.1 Implement `_is_token_expired()` method
    - Check token expiration with buffer period
    - Parse JWT token to extract `exp` claim
    - _Requirements: 8.5_
    - _Estimated time: 1.5 hours_
  
  - [x] 3.2 Write property test for expiration detection
    - **Property 9: Token Expiration Detection**
    - **Validates: Requirements 8.5**
    - Test expiration detection with various exp values
    - _Estimated time: 1 hour_
  
  - [x] 3.3 Implement `_ensure_authenticated()` method
    - Check token expiration before API calls
    - Refresh token if expired or expiring soon
    - Use `asyncio.Lock()` for thread safety
    - _Requirements: 2.5, 4.1, 4.2_
    - _Estimated time: 2 hours_
  
  - [x] 3.4 Write property test for concurrent refresh
    - **Property 7: Concurrent Refresh Mutual Exclusion**
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
    - Test that concurrent calls trigger only one refresh
    - _Estimated time: 1.5 hours_


- [x] 4. Extend configuration management
  - [x] 4.1 Add JWT credentials to `LabelStudioConfig`
    - Add `username` and `password` fields
    - Implement `get_auth_method()` to determine auth type
    - Update `validate_config()` to check JWT credentials
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
    - _Estimated time: 2 hours_
  
  - [x] 4.2 Write property test for auth method selection
    - **Property 1: Authentication Method Selection**
    - **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
    - Test auth method selection based on config
    - _Estimated time: 1 hour_
  
  - [x] 4.3 Add environment variables to settings
    - Add `LABEL_STUDIO_USERNAME` to settings
    - Add `LABEL_STUDIO_PASSWORD` to settings
    - Update `.env.example` with new variables
    - _Requirements: 6.1, 6.2_
    - _Estimated time: 1 hour_

- [x] 5. Extend LabelStudioIntegration class
  - [x] 5.1 Initialize JWT auth manager in `__init__()`
    - Detect authentication method from config
    - Create `JWTAuthManager` if JWT configured
    - Maintain backward compatibility with API token
    - _Requirements: 3.1, 3.2, 3.4_
    - _Estimated time: 2 hours_
  
  - [x] 5.2 Implement `_get_headers()` async method
    - Call `_ensure_authenticated()` for JWT auth
    - Return appropriate Authorization header
    - Handle both JWT and API token formats
    - _Requirements: 1.4, 3.3_
    - _Estimated time: 1.5 hours_
  
  - [x] 5.3 Write property test for header format
    - **Property 3: Authentication Header Format**
    - **Validates: Requirements 1.4, 3.3, 7.1, 7.2, 7.5**
    - Test correct header format for both auth methods
    - _Estimated time: 1 hour_

- [x] 6. Update existing API methods
  - [x] 6.1 Update `create_project()` to use `_get_headers()`
    - Replace `self.headers` with `await self._get_headers()`
    - Ensure JWT authentication is used
    - _Requirements: 7.1_
    - _Estimated time: 0.5 hours_
  
  - [x] 6.2 Update `import_tasks()` to use `_get_headers()`
    - Replace `self.headers` with `await self._get_headers()`
    - Ensure JWT authentication is used
    - _Requirements: 7.2_
    - _Estimated time: 0.5 hours_
  
  - [x] 6.3 Update `export_annotations()` to use `_get_headers()`
    - Replace `self.headers` with `await self._get_headers()`
    - _Requirements: 7.2_
    - _Estimated time: 0.5 hours_
  
  - [x] 6.4 Update `get_project_info()` to use `_get_headers()`
    - Replace `self.headers` with `await self._get_headers()`
    - Ensure JWT authentication is used
    - _Requirements: 7.5_
    - _Estimated time: 0.5 hours_
  
  - [x] 6.5 Update `validate_project()` to use `_get_headers()`
    - Replace `self.headers` with `await self._get_headers()`
    - Ensure JWT authentication is used
    - _Requirements: 7.5_
    - _Estimated time: 0.5 hours_
  
  - [x] 6.6 Update remaining API methods
    - Update `setup_webhooks()`, `configure_ml_backend()`, `delete_project()`
    - Replace `self.headers` with `await self._get_headers()`
    - _Requirements: 7.2_
    - _Estimated time: 1 hour_

- [x] 7. Checkpoint - Ensure all tests pass
  - Run all unit tests and property tests
  - Verify JWT authentication works end-to-end
  - Check backward compatibility with API token
  - Ask the user if questions arise
  - _Estimated time: 1 hour_


- [x] 8. Implement error handling
  - [x] 8.1 Add token expiration detection in API calls
    - Detect 401 errors with "token expired" message
    - Trigger automatic token refresh
    - Retry original API call with new token
    - _Requirements: 5.3, 8.1, 8.2_
    - _Estimated time: 2 hours_
  
  - [x] 8.2 Implement fallback to re-authentication
    - Detect refresh token expiration
    - Fall back to `login()` with username/password
    - Retry original API call after re-auth
    - _Requirements: 5.4, 8.3_
    - _Estimated time: 1.5 hours_
  
  - [x] 8.3 Write property test for error handling
    - **Property 4: Authentication Error Non-Retryability**
    - **Validates: Requirements 1.3, 5.1, 5.5**
    - Test that auth errors are not retried
    - _Estimated time: 1 hour_
  
  - [x] 8.4 Write property test for network error retry
    - **Property 8: Network Error Retryability**
    - **Validates: Requirements 5.2**
    - Test that network errors are retried with backoff
    - _Estimated time: 1 hour_
  
  - [x] 8.5 Add clear error messages
    - Implement actionable error messages for auth failures
    - Add context to error messages (status code, reason)
    - _Requirements: 1.3, 5.5_
    - _Estimated time: 1 hour_

- [x] 9. Implement security features
  - [x] 9.1 Add logging sanitization
    - Ensure tokens are never logged
    - Ensure passwords are never logged
    - Implement `get_auth_state()` for safe logging
    - _Requirements: 10.2_
    - _Estimated time: 1.5 hours_
   
  - [x] 9.2 Write property test for sensitive data protection
    - **Property 10: Sensitive Data Protection**
    - **Validates: Requirements 10.2**
    - Test that logs don't contain sensitive data
    - _Estimated time: 1 hour_
   
  - [x] 9.3 Add HTTPS enforcement for token URLs
    - Check URL scheme when generating authenticated URLs
    - Log warning if HTTP is used in production
    - _Requirements: 10.3_
    - _Estimated time: 1 hour_
   
  - [x] 9.4 Write property test for HTTPS enforcement
    - **Property 11: HTTPS for Token URLs**
    - **Validates: Requirements 10.3**
    - Test that token URLs use HTTPS
    - _Estimated time: 0.5 hours_
   
  - [x] 9.5 Implement token cleanup
    - Clear old tokens when refreshing
    - Clear tokens on authentication failure
    - _Requirements: 10.4_
    - _Estimated time: 1 hour_
   
  - [x] 9.6 Write property test for token cleanup
    - **Property 12: Token Cleanup on Expiration**
    - **Validates: Requirements 10.4**
    - Test that expired tokens are cleared
    - _Estimated time: 0.5 hours_

- [x] 10. Update iframe integration
  - [x] 10.1 Update `generate_authenticated_url()` for JWT
    - Include JWT token in URL
    - Include token expiration time
    - Support both JWT and API token
    - _Requirements: 7.3_
    - _Estimated time: 1.5 hours_
   
  - [x] 10.2 Update `AnnotationContext` interface (frontend)
    - Add `auth` field with JWT token info
    - Include token expiration time
    - Update TypeScript types
    - _Requirements: 7.4_
    - _Estimated time: 1 hour_
   
  - [x] 10.3 Write integration test for iframe auth
    - Test iframe receives JWT token
    - Test token expiration is communicated
    - _Requirements: 7.4_
    - _Estimated time: 1 hour_


- [x] 11. Add comprehensive logging
  - [x] 11.1 Add authentication success logging
    - Log "JWT authentication successful"
    - Log authentication method being used
    - _Requirements: 9.1, 9.5_
    - _Estimated time: 0.5 hours_
   
  - [x] 11.2 Add authentication failure logging
    - Log authentication errors with status code
    - Log clear error messages
    - _Requirements: 9.2_
    - _Estimated time: 0.5 hours_
   
  - [x] 11.3 Add token refresh logging
    - Log "Refreshing access token"
    - Log "Token refresh successful"
    - Log token expiration time
    - _Requirements: 9.3, 9.4_
    - _Estimated time: 0.5 hours_
   
  - [x] 11.4 Write unit tests for logging
    - Test that correct log messages are emitted
    - Test that sensitive data is not logged
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
    - _Estimated time: 1 hour_

- [x] 12. Write comprehensive unit tests
  - [x] 12.1 Write unit tests for `JWTAuthManager`
    - Test successful login
    - Test failed login with invalid credentials
    - Test successful token refresh
    - Test failed token refresh
    - Test token expiration detection
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 8.5_
    - _Estimated time: 3 hours_
   
  - [x] 12.2 Write unit tests for configuration
    - Test auth method selection
    - Test config validation
    - Test environment variable reading
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
    - _Estimated time: 2 hours_
   
  - [x] 12.3 Write unit tests for integration class
    - Test `_get_headers()` with JWT auth
    - Test `_get_headers()` with API token auth
    - Test backward compatibility
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
    - _Estimated time: 2 hours_
   
  - [x] 12.4 Write unit tests for error handling
    - Test authentication error handling
    - Test network error handling
    - Test token expiration handling
    - Test fallback to re-authentication
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
    - _Estimated time: 2.5 hours_

- [x] 13. Write integration tests
  - [x] 13.1 Write end-to-end authentication test
    - Test complete flow: login → API call → token refresh
    - Test with real Label Studio instance (or mock)
    - _Requirements: 1.1, 1.2, 1.4, 2.1, 2.5_
    - _Estimated time: 2 hours_
   
  - [x] 13.2 Write backward compatibility test
    - Test that API token authentication still works
    - Test switching between auth methods
    - _Requirements: 3.1, 3.2, 3.3_
    - _Estimated time: 1.5 hours_
   
  - [x] 13.3 Write concurrent request test
    - Test multiple concurrent API calls
    - Verify no deadlocks occur
    - Verify token refresh happens only once
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
    - _Estimated time: 2 hours_
   
  - [x] 13.4 Write error recovery test
    - Test recovery from network errors
    - Test recovery from token expiration
    - Test recovery from authentication failures
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
    - _Estimated time: 2 hours_

- [x] 14. Checkpoint - Ensure all tests pass
  - Run full test suite (unit + property + integration)
  - Verify test coverage > 90%
  - Fix any failing tests
  - Ask the user if questions arise
  - _Estimated time: 2 hours_


- [x] 15. Update documentation
  - [x] 15.1 Update `.env.example` file
    - Add `LABEL_STUDIO_USERNAME` example
    - Add `LABEL_STUDIO_PASSWORD` example
    - Add comments explaining JWT authentication
    - _Requirements: 6.1, 6.2_
    - _Estimated time: 0.5 hours_
  
  - [x] 15.2 Update README or setup guide
    - Document JWT authentication setup
    - Document backward compatibility
    - Add troubleshooting section
    - _Requirements: 6.1, 6.2, 6.3_
    - _Estimated time: 1 hour_
  
  - [x] 15.3 Add code comments and docstrings
    - Document `JWTAuthManager` class
    - Document all public methods
    - Add usage examples in docstrings
    - _Requirements: All_
    - _Estimated time: 1.5 hours_
  
  - [x] 15.4 Create migration guide
    - Document migration steps for existing deployments
    - Document rollback procedure
    - Add troubleshooting tips
    - _Requirements: 3.1, 3.2, 6.3_
    - _Estimated time: 1 hour_

- [-] 16. Performance testing and optimization
  - [x] 16.1 Test authentication latency
    - Measure login time
    - Measure token refresh time
    - Verify < 5 seconds for auth, < 2 seconds for refresh
    - _Requirements: Non-functional (Performance)_
    - _Estimated time: 1 hour_
  
  - [x] 16.2 Test concurrent request handling
    - Test with 100+ concurrent requests
    - Verify no deadlocks
    - Measure lock contention time
    - _Requirements: 4.1, 4.2, Non-functional (Performance)_
    - _Estimated time: 1.5 hours_
  
  - [x] 16.3 Test memory usage
    - Measure memory footprint of JWT auth manager
    - Verify < 1MB memory usage
    - Test token cleanup effectiveness
    - _Requirements: 10.1, 10.4, Non-functional (Performance)_
    - _Estimated time: 1 hour_
  
  - [x] 16.4 Optimize if needed
    - Optimize token parsing if slow
    - Optimize lock contention if high
    - Add connection pooling if needed
    - _Requirements: Non-functional (Performance)_
    - _Estimated time: 2 hours_

- [-] 17. Security review and hardening
  - [x] 17.1 Review token storage security
    - Verify tokens are in memory only
    - Verify no tokens in logs
    - Verify token cleanup on expiration
    - _Requirements: 10.1, 10.2, 10.4_
    - _Estimated time: 1 hour_
  
  - [x] 17.2 Review error message security
    - Verify no sensitive data in error messages
    - Verify error messages are actionable
    - _Requirements: 1.3, 5.5_
    - _Estimated time: 0.5 hours_
  
  - [x] 17.3 Review HTTPS enforcement
    - Verify HTTPS is used for token URLs
    - Verify warning is logged for HTTP in production
    - _Requirements: 10.3_
    - _Estimated time: 0.5 hours_
  
  - [x] 17.4 Conduct security audit
    - Review code for security vulnerabilities
    - Check for common JWT security issues
    - Verify thread safety
    - _Requirements: 4.1, 4.2, 4.3, 10.1, 10.2, 10.3, 10.4_
    - _Estimated time: 2 hours_

- [x] 18. Final integration and testing
  - [x] 18.1 Test with Label Studio 1.22.0+
    - Deploy Label Studio 1.22.0 in test environment
    - Test complete authentication flow
    - Verify all features work correctly
    - _Requirements: All_
    - _Estimated time: 2 hours_
  
  - [x] 18.2 Test backward compatibility
    - Test with API token authentication
    - Test switching between auth methods
    - Verify no breaking changes
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
    - _Estimated time: 1.5 hours_
  
  - [x] 18.3 Test error scenarios
    - Test with invalid credentials
    - Test with network failures
    - Test with token expiration
    - Verify error handling and recovery
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
    - _Estimated time: 1.5 hours_
  
  - [x] 18.4 Run full test suite
    - Run all unit tests
    - Run all property tests (100 iterations each)
    - Run all integration tests
    - Verify > 90% code coverage
    - _Requirements: All_
    - _Estimated time: 1 hour_

- [x] 19. Final checkpoint - Ensure all tests pass
  - Verify all tasks completed
  - Verify all tests passing
  - Verify documentation complete
  - Ask the user if questions arise
  - _Estimated time: 1 hour_

## Progress Tracking

- **Total Tasks**: 19 top-level tasks
- **Total Sub-tasks**: 67 sub-tasks
- **Estimated Total Time**: ~65 hours
- **All tasks are required for comprehensive implementation**

## Task Dependencies

```
1 → 2 → 3 → 4 → 5 → 6 → 7
         ↓
         8 → 9 → 10 → 11 → 12 → 13 → 14
                              ↓
                         15 → 16 → 17 → 18 → 19
```

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end functionality

## Risk Mitigation

1. **Authentication Failures**: Comprehensive error handling and fallback to re-authentication
2. **Token Expiration**: Proactive token refresh before expiration
3. **Concurrent Access**: Thread-safe token management with `asyncio.Lock()`
4. **Backward Compatibility**: Maintain support for API token authentication
5. **Security**: No tokens in logs, HTTPS enforcement, token cleanup

## Success Criteria

- ✅ JWT authentication works with Label Studio 1.22.0+
- ✅ Automatic token refresh prevents API call failures
- ✅ Backward compatibility with API token authentication
- ✅ No deadlocks with concurrent requests
- ✅ > 90% test coverage
- ✅ All property tests pass (100 iterations each)
- ✅ All integration tests pass
- ✅ Documentation complete
- ✅ Security review passed
