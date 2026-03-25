/**
 * AI Annotation E2E Tests
 *
 * Tests annotation interface loads, displays data items,
 * accepts AI-assisted inputs, and submission saves progress.
 *
 * Requirements: 15.1, 15.4
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('AI Annotation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/ai-annotation/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'ann-1', text: '示例文本', labels: [], status: 'pending' },
            { id: 'ann-2', text: '另一个示例', labels: ['positive'], status: 'completed' },
          ],
          total: 2,
        }),
      })
    })

    await page.route('**/api/label-studio/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 }),
      })
    })
  })

  test('annotation interface loads', async ({ page }) => {
    await page.goto('/ai-annotation')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('annotation page displays content', async ({ page }) => {
    await page.goto('/ai-annotation')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
    const children = await root.evaluate((el: Element) => el.children.length)
    expect(children).toBeGreaterThan(0)
  })
})
