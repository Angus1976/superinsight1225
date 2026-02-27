/**
 * Search query sanitization utility.
 * Strips HTML tags, script injection patterns, and trims whitespace.
 */

/** Patterns considered dangerous in search queries */
const SCRIPT_PATTERNS = [
  /javascript\s*:/gi,
  /on\w+\s*=/gi,
  /expression\s*\(/gi,
  /url\s*\(/gi,
  /import\s*\(/gi,
  /eval\s*\(/gi,
];

/**
 * Sanitize a search query string before backend submission.
 *
 * - Strips all HTML tags
 * - Removes script injection patterns (javascript:, onerror=, eval(), etc.)
 * - Trims leading/trailing whitespace
 * - Collapses multiple spaces into one
 */
export function sanitizeSearchQuery(query: string): string {
  if (!query || typeof query !== 'string') return '';

  // Strip HTML tags
  let sanitized = query.replace(/<[^>]*>/g, '');

  // Remove script injection patterns
  for (const pattern of SCRIPT_PATTERNS) {
    sanitized = sanitized.replace(pattern, '');
  }

  // Collapse multiple spaces and trim
  return sanitized.replace(/\s+/g, ' ').trim();
}
