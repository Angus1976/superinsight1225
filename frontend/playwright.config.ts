import os from 'node:os'
import { defineConfig, devices } from '@playwright/test'

/**
 * Local worker count: avoid defaulting to "all CPUs" (heavy on Apple Silicon, hurts thermals and can add flake).
 * Override with PLAYWRIGHT_WORKERS=1 (or 2–8). In CI, default is 1 unless PLAYWRIGHT_WORKERS is set (e.g. GitHub Actions uses 2 for Chromium-only runs).
 */
function resolvePlaywrightWorkers(): number {
  const raw = process.env.PLAYWRIGHT_WORKERS
  if (raw !== undefined && raw !== '') {
    const n = parseInt(raw, 10)
    if (!Number.isNaN(n) && n >= 1) return Math.min(n, 8)
  }
  if (process.env.CI) return 1
  const cores = os.cpus().length || 4
  return Math.min(4, Math.max(2, Math.floor(cores / 2)))
}

/**
 * Playwright E2E Test Configuration
 * 
 * Requirements: 4.1, 4.5, 4.6
 * - 4.1: E2E tests for user authentication workflows
 * - 4.5: Capture screenshots on failure
 * - 4.6: Execute E2E tests in headless browser mode by default
 *
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* CI: single worker for determinism. Local: capped parallel workers (see resolvePlaywrightWorkers). */
  workers: resolvePlaywrightWorkers(),
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list'],
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure - Requirement 4.5 */
    screenshot: 'only-on-failure',

    /* Video recording on failure for debugging */
    video: 'on-first-retry',

    /* Ignore HTTPS errors for testing */
    ignoreHTTPSErrors: true,

    /* Set default timeout for actions (10 seconds) */
    actionTimeout: 10000,

    /* Set default timeout for navigation (30 seconds) */
    navigationTimeout: 30000,

    /* Headless mode by default - Requirement 4.6 */
    headless: true,

    /* Collect browser console logs - Requirement 4.5 */
    launchOptions: {
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
  },

  /* Deployment specs live under e2e/deployment — only the `deployment` project should run them
   * (real services / DEPLOY_URL). Browser projects must ignore this folder or `npm run test:e2e`
   * double-runs them against the Vite dev server and fails. */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: ['**/deployment/**'],
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: ['**/deployment/**'],
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: ['**/deployment/**'],
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testIgnore: ['**/deployment/**'],
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      testIgnore: ['**/deployment/**'],
    },

    /* Deployment health checks — runs against real services (no mocking) */
    {
      name: 'deployment',
      testDir: './e2e/deployment',
      use: {
        baseURL: process.env.DEPLOY_URL || 'http://localhost:8000',
      },
      timeout: 120000,
    },
  ],

  /* Global test timeout */
  timeout: 60000,

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },

  /* Output directory for test artifacts */
  outputDir: 'test-results/',

  /* Snapshot directory */
  snapshotDir: '.snapshots',
})
