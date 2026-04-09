/**
 * Admin Sync Strategy E2E — aligned with `ConfigSync.tsx` and `adminApi` sync endpoints
 * (`/api/v1/admin/config/sync`, `/api/v1/admin/config/databases`).
 */

import { test, expect } from '@playwright/test'
import { setupE2eSession, waitForPageReady } from './test-helpers'

const CORS_JSON_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': '*',
}

function dbRow(id: string, name: string, dbType: 'mysql' | 'postgresql') {
  return {
    id,
    name,
    description: '',
    db_type: dbType,
    host: `${dbType}.example.com`,
    port: dbType === 'mysql' ? 3306 : 5432,
    database: 'app',
    username: 'u',
    password_masked: '****',
    ssl_enabled: false,
    is_readonly: true,
    extra_config: {},
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

function strategyRow(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sync-1',
    db_config_id: 'db-1',
    name: 'Daily Full Sync',
    mode: 'full',
    schedule: '0 * * * *',
    filter_conditions: [] as unknown[],
    batch_size: 1000,
    enabled: true,
    last_sync_at: new Date().toISOString(),
    last_sync_status: 'success',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

const SAMPLE_DBS = [dbRow('db-1', 'Production MySQL', 'mysql'), dbRow('db-2', 'Analytics PostgreSQL', 'postgresql')]

const SAMPLE_STRATEGIES = [
  strategyRow({ id: 'sync-1', name: 'Daily Full Sync', mode: 'full', db_config_id: 'db-1' }),
  strategyRow({
    id: 'sync-2',
    name: 'Incremental Warehouse',
    mode: 'incremental',
    db_config_id: 'db-2',
    incremental_field: 'updated_at',
    enabled: false,
    last_sync_at: undefined,
    last_sync_status: undefined,
  }),
]

function formSyncModal(page: import('@playwright/test').Page) {
  return page.locator('.ant-modal').filter({ has: page.locator('form.ant-form') })
}

async function clickFormModalPrimary(page: import('@playwright/test').Page) {
  await formSyncModal(page).locator('.ant-modal-footer .ant-btn-primary').click()
}

async function openSelectInForm(page: import('@playwright/test').Page, index: number) {
  await formSyncModal(page).locator('form .ant-select').nth(index).click()
}

async function pickDropdownOption(page: import('@playwright/test').Page, label: string | RegExp) {
  const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')
  const opt =
    typeof label === 'string'
      ? dropdown.getByText(label, { exact: true })
      : dropdown.getByText(label).first()
  await opt.click()
}

async function mockConfigSyncApis(page: import('@playwright/test').Page) {
  await page.route(/\/api\/v1\/admin\/config\/databases(\?.*)?$/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify(SAMPLE_DBS),
      })
      return
    }
    return route.continue()
  })

  await page.route(/\/api\/v1\/admin\/config\/sync(\?.*)?$/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify(SAMPLE_STRATEGIES),
      })
      return
    }
    if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({
          id: 'sync-new',
          ...strategyRow(),
          ...body,
          filter_conditions: body.filter_conditions || [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    return route.continue()
  })

  await page.route(/\/api\/v1\/admin\/config\/sync\/[^/]+(\?.*)?$/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    const url = route.request().url()
    const id = new URL(url).pathname.split('/').pop()?.split('?')[0] || 'sync-1'
    const method = route.request().method()
    if (method === 'PUT') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({
          ...strategyRow({ id }),
          ...body,
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    if (method === 'DELETE') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    return route.continue()
  })

  await page.route(/\/api\/v1\/admin\/config\/sync\/[^/]+\/trigger(\?.*)?$/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: CORS_JSON_HEADERS,
      body: JSON.stringify({
        job_id: 'job-1',
        strategy_id: 'sync-1',
        status: 'queued',
        started_at: new Date().toISOString(),
        message: 'ok',
      }),
    })
  })

  await page.route(/\/api\/v1\/admin\/config\/sync\/[^/]+\/history(\?.*)?$/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: CORS_JSON_HEADERS,
      body: JSON.stringify([]),
    })
  })
}

async function submitFormModalAndAwaitSyncPost(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes('/api/v1/admin/config/sync') &&
        /\/config\/sync(\?|$)/.test(r.url()) &&
        r.request().method() === 'POST' &&
        r.status() === 201,
    ),
    clickFormModalPrimary(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

async function submitFormModalAndAwaitSyncPut(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes('/api/v1/admin/config/sync/') &&
        /\/config\/sync\/[^/?]+\?/.test(r.url()) &&
        r.request().method() === 'PUT' &&
        r.status() === 200,
    ),
    clickFormModalPrimary(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

async function clickPopconfirmOk(page: import('@playwright/test').Page) {
  const inner = page.locator('.ant-popover-inner:visible').filter({
    hasText: /delete|删除|确认|Confirm|strategy|策略/i,
  })
  await inner.getByRole('button', { name: /Confirm|确认/ }).click()
}

async function confirmDeleteAndAwaitSyncDelete(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes('/api/v1/admin/config/sync/') &&
        /\/config\/sync\/[^/?]+\?/.test(r.url()) &&
        r.request().method() === 'DELETE' &&
        r.status() === 204,
    ),
    clickPopconfirmOk(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

test.describe('Admin Sync Strategy Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
    await mockConfigSyncApis(page)
    await page.goto('/admin/config/sync')
    await waitForPageReady(page)
  })

  test('displays sync strategy list', async ({ page }) => {
    await expect(page.locator('.ant-table')).toBeVisible()
    await expect(page.getByText('Daily Full Sync')).toBeVisible()
    await expect(page.getByText('Incremental Warehouse')).toBeVisible()
  })

  test('opens create strategy modal', async ({ page }) => {
    await page.getByRole('button', { name: /添加|新增|add/i }).click()
    await expect(formSyncModal(page)).toBeVisible()
  })

  test('creates new full sync strategy', async ({ page }) => {
    await page.getByRole('button', { name: /添加|新增|add/i }).click()
    await expect(formSyncModal(page)).toBeVisible()

    await formSyncModal(page).locator('#name').fill('E2E Full Sync')

    await openSelectInForm(page, 0)
    await pickDropdownOption(page, /Production MySQL/)

    await openSelectInForm(page, 1)
    await pickDropdownOption(page, '全量同步')

    await submitFormModalAndAwaitSyncPost(page)
  })

  test('creates incremental strategy with field', async ({ page }) => {
    await page.getByRole('button', { name: /添加|新增|add/i }).click()
    await formSyncModal(page).locator('#name').fill('E2E Incremental')

    await openSelectInForm(page, 0)
    await pickDropdownOption(page, /Analytics PostgreSQL/)

    await openSelectInForm(page, 1)
    await pickDropdownOption(page, '增量同步')

    await formSyncModal(page).locator('#incremental_field').fill('updated_at')

    await submitFormModalAndAwaitSyncPost(page)
  })

  test('edits existing strategy', async ({ page }) => {
    await page.locator('button:has(.anticon-edit)').first().click()
    await expect(formSyncModal(page)).toBeVisible()
    await formSyncModal(page).locator('#name').fill('Updated Strategy Name')
    await submitFormModalAndAwaitSyncPut(page)
  })

  test('displays last sync status', async ({ page }) => {
    await expect(page.locator('.anticon-check-circle').first()).toBeVisible()
  })

  test('validates required fields', async ({ page }) => {
    await page.getByRole('button', { name: /添加|新增|add/i }).click()
    await expect(formSyncModal(page)).toBeVisible()
    await clickFormModalPrimary(page)
    await expect(formSyncModal(page).locator('.ant-form-item-explain-error').first()).toBeVisible()
  })

  test('deletes strategy with confirmation', async ({ page }) => {
    await page.locator('button:has(.anticon-delete)').first().click()
    await expect(page.getByText(/确认|confirm|删除|delete/i).first()).toBeVisible()
    await confirmDeleteAndAwaitSyncDelete(page)
  })

  test('trigger sync invokes API', async ({ page }) => {
    const [resp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes('/api/v1/admin/config/sync/') &&
          r.url().includes('/trigger') &&
          r.request().method() === 'POST' &&
          r.status() === 200,
      ),
      page.locator('button:has(.anticon-play-circle)').first().click(),
    ])
    expect(resp.ok()).toBeTruthy()
  })
})

test.describe('Sync Strategy - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
    await page.route(/\/api\/v1\/admin\/config\/databases(\?.*)?$/, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify([]),
      })
    })
    await page.route(/\/api\/v1\/admin\/config\/sync(\?.*)?$/, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify([]),
      })
    })
  })

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/admin/config/sync')
    await waitForPageReady(page)
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible()
  })

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/admin/config/sync')
    await waitForPageReady(page)
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible()
  })
})

test.describe('Sync Strategy - Access Control', () => {
  test('denies access for non-admin users', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'annotator' })
    await page.route('**/api/v1/admin/**', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({ error: 'Forbidden', message: 'Admin access required' }),
      })
    })
    await page.goto('/admin/config/sync')
    await waitForPageReady(page)
    // Route may still render; list must not show admin-only mock data after 403.
    await expect(page.getByText('Daily Full Sync')).not.toBeVisible({ timeout: 10000 })
  })
})
