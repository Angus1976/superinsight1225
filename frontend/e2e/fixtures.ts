/**
 * Playwright Test Fixtures
 * 
 * Custom fixtures for E2E testing including:
 * - Console log collection
 * - Screenshot capture on failure
 * - Browser context setup
 */

import { test as base, Page, BrowserContext } from '@playwright/test'

/**
 * Console log entry interface
 */
interface ConsoleLogEntry {
  type: 'log' | 'debug' | 'info' | 'error' | 'warning'
  text: string
  timestamp: number
  location?: {
    url: string
    lineNumber: number
    columnNumber: number
  }
}

/**
 * Extended test fixtures for E2E testing
 */
interface TestFixtures {
  // Console log collection
  collectConsoleLogs: (() => Promise<ConsoleLogEntry[]>) & { 
    clear: () => void 
  }
  consoleLogs: ConsoleLogEntry[]
  
  // Screenshot helper
  takeScreenshot: (name: string) => Promise<void>
  
  // Authenticated page
  authenticatedPage: Page
}

interface WorkerFixtures {
  // Worker-level setup
}

/**
 * Create test fixtures for console log collection and other utilities
 */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  // Console log collection fixture
  collectConsoleLogs: [
    async ({ page }, use) => {
      const logs: ConsoleLogEntry[] = []
      
      const handler = (msg: { type(): string; text(): string; location(): any }) => {
        const type = msg.type() as ConsoleLogEntry['type']
        // Only collect errors and warnings by default (Requirement 4.5)
        if (['error', 'warning', 'log'].includes(type)) {
          logs.push({
            type,
            text: msg.text(),
            timestamp: Date.now(),
            location: msg.location()
          })
        }
      }
      
      page.on('console', handler)
      
      await use(async () => logs)
      
      // Cleanup handled by page close
    },
    { scope: 'test' }
  ],

  // Array of collected console logs
  consoleLogs: async ({ collectConsoleLogs }, use) => {
    const logs = await collectConsoleLogs()
    await use(logs)
  },

  // Screenshot helper fixture
  takeScreenshot: async ({ page }, use) => {
    await use(async (name: string) => {
      await page.screenshot({ 
        path: `test-results/screenshots/${name}-${Date.now()}.png`,
        fullPage: true 
      })
    })
  },

  // Authenticated page fixture with default admin auth
  authenticatedPage: async ({ page }, use) => {
    // Set up authentication before test
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({
          state: {
            user: {
              id: 'user-admin',
              username: 'admin',
              name: '管理员',
              email: 'admin@example.com',
              tenant_id: 'tenant-1',
              roles: ['admin'],
              permissions: ['read:all', 'write:all', 'manage:all'],
            },
            token: 'mock-jwt-token-for-testing',
            currentTenant: {
              id: 'tenant-1',
              name: '测试租户',
            },
            isAuthenticated: true,
          },
        })
      )
    })
    
    await use(page)
  },
})

/**
 * Expect assertions with console log checking
 */
export { expect } from '@playwright/test'

/**
 * Helper to filter console errors (exclude known test environment issues)
 */
export function filterConsoleErrors(logs: ConsoleLogEntry[]): ConsoleLogEntry[] {
  const knownIssues = [
    'Failed to fetch',
    'Network request failed',
    'DEPRECATION WARNING',
    'React does not recognize',
    'Warning:',
  ]
  
  return logs.filter(log => 
    !knownIssues.some(issue => log.text.includes(issue))
  )
}

/**
 * Helper to check for critical console errors
 */
export function hasCriticalErrors(logs: ConsoleLogEntry[]): boolean {
  const criticalErrors = logs.filter(log => 
    log.type === 'error' && 
    !filterConsoleErrors([log]).length
  )
  return criticalErrors.length > 0
}