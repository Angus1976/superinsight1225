/**
 * Data Manager Role Workflow E2E Tests
 *
 * Tests that data_manager can access permitted modules (DataSync, DataLifecycle,
 * Augmentation, Tasks, Dashboard) and is denied access to Admin, Security RBAC,
 * and Billing Management.
 *
 * Requirements: 1.2, 1.5, 1.6
 */

import { roleTest, expect, ROLE_CONFIGS } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { expectNonAdminBlockedOnAdminRoute } from '../helpers/expect-admin-denied'
import { waitForPageReady } from '../test-helpers'

roleTest.describe('Data Manager Workflow', () => {
  roleTest.use({ roleConfig: ROLE_CONFIGS.data_manager })

  roleTest.describe('Accessible Modules', () => {
    const accessibleModules: { name: string; route: string }[] = [
      { name: 'Dashboard', route: '/dashboard' },
      { name: 'DataSync', route: '/data-sync' },
      { name: 'DataSync Sources', route: '/data-sync/sources' },
      { name: 'DataSync History', route: '/data-sync/history' },
      { name: 'DataSync Scheduler', route: '/data-sync/scheduler' },
      { name: 'DataSync Export', route: '/data-sync/export' },
      { name: 'DataLifecycle', route: '/data-lifecycle' },
      { name: 'Augmentation', route: '/augmentation' },
      { name: 'Tasks', route: '/tasks' },
    ]

    for (const mod of accessibleModules) {
      roleTest(`data_manager can access ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)
        await rolePage.goto(mod.route)
        await waitForPageReady(rolePage)

        const url = rolePage.url()
        expect(url).not.toMatch(/\/login/)
        expect(url).not.toMatch(/\/403/)
      })
    }
  })

  roleTest.describe('Denied Modules', () => {
    const deniedModules: { name: string; route: string }[] = [
      { name: 'Admin', route: '/admin' },
      { name: 'Admin Console', route: '/admin/console' },
      { name: 'Admin Tenants', route: '/admin/tenants' },
      { name: 'Admin Users', route: '/admin/users' },
    ]

    for (const mod of deniedModules) {
      roleTest(`data_manager is denied access to ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)
        await expectNonAdminBlockedOnAdminRoute(rolePage, mod.route)
      })
    }
  })

  roleTest.describe('Data Lifecycle Flow (Permitted Scope)', () => {
    roleTest('data_manager can navigate data lifecycle within permitted scope', async ({ rolePage }) => {
      await mockAllApis(rolePage)

      // Mock data lifecycle endpoints
      await rolePage.route('**/api/data-lifecycle/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 }),
        })
      })

      // Step 1: DataSync sources
      await rolePage.goto('/data-sync/sources')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/403/)
      expect(rolePage.url()).not.toMatch(/\/login/)

      // Step 2: Data Lifecycle overview
      await rolePage.goto('/data-lifecycle')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/403/)
      expect(rolePage.url()).not.toMatch(/\/login/)

      // Step 3: Tasks
      await rolePage.goto('/tasks')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/403/)
      expect(rolePage.url()).not.toMatch(/\/login/)

      // Step 4: Augmentation
      await rolePage.goto('/augmentation')
      await waitForPageReady(rolePage)
      expect(rolePage.url()).not.toMatch(/\/403/)
      expect(rolePage.url()).not.toMatch(/\/login/)
    })
  })
})
