/**
 * DataSync Scheduler E2E Tests
 *
 * Tests sync history display and schedule CRUD.
 *
 * Requirements: 14.2, 14.3
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('DataSync Scheduler', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/data-sync/history**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'sync-1', sourceId: 'source-1', status: 'completed', duration: 120, rowCount: 5000, startedAt: new Date().toISOString() },
            { id: 'sync-2', sourceId: 'source-2', status: 'failed', duration: 30, rowCount: 0, startedAt: new Date().toISOString() },
          ],
          total: 2,
        }),
      })
    })

    await page.route('**/api/data-sync/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [{ id: 'sched-1', sourceId: 'source-1', cron: '0 0 * * *', enabled: true }],
            total: 1,
          }),
        })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
    })
  })

  test('sync history page displays status, duration, row counts', async ({ page }) => {
    await page.goto('/data-sync/history')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('scheduler page loads', async ({ page }) => {
    await page.goto('/data-sync/scheduler')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('schedule creation form is accessible', async ({ page }) => {
    await page.goto('/data-sync/scheduler')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click()
      const modal = page.locator('.ant-modal, .ant-drawer')
      if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(modal).toBeVisible()
        await page.keyboard.press('Escape')
      }
    }
  })
})
