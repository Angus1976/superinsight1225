import { defineConfig, devices } from '@playwright/test'

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
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list'],
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:3000',

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

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* Global test timeout */
  timeout: 60000,

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },

  /* Output directory for test artifacts */
  outputDir: 'test-results/',

  /* Snapshot directory */
  snapshotDir: '.snapshots',
})
