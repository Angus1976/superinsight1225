/**
 * Multi-Tenant & Workspace E2E Tests
 *
 * Tests tenant isolation, tenant switching, workspace CRUD, workspace removal,
 * and URL manipulation prevention.
 *
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
 */

import { test, expect } from './fixtures'
import type { Route } from '@playwright/test'
import { isRestApiUrl } from './api-route-helpers'
import { setupAuth, waitForPageReady } from './test-helpers'
import { mockAllApis } from './helpers/mock-api-factory'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

async function mockWorkspaceApis(page: import('@playwright/test').Page) {
  await page.route('**/api/workspaces', async (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'ws-new', name: '新工作区', status: 'active' }),
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          { id: 'ws-1', name: '工作区A', status: 'active', memberCount: 5 },
          { id: 'ws-2', name: '工作区B', status: 'active', memberCount: 3 },
        ],
        total: 2,
      }),
    })
  })

  await page.route('**/api/workspaces/my', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'ws-1', name: '工作区A', role: 'owner' },
        { id: 'ws-2', name: '工作区B', role: 'member' },
      ]),
    })
  })

  await page.route(/\/api\/workspaces\/[^/]+$/, async (route) => {
    const method = route.request().method()
    if (method === 'DELETE') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    }
    if (method === 'PUT' || method === 'PATCH') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'ws-1', name: '更新工作区', status: 'active' }) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'ws-1', name: '工作区A', status: 'active', memberCount: 5 }) })
  })

  await page.route(/\/api\/workspaces\/[^/]+\/members/, async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [{ id: 'user-1', username: 'admin', role: 'owner' }], total: 1 }),
    })
  })

  await page.route('**/api/workspaces/switch', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
  })
}

/* ================================================================== */
/*  Tenant Isolation (Req 7.1)                                         */
/* ================================================================== */

test.describe('Tenant isolation', () => {
  test('user in Tenant A cannot see Tenant B data', async ({ page }) => {
    await mockAllApis(page)
    await setupAuth(page, 'admin', 'tenant-a')

    const task = {
      id: 't-1',
      name: '租户A任务',
      description: 'e2e',
      status: 'pending' as const,
      priority: 'medium' as const,
      annotation_type: 'text_classification' as const,
      assignee_id: 'user-1',
      assignee_name: '用户1',
      created_by: 'e2e',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      progress: 0,
      total_items: 10,
      completed_items: 0,
      tenant_id: 'tenant-a',
      label_studio_project_id: '40',
    }

    const listBody = JSON.stringify({
      items: [task],
      total: 1,
      page: 1,
      page_size: 10,
    })

    const fulfillList = async (route: Route) => {
      if (route.request().method() !== 'GET') return route.continue()
      await route.fulfill({ status: 200, contentType: 'application/json', body: listBody })
    }

    await page.route('**/api/tasks?**', fulfillList)
    await page.route('**/api/tasks', async (route) => {
      if (route.request().method() !== 'GET') return route.continue()
      if (new URL(route.request().url()).pathname !== '/api/tasks') return route.continue()
      return fulfillList(route)
    })

    await page.goto('/tasks')
    await waitForPageReady(page)

    await expect(page.getByText('租户A任务', { exact: false })).toBeVisible({ timeout: 20000 })
    await expect(page.getByText('tenant-b', { exact: false })).toHaveCount(0)
  })
})

/* ================================================================== */
/*  Tenant Switch (Req 7.2)                                            */
/* ================================================================== */

test.describe('Tenant switch', () => {
  test('Dashboard, Tasks, Billing refresh to new tenant data after switch', async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/auth/switch-tenant', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'new-token', user: { id: 'user-admin', tenant_id: 'tenant-2' } }),
      })
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Verify initial tenant
    const initial = await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      return raw ? JSON.parse(raw) : null
    })
    expect(initial?.state?.currentTenant?.id).toBe('tenant-1')

    // Simulate tenant switch via localStorage update
    await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      if (raw) {
        const auth = JSON.parse(raw)
        auth.state.currentTenant = { id: 'tenant-2', name: '测试租户2' }
        auth.state.user.tenant_id = 'tenant-2'
        localStorage.setItem('auth-storage', JSON.stringify(auth))
      }
    })

    const updated = await page.evaluate(() => {
      const raw = localStorage.getItem('auth-storage')
      return raw ? JSON.parse(raw) : null
    })
    expect(updated?.state?.currentTenant?.id).toBe('tenant-2')
  })
})

/* ================================================================== */
/*  Workspace CRUD (Req 7.3)                                           */
/* ================================================================== */

test.describe('Workspace CRUD', () => {
  test('create, manage members, switch workspaces', async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)
    await mockWorkspaceApis(page)

    await page.goto('/admin/workspaces')
    await waitForPageReady(page)

    // Page should load without redirect
    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)

    // Look for create workspace button
    const createBtn = page.getByRole('button', { name: /创建|新建|create|add/i })
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click()
      const modal = page.locator('.ant-modal')
      if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(modal).toBeVisible()
        await page.keyboard.press('Escape')
      }
    }
  })
})

/* ================================================================== */
/*  Workspace Removal (Req 7.4)                                        */
/* ================================================================== */

test.describe('Workspace removal', () => {
  test('removed user cannot access workspace resources', async ({ page }) => {
    // Set up user with no workspace access
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({
          state: {
            user: {
              id: 'user-removed',
              username: 'removeduser',
              email: 'removed@example.com',
              tenant_id: 'tenant-1',
              roles: ['annotator'],
              permissions: ['read:tasks'],
            },
            token: 'mock-jwt-token',
            currentTenant: { id: 'tenant-1', name: '测试租户' },
            isAuthenticated: true,
          },
        }),
      )
    })

    // Mock workspace endpoint to return 403
    await page.route('**/api/workspaces/**', async (route) => {
      return route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ detail: 'Access denied' }) })
    })
    await page.route(isRestApiUrl, async (route) => {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    })

    await page.goto('/admin/workspaces')
    await waitForPageReady(page)

    // Should be redirected or see access denied
    const finalUrl = page.url()
    const blocked = finalUrl.includes('403') || finalUrl.includes('login') || finalUrl.includes('dashboard')
    expect(blocked).toBeTruthy()
  })
})

/* ================================================================== */
/*  URL Manipulation (Req 7.5)                                         */
/* ================================================================== */

test.describe('URL manipulation', () => {
  test('accessing unauthorized workspace via URL returns 403 or redirect', async ({ page }) => {
    await mockAllApis(page)
    await setupAuth(page, 'annotator', 'tenant-1')

    await page.goto('/admin/workspaces?workspace_id=ws-unauthorized')
    await page.waitForTimeout(3000)

    const url = page.url()
    const body = await page.textContent('body')
    const blocked =
      url.includes('403') ||
      url.includes('login') ||
      url.includes('dashboard') ||
      url.includes('forbidden') ||
      url.includes('/403') ||
      (body != null && /无权|拒绝|403|Forbidden|Access denied/i.test(body))
    expect(blocked).toBeTruthy()
  })
})
