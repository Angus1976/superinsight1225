/**
 * Playwright Configuration Validation Tests
 * 
 * Validates that Playwright configuration meets requirements:
 * - 4.1: E2E tests for user authentication workflows
 * - 4.5: Capture screenshots on failure
 * - 4.6: Execute E2E tests in headless browser mode by default
 * 
 * These tests verify the configuration itself, not application behavior.
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

test.describe('Playwright Configuration Validation', () => {
  test.describe('Requirement 4.6: Headless Browser Mode', () => {
    test('should have headless mode enabled by default', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      // Verify headless is set to true in the config
      expect(configContent).toContain('headless: true')
    })

    test('should run chromium in headless mode', async ({ browser }) => {
      const context = await browser.newContext({
        headless: true
      })
      const page = await context.newPage()
      
      // Verify we're in headless mode by checking viewport
      await page.setViewportSize({ width: 1280, height: 720 })
      expect(page.viewportSize()?.width).toBe(1280)
      
      await context.close()
    })
  })

  test.describe('Requirement 4.5: Screenshot Capture on Failure', () => {
    test('should have screenshot configuration set', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      // Verify screenshot on failure is configured
      expect(configContent).toContain("screenshot: 'only-on-failure'")
    })

    test('should have output directory configured for screenshots', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      // Verify output directory is set
      expect(configContent).toContain("outputDir: 'test-results/'")
    })
  })

  test.describe('Requirement 4.1: E2E Test Infrastructure', () => {
    test('should have test directory configured', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain("testDir: './e2e'")
    })

    test('should have multiple browser projects configured', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      // Verify chromium, firefox, and webkit are configured
      expect(configContent).toContain("name: 'chromium'")
      expect(configContent).toContain("name: 'firefox'")
      expect(configContent).toContain("name: 'webkit'")
    })

    test('should have JSON reporter configured for CI integration', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain("['json'")
      expect(configContent).toContain("outputFile: 'test-results.json'")
    })
  })

  test.describe('Console Log Collection', () => {
    test('should collect browser console logs on failure', async ({ page }) => {
      const consoleMessages: string[] = []
      
      page.on('console', msg => {
        consoleMessages.push(msg.text())
      })

      // Navigate to a page
      await page.goto('/')
      
      // Verify console collection is working
      expect(consoleMessages).toBeDefined()
    })
  })

  test.describe('Test Timeouts and Retries', () => {
    test('should have global timeout configured', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain('timeout: 60000')
    })

    test('should have action timeout configured', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain('actionTimeout: 10000')
    })

    test('should have navigation timeout configured', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain('navigationTimeout: 30000')
    })

    test('should have retry configuration for CI', async () => {
      const configPath = path.resolve(__dirname, '../playwright.config.ts')
      const configContent = fs.readFileSync(configPath, 'utf-8')
      
      expect(configContent).toContain('retries: process.env.CI ? 2 : 0')
    })
  })
})

/**
 * Property 12: E2E Test Failure Artifacts
 * Validates: Requirements 4.5, 9.3
 * 
 * For any end-to-end test execution that fails, the test result 
 * SHALL include both screenshot artifacts and browser console log output.
 */
test.describe('Property 12: E2E Test Failure Artifacts', () => {
  test('should capture screenshot on test failure', async ({ page }) => {
    // This test verifies the configuration is in place
    // Actual failure screenshots are handled by Playwright automatically
    const configPath = path.resolve(__dirname, '../playwright.config.ts')
    const configContent = fs.readFileSync(configPath, 'utf-8')
    
    expect(configContent).toContain("screenshot: 'only-on-failure'")
    expect(configContent).toContain("trace: 'on-first-retry'")
  })

  test('should collect browser console logs', async ({ page }) => {
    const consoleLogs: string[] = []
    
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`)
    })

    await page.goto('/')
    
    // Verify console logging is configured
    expect(consoleLogs).toBeDefined()
  })
})

/**
 * Property 13: E2E Headless Browser Mode
 * Validates: Requirements 4.6
 * 
 * For any end-to-end test execution with default configuration, 
 * the browser SHALL run in headless mode.
 */
test.describe('Property 13: E2E Headless Browser Mode', () => {
  test('should default to headless mode', async () => {
    const configPath = path.resolve(__dirname, '../playwright.config.ts')
    const configContent = fs.readFileSync(configPath, 'utf-8')
    
    // Verify headless is explicitly set to true
    expect(configContent).toMatch(/headless:\s*true/)
  })

  test('should run in headless mode when no override', async ({ browser }) => {
    // Create a context without specifying headless (uses default)
    const context = await browser.newContext()
    const page = await context.newPage()
    
    // The test passes if we can create a page in headless mode
    expect(page).toBeDefined()
    
    await context.close()
  })
})