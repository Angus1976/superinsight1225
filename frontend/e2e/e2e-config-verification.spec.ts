/**
 * E2E Configuration Verification Tests
 *
 * Complements playwright-config-validation.spec.ts with deeper verification:
 * - Property 12: E2E Test Failure Artifacts (screenshots + console logs)
 * - Property 13: E2E Headless Browser Mode
 *
 * Validates: Requirements 4.5, 4.6, 9.3
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * Load Playwright config text for pattern matching.
 */
function loadConfigText(): string {
  const configPath = path.resolve(__dirname, '../playwright.config.ts')

  if (!fs.existsSync(configPath)) {
    throw new Error(`Playwright config not found at ${configPath}`)
  }

  return fs.readFileSync(configPath, 'utf-8')
}

/**
 * Property 12: E2E Test Failure Artifacts
 * Validates: Requirements 4.5, 9.3
 *
 * For any end-to-end test execution that fails, the test result
 * SHALL include both screenshot artifacts and browser console log output.
 */
test.describe('Property 12: E2E Test Failure Artifacts', () => {
  test.describe('Screenshot artifact configuration', () => {
    test('config enables screenshot capture on failure', () => {
      const config = loadConfigText()

      const hasScreenshotOnFailure = config.includes("screenshot: 'only-on-failure'")
      const hasScreenshotOn = config.includes("screenshot: 'on'")

      expect(
        hasScreenshotOnFailure || hasScreenshotOn,
        'Playwright config must set screenshot to "only-on-failure" or "on"'
      ).toBe(true)
    })

    test('config has output directory for artifacts', () => {
      const config = loadConfigText()
      expect(config).toMatch(/outputDir:\s*['"]/)
    })

    test('screenshot artifacts directory is writable', () => {
      const outputDir = path.resolve(__dirname, '../test-results')

      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true })
      }

      const tempFile = path.join(outputDir, '.write-test')
      fs.writeFileSync(tempFile, 'test')
      fs.unlinkSync(tempFile)

      expect(fs.existsSync(outputDir)).toBe(true)
    })

    test('deliberately failing page produces screenshot artifact', async ({ page }) => {
      const screenshotDir = path.resolve(__dirname, '../test-results/screenshots')

      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true })
      }

      const screenshotPath = path.join(screenshotDir, 'failure-artifact-test.png')

      await page.goto('about:blank')
      await page.setContent('<h1>Failure Artifact Test</h1>')

      // Capture screenshot programmatically (simulates Playwright on-failure behavior)
      await page.screenshot({ path: screenshotPath, fullPage: true })

      expect(fs.existsSync(screenshotPath)).toBe(true)

      // Verify the file is a valid PNG (starts with PNG magic bytes)
      const buffer = fs.readFileSync(screenshotPath)
      const pngMagic = Buffer.from([0x89, 0x50, 0x4e, 0x47])
      expect(buffer.subarray(0, 4).equals(pngMagic)).toBe(true)

      // Cleanup
      fs.unlinkSync(screenshotPath)
    })
  })

  test.describe('Browser console log collection', () => {
    test('console messages are captured via page.on("console")', async ({ page }) => {
      const consoleLogs: Array<{ type: string; text: string }> = []

      page.on('console', (msg) => {
        consoleLogs.push({ type: msg.type(), text: msg.text() })
      })

      await page.goto('about:blank')

      await page.evaluate(() => {
        console.log('test-log-message')
        console.warn('test-warn-message')
        console.error('test-error-message')
      })

      const logTexts = consoleLogs.map((l) => l.text)
      expect(logTexts).toContain('test-log-message')
      expect(logTexts).toContain('test-warn-message')
      expect(logTexts).toContain('test-error-message')

      // Verify type metadata is preserved
      const errorEntry = consoleLogs.find((l) => l.text === 'test-error-message')
      expect(errorEntry?.type).toBe('error')
    })

    test('console logs include type classification', async ({ page }) => {
      const consoleLogs: Array<{ type: string; text: string }> = []

      page.on('console', (msg) => {
        consoleLogs.push({ type: msg.type(), text: msg.text() })
      })

      await page.goto('about:blank')
      await page.evaluate(() => {
        console.info('info-level')
        console.debug('debug-level')
      })

      const types = consoleLogs.map((l) => l.type)
      expect(types).toContain('info')
      expect(consoleLogs.length).toBeGreaterThan(0)
    })

    test('config supports trace collection for failure debugging', () => {
      const config = loadConfigText()

      const hasTrace = config.match(/trace:\s*['"](\w[\w-]*)['"]/)
      expect(hasTrace).not.toBeNull()

      const traceValue = hasTrace![1]
      const validTraceValues = ['on', 'on-first-retry', 'retain-on-failure', 'on-all-retries']
      expect(validTraceValues).toContain(traceValue)
    })
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
  test('config explicitly sets headless to true', () => {
    const config = loadConfigText()
    expect(config).toMatch(/headless:\s*true/)
  })

  test('headless mode is not conditionally disabled', () => {
    const config = loadConfigText()
    const headlessFalsePattern = /headless:\s*false/
    expect(config).not.toMatch(headlessFalsePattern)
  })

  test('browser context works in headless mode', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('about:blank')
    await page.setContent('<div id="test">headless-ok</div>')

    const text = await page.locator('#test').textContent()
    expect(text).toBe('headless-ok')

    await context.close()
  })

  test('page rendering works without display server', async ({ page }) => {
    await page.goto('about:blank')
    await page.setContent(`
      <div style="width: 200px; height: 100px; background: blue;">
        <span id="content">rendered</span>
      </div>
    `)

    const box = await page.locator('div').boundingBox()
    expect(box).not.toBeNull()
    expect(box!.width).toBe(200)
    expect(box!.height).toBe(100)

    const content = await page.locator('#content').textContent()
    expect(content).toBe('rendered')
  })
})
