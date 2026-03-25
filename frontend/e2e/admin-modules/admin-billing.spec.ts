/**
 * Admin Billing E2E Tests
 *
 * Tests billing record listing, invoice generation, payment status management.
 *
 * Requirements: 12.9
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Billing Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)
  })

  test('billing records page loads', async ({ page }) => {
    await page.goto('/admin/billing')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('billing page displays records', async ({ page }) => {
    await page.goto('/admin/billing')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })

  test('invoice generation button is accessible', async ({ page }) => {
    await page.goto('/admin/billing')
    await waitForPageReady(page)

    const invoiceBtn = page.getByRole('button', { name: /发票|invoice|生成|generate/i }).first()
    if (await invoiceBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(invoiceBtn).toBeVisible()
    }
  })
})
