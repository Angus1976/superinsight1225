/**
 * Tokens for Playwright E2E that satisfy {@link isTokenExpired} in the app
 * (must be three-part JWT-shaped strings with a far-future `exp` claim).
 */
export const E2E_VALID_ACCESS_TOKEN =
  'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJlMmUtdXNlciIsImV4cCI6NDEwMjQ0NDgwMCwidGVuYW50X2lkIjoidGVuYW50LTEifQ.e2e'

/** Second valid token (different payload) for multi-context E2E */
export const E2E_VALID_ACCESS_TOKEN_CTX1 =
  'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJjdHgxIiwiZXhwIjo0MTAyNDQ0ODAwLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtMSJ9.x'

export const E2E_VALID_ACCESS_TOKEN_CTX2 =
  'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJjdHgyIiwiZXhwIjo0MTAyNDQ0ODAwLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQtMiJ9.x'
