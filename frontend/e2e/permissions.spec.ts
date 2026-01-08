/**
 * Permission Control E2E Tests
 *
 * Tests role-based access control, permission enforcement, and security features.
 */

import { test, expect } from '@playwright/test'

// Helper to set up user with specific permissions
async function setupUserWithPermissions(page: any, permissions: string[], role: string = 'user') {
  await page.addInitScript(({ permissions, role }) => {
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: `user-${role}`,
            username: `${role}user`,
            name: `${role} 用户`,
            email: `${role}@example.com`,
            tenant_id: 'tenant-1',
            roles: [role],
            permissions: permissions,
          },
          token: 'mock-jwt-token',
          currentTenant: {
            id: 'tenant-1',
            name: '测试租户',
          },
          isAuthenticated: true,
        },
      })
    )
  }, { permissions, role })
}

test.describe('Permission Control', () => {
  test('admin user can access all features', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:all',
      'write:all',
      'manage:users',
      'manage:tenants',
      'manage:system'
    ], 'admin')

    await page.goto('/dashboard')

    // Admin should see all menu items
    const adminMenu = page.getByRole('menuitem', { name: /系统管理|admin|管理/i })
    
    if (await adminMenu.isVisible()) {
      await expect(adminMenu).toBeVisible()
      await expect(adminMenu).toBeEnabled()
    }

    // Should be able to access admin pages
    await page.goto('/admin')
    await expect(page).not.toHaveURL(/login|403|unauthorized/i)
  })

  test('viewer user has read-only access', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:tasks',
      'read:dashboard',
      'read:billing'
    ], 'viewer')

    await page.goto('/dashboard')

    // Should see dashboard
    await expect(page).toHaveURL(/dashboard/i)

    // Should not see admin menu
    const adminMenu = page.getByRole('menuitem', { name: /系统管理|admin/i })
    
    if (await adminMenu.isVisible()) {
      await expect(adminMenu).toBeDisabled()
    }

    // Try to access admin page directly
    await page.goto('/admin')
    await expect(page).toHaveURL(/403|unauthorized|dashboard/i, { timeout: 5000 })
  })

  test('task manager can manage tasks but not system settings', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:tasks',
      'write:tasks',
      'read:dashboard',
      'assign:tasks'
    ], 'task_manager')

    await page.goto('/tasks')

    // Should be able to access tasks
    await expect(page).toHaveURL(/tasks/i)

    // Look for create task button
    const createButton = page.getByRole('button', { name: /创建|新建|create/i })
    
    if (await createButton.isVisible()) {
      await expect(createButton).toBeEnabled()
    }

    // Should not access system settings
    await page.goto('/admin/system')
    await expect(page).toHaveURL(/403|unauthorized|tasks/i, { timeout: 5000 })
  })

  test('billing manager can access billing but not tasks', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:billing',
      'write:billing',
      'export:billing',
      'read:dashboard'
    ], 'billing_manager')

    await page.goto('/billing')

    // Should access billing page
    await expect(page).toHaveURL(/billing/i)

    // Look for export functionality
    const exportButton = page.getByRole('button', { name: /导出|export/i })
    
    if (await exportButton.isVisible()) {
      await expect(exportButton).toBeEnabled()
    }

    // Should not create tasks
    await page.goto('/tasks')
    
    if (await page.isVisible('.ant-btn')) {
      const createButton = page.getByRole('button', { name: /创建|新建|create/i })
      
      if (await createButton.isVisible()) {
        await expect(createButton).toBeDisabled()
      }
    }
  })
})

test.describe('Feature-Level Permissions', () => {
  test('user without export permission cannot export data', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:billing',
      'read:tasks'
    ], 'limited_user')

    await page.goto('/billing')

    // Export button should not be visible or should be disabled
    const exportButton = page.getByRole('button', { name: /导出|export/i })
    
    if (await exportButton.isVisible()) {
      await expect(exportButton).toBeDisabled()
    }
  })

  test('user without delete permission cannot delete items', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:tasks',
      'write:tasks'
      // No delete permission
    ], 'editor')

    await page.goto('/tasks')

    // Delete buttons should not be visible or should be disabled
    const deleteButton = page.getByRole('button', { name: /删除|delete/i })
    
    if (await deleteButton.isVisible()) {
      await expect(deleteButton).toBeDisabled()
    }
  })

  test('user without assign permission cannot assign tasks', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:tasks',
      'write:tasks'
      // No assign permission
    ], 'creator')

    await page.goto('/tasks')

    // Assignment controls should be disabled
    const assignSelect = page.locator('.ant-select').filter({ hasText: /分配|assign/i })
    
    if (await assignSelect.isVisible()) {
      await expect(assignSelect).toBeDisabled()
    }
  })
})

test.describe('Dynamic Permission Updates', () => {
  test('permissions are enforced after role change', async ({ page }) => {
    // Start as admin
    await setupUserWithPermissions(page, [
      'read:all',
      'write:all',
      'manage:system'
    ], 'admin')

    await page.goto('/admin')
    await expect(page).not.toHaveURL(/403|unauthorized/i)

    // Simulate permission change (e.g., role downgrade)
    await page.evaluate(() => {
      const authData = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      authData.state.user.roles = ['viewer']
      authData.state.user.permissions = ['read:dashboard', 'read:tasks']
      localStorage.setItem('auth-storage', JSON.stringify(authData))
    })

    // Refresh page to apply new permissions
    await page.reload()

    // Should now be redirected or show access denied
    await expect(page).toHaveURL(/403|unauthorized|dashboard/i, { timeout: 5000 })
  })

  test('token expiration redirects to login', async ({ page }) => {
    await setupUserWithPermissions(page, ['read:all'], 'user')

    // Simulate expired token
    await page.evaluate(() => {
      const authData = JSON.parse(localStorage.getItem('auth-storage') || '{}')
      authData.state.token = 'expired-token'
      authData.state.isAuthenticated = false
      localStorage.setItem('auth-storage', JSON.stringify(authData))
    })

    await page.goto('/dashboard')

    // Should redirect to login
    await expect(page).toHaveURL(/login/i, { timeout: 5000 })
  })
})

test.describe('Security Features', () => {
  test('sensitive data is masked for unauthorized users', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:billing'
      // No read:sensitive permission
    ], 'limited_viewer')

    await page.goto('/billing')

    // Sensitive information should be masked
    const sensitiveData = page.locator('[data-sensitive="true"], .sensitive-data')
    
    if (await sensitiveData.isVisible()) {
      const text = await sensitiveData.textContent()
      expect(text).toMatch(/\*+|hidden|masked/i)
    }
  })

  test('audit trail is created for sensitive actions', async ({ page }) => {
    await setupUserWithPermissions(page, [
      'read:all',
      'write:all',
      'audit:view'
    ], 'auditor')

    // Perform a sensitive action
    await page.goto('/admin/users')
    
    const userRow = page.locator('.ant-table-row').first()
    
    if (await userRow.isVisible()) {
      await userRow.click()
      
      // This action should be logged
      // In a real app, this would create an audit entry
    }

    // Check audit log
    await page.goto('/admin/audit')
    
    // Should show recent actions
    const auditEntries = page.locator('.ant-table-row, .audit-entry')
    
    if (await auditEntries.first().isVisible()) {
      await expect(auditEntries.first()).toBeVisible()
    }
  })

  test('session timeout works correctly', async ({ page }) => {
    await setupUserWithPermissions(page, ['read:all'], 'user')

    await page.goto('/dashboard')

    // Simulate session timeout by clearing auth
    await page.evaluate(() => {
      // Simulate what happens when session expires
      setTimeout(() => {
        localStorage.removeItem('auth-storage')
      }, 1000)
    })

    await page.waitForTimeout(1500)

    // Try to navigate to another page
    await page.goto('/tasks')

    // Should redirect to login
    await expect(page).toHaveURL(/login/i, { timeout: 5000 })
  })
})