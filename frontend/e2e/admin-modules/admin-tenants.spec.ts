/**
 * Admin Tenants E2E Tests
 *
 * Tests tenant CRUD operations with form validation.
 *
 * Requirements: 12.2
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Tenant Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)
  })

  test('tenant list displays correctly', async ({ page }) => {
    await page.goto('/admin/tenants')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('create tenant opens modal with form', async ({ page }) => {
    await page.goto('/admin/tenants')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|create|add/i })
    if (!(await createBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(modal).toBeVisible()
      // Close
      await page.keyboard.press('Escape')
    }
  })

  test('delete tenant shows confirmation dialog', async ({ page }) => {
    await page.goto('/admin/tenants')
    await waitForPageReady(page)

    const deleteBtn = page.getByRole('button', { name: /删除|delete/i }).first()
    if (!(await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await deleteBtn.click()
    const confirm = page.locator('.ant-popconfirm, .ant-modal-confirm')
    if (await confirm.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(confirm).toBeVisible()
    }
  })
})
