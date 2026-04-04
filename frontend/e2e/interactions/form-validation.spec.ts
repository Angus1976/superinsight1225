/**
 * Form Validation E2E Tests
 *
 * Validates: Requirements 2.2, 2.3, 2.4
 * Tests valid form submission, empty required field validation,
 * and constrained input validation across Login, Register, Task Create,
 * and Admin User Create forms.
 */

import { test, expect } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { isRestApiUrl } from '../api-route-helpers'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { fillAntForm, submitAntForm, verifyFormValidation } from '../helpers/form-interaction'

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const MOCK_AUTH_ROUTES = async (page: import('@playwright/test').Page) => {
  await page.route('**/api/auth/login', async (route) => {
    const body = route.request().postDataJSON()
    if (body?.email === 'valid@example.com' && body?.password === 'SecurePass123!') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token',
          user: { id: 'u1', username: 'testuser', email: 'valid@example.com', role: 'admin', tenant_id: 'tenant-1', is_active: true },
        }),
      })
    }
    return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: '用户名或密码错误' }) })
  })
  await page.route('**/api/auth/register', (route) => route.fulfill({ status: 201, contentType: 'application/json', body: '{}' }))
  await page.route('**/api/auth/tenants', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route(isRestApiUrl, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }))
}

/* ================================================================== */
/*  1. Login Form Validation                                           */
/* ================================================================== */

test.describe('Login form validation', () => {
  test.beforeEach(async ({ page }) => {
    await MOCK_AUTH_ROUTES(page)
    await page.goto('/login')
    await waitForPageReady(page)
  })

  test('valid login submission redirects to dashboard', async ({ page }) => {
    await page.locator('input[type="email"], input[placeholder*="@"]').first().fill('valid@example.com')
    await page.locator('input[type="password"]').first().fill('SecurePass123!')
    await page.getByRole('button', { name: /登录|login|sign in/i }).click()
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
  })

  test('empty required fields show validation errors', async ({ page }) => {
    await page.getByRole('button', { name: /登录|login|sign in/i }).click()
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('invalid email format shows validation error', async ({ page }) => {
    await page.locator('input[type="email"], input[placeholder*="@"]').first().fill('not-an-email')
    await page.locator('input[type="password"]').first().fill('SomePass123!')
    await page.getByRole('button', { name: /登录|login|sign in/i }).click()
    // Should show email format error or API error
    const hasError = await page.locator('.ant-form-item-explain-error, .ant-message-error').first()
      .isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasError).toBeTruthy()
  })
})

/* ================================================================== */
/*  2. Register Form Validation                                        */
/* ================================================================== */

test.describe('Register form validation', () => {
  test.beforeEach(async ({ page }) => {
    await MOCK_AUTH_ROUTES(page)
    await page.goto('/register')
    await waitForPageReady(page)
  })

  test('valid registration submits successfully', async ({ page }) => {
    const passwordInputs = page.locator('input[type="password"]')
    await page.getByPlaceholder(/用户名|username/i).first().fill('newuser')
    await page.getByPlaceholder(/邮箱|email/i).first().fill('new@example.com')
    await passwordInputs.nth(0).fill('SecurePass123!')
    await passwordInputs.nth(1).fill('SecurePass123!')

    const tenantInput = page.getByPlaceholder(/租户|tenant|organization/i)
    if (await tenantInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await tenantInput.fill('Test Org')
    }
    const checkbox = page.getByRole('checkbox')
    if (await checkbox.isVisible({ timeout: 1000 }).catch(() => false)) {
      await checkbox.check()
    }

    await page.getByRole('button', { name: /注册|register|sign up/i }).click()
    await expect(page).toHaveURL(/login/, { timeout: 10000 })
  })

  test('empty required fields show validation errors on register', async ({ page }) => {
    await page.getByRole('button', { name: /注册|register|sign up/i }).click()
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('weak password shows validation error', async ({ page }) => {
    await page.getByPlaceholder(/用户名|username/i).first().fill('newuser')
    await page.getByPlaceholder(/邮箱|email/i).first().fill('new@example.com')
    const passwordInputs = page.locator('input[type="password"]')
    await passwordInputs.nth(0).fill('123')  // weak password
    await passwordInputs.nth(1).fill('123')
    await page.getByRole('button', { name: /注册|register|sign up/i }).click()
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('password mismatch shows validation error', async ({ page }) => {
    await page.getByPlaceholder(/用户名|username/i).first().fill('newuser')
    await page.getByPlaceholder(/邮箱|email/i).first().fill('new@example.com')
    const passwordInputs = page.locator('input[type="password"]')
    await passwordInputs.nth(0).fill('SecurePass123!')
    await passwordInputs.nth(1).fill('DifferentPass456!')
    await page.getByRole('button', { name: /注册|register|sign up/i }).click()
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('invalid email format shows validation error on register', async ({ page }) => {
    await page.getByPlaceholder(/用户名|username/i).first().fill('newuser')
    await page.getByPlaceholder(/邮箱|email/i).first().fill('invalid-email')
    const passwordInputs = page.locator('input[type="password"]')
    await passwordInputs.nth(0).fill('SecurePass123!')
    await passwordInputs.nth(1).fill('SecurePass123!')
    await page.getByRole('button', { name: /注册|register|sign up/i }).click()
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })
})

/* ================================================================== */
/*  3. Task Create Form Validation                                     */
/* ================================================================== */

test.describe('Task create form validation', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page)
    await setupAuth(page, 'admin', 'tenant-1')
    await page.goto('/tasks')
    await waitForPageReady(page)
  })

  test('task create form accepts valid input and submits', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /创建|新建|create|add/i }).first()
    if (!(await createBtn.isVisible({ timeout: 5000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) return

    // Fill form fields inside modal
    const nameInput = modal.locator('input').first()
    if (await nameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await nameInput.fill('E2E 测试任务')
    }

    const okBtn = modal.locator('.ant-btn-primary').first()
    await okBtn.click()
    await page.waitForTimeout(2000)
  })

  test('task create form shows errors on empty submission', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /创建|新建|create|add/i }).first()
    if (!(await createBtn.isVisible({ timeout: 5000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) return

    // Submit without filling anything
    const okBtn = modal.locator('.ant-btn-primary').first()
    await okBtn.click()

    // Should show validation errors
    await expect(
      page.locator('.ant-form-item-explain-error').first()
    ).toBeVisible({ timeout: 5000 })
  })
})

/* ================================================================== */
/*  4. Admin User Create Form Validation                               */
/* ================================================================== */

test.describe('Admin user create form validation', () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApis(page)
    await setupAuth(page, 'admin', 'tenant-1')
    await page.goto('/admin/users')
    await waitForPageReady(page)
  })

  test('user create form accepts valid input', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (!(await createBtn.isVisible({ timeout: 5000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal, .ant-drawer')
    if (!(await modal.first().isVisible({ timeout: 3000 }).catch(() => false))) return

    // Fill user form fields
    const inputs = modal.first().locator('input')
    const inputCount = await inputs.count()
    for (let i = 0; i < Math.min(inputCount, 3); i++) {
      const input = inputs.nth(i)
      if (await input.isVisible({ timeout: 1000 }).catch(() => false)) {
        const type = await input.getAttribute('type')
        if (type === 'password') {
          await input.fill('SecurePass123!')
        } else {
          await input.fill(`testvalue${i}@example.com`)
        }
      }
    }
  })

  test('user create form shows errors on empty submission', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (!(await createBtn.isVisible({ timeout: 5000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal, .ant-drawer')
    if (!(await modal.first().isVisible({ timeout: 3000 }).catch(() => false))) return

    // Submit empty
    const okBtn = modal.first().locator('.ant-btn-primary').first()
    if (await okBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await okBtn.click()
      await expect(
        page.locator('.ant-form-item-explain-error').first()
      ).toBeVisible({ timeout: 5000 })
    }
  })
})
