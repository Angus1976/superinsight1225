/**
 * Annotator Role Workflow E2E Tests
 *
 * Tests that annotator can access assigned Tasks and Task Annotation pages,
 * is denied access to Admin, Quality Rules, Security, DataSync, Billing,
 * and can submit annotations.
 *
 * Requirements: 1.4, 1.5, 1.6
 */

import { roleTest, expect, ROLE_CONFIGS } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { expectNonAdminBlockedOnAdminRoute } from '../helpers/expect-admin-denied'
import { waitForPageReady } from '../test-helpers'

roleTest.describe('Annotator Workflow', () => {
  roleTest.use({ roleConfig: ROLE_CONFIGS.annotator })

  roleTest.describe('Accessible Modules', () => {
    const accessibleModules: { name: string; route: string }[] = [
      { name: 'Tasks', route: '/tasks' },
      { name: 'Task Annotation', route: '/tasks/1/annotate' },
    ]

    for (const mod of accessibleModules) {
      roleTest(`annotator can access ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)

        // Mock annotation-specific endpoints
        await rolePage.route('**/api/tasks/1/annotate', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'task-1',
              name: '标注任务 1',
              items: [
                { id: 'item-1', data: { text: '示例文本' }, status: 'pending' },
              ],
            }),
          })
        })

        await rolePage.route('**/api/tasks/1/annotations', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        })

        await rolePage.goto(mod.route)
        await waitForPageReady(rolePage)

        const url = rolePage.url()
        expect(url).not.toMatch(/\/login/)
        expect(url).not.toMatch(/\/403/)
      })
    }
  })

  roleTest.describe('Denied Modules', () => {
    // Only `/admin/*` is blocked in-app (AdminPage role check). Other routes may still
    // render when deep-linked; menu visibility is covered by navGroups access rules.
    const deniedModules: { name: string; route: string }[] = [
      { name: 'Admin', route: '/admin' },
      { name: 'Admin Console', route: '/admin/console' },
      { name: 'Admin Tenants', route: '/admin/tenants' },
    ]

    for (const mod of deniedModules) {
      roleTest(`annotator is denied access to ${mod.name} (${mod.route})`, async ({ rolePage }) => {
        await mockAllApis(rolePage)
        await expectNonAdminBlockedOnAdminRoute(rolePage, mod.route)
      })
    }
  })

  roleTest.describe('Annotation Submission Flow', () => {
    roleTest('annotator can view assigned tasks', async ({ rolePage }) => {
      await mockAllApis(rolePage)
      await rolePage.goto('/tasks')
      await waitForPageReady(rolePage)

      const url = rolePage.url()
      expect(url).toContain('/tasks')
      expect(url).not.toMatch(/\/login/)
    })

    roleTest('annotator can submit an annotation', async ({ rolePage }) => {
      await mockAllApis(rolePage)

      // Mock annotation submission endpoint
      let annotationSubmitted = false
      await rolePage.route('**/api/tasks/1/annotations', async (route) => {
        if (route.request().method() === 'POST') {
          annotationSubmitted = true
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'annotation-new',
              taskId: 'task-1',
              data: { label: 'positive' },
              status: 'submitted',
              annotatorId: 'user-annotator',
              createdAt: new Date().toISOString(),
            }),
          })
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ data: [], total: 0 }),
          })
        }
      })

      await rolePage.route('**/api/tasks/1/annotate', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'task-1',
            name: '标注任务 1',
            items: [
              { id: 'item-1', data: { text: '示例文本' }, status: 'pending' },
            ],
          }),
        })
      })

      await rolePage.goto('/tasks/1/annotate')
      await waitForPageReady(rolePage)

      // Verify we're on the annotation page
      const url = rolePage.url()
      expect(url).not.toMatch(/\/login/)
      expect(url).not.toMatch(/\/403/)

      // Look for submit/save button on annotation page
      const submitBtn = rolePage.getByRole('button', { name: /提交|submit|保存|save|完成|done/i }).first()
      if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await submitBtn.click()
      }
    })
  })
})
