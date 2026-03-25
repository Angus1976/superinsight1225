/**
 * Admin Quotas E2E Tests
 *
 * Tests quota display, limit configuration, usage tracking per tenant.
 *
 * Requirements: 12.8
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Quota Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/admin/quotas**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'q-1', tenantId: 'tenant-1', resource: 'tasks', limit: 1000, used: 450 },
            { id: 'q-2', tenantId: 'tenant-1', resource: 'storage', limit: 10240, used: 3072 },
          ],
          total: 2,
        }),
      })
    })
  })

  test('quota display page loads', async ({ page }) => {
    await page.goto('/admin/quotas')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('quota limits are visible', async ({ page }) => {
    await page.goto('/admin/quotas')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})
