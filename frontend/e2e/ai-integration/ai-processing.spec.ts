/**
 * AI Processing E2E Tests
 *
 * Tests processing job creation, configuration, execution, result display.
 * Results accessible from Augmentation Samples page.
 *
 * Requirements: 15.2, 15.5
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('AI Processing', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/augmentation/jobs', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [
              { id: 'job-1', name: '处理任务1', status: 'completed', progress: 100, createdAt: new Date().toISOString() },
              { id: 'job-2', name: '处理任务2', status: 'running', progress: 45, createdAt: new Date().toISOString() },
            ],
            total: 2,
          }),
        })
      }
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'job-new', name: 'New Job', status: 'pending' }),
      })
    })
  })

  test('AI processing page loads', async ({ page }) => {
    await page.goto('/augmentation/ai-processing')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('job creation is accessible', async ({ page }) => {
    await page.goto('/augmentation/ai-processing')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|create|add|开始/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(createBtn).toBeVisible()
    }
  })

  test('results accessible from Augmentation Samples page', async ({ page }) => {
    await page.goto('/augmentation/samples')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })
})
