/**
 * Security-related pure checks (Properties 13–18, 前端侧).
 */

/** Escape HTML special chars for safe text insertion (Property 13). */
export function escapeHtmlText(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** After escaping, angle brackets from user input must not form tags. */
export function escapedHasNoRawTags(s: string): boolean {
  const e = escapeHtmlText(s)
  return !/<[a-z]/i.test(e)
}

/** Property 14: API JSON string field for display should be escaped before innerHTML. */
export function safeApiTextForDisplay(raw: string): string {
  return escapeHtmlText(raw)
}

/** Property 15: SQL fragments must not be concatenated — use bound parameter idiom. */
export function buildParameterizedWhere(
  column: string,
  userFragment: string,
): { sql: string; params: string[] } {
  const safeCol = /^[a-z_][a-z0-9_]*$/i.test(column) ? column : 'id'
  return { sql: `SELECT * FROM t WHERE ${safeCol} = ?`, params: [userFragment] }
}

/** Property 16: resource tenant must match current tenant for access. */
export function tenantCanAccessResource(resourceTenantId: string, currentTenantId: string): boolean {
  return resourceTenantId === currentTenantId
}

/** Property 17: password input attributes. */
export function passwordFieldAttributes(): { type: string; autoComplete: string } {
  return { type: 'password', autoComplete: 'off' }
}

/** Property 18: safe error body for client — no stack / DB hints. */
const UNSAFE_ERROR_PATTERNS = [
  /at\s+.+\(/,
  /Traceback/i,
  /postgres/i,
  /sqlite/i,
  /SELECT\s+\*/i,
  /INSERT\s+INTO/i,
  /internal server error:\s*\/[^\s]+/i,
] as const

export function isSafeClientErrorMessage(message: string): boolean {
  return !UNSAFE_ERROR_PATTERNS.some((re) => re.test(message))
}
