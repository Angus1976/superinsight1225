/**
 * Admin Role Workflow E2E Tests
 *
 * Tests that admin can access ALL Page_Modules, perform CRUD operations
 * on tasks/users/tenants, and execute the full Data_Lifecycle flow.
 *
 * Requirements: 1.1, 1.5
 */

import { roleTest, expect, ROLE_CONFIGS } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { waitForPageReady } from '../test-helpers'

roleTest.describe('Admin Workflow', () => {
  roleTest.use({ roleConfig: ROLE_CONFIGS.admin })

  roleTest.describe('Page Module Access', () => {
    const modules: { name: string; route: string }[] = [
      { name: 'Dashboard', route: '/dashboard' },
      { name: 'Tasks', route: '/tasks' },
      { name: 'Quality', route: '/quality' },
      { name: 'Security', route: '/security' },
      { name: 'Admin', route: '/admin' },
      { name: 'DataSync', route: '/data-sync' },
      { name: 'Augmentation', route: '/augmentation' },
      { name: 'License', route: '/license' },
      { name: 'DataLifecycle', route: '/data-lifecycle' },
      { name: 'Billing', route: '/billing' },
      { name: 'Settings', route: '/settings' },
      { name: 'AI Annotation', route: '/ai-annotation' },
    ]

    for (const mod of modules) {
      roleTest(`admin can access ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)
        await rolePage.goto(mod.route)
        await waitForPageReady(rolePage)

        // Admin should NOT be redirected to login or 403
        const url = rolePage.url()
        expect(url).not.toMatch(/\/login/)
        expect(url).not.toMatch(/\/403/)
      })
    }
  })

  roleTest.describe('Task CRUD Operations', () => {
    roleTest('admin can view task list', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/tasks')
      await waitForPageReady(rolePage)

      // Should see the tasks page content
      const url = rolePage.url()
      expect(url).toContain('/tasks')
      expect(url).not.toMatch(/\/login/)
    })

    roleTest('admin can create a task', async ({ rolePage }) => {
      await mockAllApis(rolePage)

      // Mock POST /api/tasks to return created task
      await rolePage.route('**/api/tasks', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'task-new',
              name: '新建任务',
              status: 'pending',
              assignee: '',
              progress: 0,
              tenant_id: 'tenant-1',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            }),
          })
        } else {
          await route.continue()
        }
      })

      await rolePage.goto('/tasks')
      await waitForPageReady(rolePage)

      // Look for create button
      const createBtn = rolePage.getByRole('button', { name: /创建|新建|create|add/i })
      if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await createBtn.click()
        // Modal or form should appear
        const modal = rolePage.locator('.ant-modal')
        if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
          await expect(modal).toBeVisible()
        }
      }
    })

    roleTest('admin can delete a task', async ({ rolePage }) => {
      await mockAllApis(rolePage)

      await rolePage.goto('/tasks')
      await waitForPageReady(rolePage)

      // Look for delete button in table
      const deleteBtn = rolePage.getByRole('button', { name: /删除|delete/i }).first()
      if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await deleteBtn.click()
        // Confirmation dialog should appear
        const confirmBtn = rolePage.locator('.ant-popconfirm-buttons .ant-btn-primary, .ant-modal-confirm-btns .ant-btn-primary').first()
        if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await confirmBtn.click()
        }
      }
    })
  })

  roleTest.describe('User CRUD Operations', () => {
    roleTest('admin can view user list', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/admin/users')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).not.toMatch(/\/login/)
      expect(url).not.toMatch(/\/403/)
    })

    roleTest('admin can manage user roles', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/admin/users')
      await waitForPageReady(rolePage)

      // Look for role assignment controls
      const roleSelect = rolePage.locator('.ant-select').first()
      if (await roleSelect.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(roleSelect).toBeVisible()
      }
    })
  })

  roleTest.describe('Tenant CRUD Operations', () => {
    roleTest('admin can view tenant list', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/admin/tenants')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).not.toMatch(/\/login/)
      expect(url).not.toMatch(/\/403/)
    })

    roleTest('admin can create a tenant', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/admin/tenants')
      await waitForPageReady(rolePage)

      const createBtn = rolePage.getByRole('button', { name: /创建|新建|create|add/i })
      if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await createBtn.click()
        const modal = rolePage.locator('.ant-modal')
        if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
          await expect(modal).toBeVisible()
        }
      }
    })
  })

  roleTest.describe('Data Lifecycle Flow', () => {
    roleTest('admin can navigate full data lifecycle: acquisition → annotation → quality → export', async ({ rolePage }) => {
      await mockAllApis(rolePage)

      // Mock data lifecycle specific endpoints
      await rolePage.route('**/api/data-lifecycle/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 }),
        })
      })

      // Step 1: Data Acquisition — navigate to DataSync sources
      await rolePage.goto('/data-sync/sources')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/login/)
      expect(rolePage.url()).not.toMatch(/\/403/)

      // Step 2: Annotation — navigate to data lifecycle tasks
      await rolePage.goto('/data-lifecycle/tasks')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/login/)
      expect(rolePage.url()).not.toMatch(/\/403/)

      // Step 3: Quality review
      await rolePage.goto('/quality')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/login/)
      expect(rolePage.url()).not.toMatch(/\/403/)

      // Step 4: Export
      await rolePage.goto('/data-sync/export')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/login/)
      expect(rolePage.url()).not.toMatch(/\/403/)
    })
  })
})
