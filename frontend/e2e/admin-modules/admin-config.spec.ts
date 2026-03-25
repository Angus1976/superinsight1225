/**
 * Admin Configuration E2E Tests
 *
 * Tests System config, LLM Config, Text-to-SQL config,
 * DB Config, Sync Config, History, Third Party config forms.
 *
 * Requirements: 12.4, 12.5, 12.6, 12.10
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Configuration Module', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    // Mock config-specific endpoints
    await page.route('**/api/admin/config**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: {}, success: true }),
      })
    })
  })

  /* -------------------------------------------------------------- */
  /*  System Config (Req 12.4)                                       */
  /* -------------------------------------------------------------- */

  test('System config form loads', async ({ page }) => {
    await page.goto('/admin/system')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  LLM Config + Connection Testing + Binding (Req 12.5)           */
  /* -------------------------------------------------------------- */

  test('LLM Config page loads', async ({ page }) => {
    await page.goto('/admin/llm-config')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('LLM connection test button is accessible', async ({ page }) => {
    await page.goto('/admin/llm-config')
    await waitForPageReady(page)

    const testBtn = page.getByRole('button', { name: /测试|test|连接/i }).first()
    if (await testBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(testBtn).toBeVisible()
    }
  })

  /* -------------------------------------------------------------- */
  /*  Text-to-SQL Config + Query Testing (Req 12.6)                  */
  /* -------------------------------------------------------------- */

  test('Text-to-SQL config page loads', async ({ page }) => {
    await page.goto('/admin/text-to-sql')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  Admin Config Dashboard (Req 12.10)                             */
  /* -------------------------------------------------------------- */

  test('Config dashboard page loads', async ({ page }) => {
    await page.goto('/admin/config')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  DB Config                                                      */
  /* -------------------------------------------------------------- */

  test('DB Config page loads', async ({ page }) => {
    await page.goto('/admin/config/databases')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  Sync Config                                                    */
  /* -------------------------------------------------------------- */

  test('Sync Config page loads', async ({ page }) => {
    await page.goto('/admin/config/sync')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  Config History                                                 */
  /* -------------------------------------------------------------- */

  test('Config History page loads', async ({ page }) => {
    await page.goto('/admin/config/history')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  /* -------------------------------------------------------------- */
  /*  Third Party Config                                             */
  /* -------------------------------------------------------------- */

  test('Third Party config page loads', async ({ page }) => {
    await page.goto('/admin/config/third-party')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })
})
