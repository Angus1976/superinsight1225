/**
 * Playwright Test Fixtures
 * 
 * Custom fixtures for E2E testing including:
 * - Console log collection
 * - Screenshot capture on failure
 * - Browser context setup
 */

import { test as base, Page, BrowserContext } from '@playwright/test'
import { RoleConfig, ROLE_CONFIGS } from './helpers/role-permissions'
import { setupAuth } from './test-helpers'
import { E2E_VALID_ACCESS_TOKEN } from './e2e-tokens'

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
    await page.addInitScript((accessToken: string) => {
      localStorage.setItem('auth_token', JSON.stringify(accessToken))
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
            token: accessToken,
            currentTenant: {
              id: 'tenant-1',
              name: '测试租户',
            },
            isAuthenticated: true,
          },
          version: 0,
        }),
      )
    }, E2E_VALID_ACCESS_TOKEN)

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

// ---------------------------------------------------------------------------
// Role-parameterized fixtures (Requirements: 16.1, 1.1–1.4)
// ---------------------------------------------------------------------------

/**
 * Fixtures for role-based E2E tests.
 * `rolePage` is a Page pre-authenticated as the role specified by `roleConfig`.
 */
export interface RoleTestFixtures {
  rolePage: Page
  roleConfig: RoleConfig
}

/**
 * Extended test object that includes role-parameterized fixtures.
 *
 * Usage:
 * ```ts
 * import { roleTest } from '../fixtures'
 * for (const [roleName, config] of Object.entries(ROLE_CONFIGS)) {
 *   roleTest.describe(`${roleName} workflow`, () => {
 *     roleTest.use({ roleConfig: config })
 *     roleTest('can access dashboard', async ({ rolePage }) => { ... })
 *   })
 * }
 * ```
 */
export const roleTest = test.extend<RoleTestFixtures>({
  // Default role config — override with roleTest.use({ roleConfig: ... })
  roleConfig: [ROLE_CONFIGS.admin, { option: true }],

  rolePage: async ({ page, roleConfig }, use) => {
    await setupAuth(page, roleConfig.role, roleConfig.tenantId)
    await use(page)
  },
})

// Re-export ROLE_CONFIGS for convenience
export { ROLE_CONFIGS } from './helpers/role-permissions'
export type { RoleConfig } from './helpers/role-permissions'