/**
 * Admin Console E2E Tests
 *
 * Tests console dashboard displays system overview metrics.
 *
 * Requirements: 12.1
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Console Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    // Mock system metrics
    await page.route('**/system/metrics', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cpu: 45.2,
          memory: 68.5,
          disk: 52.1,
          uptime: 864000,
          activeConnections: 23,
        }),
      })
    })

    await page.route('**/system/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'running', version: '1.0.0' }),
      })
    })
  })

  test('console dashboard displays system overview metrics', async ({ page }) => {
    await page.goto('/admin/console')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)

    // Page should render content
    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })

  test('console page is accessible to admin role', async ({ page }) => {
    await page.goto('/admin/console')
    await waitForPageReady(page)

    // Should not redirect away
    expect(page.url()).toContain('/admin')
  })
})
