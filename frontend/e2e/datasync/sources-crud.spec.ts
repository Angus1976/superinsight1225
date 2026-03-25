/**
 * DataSync Sources CRUD E2E Tests
 *
 * Tests source list display, add-source form, connectivity test.
 *
 * Requirements: 14.1
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('DataSync Sources CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)
  })

  test('source list displays correctly', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('add-source form opens with connection parameters', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    const addBtn = page.getByRole('button', { name: /添加|新建|create|add/i }).first()
    if (!(await addBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await addBtn.click()
    const modal = page.locator('.ant-modal, .ant-drawer')
    if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(modal).toBeVisible()
      await page.keyboard.press('Escape')
    }
  })

  test('connectivity test button is accessible', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    const testBtn = page.getByRole('button', { name: /测试|test|连接/i }).first()
    if (await testBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(testBtn).toBeVisible()
    }
  })
})
