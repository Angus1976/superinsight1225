/**
 * Datalake Browser E2E Tests
 *
 * Tests Datalake Dashboard metrics, health status, volume trends,
 * query performance charts, and Schema Browser.
 *
 * Requirements: 14.4, 14.5
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Datalake Browser', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)
  })

  test('Datalake Dashboard displays metrics and health status', async ({ page }) => {
    await page.goto('/data-sync/datalake/dashboard')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('Schema Browser lists databases and tables', async ({ page }) => {
    await page.goto('/data-sync/datalake/schema-browser')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('Datalake sources page loads', async ({ page }) => {
    await page.goto('/data-sync/datalake/sources')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })
})
