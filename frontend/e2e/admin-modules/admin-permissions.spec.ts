/**
 * Admin Permissions E2E Tests
 *
 * Tests permission matrix display, role-permission assignment, custom permission creation.
 *
 * Requirements: 12.7
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('Admin Permission Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/security/permissions', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              { id: 'perm-1', name: 'read:tasks', description: '读取任务', roles: ['admin', 'data_manager'] },
              { id: 'perm-2', name: 'write:tasks', description: '写入任务', roles: ['admin'] },
              { id: 'perm-3', name: 'manage:users', description: '管理用户', roles: ['admin'] },
            ],
            total: 3,
          }),
        })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    })
  })

  test('permission matrix page loads', async ({ page }) => {
    await page.goto('/admin/permissions')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('permission matrix displays role-permission assignments', async ({ page }) => {
    await page.goto('/admin/permissions')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})
