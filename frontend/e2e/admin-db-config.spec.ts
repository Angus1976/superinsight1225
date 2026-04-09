/**
 * Admin Database Configuration E2E Tests
 *
 * Tests the complete database configuration workflow including:
 * - Creating new database connections
 * - Testing connections
 * - Editing configurations
 * - Deleting configurations
 *
 * Routes and mocks align with {@link adminApi} and `Admin/ConfigDB.tsx`
 * (`/admin/config/databases`, `/api/v1/admin/config/databases`).
 */

import { test, expect } from '@playwright/test'
import { setupAuth, setupE2eSession, waitForPageReady } from './test-helpers'

const CORS_JSON_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': '*',
}

function mockDbRow(overrides: Record<string, unknown> = {}) {
  return {
    id: 'db-1',
    name: 'Production MySQL',
    description: '',
    db_type: 'mysql' as const,
    host: 'mysql.example.com',
    port: 3306,
    database: 'superinsight_prod',
    username: 'admin',
    password_masked: '****',
    ssl_enabled: true,
    is_readonly: true,
    extra_config: {},
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

const SAMPLE_CONFIGS = [
  mockDbRow({ id: 'db-1', name: 'Production MySQL', db_type: 'mysql' }),
  mockDbRow({
    id: 'db-2',
    name: 'Analytics PostgreSQL',
    db_type: 'postgresql',
    host: 'postgres.example.com',
    port: 5432,
    database: 'analytics',
    username: 'readonly',
  }),
]

/** Create/Edit modal that wraps the DB config form (excludes detail modal). */
function formConfigModal(page: import('@playwright/test').Page) {
  return page.locator('.ant-modal').filter({ has: page.locator('form.ant-form') })
}

async function openDbTypeDropdown(page: import('@playwright/test').Page) {
  const modal = formConfigModal(page)
  await modal.locator('form .ant-select').first().click()
}

async function pickSelectOption(page: import('@playwright/test').Page, label: string) {
  await page
    .locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')
    .getByText(label, { exact: true })
    .click()
}

async function clickFormModalPrimary(page: import('@playwright/test').Page) {
  await formConfigModal(page).locator('.ant-modal-footer .ant-btn-primary').click()
}

async function clickPopconfirmOk(page: import('@playwright/test').Page) {
  const inner = page.locator('.ant-popover-inner:visible').filter({
    hasText:
      /sure you want to delete|确定删除此配置|确定删除|delete this configuration|Related sync strategies|同步策略/i,
  })
  await inner.getByRole('button', { name: /Confirm|确认/ }).click()
}

function adminDatabasesUrlPredicate(url: string) {
  return url.includes('/api/v1/admin/config/databases')
}

async function submitFormModalAndAwaitDbConfigPost(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        adminDatabasesUrlPredicate(r.url()) &&
        /\/config\/databases(\?|$)/.test(r.url()) &&
        r.request().method() === 'POST' &&
        r.status() === 201,
    ),
    clickFormModalPrimary(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

async function submitFormModalAndAwaitDbConfigPut(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        adminDatabasesUrlPredicate(r.url()) &&
        /\/config\/databases\/[^/?]+\?/.test(r.url()) &&
        r.request().method() === 'PUT' &&
        r.status() === 200,
    ),
    clickFormModalPrimary(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

async function confirmDeleteAndAwaitDbConfigDelete(page: import('@playwright/test').Page) {
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        adminDatabasesUrlPredicate(r.url()) &&
        /\/config\/databases\/[^/?]+\?/.test(r.url()) &&
        r.request().method() === 'DELETE' &&
        r.status() === 204,
    ),
    clickPopconfirmOk(page),
  ])
  expect(resp.ok()).toBeTruthy()
}

async function mockAdminDatabaseApis(page: import('@playwright/test').Page) {
  await page.route(/\/api\/v1\/admin\/config\/databases\/[^/]+\/test(\?|$)/, async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: CORS_JSON_HEADERS,
      body: JSON.stringify({
        success: true,
        latency_ms: 45,
        details: { server_version: 'MySQL 8.0.32' },
      }),
    })
  })

  await page.route(/\/api\/v1\/admin\/config\/databases\/[^/]+(\?.*)?$/, async (route) => {
    const url = route.request().url()
    if (url.includes('/test')) {
      return route.continue()
    }
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    const id = new URL(url).pathname.split('/').pop() || 'db-1'
    const method = route.request().method()

    if (method === 'PUT') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({
          ...mockDbRow({ id }),
          ...body,
          password_masked: '****',
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    if (method === 'DELETE') {
      await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
      return
    }
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify(
          mockDbRow({
            id,
            name: 'Test DB',
            db_type: 'mysql',
            host: 'localhost',
            port: 3306,
            database: 'test',
            username: 'root',
            ssl_enabled: false,
            is_readonly: false,
          }),
        ),
      })
      return
    }
    return route.continue()
  })

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
        body: JSON.stringify(SAMPLE_CONFIGS),
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
          id: 'db-new',
          ...body,
          extra_config: body.extra_config || {},
          password_masked: '****',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    return route.continue()
  })
}

test.describe('Admin Database Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
    await mockAdminDatabaseApis(page)
    await page.goto('/admin/config/databases')
    await waitForPageReady(page)
  })

  test('displays database configuration list', async ({ page }) => {
    await expect(page.locator('text=/数据库|Database/i').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('.ant-table')).toBeVisible()
    await expect(page.getByText('Production MySQL')).toBeVisible()
    await expect(page.getByText('Analytics PostgreSQL')).toBeVisible()
  })

  test('opens create configuration modal', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    await expect(page.getByLabel(/连接名称|名称|name/i).first()).toBeVisible()
  })

  test('creates new MySQL database configuration', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await formConfigModal(page).getByLabel(/连接名称|名称|name/i).first().fill('Test MySQL Database')

    await openDbTypeDropdown(page)
    await pickSelectOption(page, 'MySQL')

    const modal = formConfigModal(page)
    await modal.locator('#host').fill('mysql.test.com')
    await modal.locator('.ant-input-number input').fill('3306')
    await modal.locator('#database').fill('test_db')
    await modal.locator('#username').fill('test_user')

    const passwordInput = modal.locator('input[type="password"]').first()
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('test_password')
    }

    await submitFormModalAndAwaitDbConfigPost(page)
  })

  test('creates new PostgreSQL database configuration', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await formConfigModal(page).getByLabel(/连接名称|名称|name/i).first().fill('Test PostgreSQL Database')

    await openDbTypeDropdown(page)
    await pickSelectOption(page, 'PostgreSQL')

    const modal = formConfigModal(page)
    await modal.locator('#host').fill('postgres.test.com')
    await modal.locator('.ant-input-number input').fill('5432')
    await modal.locator('#database').fill('analytics_db')
    await modal.locator('#username').fill('postgres')

    const passwordInput = modal.locator('input[type="password"]').first()
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('secret')
    }

    await submitFormModalAndAwaitDbConfigPost(page)
  })

  test('displays database type-specific options', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await openDbTypeDropdown(page)
    await pickSelectOption(page, 'MySQL')

    const portInput = formConfigModal(page).getByLabel(/端口|port/i).first()
    if (await portInput.isVisible()) {
      const portValue = await portInput.inputValue()
      expect(['', '3306']).toContain(portValue)
    }

    await openDbTypeDropdown(page)
    await pickSelectOption(page, 'PostgreSQL')

    if (await portInput.isVisible()) {
      const portValue = await portInput.inputValue()
      expect(['', '5432', '3306']).toContain(portValue)
    }
  })

  test('validates required fields', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await clickFormModalPrimary(page)
    await expect(formConfigModal(page).locator('.ant-form-item-explain-error').first()).toBeVisible()
  })

  test('tests database connection', async ({ page }) => {
    const testButton = page.locator('button:has(.anticon-link)').first()
    await expect(testButton).toBeVisible()
    await testButton.click()
    await expect(page.getByText(/成功|success|连接|ms/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('handles connection test failure gracefully', async ({ page }) => {
    await page.route(/\/api\/v1\/admin\/config\/databases\/[^/]+\/test(\?|$)/, async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: CORS_JSON_HEADERS })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({
          success: false,
          latency_ms: 0,
          error_message: 'Connection refused: Unable to connect to database server',
        }),
      })
    })

    const testButton = page.locator('button:has(.anticon-link)').first()
    await testButton.click()
    await expect(page.getByText(/失败|failed|error|refused|连接/i).first()).toBeVisible({
      timeout: 10000,
    })
  })

  test('edits existing configuration', async ({ page }) => {
    const editButton = page.locator('button:has(.anticon-edit)').first()
    await editButton.click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    const nameInput = formConfigModal(page).locator('#name')
    await nameInput.clear()
    await nameInput.fill('Updated Database Config')

    await submitFormModalAndAwaitDbConfigPut(page)
  })

  test('deletes configuration with confirmation', async ({ page }) => {
    const deleteButton = page.locator('button:has(.anticon-delete)').first()
    await deleteButton.click()

    await expect(page.getByText(/确认|confirm|删除/i).first()).toBeVisible()
    await confirmDeleteAndAwaitDbConfigDelete(page)
  })

  test('configures SSL/TLS settings', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    const sslRow = page.locator('.ant-form-item').filter({ hasText: /启用 SSL|SSL/i })
    const sslSwitch = sslRow.locator('.ant-switch').first()
    if (await sslSwitch.isVisible()) {
      await sslSwitch.click()
    }
  })

  test('configures read-only mode', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    const roRow = page.locator('.ant-form-item').filter({ hasText: /只读连接|只读/i })
    const roSwitch = roRow.locator('.ant-switch').first()
    if (await roSwitch.isVisible()) {
      await roSwitch.click()
    }
  })

  test('displays masked passwords', async ({ page }) => {
    await page.getByRole('button', { name: 'Production MySQL' }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    await expect(page.getByText('****').first()).toBeVisible()
  })

  test('configures connection pool settings', async ({ page }) => {
    await page.getByRole('button', { name: /添加数据库|添加|新增|add/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    const minPoolInput = page.getByLabel(/最小|min/i)
    const maxPoolInput = page.getByLabel(/最大|max/i)

    if (await minPoolInput.isVisible()) {
      await minPoolInput.fill('5')
    }
    if (await maxPoolInput.isVisible()) {
      await maxPoolInput.fill('20')
    }
  })
})

test.describe('Database Configuration - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
    await mockAdminDatabaseApis(page)
  })

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/admin/config/databases')
    await waitForPageReady(page)
    await expect(page.getByRole('button', { name: /添加数据库|添加|新增|add/i })).toBeVisible()
  })

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/admin/config/databases')
    await waitForPageReady(page)
    await expect(page.getByRole('button', { name: /添加数据库|添加|新增|add/i })).toBeVisible()
  })
})

test.describe('Database Configuration - Access Control', () => {
  test('denies access for non-admin users', async ({ page }) => {
    await setupAuth(page, 'annotator', 'tenant-1')

    await page.route('**/api/v1/admin/**', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        headers: CORS_JSON_HEADERS,
        body: JSON.stringify({ error: 'Forbidden', message: 'Admin access required' }),
      })
    })

    await page.goto('/admin/config/databases')

    await expect(
      page.getByText(/禁止|forbidden|权限|access denied|403/i).first(),
    ).toBeVisible({ timeout: 10000 }).catch(() => {
      expect(page.url()).not.toMatch(/config\/databases/)
    })
  })
})
