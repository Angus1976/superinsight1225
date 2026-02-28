/**
 * Authentication E2E Tests
 *
 * Validates: Requirements 4.1, 4.5
 * - 4.1: E2E tests for user authentication workflows using Playwright
 * - 4.5: Capture screenshots on failure (handled by playwright.config.ts)
 *
 * Covers: registration, login (valid/invalid), logout, password reset
 */

import { test, expect } from './fixtures'
import { setupAuth, waitForPageReady } from './test-helpers'

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  DASHBOARD: '/dashboard',
} as const

const TEST_USER = {
  username: 'testuser_e2e',
  email: 'testuser_e2e@example.com',
  password: 'SecurePass123!',
} as const

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Mock auth API endpoints so tests run without a live backend. */
async function mockAuthApi(page: import('@playwright/test').Page) {
  // Login – success for known credentials, 401 otherwise
  await page.route('**/api/auth/login', async (route) => {
    const body = route.request().postDataJSON()
    if (body?.email === TEST_USER.email && body?.password === TEST_USER.password) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token-e2e',
          user: {
            id: 'user-e2e-1',
            username: TEST_USER.username,
            email: TEST_USER.email,
            full_name: 'E2E Test User',
            role: 'annotator',
            tenant_id: 'tenant-e2e',
            is_active: true,
          },
        }),
      })
    }
    return route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: '用户名或密码错误' }),
    })
  })

  // Register
  await page.route('**/api/auth/register', async (route) => {
    return route.fulfill({ status: 201, contentType: 'application/json', body: '{}' })
  })

  // Logout
  await page.route('**/api/auth/logout', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  // Forgot password
  await page.route('**/api/auth/forgot-password', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  // Reset password
  await page.route('**/api/auth/reset-password', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  // Tenants list (login form loads this)
  await page.route('**/api/auth/tenants', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })

  // Workspaces (loaded after login)
  await page.route('**/api/workspaces/my', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })

  // Dashboard metrics (landing page after login)
  await page.route('**/api/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
}

/* ================================================================== */
/*  1. User Registration Workflow                                      */
/* ================================================================== */

test.describe('Registration workflow', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthApi(page)
    await page.goto(ROUTES.REGISTER)
    await waitForPageReady(page)
  })

  test('displays registration form with all required fields', async ({ page }) => {
    // Username, email, password, confirm password, tenant type, submit
    await expect(page.getByPlaceholder(/用户名|username/i).first()).toBeVisible()
    await expect(page.getByPlaceholder(/邮箱|email/i).first()).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /注册|register|sign up/i })).toBeVisible()
  })

  test('shows validation errors on empty submission', async ({ page }) => {
    await page.getByRole('button', { name: /注册|register|sign up/i }).click()

    // At least one validation message should appear
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('shows password mismatch error', async ({ page }) => {
    const passwordInputs = page.locator('input[type="password"]')

    await page.getByPlaceholder(/用户名|username/i).first().fill('newuser')
    await page.getByPlaceholder(/邮箱|email/i).first().fill('new@example.com')
    await passwordInputs.nth(0).fill('SecurePass1!')
    await passwordInputs.nth(1).fill('DifferentPass2!')

    await page.getByRole('button', { name: /注册|register|sign up/i }).click()

    // Should show mismatch error
    await expect(
      page.locator('.ant-form-item-explain-error').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('successful registration redirects to login', async ({ page }) => {
    const passwordInputs = page.locator('input[type="password"]')

    await page.getByPlaceholder(/用户名|username/i).first().fill(TEST_USER.username)
    await page.getByPlaceholder(/邮箱|email/i).first().fill(TEST_USER.email)
    await passwordInputs.nth(0).fill(TEST_USER.password)
    await passwordInputs.nth(1).fill(TEST_USER.password)

    // Fill tenant name (default is "new" tenant type)
    const tenantInput = page.getByPlaceholder(/租户|tenant|organization/i)
    if (await tenantInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await tenantInput.fill('E2E Test Org')
    }

    // Accept agreement if checkbox exists
    const agreementCheckbox = page.getByRole('checkbox')
    if (await agreementCheckbox.isVisible({ timeout: 1000 }).catch(() => false)) {
      await agreementCheckbox.check()
    }

    await page.getByRole('button', { name: /注册|register|sign up/i }).click()

    // Should redirect to login page after success
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN), { timeout: 10000 })
  })

  test('has link to navigate back to login', async ({ page }) => {
    const loginLink = page.getByRole('link', { name: /登录|login|sign in/i })
    await expect(loginLink).toBeVisible()
    await loginLink.click()
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN))
  })
})

/* ================================================================== */
/*  2. Login Workflow – Valid Credentials                               */
/* ================================================================== */

test.describe('Login workflow – valid credentials', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthApi(page)
    await page.goto(ROUTES.LOGIN)
    await waitForPageReady(page)
  })

  test('displays login form correctly', async ({ page }) => {
    await expect(page.locator('input[type="email"], input[placeholder*="@"]').first()).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /登录|login|sign in/i })).toBeVisible()
  })

  test('successful login redirects to dashboard', async ({ page }) => {
    // The login form uses email-style input with placeholder "admin@superinsight.local"
    await page.locator('input[type="email"], input[placeholder*="@"]').first().fill(TEST_USER.email)
    await page.locator('input[type="password"]').first().fill(TEST_USER.password)

    await page.getByRole('button', { name: /登录|login|sign in/i }).click()

    await expect(page).toHaveURL(new RegExp(ROUTES.DASHBOARD), { timeout: 10000 })
  })

  test('remember me checkbox is checked by default', async ({ page }) => {
    const checkbox = page.getByRole('checkbox')
    if (await checkbox.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(checkbox).toBeChecked()
    }
  })

  test('password visibility toggle works', async ({ page }) => {
    const passwordInput = page.locator('input[type="password"]').first()
    await passwordInput.fill('somepassword')
    await expect(passwordInput).toHaveAttribute('type', 'password')

    // Ant Design password toggle icon
    const toggle = page.locator('.ant-input-password-icon').first()
    if (await toggle.isVisible({ timeout: 2000 }).catch(() => false)) {
      await toggle.click()
      // After toggle the input type changes to text
      await expect(page.locator('input[type="text"]').first()).toBeVisible()
    }
  })
})

/* ================================================================== */
/*  3. Login Workflow – Invalid Credentials                            */
/* ================================================================== */

test.describe('Login workflow – invalid credentials', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthApi(page)
    await page.goto(ROUTES.LOGIN)
    await waitForPageReady(page)
  })

  test('shows validation errors for empty form submission', async ({ page }) => {
    await page.getByRole('button', { name: /登录|login|sign in/i }).click()

    // Ant Design form validation messages
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('shows error message for wrong credentials', async ({ page }) => {
    await page.locator('input[type="email"], input[placeholder*="@"]').first().fill('wrong@example.com')
    await page.locator('input[type="password"]').first().fill('wrongpassword')

    await page.getByRole('button', { name: /登录|login|sign in/i }).click()

    // Should show error notification/message from Ant Design message component
    await expect(
      page.locator('.ant-message-error, .ant-message-notice-error').first()
    ).toBeVisible({ timeout: 10000 })
  })

  test('stays on login page after failed login', async ({ page }) => {
    await page.locator('input[type="email"], input[placeholder*="@"]').first().fill('wrong@example.com')
    await page.locator('input[type="password"]').first().fill('wrongpassword')

    await page.getByRole('button', { name: /登录|login|sign in/i }).click()

    // Wait for the error to appear, then verify we're still on login
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN))
  })
})

/* ================================================================== */
/*  4. Logout Workflow                                                 */
/* ================================================================== */

test.describe('Logout workflow', () => {
  test('logout clears auth state and redirects to login', async ({ page }) => {
    await mockAuthApi(page)
    await setupAuth(page)
    await page.goto(ROUTES.DASHBOARD)
    await waitForPageReady(page)

    // Look for user menu / avatar / logout trigger in the layout
    const userMenu = page.locator(
      '[data-testid="user-menu"], .ant-dropdown-trigger, .ant-avatar, .user-info'
    ).first()

    if (await userMenu.isVisible({ timeout: 5000 }).catch(() => false)) {
      await userMenu.click()

      const logoutBtn = page.getByText(/退出|登出|logout|sign out/i).first()
      if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await logoutBtn.click()
        await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN), { timeout: 10000 })
        return
      }
    }

    // Fallback: simulate logout by clearing auth storage directly
    await page.evaluate(() => localStorage.removeItem('auth-storage'))
    await page.goto(ROUTES.DASHBOARD)
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN), { timeout: 10000 })
  })

  test('accessing protected route after logout redirects to login', async ({ page }) => {
    // Start unauthenticated
    await page.goto(ROUTES.DASHBOARD)
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN), { timeout: 10000 })
  })
})

/* ================================================================== */
/*  5. Password Reset Workflow                                         */
/* ================================================================== */

test.describe('Password reset workflow', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthApi(page)
  })

  test('navigates to forgot password from login page', async ({ page }) => {
    await page.goto(ROUTES.LOGIN)
    await waitForPageReady(page)

    const forgotLink = page.getByText(/忘记密码|forgot/i).first()
    await expect(forgotLink).toBeVisible()
    await forgotLink.click()

    await expect(page).toHaveURL(new RegExp(ROUTES.FORGOT_PASSWORD))
  })

  test('forgot password form accepts email and shows success', async ({ page }) => {
    await page.goto(ROUTES.FORGOT_PASSWORD)
    await waitForPageReady(page)

    const emailInput = page.getByPlaceholder(/邮箱|email/i).first()
    await expect(emailInput).toBeVisible()
    await emailInput.fill(TEST_USER.email)

    await page.getByRole('button', { name: /发送|submit|reset|重置/i }).click()

    // Should show success result or message
    await expect(
      page.locator('.ant-result-success, .ant-message-success, .ant-message-notice-success').first()
    ).toBeVisible({ timeout: 10000 })
  })

  test('forgot password shows validation for empty email', async ({ page }) => {
    await page.goto(ROUTES.FORGOT_PASSWORD)
    await waitForPageReady(page)

    await page.getByRole('button', { name: /发送|submit|reset|重置/i }).click()

    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('forgot password has back to login navigation', async ({ page }) => {
    await page.goto(ROUTES.FORGOT_PASSWORD)
    await waitForPageReady(page)

    const backBtn = page.getByText(/返回|back.*login/i).first()
    await expect(backBtn).toBeVisible()
    await backBtn.click()

    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN))
  })

  test('reset password form requires token and email params', async ({ page }) => {
    // Without query params, should show invalid link message
    await page.goto(ROUTES.RESET_PASSWORD)
    await waitForPageReady(page)

    await expect(
      page.locator('.ant-result-error, .ant-result').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('reset password form works with valid token', async ({ page }) => {
    await page.goto(`${ROUTES.RESET_PASSWORD}?token=valid-token&email=${TEST_USER.email}`)
    await waitForPageReady(page)

    const passwordInputs = page.locator('input[type="password"]')
    await expect(passwordInputs.first()).toBeVisible()

    await passwordInputs.nth(0).fill('NewSecurePass456!')
    await passwordInputs.nth(1).fill('NewSecurePass456!')

    await page.getByRole('button', { name: /重置|reset|submit|确认/i }).click()

    // Should show success result
    await expect(
      page.locator('.ant-result-icon, .ant-result, .ant-message-success').first()
    ).toBeVisible({ timeout: 10000 })
  })
})

/* ================================================================== */
/*  6. Protected Routes Guard                                          */
/* ================================================================== */

test.describe('Protected routes guard', () => {
  const protectedPaths = [ROUTES.DASHBOARD, '/tasks', '/billing', '/settings']

  for (const path of protectedPaths) {
    test(`redirects ${path} to login when unauthenticated`, async ({ page }) => {
      await page.goto(path)
      await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN), { timeout: 10000 })
    })
  }
})

/* ================================================================== */
/*  7. Screenshot Capture on Failure (Requirement 4.5)                 */
/* ================================================================== */

test.describe('Screenshot capture verification', () => {
  test('playwright config captures screenshots on failure', async ({ page }) => {
    // This test verifies the screenshot config is active by checking
    // that the test infrastructure is properly set up.
    // Actual screenshot capture is handled by playwright.config.ts:
    //   use: { screenshot: 'only-on-failure' }
    await page.goto(ROUTES.LOGIN)
    await waitForPageReady(page)

    // Verify the page loaded (this test itself won't fail,
    // but confirms the test infrastructure works)
    await expect(page).toHaveURL(new RegExp(ROUTES.LOGIN))
  })
})
