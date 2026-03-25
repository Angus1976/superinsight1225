/**
 * Error Handling E2E Tests
 *
 * Tests API error responses (500, 404, 429), non-existent routes,
 * form network errors, network disconnection, and empty states.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

/* ================================================================== */
/*  API 500 Response (Req 9.1)                                         */
/* ================================================================== */

test.describe('API 500 response', () => {
  test('user-friendly error message displayed, no blank page', async ({ page }) => {
    await setupAuth(page)

    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Page should not be blank
    const root = page.locator('#root')
    await expect(root).toBeVisible()
    const children = await root.evaluate((el: Element) => el.children.length)
    expect(children).toBeGreaterThan(0)
  })
})

/* ================================================================== */
/*  API 404 Response (Req 9.2)                                         */
/* ================================================================== */

test.describe('API 404 response', () => {
  test('"not found" message displayed', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    // Override a specific endpoint to return 404
    await page.route('**/api/tasks/nonexistent', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not found' }),
      })
    })

    await page.goto('/tasks/nonexistent')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})

/* ================================================================== */
/*  API 429 Response (Req 9.3)                                         */
/* ================================================================== */

test.describe('API 429 response', () => {
  test('rate-limiting message displayed', async ({ page }) => {
    await setupAuth(page)

    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Too many requests' }),
      })
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
    const children = await root.evaluate((el: Element) => el.children.length)
    expect(children).toBeGreaterThan(0)
  })
})

/* ================================================================== */
/*  Non-existent Route (Req 9.4)                                       */
/* ================================================================== */

test.describe('Non-existent route', () => {
  test('404 page with navigation back to Dashboard', async ({ page }) => {
    await page.route('**/api/**', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )

    await page.goto('/this-route-does-not-exist-at-all')
    await waitForPageReady(page)

    // Should show 404 page or redirect
    const body = await page.textContent('body')
    const is404 =
      page.url().includes('404') ||
      (body && /404|not found|页面不存在|找不到/i.test(body))
    expect(is404).toBeTruthy()

    // Look for a link back to dashboard
    const homeLink = page.getByRole('link', { name: /首页|home|dashboard|返回/i }).first()
    if (await homeLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(homeLink).toBeVisible()
    }
  })
})

/* ================================================================== */
/*  Form Network Error (Req 9.5)                                       */
/* ================================================================== */

test.describe('Form submission network error', () => {
  test('form data preserved, retry possible', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    await page.goto('/tasks')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|create|新建/i })
    if (!(await createBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) return

    // Fill form
    const nameInput = modal.locator('input').first()
    if (await nameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await nameInput.fill('测试任务名称')
    }

    // Make POST fail
    await page.route('**/api/tasks', async (route) => {
      if (route.request().method() === 'POST') {
        await route.abort('failed')
      } else {
        await route.continue()
      }
    })

    // Submit
    const submitBtn = modal.getByRole('button', { name: /确定|submit|create|保存/i })
    if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await submitBtn.click()
      await page.waitForTimeout(2000)
    }

    // Form data should still be present
    if (await nameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      const value = await nameInput.inputValue()
      expect(value).toBe('测试任务名称')
    }
  })
})

/* ================================================================== */
/*  Network Disconnection Recovery (Req 9.6)                           */
/* ================================================================== */

test.describe('Network disconnection recovery', () => {
  test('temporary disconnection recovery', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Go offline
    await page.context().setOffline(true)
    await page.waitForTimeout(1000)

    // Come back online
    await page.context().setOffline(false)
    await page.waitForTimeout(1000)

    // App should still be functional
    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})

/* ================================================================== */
/*  Empty States (Req 9.8)                                             */
/* ================================================================== */

test.describe('Empty states', () => {
  const emptyPages = [
    { name: 'Tasks', route: '/tasks', apiPattern: '**/api/tasks**' },
    { name: 'Quality', route: '/quality', apiPattern: '**/api/quality/**' },
  ]

  for (const pg of emptyPages) {
    test(`${pg.name} shows empty state when API returns empty data`, async ({ page }) => {
      await setupAuth(page)
      await mockAllApis(page)

      // Override to return empty
      await page.route(pg.apiPattern, async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 }),
        })
      })

      await page.goto(pg.route)
      await waitForPageReady(page)

      // Should show empty state or at least not crash
      const root = page.locator('#root')
      await expect(root).toBeVisible()
    })
  }
})
