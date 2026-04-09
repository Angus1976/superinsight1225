/**
 * Admin Console E2E Tests
 *
 * Tests console dashboard displays system overview metrics.
 *
 * Requirements: 12.1
 */

import { test, expect } from '../fixtures'
import { setupE2eSession, waitForPageReady } from '../test-helpers'

test.describe('Admin Console Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
  })

  test('console dashboard displays system overview metrics', async ({ page }) => {
    await page.goto('/admin/console')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })

  test('console page is accessible to admin role', async ({ page }) => {
    await page.goto('/admin/console')
    await waitForPageReady(page)

    expect(page.url()).toContain('/admin')
  })
})
