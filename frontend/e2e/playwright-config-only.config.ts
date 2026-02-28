/**
 * Minimal Playwright config for running config-verification tests
 * that don't need a running dev server (they use about:blank).
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    headless: true,
    actionTimeout: 10000,
    launchOptions: {
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  timeout: 30000,
  outputDir: '../test-results/',
})
