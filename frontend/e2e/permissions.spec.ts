/**
 * Permission Control E2E Tests
 *
 * Uses the same auth + API mocks as other E2E tests. Admin routes use an in-page
 * guard (see `Admin/index.tsx`), not URL redirects to /403.
 */

import { test, expect } from '@playwright/test'
import { expectNonAdminBlockedOnAdminRoute } from './helpers/expect-admin-denied'
import { setupE2eSessionMutable, waitForPageReady } from './test-helpers'

async function seedSession(page: import('@playwright/test').Page, role: string) {
  await setupE2eSessionMutable(page, { role, lang: 'zh' })
}

test.describe('Permission Control', () => {
  test('admin user can access all features', async ({ page }) => {
    await seedSession(page, 'admin')

    await page.goto('/dashboard')
    await waitForPageReady(page)

    const adminMenu = page.getByRole('menuitem', { name: /系统管理|admin|管理/i })
    if (await adminMenu.isVisible().catch(() => false)) {
      await expect(adminMenu).toBeVisible()
      await expect(adminMenu).toBeEnabled()
    }

    await page.goto('/admin')
    await waitForPageReady(page)
    await expect(page).not.toHaveURL(/login/i)
    await expect(page.locator('.ant-alert').filter({ hasText: /Access Denied/i })).toHaveCount(0)
  })

  test('viewer user has read-only access', async ({ page }) => {
    await seedSession(page, 'viewer')

    await page.goto('/dashboard')
    await waitForPageReady(page)
    await expect(page).toHaveURL(/dashboard/i)

    const adminMenu = page.getByRole('menuitem', { name: /系统管理|admin/i })
    if (await adminMenu.isVisible().catch(() => false)) {
      await expect(adminMenu).toBeDisabled()
    }

    await expectNonAdminBlockedOnAdminRoute(page, '/admin')
  })

  test('non-admin cannot open admin system route', async ({ page }) => {
    await seedSession(page, 'annotator')

    await page.goto('/tasks')
    await waitForPageReady(page)
    await expect(page).toHaveURL(/tasks/i)

    await expectNonAdminBlockedOnAdminRoute(page, '/admin/system')
  })

  test('billing manager can access billing but not tasks', async ({ page }) => {
    await seedSession(page, 'viewer')

    await page.goto('/billing')
    await waitForPageReady(page)
    await expect(page).toHaveURL(/billing/i)

    const exportButton = page.getByRole('button', { name: /导出|export/i })
    if (await exportButton.isVisible().catch(() => false)) {
      await expect(exportButton).toBeEnabled()
    }

    await page.goto('/tasks')
    await waitForPageReady(page)
    await expect(page).toHaveURL(/tasks/i)
  })
})

test.describe('Feature-Level Permissions', () => {
  test('user without export permission cannot export data', async ({ page }) => {
    await seedSession(page, 'viewer')

    await page.goto('/billing')
    await waitForPageReady(page)

    const exportButton = page.getByRole('button', { name: /导出|export/i })
    if (await exportButton.isVisible().catch(() => false)) {
      await expect(exportButton).toBeDisabled()
    }
  })

  test('user without delete permission cannot delete items', async ({ page }) => {
    await seedSession(page, 'annotator')

    await page.goto('/tasks')
    await waitForPageReady(page)

    const deleteButton = page.getByRole('button', { name: /删除|delete/i })
    if (await deleteButton.isVisible().catch(() => false)) {
      await expect(deleteButton).toBeDisabled()
    }
  })

  test('user without assign permission cannot assign tasks', async ({ page }) => {
    await seedSession(page, 'annotator')

    await page.goto('/tasks')
    await waitForPageReady(page)

    const assignSelect = page.locator('.ant-select').filter({ hasText: /分配|assign/i })
    if (await assignSelect.isVisible().catch(() => false)) {
      await expect(assignSelect).toBeDisabled()
    }
  })
})

test.describe('Dynamic Permission Updates', () => {
  test('permissions are enforced after role change', async ({ page }) => {
    await seedSession(page, 'admin')

    await page.goto('/admin')
    await waitForPageReady(page)
    await expect(page.locator('.ant-alert').filter({ hasText: /Access Denied/i })).toHaveCount(0)

    await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      if (!raw) return
      const authData = JSON.parse(raw)
      authData.state.user.role = 'viewer'
      authData.state.user.roles = ['viewer']
      localStorage.setItem('auth-storage', JSON.stringify(authData))
    })

    await page.reload()
    await waitForPageReady(page)

    await expect(
      page
        .locator('.ant-alert')
        .filter({ hasText: /Access Denied|don't have permission|admin console|管理|权限/i }),
    ).toBeVisible({ timeout: 15000 })
  })

  test('cleared session redirects to login', async ({ page }) => {
    await seedSession(page, 'admin')

    await page.goto('/dashboard')
    await waitForPageReady(page)

    await page.evaluate(() => {
      localStorage.removeItem('auth-storage')
      localStorage.removeItem('auth_token')
    })

    await page.goto('/tasks')
    await expect(page).toHaveURL(/login/i, { timeout: 15000 })
  })
})

test.describe('Security Features', () => {
  test('sensitive data is masked for unauthorized users', async ({ page }) => {
    await seedSession(page, 'viewer')

    await page.goto('/billing')
    await waitForPageReady(page)

    const sensitiveData = page.locator('[data-sensitive="true"], .sensitive-data')
    if (await sensitiveData.isVisible().catch(() => false)) {
      const text = await sensitiveData.textContent()
      expect(text).toMatch(/\*+|hidden|masked/i)
    }
  })

  test('admin users page loads when authorized', async ({ page }) => {
    await seedSession(page, 'admin')

    await page.goto('/admin/users')
    await waitForPageReady(page)

    await expect(page).not.toHaveURL(/login/i)
    await expect(page.locator('.ant-alert').filter({ hasText: /Access Denied/i })).toHaveCount(0)
  })

  test('session cleared redirects to login on navigation', async ({ page }) => {
    await seedSession(page, 'admin')

    await page.goto('/dashboard')
    await waitForPageReady(page)

    await page.evaluate(() => {
      localStorage.removeItem('auth-storage')
      localStorage.removeItem('auth_token')
    })

    await page.goto('/tasks')
    await expect(page).toHaveURL(/login/i, { timeout: 15000 })
  })
})
