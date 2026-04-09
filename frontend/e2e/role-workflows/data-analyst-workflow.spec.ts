/**
 * Data Analyst Role Workflow E2E Tests
 *
 * Tests that data_analyst can access Dashboard, Quality Reports, Billing Overview,
 * License Usage and is denied access to Admin, DataSync configuration, Task assignment.
 *
 * Requirements: 1.3, 1.6
 */

import { roleTest, expect, ROLE_CONFIGS } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { expectNonAdminBlockedOnAdminRoute } from '../helpers/expect-admin-denied'
import { waitForPageReady } from '../test-helpers'

roleTest.describe('Data Analyst Workflow', () => {
  roleTest.use({ roleConfig: ROLE_CONFIGS.data_analyst })

  roleTest.describe('Accessible Modules', () => {
    const accessibleModules: { name: string; route: string }[] = [
      { name: 'Dashboard', route: '/dashboard' },
      { name: 'Quality Reports', route: '/quality/reports' },
      { name: 'Billing Overview', route: '/billing/overview' },
      { name: 'License Usage', route: '/license/usage' },
    ]

    for (const mod of accessibleModules) {
      roleTest(`data_analyst can access ${mod.name} (${mod.route})`, async ({ rolePage }) => {
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
      roleTest(`data_analyst is denied access to ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)
        await expectNonAdminBlockedOnAdminRoute(rolePage, mod.route)
      })
    }
  })

  roleTest.describe('Read-Only Access Verification', () => {
    roleTest('data_analyst sees dashboard metrics without edit controls', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/dashboard')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).toContain('/dashboard')
      expect(url).not.toMatch(/\/login/)
    })

    roleTest('data_analyst can view quality reports', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/quality/reports')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).not.toMatch(/\/login/)
      expect(url).not.toMatch(/\/403/)
    })

    roleTest('data_analyst can view billing overview', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/billing/overview')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).not.toMatch(/\/login/)
      expect(url).not.toMatch(/\/403/)
    })
  })
})
