/**
 * Console log filtering for E2E (known noisy messages in test env).
 * Used by {@link ../fixtures.ts} and `console-filter.property.test.ts`.
 */

export const E2E_KNOWN_CONSOLE_IGNORE_SUBSTRINGS = [
  'Failed to fetch',
  'Network request failed',
  'DEPRECATION WARNING',
  'React does not recognize',
  'Warning:',
] as const

export function shouldIgnoreConsoleNoise(text: string): boolean {
  return E2E_KNOWN_CONSOLE_IGNORE_SUBSTRINGS.some((issue) => text.includes(issue))
}

export function filterConsoleErrorLines(lines: readonly string[]): string[] {
  return lines.filter((line) => !shouldIgnoreConsoleNoise(line))
}
